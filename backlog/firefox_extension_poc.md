# Firefox Extension POC — Notes & Decisions

## Status
First hello-world extension working (sidebar + Flask ping). See `mtf_firefox_ext/`.

## Architecture validated
- Sidebar extension (MV2) with `browser.tabs` API
- Flask on `localhost:5001` with `Access-Control-Allow-Origin: *`
- Message passing: sidebar ↔ content script via `browser.runtime.sendMessage`

## Page capture — options evaluated

### Content script (recommended first attempt)
Inject JS into the active tab, grab DOM, send back to sidebar.
- Use `document.body.innerText` for quick POC
- Use [Readability.js](https://github.com/mozilla/readability) or [defuddle](https://github.com/kepano/defuddle) for clean article extraction (what Obsidian Clipper does)
- HTML → Markdown conversion happens inside the extension
- Risk: blocked by strict CSP on some sites

### Screenshot (`browser.tabs.captureVisibleTab`)
- Scriptable, returns PNG of visible viewport only
- Full-page requires scroll+stitch (complex)
- Not parseable as text — needs OCR or vision LLM
- Interesting fallback: send screenshot to Claude vision instead of parsing DOM
  → avoids bot detection since no JS injection

### Manual save + watchdog (tinkered fallback)
- User presses `Ctrl+S` manually (browser saves full HTML to `~/Downloads/`)
- Flask watches `~/Downloads/` with `watchdog` for new `.html` files
- Extension only needs to tell Flask "I'm on company X" — no JS injection
- Pros: zero bot detection risk, handles any site
- Cons: one manual step, file association relies on timing heuristic

### Print / Save as PDF
- `window.print()` opens dialog but output is not scriptable
- `browser.tabs.saveAsPDF()` exists but not stable in Firefox
- Dead end for automation.

### Server-side fetch (Flask requests)
- Flask fetches the URL directly with `requests`
- Blocked by Cloudflare, LinkedIn, etc.
- Only useful for simple/open sites.

## Recommended POC order
1. Content script + `innerText` — validate message passing pipeline
2. If blocked on target sites → manual save + watchdog
3. Screenshot + vision LLM — if structured text extraction fails and Claude vision is acceptable latency/cost

## Browser isolation — dedicated Firefox profile

**Decision: use a separate Firefox profile for map_the_field work.**

Rationale:
- Extension should not interfere with normal browsing (unrelated tabs, history, cookies)
- Dedicated profile = clean slate, only job search tabs open
- Better security isolation — extension permissions scoped to a throwaway profile
- Enables automation: the profile can be launched headlessly or scripted independently

Launch command:
```bash
firefox --profile ~/.mozilla/firefox/map_the_field --no-remote
```
`--no-remote` forces a new window even if Firefox is already open.
Install the extension only in that profile via `about:debugging`.

**Tab groups (`browser.tabGroups`, Firefox 131+):** evaluated but rejected for isolation.
Extensions can create/manage groups but can't prevent tabs from leaking out.
Better use case: organizing tabs *within* the workflow (e.g. "to review" vs "triaged").

## Tab tracking — known issue

`currentTab` is captured once at sidebar load and not updated on tab switches.
Fix: listen to `browser.tabs.onActivated` + `browser.tabs.onUpdated` to always track
the most recently active tab. Especially important in the two-window setup where
`currentWindow: true` may resolve to the sidebar window, not the browsing window.

## Next steps (not started)
- Fix tab tracking with `onActivated` listener
- `/current` endpoint on Flask — returns current company JSON to sidebar
- Sidebar displays company name, URL, one-liner
- Status buttons (PURSUE / WATCH / PASS / LATER) posting to Flask
- Notes textarea with autosave
