"""
Screening app — browse company summaries one by one.
Usage: python tools/screening_app.py
"""

import glob
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import trafilatura
import yaml
from flask import Flask, jsonify, render_template_string, request, send_from_directory

SUMMARIES_DIR  = Path(__file__).parent.parent / "data/company_data/company_summaries"
TRIAGE_DIR     = Path(__file__).parent.parent / "data/company_data/triage"
ASSETS_DIR     = Path(__file__).parent / "assets"
WEB_SCRAPS_DIR = Path(__file__).parent.parent / "data/web_scraps"
NODES_DIR      = Path(__file__).parent.parent / "data/nodes"
INDEX_FILE     = NODES_DIR / "index.jsonl"
TRIAGE_DIR.mkdir(parents=True, exist_ok=True)
WEB_SCRAPS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/capture", methods=["POST", "OPTIONS"])
def capture():
    if request.method == "OPTIONS":
        return "", 204
    data = request.get_json()
    url = data.get("url", "")
    html = data.get("html", "")

    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    parsed = urlparse(url)
    slug = re.sub(r"[^a-z0-9]+", "-", (parsed.netloc + parsed.path).lower()).strip("-")[:60]
    dirname = f"{url_hash}_{slug}"
    dest = WEB_SCRAPS_DIR / dirname
    dest.mkdir(parents=True, exist_ok=True)

    (dest / "page.html").write_text(html, encoding="utf-8")

    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
    if markdown:
        (dest / "content.md").write_text(markdown, encoding="utf-8")

    meta = {"url": url, "captured_at": datetime.now(timezone.utc).isoformat(), "has_markdown": markdown is not None}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return jsonify({"path": str(dest.relative_to(Path(__file__).parent.parent))})


def load_summaries():
    files = sorted(glob.glob(str(SUMMARIES_DIR / "*.yaml")))
    summaries = []
    for f in files:
        with open(f) as fh:
            data = yaml.safe_load(fh)
            data["_file"] = os.path.basename(f)
            summaries.append(data)
    return summaries


def load_triage(siren):
    path = TRIAGE_DIR / f"{siren}.jsonl"
    if not path.exists():
        return None
    entries = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries[-1] if entries else None


SUMMARIES = load_summaries()

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Company Screening</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; height: 100vh; display: flex; flex-direction: column; background: #f4f4f4; }

  #toolbar {
    padding: 8px 16px;
    background: #1e1e2e;
    color: #cdd6f4;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }
  #toolbar strong { font-size: 15px; }
  #counter { color: #a6adc8; font-size: 13px; margin-right: auto; }
  #saved-indicator { font-size: 12px; color: #a6e3a1; opacity: 0; transition: opacity 0.4s; }
  #saved-indicator.show { opacity: 1; }

  #main { display: flex; flex: 1; overflow: hidden; }

  /* LEFT PANEL */
  #left {
    width: 520px;
    min-width: 380px;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-right: 1px solid #ddd;
    overflow: hidden;
  }
  #info { flex: 1; overflow-y: auto; padding: 16px; }

  .company-name { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
  .meta { color: #666; font-size: 12px; margin-bottom: 12px; }
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 4px;
    margin-bottom: 6px;
  }
  .badge-good  { background: #d1fae5; color: #065f46; }
  .badge-maybe { background: #fef3c7; color: #92400e; }
  .badge-weak  { background: #fee2e2; color: #991b1b; }
  .badge-type  { background: #e0e7ff; color: #3730a3; }
  .summary-text { line-height: 1.5; color: #333; margin: 10px 0; }
  .keywords { color: #888; font-size: 12px; margin-bottom: 12px; }

  .section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #999; margin: 12px 0 6px; letter-spacing: 0.05em; }

  .link-row { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 7px; }
  .link-row a {
    color: #2563eb;
    text-decoration: none;
    font-size: 12px;
    cursor: pointer;
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .link-row a:hover { text-decoration: underline; }
  .url-rating { display: flex; gap: 3px; flex-shrink: 0; }
  .url-rating button {
    border: 1px solid #e5e7eb;
    background: #f9fafb;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    padding: 1px 5px;
    line-height: 1.4;
    opacity: 0.5;
    transition: opacity 0.15s, background 0.15s;
  }
  .url-rating button:hover { opacity: 1; }
  .url-rating button.active-good  { background: #d1fae5; border-color: #6ee7b7; opacity: 1; }
  .url-rating button.active-wrong { background: #fee2e2; border-color: #fca5a5; opacity: 1; }
  .snippet { color: #666; font-size: 11px; margin-top: 2px; margin-left: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .best-url-marker { font-size: 10px; color: #059669; font-weight: 600; margin-left: 4px; }
  .url-dim  { color: #aaa; }
  .url-host { color: #1d4ed8; font-weight: 500; }

  /* BOTTOM TRIAGE PANEL */
  #bottom {
    padding: 12px 16px;
    border-top: 1px solid #eee;
    background: #fafafa;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Vibe */
  .vibe-buttons { display: flex; gap: 6px; }
  .vibe-btn {
    flex: 1;
    padding: 4px;
    border: 3px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    background: #f1f5f9;
    transition: all 0.15s;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
  }
  .vibe-btn img { width: 42px; height: 42px; object-fit: contain; display: block; }
  .vibe-btn span { font-size: 9px; color: #64748b; line-height: 1.2; text-align: center; }
  .vibe-btn:hover { transform: scale(1.08); background: #e2e8f0; }
  .vibe-btn.selected { border-color: #6366f1; background: #eef2ff; transform: scale(1.08); }
  .vibe-btn.selected span { color: #4338ca; font-weight: 700; }

  textarea#comment {
    width: 100%;
    height: 56px;
    resize: none;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
    font-family: inherit;
  }
  textarea#comment:focus { outline: none; border-color: #2563eb; }

  .nav-buttons { display: flex; gap: 8px; }
  .btn { padding: 7px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 600; }
  .btn-prev { background: #e5e7eb; color: #374151; }
  .btn-prev:hover { background: #d1d5db; }
  .btn-save { background: #2563eb; color: #fff; flex: 1; }
  .btn-save:hover { background: #1d4ed8; }
  .btn-next { background: #e5e7eb; color: #374151; }
  .btn-next:hover { background: #d1d5db; }

  /* RIGHT PANEL */
  #right { flex: 1; display: flex; flex-direction: column; background: #f9f9f9; }
  #iframe-bar {
    padding: 6px 12px;
    background: #f1f5f9;
    border-bottom: 1px solid #ddd;
    font-size: 12px;
    color: #555;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  #current-url { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #2563eb; }
  #open-tab { text-decoration: none; color: #2563eb; font-size: 12px; white-space: nowrap; }
  #preview { flex: 1; border: none; background: #fff; }
</style>
</head>
<body>

<div id="toolbar">
  <strong>Company Screening</strong>
  <span id="counter"></span>
  <span id="saved-indicator">✓ saved</span>
</div>

<div id="main">
  <div id="left">
    <div id="info"></div>

    <div id="bottom">
      <div>
        <div class="section-title">Vibe</div>
        <div class="vibe-buttons">
          <button class="vibe-btn" data-vibe="1" onclick="setVibe(1)" title="Hell no — run away from this">
            <img src="/assets/1_nope.png" alt="Hell no"><span>Hell no</span>
          </button>
          <button class="vibe-btn" data-vibe="2" onclick="setVibe(2)" title="Not interested, but no offense">
            <img src="/assets/2_skip_it.png" alt="Skip it"><span>Skip it</span>
          </button>
          <button class="vibe-btn" data-vibe="3" onclick="setVibe(3)" title="What? Not enough data to judge">
            <img src="/assets/3_what.png" alt="What?"><span>What?</span>
          </button>
          <button class="vibe-btn" data-vibe="4" onclick="setVibe(4)" title="Boring, but keep it">
            <img src="/assets/4_keep_it.png" alt="Keep it"><span>Keep it</span>
          </button>
          <button class="vibe-btn" data-vibe="5" onclick="setVibe(5)" title="Interested — tell me more">
            <img src="/assets/5_interested.png" alt="Interested"><span>Interested</span>
          </button>
          <button class="vibe-btn" data-vibe="6" onclick="setVibe(6)" title="Excited — let's go now!">
            <img src="/assets/6_excited.png" alt="Excited"><span>Excited!</span>
          </button>
        </div>
      </div>

      <textarea id="comment" placeholder="Notes, observations, questions…"></textarea>

      <div class="nav-buttons">
        <button class="btn btn-prev" onclick="go(-1)">&#8592; Prev</button>
        <button class="btn btn-save" onclick="save()">Save</button>
        <button class="btn btn-next" onclick="saveAndNext()">Save &amp; Next &#8594;</button>
      </div>
    </div>
  </div>

  <div id="right">
    <div id="iframe-bar">
      <span id="current-url">—</span>
      <a id="open-tab" href="#" target="_blank">open in tab ↗</a>
    </div>
    <iframe id="preview" src="about:blank"></iframe>
  </div>
</div>

<script>
  const VIBE_LABELS = { 1: 'hell_no', 2: 'skip_it', 3: 'what', 4: 'keep_it', 5: 'interested', 6: 'excited' };

  function formatUrl(url) {
    try {
      const u = new URL(url);
      const dim  = s => `<span class="url-dim">${s}</span>`;
      const bold = s => `<span class="url-host">${s}</span>`;
      const parts = u.hostname.split('.');
      const main  = parts.length > 2 ? parts.slice(-2).join('.') : u.hostname;
      const sub   = parts.length > 2 ? dim(parts.slice(0, -2).join('.') + '.') : '';
      const rest  = dim((u.pathname === '/' ? '' : u.pathname) + u.search + u.hash);
      return dim(u.protocol + '//') + sub + bold(main) + rest;
    } catch { return url; }
  }

  const companies = {{ companies|tojson }};
  let idx = 0;
  let state = {};        // { vibe, urlRatings }
  let visitedUrls = [];

  function confidence_class(c) {
    return { good: 'badge-good', maybe: 'badge-maybe', weak: 'badge-weak' }[c] || 'badge-maybe';
  }

  function setVibe(v) {
    state.vibe = (state.vibe === v) ? null : v;
    document.querySelectorAll('.vibe-btn').forEach(b => {
      b.classList.toggle('selected', parseInt(b.dataset.vibe) === state.vibe);
    });
  }

  function setUrlRating(url, rating) {
    if (!state.urlRatings) state.urlRatings = {};
    state.urlRatings[url] = (state.urlRatings[url] === rating) ? null : rating;
    refreshUrlRatings();
  }

  function refreshUrlRatings() {
    document.querySelectorAll('.url-rating button').forEach(b => {
      const url    = b.closest('[data-url]').dataset.url;
      const rating = b.dataset.rating;
      const cur    = state.urlRatings?.[url];
      b.className  = cur === rating ? `active-${rating}` : '';
    });
  }

  function render(i) {
    const c  = companies[i];
    const co = c.company;
    const s  = c.summary;
    const best = s.best_url || '';

    // reset state, then load saved triage if any
    state = { vibe: null, urlRatings: {} };
    visitedUrls = [];
    const saved = c._triage;
    if (saved) {
      state.vibe       = saved.vibe || null;
      state.urlRatings = saved.url_ratings || {};
      document.getElementById('comment').value = saved.note || '';
    } else {
      document.getElementById('comment').value = '';
    }

    // update toolbar
    const reviewed = companies.filter(x => x._triage).length;
    document.getElementById('counter').textContent =
      `${i + 1} / ${companies.length}  ·  ${reviewed} reviewed`;

    // restore vibe buttons
    document.querySelectorAll('.vibe-btn').forEach(b => {
      b.classList.toggle('selected', parseInt(b.dataset.vibe) === state.vibe);
    });

    const links = (c.search_results || []).map(r => {
      const isBest = r.url === best;
      const safeUrl = r.url.replace(/"/g, '&quot;');
      return `<div class="link-row" data-url="${safeUrl}">
        <div style="flex:1;min-width:0">
          <a onclick="loadUrl('${r.url.replace(/'/g, "\\'")}', this)" title="${r.title || ''}">
            ${formatUrl(r.url)}${isBest ? '<span class="best-url-marker">★</span>' : ''}
          </a>
          <div class="snippet">${r.snippet || ''}</div>
        </div>
        <div class="url-rating">
          <button data-rating="good"  onclick="setUrlRating('${safeUrl}','good')"  title="Good URL">👍</button>
          <button data-rating="wrong" onclick="setUrlRating('${safeUrl}','wrong')" title="Wrong result">👎</button>
        </div>
      </div>`;
    }).join('');

    document.getElementById('info').innerHTML = `
      <div class="company-name">${co.name}</div>
      <div class="meta">${co.city}${co.postal_code ? ' (' + co.postal_code + ')' : ''} · ${co.size_category} · ${co.naf_label} (${co.naf_code})</div>
      <span class="badge ${confidence_class(s.confidence)}">${s.confidence}</span>
      ${s.type ? `<span class="badge badge-type">${s.type}</span>` : ''}
      <div class="summary-text">${s.summary || '<em>No summary</em>'}</div>
      <div class="keywords">🏷 ${(s.keywords || '').toString()}</div>
      <div class="section-title">Search results</div>
      ${links}
    `;

    refreshUrlRatings();
    loadUrl(best || '');
  }

  function loadUrl(url, linkEl) {
    if (!url) {
      document.getElementById('preview').src = 'about:blank';
      document.getElementById('current-url').textContent = '—';
      document.getElementById('open-tab').href = '#';
      return;
    }
    if (!visitedUrls.includes(url)) visitedUrls.push(url);
    document.getElementById('current-url').textContent = url;
    document.getElementById('open-tab').href = url;
    document.getElementById('preview').src = url;
  }

  async function save() {
    const c = companies[idx];
    const payload = {
      siren:        c.company.siren || c._siren,
      slug:         c._slug,
      note:         document.getElementById('comment').value,
      vibe:         state.vibe,
      vibe_label:   state.vibe ? VIBE_LABELS[state.vibe] : null,
      url_ratings:  state.urlRatings || {},
      visited_urls: visitedUrls,
    };
    const resp = await fetch('/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      c._triage = payload;  // update in-memory so counter reflects it
      const ind = document.getElementById('saved-indicator');
      ind.classList.add('show');
      setTimeout(() => ind.classList.remove('show'), 1500);
    }
  }

  async function saveAndNext() {
    await save();
    go(1);
  }

  function go(dir) {
    idx = Math.max(0, Math.min(companies.length - 1, idx + dir));
    render(idx);
  }

  document.addEventListener('keydown', e => {
    if (['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) return;
    if (e.key === 'ArrowRight' || e.key === 'n') go(1);
    if (e.key === 'ArrowLeft'  || e.key === 'p') go(-1);
    if (e.key === 's') save();
  });

  render(0);
</script>
</body>
</html>
"""


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/")
def index():
    companies = []
    for s in SUMMARIES:
        co   = s.get("company", {})
        meta = s.get("meta", {})
        co.setdefault("postal_code", meta.get("postal_code", ""))
        siren = str(meta.get("siren", ""))
        slug  = meta.get("slug", "")
        companies.append({
            "company":        co,
            "summary":        s.get("summary", {}),
            "search_results": s.get("search_results", []),
            "_file":          s.get("_file", ""),
            "_siren":         siren,
            "_slug":          slug,
            "_triage":        load_triage(siren),
        })
    return render_template_string(TEMPLATE, companies=companies)


@app.route("/save", methods=["POST"])
def save():
    data  = request.get_json()
    siren = data.get("siren") or data.get("_siren", "unknown")
    entry = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "siren":        siren,
        "slug":         data.get("slug", ""),
        "note":         data.get("note", ""),
        "vibe":         data.get("vibe"),
        "vibe_label":   data.get("vibe_label"),
        "url_ratings":  data.get("url_ratings", {}),
        "visited_urls": data.get("visited_urls", []),
    }
    path = TRIAGE_DIR / f"{siren}.jsonl"
    with open(path, "a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return jsonify({"ok": True})


@app.route("/nodes/<node_id>")
def node_detail(node_id):
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return jsonify({"error": "not found"}), 404

    meta = json.loads((node_dir / "meta.json").read_text())

    # current summary = latest file in summary_history/ by name sort
    summaries = sorted((node_dir / "summary_history").glob("summary_*.md"))
    summary_md = summaries[-1].read_text() if summaries else ""
    summary_file = summaries[-1].name if summaries else None

    # triage history
    triage_entries = []
    triage_file = node_dir / "triage.jsonl"
    if triage_file.exists():
        for line in triage_file.read_text().splitlines():
            line = line.strip()
            if line:
                triage_entries.append(json.loads(line))
    current_rank = triage_entries[-1].get("rank") if triage_entries else None

    # sources
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
    # update index
    _update_index_entry(node_id, current_rank=rank)
    return jsonify({"ok": True, "rank": rank})


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
    _update_index_entry(node_id, updated_at=ts)
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
    return jsonify({"ok": True, "file": base, "has_markdown": markdown is not None})


def _update_index_entry(node_id, current_rank=None, updated_at=None):
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
        new_lines.append(json.dumps(entry, ensure_ascii=False))
    INDEX_FILE.write_text("\n".join(new_lines) + "\n")


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


if __name__ == "__main__":
    print(f"Loaded {len(SUMMARIES)} summaries from {SUMMARIES_DIR}")
    app.run(debug=True, port=5001)
