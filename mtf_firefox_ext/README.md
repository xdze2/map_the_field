# mtf_firefox_ext

Firefox sidebar extension for the map_the_field job search triage workflow.
Companion to the Flask screening app (`tools/screening_app.py`, port 5001).

See also: `backlog/firefox_extension_poc.md` for architecture decisions and options evaluated.

## Current state

- Sidebar opens, shows current tab URL
- Ping button hits `localhost:5001` and reports the HTTP status
- Capture button grabs full page HTML via content script, POSTs to Flask `/capture`
- Flask saves to `data/web_scraps/{hash}_{slug}/page.html` + `meta.json`

## Files

| File | Role |
|---|---|
| `manifest.json` | MV2 manifest — declares sidebar, activeTab permission, localhost host_permission |
| `sidebar.html` | Sidebar UI |
| `sidebar.js` | Sidebar logic — tabs API, Flask fetch |
| `icon.svg` | Extension icon |

## Dev setup

**Launch dedicated Firefox profile** (profile dir must exist first):
```bash
mkdir -p ~/.mozilla/firefox/map_the_field
firefox --profile ~/.mozilla/firefox/map_the_field --no-remote
```
`--no-remote` forces a new window even if Firefox is already open. Keep this instance separate from normal browsing — extension is installed here only.

**Load extension:**
1. `about:debugging` → This Firefox → Load Temporary Add-on → select `manifest.json`
2. Sidebar: View → Sidebar → Map the Field
3. To reload after code changes: `about:debugging` → Reload button

**Flask backend:**
```bash
source tools/venv/bin/activate
python tools/screening_app.py
```
Must be running for the ping button to work. CORS is set to `*` in `after_request` hook.

## Key technical notes

- **MV2** (not MV3) — simpler, better supported in Firefox today; persistent background page instead of service worker
- **CORS**: Flask needs `Access-Control-Allow-Origin: *` — wildcard origin strings like `moz-extension://*` are not valid in that header
- **host_permissions** in MV2: add `"http://localhost:5001/*"` to the `permissions` array if manifest reload complains about `host_permissions`
- Content scripts (for page scraping) require `tabs` permission and explicit `executeScript` calls — not yet implemented

## Planned next steps

1. `/current` Flask endpoint → sidebar displays current company (name, URL, description)
2. Content script POC — `document.body.innerText` → message passing → sidebar
3. Status buttons (PURSUE / WATCH / PASS / LATER) → POST to Flask → `status.csv`
4. Notes textarea with autosave to `notes.jsonl`
