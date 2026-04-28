# Structured node fields (YAML frontmatter + index sync)

## Problem

`meta.json` was the original home for structured fields (name, type, SIREN, URL...) but it requires a maintained schema and is only useful for SIREN-typed nodes. Fields are not easily editable from the browser sidebar.

Meanwhile, the summary markdown is already the living document the user edits — it's the right place to add ad-hoc structured fields (company-type, commute distance, tags, etc.) as the project evolves.

## Decision

Drop `meta.json` as the source of truth for structured fields. Instead:

- Summary files carry a **YAML frontmatter block** (`---` header) for structured fields
- `index.jsonl` is the **materialized view**: Flask re-extracts frontmatter on every summary save and updates the matching index entry
- Fields are schemaless — any key can be added at any time without migration

## Implementation

**Summary file format:**
```markdown
---
name: Acme Corp
type: company
siren: 123456789
url: https://acme.fr
company_type: product-company
tags: NLP, open-source
commute_km: 8.2
---

Free-text summary content...
```

**Flask `POST /nodes/{id}/summary` changes:**
1. Parse YAML frontmatter from the incoming markdown (e.g. with `python-frontmatter`)
2. Merge extracted fields into the `index.jsonl` entry for this node
3. Unknown fields are passed through — no validation, no schema

**Extension list view:**
- Already reads `index.jsonl` — filter/sort UI just needs to handle arbitrary extra keys gracefully
- New fields appear in filters as soon as they exist in the index

## Fields to seed immediately

| Key | Source | Notes |
|---|---|---|
| `name` | SIREN bootstrap | |
| `type` | SIREN bootstrap | open string, not enum |
| `siren` | SIREN bootstrap | |
| `url` | DDG / user | best URL for the company |
| `company_type` | LLM / user | `product-company`, `esn-consulting`, `research-lab`, `association`, `unclear` |
| `tags` | LLM / user | comma-separated, 3–5 terms |
| `commute_km` | computed | straight-line from home, see SIREN pipeline backlog §4 |

## Notes

- `triage.jsonl` and `summary_history/` remain precious and unchanged
- The index entry must always be recomputable from the summary files — it's fully derived
- Flask is the single writer for `index.jsonl`; never update it directly from scripts
