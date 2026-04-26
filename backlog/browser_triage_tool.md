# Browser-integrated triage tool

## Context

The `screening_app.py` Flask app (tools/) works for reviewing company summaries,
but has a fundamental limitation: iframes are blocked by many sites (X-Frame-Options,
CSP). The current workaround is "open in tab", which breaks the integrated flow.

The deeper insight: **human judgment while browsing is very efficient**, and a
close integration between the browser and the AI/data layer is more valuable than
full autonomous scraping (which gets blocked anyway — Playwright is detectable).

## Ideal architecture

```
Firefox extension (sidebar, always visible)
  ├── sidebar UI        ← screening panel: company info, notes, actions
  ├── content script    ← reads current page DOM directly (no iframe limits)
  └── fetch to Flask    ← reads/writes YAMLs, calls LLM, updates status.csv

User browses normally in the main window → no anti-bot detection
```

Key advantage: content scripts run *inside* the real page, so cross-origin
restrictions don't apply. The Flask backend stays as the data/AI brain.

## Implementation path

1. `manifest.json` — declare sidebar + content script + localhost permissions
2. Sidebar HTML/JS — port the screening_app left panel
3. Content script — on demand, extract page text/links, send to sidebar
4. Message passing — `browser.runtime.sendMessage()` sidebar ↔ content script
5. `fetch('http://localhost:5001/...')` — read YAML data, post triage decisions
6. Firefox sideload via `about:debugging` (no signing needed during dev)

Estimated effort: 1-2 days for a working prototype, given existing Flask backend.

## Existing tools to evaluate first

- **WorldBrain Memex** — open source, local-first, sidebar + web annotation.
  Most promising: might be forkable/extensible rather than building from scratch.
  Repo: https://github.com/WorldBrain/Memex
- **Hypothesis** (hypothes.is) — open source annotation, local server mode.
  Could store triage notes as annotations attached to URLs.
- **Monica browser extension** — good architecture reference for sidebar+context pattern.

## Rejected approaches

- **Playwright sidecar** — gets blocked by Cloudflare, LinkedIn, etc.
- **PyWebView** — Python + embedded browser, interesting middle ground but
  no ecosystem, custom UI from scratch.
- **Raindrop/Hoarder/Omnivore** — bookmarking tools, no AI integration path.
- **Tampermonkey userscripts** — no persistent sidebar, limited for this workflow.

## Decision

Parking for now — Flask app is good enough for the current 41-company batch.
Revisit when the screening volume grows or iframe blocking becomes too painful.
Check Memex source before starting from scratch.
