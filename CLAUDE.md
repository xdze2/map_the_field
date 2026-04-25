# Map the Field 2026

## Purpose
Structured exploration of the tech × social impact job market to inform career decisions. The goal is to gather landscape sources, discover organizations and projects, attend events, and use first-principles reasoning to identify the best opportunities.

## Current State (2026-04-23)
Three raw sources collected:
- 001: Data.org landscape (11 org categories in data-for-good ecosystem)
- 002: AI for Good Foundation (ai4good.org) — Deploy/Educate/Govern pillars, Ukraine humanitarian projects
- 003: Data Science for Social Good (datascienceforsocialgood.org) — fellowship, Aequitas bias toolkit, Solve for Good volunteer platform

## How Claude Should Help
When asked to explore, discover, or research:
- Assume the goal is to enrich the landscape map and feed the job search
- Format new findings consistently with existing raw_source files
- Index findings in INDEX.md for easy reference
- Look for patterns across sources and identify gaps

## File Structure

**Knowledge base & Quartz site** (root directory):
- `/raw_source/` — raw collected sources (numbered 001, 002, etc.) — immutable
- `/wiki/` — knowledge base with entity pages, concept pages, synthesis (LLM-maintained)
  - `index.md` — catalog of all wiki pages
  - `organizations/` — organization pages
  - `concepts/` — topics, themes, trends
  - `people/` — key people and their roles
- `/content/` — Quartz static site content
  - `articles/` — refined, narrative pieces (longer-form synthesis)
  - `sources/` — index of ingested documents with summaries
  - `log.md` — project timeline and changelog

**SIREN data tools** (standalone Python environment):
- `/tools/` — Python scripts for SIREN/enterprise data
  - `tools/venv/` — isolated virtual environment (do NOT commit)
  - `requirements.txt` — Python dependencies
  - `download_entreprises.py` — Download companies from Recherche d'Entreprises API
  - `view_entreprises.py` — View/filter downloaded JSONL data (filters out closed companies by default)
  - `search_internet.py` — Search for company websites via DuckDuckGo
  - `naf_categories.yaml` — NAF activity categories for filtering
  - `naf_codes.csv` — Full NAF code reference
- `/data/raw/searches/` — Downloaded JSONL data (`.gitignore`d)
  - `*.jsonl` — one enterprise per line, full API response
  - `metadata/search_log.jsonl` — search parameters & result counts

## Workflow

### Knowledge Base (Wiki + Quartz)

**Ingest a new source:**
1. Add raw file to `/raw_source/` (e.g., `004_source_name.md`)
2. Tell Claude to ingest it
3. Claude reads the source, updates wiki pages, adds entry to `log.md`
4. Review updates in the wiki
5. Run `npm run build` to regenerate the Quartz site

**Explore and query:**
1. Ask Claude questions about the wiki
2. Good findings can be filed as new wiki pages or articles
3. Run `npm run build` to update the site

**Maintain:**
- Periodically lint the wiki for contradictions, orphans, gaps
- Archive old log entries if they get too long

### SIREN Tools (Python Scripts)

**Setup:**
```bash
cd tools
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Download company data:**
```bash
source tools/venv/bin/activate
python tools/download_entreprises.py --postal-code 75001 --naf-category tech
```

**View downloaded data:**
```bash
source tools/venv/bin/activate
python tools/view_entreprises.py --file data/raw/searches/ --format condensed
```

**Search for company websites:**
```bash
source tools/venv/bin/activate
python tools/search_internet.py SIREN_ID
```

**Notes:**
- All scripts require activation of `tools/venv/` first
- Downloaded data stored in `/data/raw/searches/` (not version controlled)
- Scripts filter out closed companies by default
- DuckDuckGo blacklist editable in `search_internet.py`
