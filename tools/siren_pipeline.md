# SIREN Pipeline

Three-step pipeline to discover and characterize companies near a given location for job prospecting.

## Overview

```
download_entreprises.py  →  search_duckduckgo.py  →  add_company_summary.py
        ↓                          ↓                          ↓
  sirene_searches/*.jsonl   ddg_searches/*.json    web_presence_validations/*.yaml
```

## Steps

### 1. Download from SIREN (`download_entreprises.py`)

Queries the free [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr) and saves raw results as JSONL (one company per line).

```bash
source tools/venv/bin/activate
python tools/download_entreprises.py -p 75015 -c core-tech
```

Options:
- `-p` postal code (required)
- `-c` NAF category: `core-tech`, `data`, `research`, `consulting`, `all`
- `-n` specific NAF code(s), e.g. `-n 62.01Z -n 62.02A`
- `-q` text query, e.g. `-q "intelligence artificielle"`

Output: `data/company_data/sirene_searches/postal_{code}_cat_{category}_{date}.jsonl`

Rate limit respected (7 req/s). All pages fetched automatically.

---

### 2. DuckDuckGo search (`search_duckduckgo.py`)

For each SIREN, looks up the company in local JSONL data, searches DuckDuckGo by company name, filters out directory aggregators (societe.com etc.), and saves results.

```bash
# Single company
python tools/search_duckduckgo.py 123456789

# Batch via xargs from a list of SIRENs
cat sirens.txt | xargs -I{} python tools/search_duckduckgo.py {}
```

Skips SIRENs that already have a DDG file (`--skip-existing` is on by default).

Output: `data/company_data/ddg_searches/ddg_search_{siren}_{slug}_{date}.json`

Each file contains: SIREN metadata, query used, filtering stats, and up to 25 results (url + title + snippet), with blacklisted results kept separately.

---

### 3. LLM summary (`add_company_summary.py`)

Reads each DDG JSON file, builds a prompt with SIREN registry data + top 8 search results, calls a local LLM, and saves a structured YAML card.

```bash
# Process all pending DDG files
python tools/add_company_summary.py --all

# Process specific SIRENs
python tools/add_company_summary.py 123456789 987654321

# Dry-run: print prompts without calling LLM
python tools/add_company_summary.py --all --dry-run
```

LLM backends:
- `--provider llamacpp` (default) — local llama.cpp server at `http://localhost:8083/v1`, model `qwen2.5-3b-instruct-q4_k_m.gguf`
- `--provider ollama` — Ollama, model `qwen3:4b`

The LLM returns three fields parsed from its response:
- `BEST_URL` — best matching URL (official site or Wikipedia preferred)
- `CONFIDENCE` — `good` / `maybe` / `weak`
- `SUMMARY` — 1–3 sentence factual description

Output: `data/company_data/web_presence_validations/{siren}_{slug}_{size}_{city}_{confidence}_{timestamp}.yaml`

Each YAML contains: meta (siren, author tag, dates), company (name, city, size, NAF, ESS/association flags), summary (confidence, best URL, text, elapsed time), and the top 8 search results.

---

## Full pipeline run

```bash
source tools/venv/bin/activate

# 1. Download companies by postal code and activity type
python tools/download_entreprises.py -p 75015 -c core-tech

# 2. Search the web for each company (run once per SIREN, idempotent)
python tools/view_entreprises.py --file data/company_data/sirene_searches/ --json \
  | jq -r '.[].siren' \
  | xargs -P4 -I{} python tools/search_duckduckgo.py {}

# 3. Generate LLM summary cards for all new DDG files
python tools/add_company_summary.py --all
```

---

## Data directories

| Directory | Contents | Versioned |
|-----------|----------|-----------|
| `data/company_data/sirene_searches/` | Raw SIREN API results (JSONL) | No |
| `data/company_data/ddg_searches/` | DuckDuckGo results per company (JSON) | No |
| `data/company_data/web_presence_validations/` | LLM summary YAML cards | No |
| `data/company_data/insights/status.csv` | Triage decisions (append-only) | Yes |

---

## NAF categories

Defined in `tools/siren_infos/naf_categories.yaml`.

| Category | Description |
|----------|-------------|
| `core-tech` | Software dev, IT consulting, software publishing |
| `data` | Data processing, cloud hosting, market research |
| `research` | Biotech, science, social science R&D |
| `consulting` | Management consulting, advertising/ad tech |
