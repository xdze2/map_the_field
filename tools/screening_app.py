"""
Map the Field — Flask backend.
Usage: python tools/screening_app.py
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

import trafilatura
from flask import Flask, jsonify, request, send_from_directory

ASSETS_DIR     = Path(__file__).parent / "assets"
EXT_DIR        = Path(__file__).parent.parent / "mtf_firefox_ext"
NODES_DIR      = Path(__file__).parent.parent / "data/nodes"
INDEX_FILE     = NODES_DIR / "index.jsonl"

app = Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ── Static assets ──────────────────────────────────────────────────────────────

@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/")
def web_ui_index():
    return send_from_directory(EXT_DIR, "sidebar.html")


@app.route("/sidebar.js")
def web_ui_js():
    return send_from_directory(EXT_DIR, "sidebar.js")


@app.route("/marked.min.js")
def web_ui_marked():
    return send_from_directory(EXT_DIR, "marked.min.js")


@app.route("/codemirror.min.js")
def web_ui_cm_js():
    return send_from_directory(EXT_DIR, "codemirror.min.js")


@app.route("/codemirror.min.css")
def web_ui_cm_css():
    return send_from_directory(EXT_DIR, "codemirror.min.css")


@app.route("/codemirror-markdown.min.js")
def web_ui_cm_md():
    return send_from_directory(EXT_DIR, "codemirror-markdown.min.js")


@app.route("/codemirror-yaml.min.js")
def web_ui_cm_yaml():
    return send_from_directory(EXT_DIR, "codemirror-yaml.min.js")


@app.route("/codemirror-overlay.min.js")
def web_ui_cm_overlay():
    return send_from_directory(EXT_DIR, "codemirror-overlay.min.js")


@app.route("/codemirror-yaml-frontmatter.min.js")
def web_ui_cm_yaml_fm():
    return send_from_directory(EXT_DIR, "codemirror-yaml-frontmatter.min.js")


@app.route("/<filename>.png")
def web_ui_png(filename):
    """Rank icon images requested by the web UI."""
    return send_from_directory(EXT_DIR, f"{filename}.png")


# ── Node API ───────────────────────────────────────────────────────────────────

@app.route("/nodes")
def nodes():
    if not INDEX_FILE.exists():
        return jsonify([])
    entries = []
    with open(INDEX_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    sort_by = request.args.get("sort", "unranked")
    rank_labels = {1: "Hell no", 2: "Not interested", 3: "What?", 4: "Boring", 5: "Interested", 6: "Excited"}
    for e in entries:
        e["rank_label"] = rank_labels.get(e.get("current_rank")) if e.get("current_rank") else None

    if sort_by == "rank_asc":
        entries.sort(key=lambda e: (e["current_rank"] is None, e["current_rank"] or 0))
    elif sort_by == "rank_desc":
        entries.sort(key=lambda e: (e["current_rank"] is None, -(e["current_rank"] or 0)))
    elif sort_by == "updated":
        entries.sort(key=lambda e: e.get("updated_at", ""), reverse=True)
    else:  # unranked first
        entries.sort(key=lambda e: (e["current_rank"] is not None, e.get("updated_at", "")))

    return jsonify(entries)


@app.route("/nodes/<node_id>")
def node_detail(node_id):
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404

    meta = json.loads((node_dir / "meta.json").read_text())

    summaries = sorted((node_dir / "summary_history").glob("summary_*.md"))
    summary_md = summaries[-1].read_text() if summaries else ""
    summary_file = summaries[-1].name if summaries else None

    triage_entries = []
    triage_file = node_dir / "triage.jsonl"
    if triage_file.exists():
        for line in triage_file.read_text().splitlines():
            line = line.strip()
            if line:
                triage_entries.append(json.loads(line))
    current_rank = triage_entries[-1].get("rank") if triage_entries else None

    sources = []
    for f in sorted((node_dir / "sources").glob("*.json")):
        try:
            s = json.loads(f.read_text())
            s["_file"] = f.name
            sources.append(s)
        except Exception:
            pass

    return jsonify({
        "node_id": node_id,
        "meta": meta,
        "summary_md": summary_md,
        "summary_file": summary_file,
        "current_rank": current_rank,
        "triage": triage_entries,
        "sources": sources,
    })


@app.route("/nodes/<node_id>/rank", methods=["POST", "OPTIONS"])
def node_rank(node_id):
    if request.method == "OPTIONS":
        return "", 204
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    rank = data.get("rank")
    note = data.get("note", "")
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "rank": rank, "note": note}
    with open(node_dir / "triage.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _update_index_entry(node_id, current_rank=rank)
    return jsonify({"ok": True, "rank": rank, "entry": entry})


@app.route("/nodes/<node_id>/summary", methods=["POST", "OPTIONS"])
def node_summary(node_id):
    if request.method == "OPTIONS":
        return "", 204
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    content = data.get("content", "")
    author = data.get("author", "user")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"summary_{ts}_{author}.md"
    (node_dir / "summary_history" / filename).write_text(content, encoding="utf-8")
    triage_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "action": "summary", "author": author}
    with open(node_dir / "triage.jsonl", "a") as f:
        f.write(json.dumps(triage_entry, ensure_ascii=False) + "\n")
    frontmatter = _parse_frontmatter(content)
    _update_index_entry(node_id, updated_at=ts, **frontmatter)
    return jsonify({"ok": True, "file": filename})


@app.route("/nodes/<node_id>/capture", methods=["POST", "OPTIONS"])
def node_capture(node_id):
    if request.method == "OPTIONS":
        return "", 204
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    url = data.get("url", "")
    html = data.get("html", "")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    parsed = urlparse(url)
    slug = re.sub(r"[^a-z0-9]+", "-", (parsed.netloc + parsed.path).lower()).strip("-")[:40]
    base = f"{url_hash}_{slug}_{ts}"
    sources_dir = node_dir / "sources"
    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
    if markdown:
        (sources_dir / f"{base}.md").write_text(markdown, encoding="utf-8")
    meta = {"url": url, "captured_at": datetime.now(timezone.utc).isoformat(),
            "has_markdown": markdown is not None, "status": "good"}
    (sources_dir / f"{base}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "file": base, "has_markdown": markdown is not None,
                    "source": {"url": url, "captured_at": meta["captured_at"], "_file": f"{base}.json"}})


@app.route("/nodes/<node_id>/history")
def node_history(node_id):
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404
    triage_entries = []
    triage_file = node_dir / "triage.jsonl"
    if triage_file.exists():
        for line in triage_file.read_text().splitlines():
            line = line.strip()
            if line:
                triage_entries.append(json.loads(line))
    current_rank = triage_entries[-1].get("rank") if triage_entries else None
    sources = []
    for f in sorted((node_dir / "sources").glob("*.json")):
        try:
            s = json.loads(f.read_text())
            s["_file"] = f.name
            sources.append(s)
        except Exception:
            pass
    return jsonify({"triage": triage_entries, "current_rank": current_rank, "sources": sources})


def _parse_frontmatter(content):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _update_index_entry(node_id, current_rank=None, updated_at=None, **fields):
    if not INDEX_FILE.exists():
        return
    lines = INDEX_FILE.read_text().splitlines()
    new_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if entry["node_id"] == node_id:
            if current_rank is not None:
                entry["current_rank"] = current_rank
            if updated_at is not None:
                entry["updated_at"] = updated_at
            entry.update(fields)
        new_lines.append(json.dumps(entry, ensure_ascii=False))
    INDEX_FILE.write_text("\n".join(new_lines) + "\n")


if __name__ == "__main__":
    print(f"Nodes dir: {NODES_DIR}")
    print("Web UI: http://localhost:5001/")
    app.run(debug=True, port=5001)
