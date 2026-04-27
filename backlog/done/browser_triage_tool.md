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

## Specification

### Features

| Feature | Approach | Priority |
|---|---|---|
| Display formatted company data + links | Flask left panel | core |
| Open links without losing the app | side-by-side windows (Flask app + real browser) | core |
| Capture page content as markdown | bookmarklet → POST to Flask | nice-to-have |
| Capture page images | on-demand, optional | optional |
| Free-form notes | textarea, per company | core |
| Triage decision (structured status) | status buttons | core |
| Persist data in Python-readable format | append to CSV/JSONL | core |
| Progress tracking (reviewed / left / by status) | counter + filter bar | nice-to-have |
| Jump to company / search | dropdown or text filter | nice-to-have |
| Autosave draft notes | localStorage | nice-to-have |
| AI live feedback | TBD | optional |

### Triage decision states

The core output is a single status field per company, capturing energy investment intent:

- **PURSUE** — actively reach out, research contacts, prepare a pitch
- **WATCH** — interesting, revisit if it surfaces again
- **PASS** — not relevant, don't spend more time
- **LATER** — interesting but blocked by something external (timing, location, etc.)

Free-form notes carry the *why*; the status drives the *workflow*.

### Data format

User input (notes + status) should be appended to existing `data/company_data/insights/status.csv`
plus a companion `notes.jsonl` (one JSON object per save: siren, timestamp, notes, captured_text).
Both must be trivially readable from any Python script.

### "Two windows" architecture

No iframe needed. Flask app runs on port 5001 (left window), user browses normally
in a second window. Flask holds shared state (current company, saved notes).

To capture page content: a **bookmarklet** (one-click JS snippet saved in the browser)
extracts `document.body` as text/markdown and POSTs it to `localhost:5001/capture`.
No extension required.

```
[Flask app window]          [Normal browser window]
  company info panel    ←→    user browses best_url
  notes + status              bookmarklet captures page text
  progress counter            → POST to Flask → saved to notes.jsonl
```

## Decision

Parking for now — Flask app is good enough for the current 41-company batch.
Revisit when the screening volume grows or iframe blocking becomes too painful.
Check Memex source before starting from scratch.
