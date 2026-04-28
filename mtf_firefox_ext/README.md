# mtf_firefox_ext

Firefox sidebar extension for the map_the_field job search triage workflow.
Companion to the Flask screening app (`tools/screening_app.py`, port 5001).

See also: `backlog/firefox_extension_poc.md` for architecture decisions and options evaluated.

## Current state

- Sidebar opens, shows current tab URL
- Ping button hits `localhost:5001` and reports the HTTP status
- Capture button grabs full page HTML via content script, POSTs to Flask `/capture`
- Flask saves to `data/web_scraps/{hash}_{slug}/`: `page.html` + `content.md` (trafilatura) + `meta.json`

## Files

| File | Role |
|---|---|
| `manifest.json` | MV2 manifest — declares sidebar, activeTab permission, localhost host_permission |
| `sidebar.html` | Sidebar UI |
| `sidebar.js` | Sidebar logic — tabs API, Flask fetch |
| `icon.svg` | Extension icon |


## Key technical notes

- **MV2** (not MV3) — simpler, better supported in Firefox today; persistent background page instead of service worker
- **CORS**: Flask needs `Access-Control-Allow-Origin: *` — wildcard origin strings like `moz-extension://*` are not valid in that header
- **host_permissions** in MV2: add `"http://localhost:5001/*"` to the `permissions` array if manifest reload complains about `host_permissions`
- Content scripts require `tabs` + `<all_urls>` permissions for `executeScript` to work from the sidebar (`activeTab` alone is not enough — it only works from toolbar button clicks)
- Tab tracking: `currentTab` is updated via `onActivated` + `onUpdated` listeners across all windows; `currentWindow: true` would wrongly resolve to the sidebar's own window
- trafilatura may return `None` on heavy JS-rendered pages — `meta.json` flags this with `"has_markdown": false`

## Planned next steps

1. `/current` Flask endpoint → sidebar displays current company (name, URL, description)
2. Status buttons (PURSUE / WATCH / PASS / LATER) → POST to Flask → `status.csv`
3. Notes textarea with autosave to `notes.jsonl`
