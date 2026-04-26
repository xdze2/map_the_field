"""
Screening app — browse company summaries one by one.
Usage: python tools/screening_app.py
"""

import glob
import os
from pathlib import Path

import yaml
from flask import Flask, jsonify, render_template_string, request

SUMMARIES_DIR = Path(__file__).parent.parent / "data/company_data/company_summaries"

app = Flask(__name__)


def load_summaries():
    files = sorted(glob.glob(str(SUMMARIES_DIR / "*.yaml")))
    summaries = []
    for f in files:
        with open(f) as fh:
            data = yaml.safe_load(fh)
            data["_file"] = os.path.basename(f)
            summaries.append(data)
    return summaries


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
  #counter { color: #a6adc8; font-size: 13px; }

  #main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  /* LEFT PANEL */
  #left {
    width: 380px;
    min-width: 280px;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-right: 1px solid #ddd;
    overflow: hidden;
  }
  #info {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }
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
  .badge-good { background: #d1fae5; color: #065f46; }
  .badge-maybe { background: #fef3c7; color: #92400e; }
  .badge-weak { background: #fee2e2; color: #991b1b; }
  .badge-type { background: #e0e7ff; color: #3730a3; }
  .summary-text { line-height: 1.5; color: #333; margin: 10px 0; }
  .keywords { color: #888; font-size: 12px; margin-bottom: 12px; }

  .section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #999; margin: 12px 0 6px; letter-spacing: 0.05em; }
  .link-list { list-style: none; }
  .link-list li { margin-bottom: 5px; }
  .link-list a {
    color: #2563eb;
    text-decoration: none;
    font-size: 12px;
    cursor: pointer;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .link-list a:hover { text-decoration: underline; }
  .link-list .snippet { color: #666; font-size: 11px; margin-top: 2px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .best-url-marker { font-size: 10px; color: #059669; font-weight: 600; margin-left: 4px; }
  .url-dim { color: #aaa; }
  .url-host { color: #1d4ed8; font-weight: 500; }

  #bottom {
    padding: 12px 16px;
    border-top: 1px solid #eee;
    background: #fafafa;
    flex-shrink: 0;
  }
  #comment {
    width: 100%;
    height: 64px;
    resize: none;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
    font-family: inherit;
  }
  #comment:focus { outline: none; border-color: #2563eb; }
  .actions { display: flex; gap: 8px; margin-top: 8px; }
  .btn {
    padding: 7px 14px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
  }
  .btn-skip { background: #e5e7eb; color: #374151; flex: 1; }
  .btn-prev { background: #e5e7eb; color: #374151; }
  .btn-skip:hover { background: #d1d5db; }
  .btn-prev:hover { background: #d1d5db; }

  /* RIGHT PANEL */
  #right {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: #f9f9f9;
  }
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
  #current-url {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #2563eb;
  }
  #open-tab {
    text-decoration: none;
    color: #2563eb;
    font-size: 12px;
    white-space: nowrap;
  }
  #preview {
    flex: 1;
    border: none;
    background: #fff;
  }
  #iframe-blocked {
    display: none;
    flex: 1;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 12px;
    color: #666;
    font-size: 14px;
  }
  #iframe-blocked a { color: #2563eb; }
</style>
</head>
<body>

<div id="toolbar">
  <strong>Company Screening</strong>
  <span id="counter"></span>
</div>

<div id="main">
  <div id="left">
    <div id="info"></div>
    <div id="bottom">
      <textarea id="comment" placeholder="Notes, accuracy, interest…"></textarea>
      <div class="actions">
        <button class="btn btn-prev" onclick="go(-1)">&#8592; Prev</button>
        <button class="btn btn-skip" onclick="go(1)">Next &#8594;</button>
      </div>
    </div>
  </div>

  <div id="right">
    <div id="iframe-bar">
      <span id="current-url">—</span>
      <a id="open-tab" href="#" target="_blank">open in tab ↗</a>
    </div>
    <iframe id="preview" src="about:blank"></iframe>
    <div id="iframe-blocked">
      <span>This site blocks embedding.</span>
      <a id="blocked-link" href="#" target="_blank">Open in new tab ↗</a>
    </div>
  </div>
</div>

<script>
  function formatUrl(url) {
    try {
      const u = new URL(url);
      const dim = s => `<span class="url-dim">${s}</span>`;
      const bold = s => `<span class="url-host">${s}</span>`;
      const scheme = dim(u.protocol + '//');
      // split off subdomain(s) from registrable domain (last two parts)
      const parts = u.hostname.split('.');
      const main = parts.length > 2 ? parts.slice(-2).join('.') : u.hostname;
      const sub = parts.length > 2 ? dim(parts.slice(0, -2).join('.') + '.') : '';
      const rest = dim((u.pathname === '/' ? '' : u.pathname) + u.search + u.hash);
      return scheme + sub + bold(main) + rest;
    } catch {
      return url;
    }
  }

  const companies = {{ companies|tojson }};
  let idx = 0;

  function confidence_class(c) {
    return { good: 'badge-good', maybe: 'badge-maybe', weak: 'badge-weak' }[c] || 'badge-maybe';
  }

  function render(i) {
    const c = companies[i];
    const co = c.company;
    const s = c.summary;
    const best = s.best_url || '';

    document.getElementById('counter').textContent = `${i + 1} / ${companies.length}`;
    document.getElementById('comment').value = '';

    const links = (c.search_results || []).map(r => {
      const isBest = r.url === best;
      return `<li>
        <a onclick="loadUrl('${r.url.replace(/'/g, "\\'")}')" title="${r.title || ''}">
          ${formatUrl(r.url)}${isBest ? '<span class="best-url-marker">★ best</span>' : ''}
        </a>
        <div class="snippet">${r.snippet || ''}</div>
      </li>`;
    }).join('');

    document.getElementById('info').innerHTML = `
      <div class="company-name">${co.name}</div>
      <div class="meta">${co.city}${co.postal_code ? ' (' + co.postal_code + ')' : ''} · ${co.size_category} · ${co.naf_label} (${co.naf_code})</div>
      <span class="badge ${confidence_class(s.confidence)}">${s.confidence}</span>
      ${s.type ? `<span class="badge badge-type">${s.type}</span>` : ''}
      <div class="summary-text">${s.summary || '<em>No summary</em>'}</div>
      <div class="keywords">🏷 ${(s.keywords || '').toString()}</div>
      <div class="section-title">Search results</div>
      <ul class="link-list">${links}</ul>
    `;

    loadUrl(best || '');
  }

  function loadUrl(url) {
    if (!url) {
      document.getElementById('preview').src = 'about:blank';
      document.getElementById('current-url').textContent = '—';
      document.getElementById('open-tab').href = '#';
      return;
    }
    document.getElementById('current-url').textContent = url;
    document.getElementById('open-tab').href = url;
    document.getElementById('blocked-link').href = url;
    document.getElementById('preview').src = url;
  }

  function go(dir) {
    idx = Math.max(0, Math.min(companies.length - 1, idx + dir));
    render(idx);
  }

  // keyboard nav
  document.addEventListener('keydown', e => {
    if (document.activeElement === document.getElementById('comment')) return;
    if (e.key === 'ArrowRight' || e.key === 'n') go(1);
    if (e.key === 'ArrowLeft'  || e.key === 'p') go(-1);
  });

  render(0);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    companies = []
    for s in SUMMARIES:
        co = s.get("company", {})
        co.setdefault("postal_code", s.get("meta", {}).get("postal_code", ""))
        companies.append({
            "company": co,
            "summary": s.get("summary", {}),
            "search_results": s.get("search_results", []),
            "_file": s.get("_file", ""),
        })
    return render_template_string(TEMPLATE, companies=companies)


if __name__ == "__main__":
    print(f"Loaded {len(SUMMARIES)} summaries from {SUMMARIES_DIR}")
    app.run(debug=True, port=5001)
