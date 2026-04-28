"""
Map the Field — Flask backend.
Usage: mtf-app  (or: python backend_app/screening_app.py)
"""

import json
from pathlib import Path

import trafilatura
from flask import Flask, jsonify, request, send_from_directory

from backend_app import node_store

ASSETS_DIR = Path(__file__).parent / "assets"
EXT_DIR    = Path(__file__).parent.parent / "firefox_ext"

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
    if not node_store.INDEX_FILE.exists():
        return jsonify([])
    entries = []
    for line in node_store.INDEX_FILE.read_text(encoding="utf-8").splitlines():
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
    node = node_store.read_node(node_id)
    if node is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(node)


@app.route("/nodes/<node_id>/rank", methods=["POST", "OPTIONS"])
def node_rank(node_id):
    if request.method == "OPTIONS":
        return "", 204
    if not (node_store.NODES_DIR / node_id).exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    rank = data.get("rank")
    note = data.get("note", "")
    entry = node_store.write_rank(node_id, rank, note)
    return jsonify({"ok": True, "rank": rank, "entry": entry})


@app.route("/nodes/<node_id>/summary", methods=["POST", "OPTIONS"])
def node_summary(node_id):
    if request.method == "OPTIONS":
        return "", 204
    if not (node_store.NODES_DIR / node_id).exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    content = data.get("content", "")
    author = data.get("author", "user")
    filename = node_store.write_summary(node_id, content, author)
    return jsonify({"ok": True, "file": filename})


@app.route("/nodes/<node_id>/capture", methods=["POST", "OPTIONS"])
def node_capture(node_id):
    if request.method == "OPTIONS":
        return "", 204
    if not (node_store.NODES_DIR / node_id).exists():
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    url = data.get("url", "")
    html = data.get("html", "")
    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
    captured_at = node_store.now_iso()
    meta = {"url": url, "captured_at": captured_at, "has_markdown": markdown is not None, "status": "good"}
    base = node_store.write_capture(node_id, url, markdown, meta)
    return jsonify({"ok": True, "file": base, "has_markdown": markdown is not None,
                    "source": {"url": url, "captured_at": captured_at, "_file": f"{base}.json"}})


@app.route("/nodes/<node_id>/history")
def node_history(node_id):
    node = node_store.read_node(node_id)
    if node is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"triage": node["triage"], "current_rank": node["current_rank"], "sources": node["sources"]})


def main():
    print(f"Nodes dir: {node_store.NODES_DIR}")
    print("Web UI: http://localhost:5001/")
    app.run(debug=True, port=5001)


if __name__ == "__main__":
    main()
