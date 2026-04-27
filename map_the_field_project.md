# Map the Field — Project Definition

## Goal

Build a personal tool for structured job market exploration: identify future opportunities (companies, projects, people) in the tech × social impact space, rank them progressively, and make the exploration more efficient over time through active learning.

---

## The problem

Starting from 2000+ SIREN candidates, the user needs to triage them over several weeks without losing context, without tab explosion, and without rebuilding mental state from scratch each session. Human judgment is the scarce resource — the tool should minimize friction per useful signal.

---

## Core concept: the Node

A **node** is anything worth tracking: a company, a project, a person, an organization. The SIREN number is one possible identifier, not the identity itself.

Node types (open `type` field, not an enum):
- `company` — French registered company (has SIREN)
- `project` — open source project, research initiative, etc.
- `person` — contact, founder, researcher
- `org` — international org, NGO without SIREN

---

## Data model

One folder per node:

```
data/nodes/{node_id}/
  meta.json             ← name, type, identifiers (siren, url, ...), created_at
  summary_history/      ← all summaries, timestamped; current = latest by filename sort
    summary_{TIMESTAMP}_{author}.md  ← author: "user" or e.g. "llm_claude_sonnet46"
  sources/              ← raw captured data
    {hash}_{slug}_{timestamp}.md    ← captured page as markdown
    {hash}_{slug}_{timestamp}.json  ← fetch metadata (url, captured_at, status) status: good, dubious, discarded ?
  triage.jsonl          ← append-only user input (ranks, notes) — precious
```

`node_id` convention:
- `siren_{number}` for French companies
- `slug_{hash}` for everything else

Global index (Flask reads this to serve the list view without scanning all folders):

```
data/nodes/index.jsonl  ← one line per node: id, name, type, current_rank, updated_at
```

### What is precious vs. derived

| File | Status | Notes |
|---|---|---|
| `triage.jsonl` | **Precious** | Append-only, never overwrite |
| `summary_history/` | **Precious** | Never delete; latest file = current summary |
| `sources/` | **Precious** | Captured raw data |
| `meta.json` | Derived | Populated from SIREN + user input |
| `index.jsonl` | Derived | Recomputable from node folders |

---

## Ranking scale

6-level scale capturing both rejection reason and attraction level:

| Level | Label | Meaning |
|---|---|---|
| 1 | Hell no | Run away from this |
| 2 | Not interested | No offense, just not relevant |
| 3 | What? | Not enough data to judge — keep it |
| 4 | Boring | Fine, but not exciting |
| 5 | Interested | Tell me more |
| 6 | Excited | Let's go now |

Rank is stored in `triage.jsonl` and can change across passes as evidence accumulates.

---

## Multi-pass workflow

The tool is designed for work over several weeks. A node record accumulates evidence progressively:

**Pass 1 — SIREN + DDG:**
- `meta.json` populated from SIREN data
- Top-10 DuckDuckGo results fetched automatically (titles, snippets, URLs)
- User can already set a rank (often "3 — What?" at this stage)

**Pass 2 — Browse + Capture:**
- User browses to the company site in the main window
- Captures page as markdown via the extension
- Adds/removes URLs in `summary.md`

**Pass 3 — Summarize:**
- "Generate summary" button triggers LLM call → rewrites `summary.md`
- User can edit the summary directly (toggle render/edit mode)
- Every save snapshots to `summary_history/`

**Later passes:**
- Rank updates as more information arrives
- Active learning suggests which unranked nodes to look at next

---

## Architecture

```
Firefox extension (sidebar)
  ├── List view          ← all nodes, sortable/filterable
  ├── Node view          ← summary, sources, rank form, notes, history
  └── fetch to Flask     ← read/write all state

Flask app (localhost:5001)
  ├── serves node data   ← reads from data/nodes/
  ├── writes triage      ← appends to triage.jsonl
  ├── saves captures     ← writes to sources/
  ├── snapshots summary  ← on every summary.md save
  └── updates index      ← keeps index.jsonl current
```

Flask is the data brain — the extension is a thin UI. All data lives as files on disk, readable from any Python script independently of the browser.

---

## Firefox extension UI

### List view
- All nodes, one row each: name, type, current rank, last updated
- Sort by: rank, last updated, unranked first
- Filter by: rank, type, has-captures, has-summary
- Click a row → Node view

### Node view
- **Header:** name, type, identifiers (SIREN, main URL)
- **Summary panel:** `summary.md` rendered as markdown, toggle to edit mode
  - Edit mode: textarea, explicit Save button
  - Save snapshots to `summary_history/` via Flask
- **Sources:** list of captured URLs with status (fetched / relevant / removed)
  - "Add URL" input
- **Rank:** 6 buttons (1–6), current rank highlighted
- **Notes:** free-text textarea, saved to `triage.jsonl` on submit
- **History:** collapsible list of past triage entries (rank changes, notes, captures)
- **"Generate summary" button:** manual trigger only — no auto LLM calls

---

## Flask API (planned endpoints)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/nodes` | List view data (from index.jsonl) |
| GET | `/nodes/{id}` | Full node data |
| POST | `/nodes/{id}/rank` | Append rank to triage.jsonl |
| POST | `/nodes/{id}/notes` | Append note to triage.jsonl |
| POST | `/nodes/{id}/summary` | Save summary.md + snapshot |
| POST | `/nodes/{id}/sources` | Add a URL to sources |
| POST | `/nodes/{id}/capture` | Save captured markdown from extension |
| GET | `/nodes/{id}/history` | Return triage.jsonl entries |

---

## Phase 1 scope (now)

- Node folder structure + index
- Flask endpoints above
- Extension: list view + node view
- Manual rank + notes
- Summary edit with snapshot history
- Page capture via content script → markdown

## Phase 2 (later)

- Active learning: score unranked nodes by predicted interest based on ranked history
- Automated info gathering: fetch + summarize company site without user browsing
- "Generate summary" connected to LLM API
- Pattern analysis: what features separate rank 5-6 from rank 1-2

---

## Technical stack

| Component | Choice | Notes |
|---|---|---|
| Extension | Firefox MV2, vanilla JS | No framework — sidebar is simple enough |
| Backend | Flask (Python) | Already running on port 5001 |
| Page extraction | trafilatura | Already integrated |
| Markdown render | marked.js | Lightweight, no build step |
| LLM (phase 2) | Claude API | Via terminal for now, API later |
| Data | Files on disk | JSONL + Markdown — no database |
