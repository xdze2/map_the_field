# Work Session Summary: Company Data Triage Infrastructure

**Date:** 2026-04-25  
**Time:** ~15:00 onwards

## Completed

### 1. Unified Directory Structure for Company Research
Consolidated all company data under `/data/company_data/`:
- `sirene_searches/` — SIREN API downloads (JSONL format, append-only metadata log removed)
- `ddg_searches/` — DuckDuckGo search results (JSON with metadata: SIREN, company name slug, epoch timestamp)
- `insights/` — Triage decisions (append-only CSV for audit trail)

**Rationale:** Centralizes all company research in one place, separates raw data (searches) from judgments (insights).

### 2. Simplified SIREN Download Script
- Removed metadata logging from `download_entreprises.py` (one less file to maintain)
- Output is now raw JSONL only to `/data/company_data/sirene_searches/`
- Consolidated duplicate `search_entreprises.py` — deleted after simplifying it
- Updated `view_entreprises.py` to point to new location

### 3. Enhanced DuckDuckGo Search Script
- Auto-saves full DDG results to `/data/company_data/ddg_searches/`
- JSON filenames include: SIREN, company slug, ISO date
- JSON metadata includes: SIREN, company name, slug, epoch timestamp, full results array
- Increased max results from 10 to 20 per search
- Added `region="fr-fr"` parameter to prioritize French results

**Workflow:** `python tools/search_duckduckgo.py SIREN_ID` → finds company in local SIREN data → searches DDG → saves full results + filtered candidates.

### 4. Documentation Updates
- Updated CLAUDE.md with new directory structure and simplified workflow
- Updated help text in all scripts to reflect new locations
- Deleted deprecated references

## Architecture: Company Research Pipeline

```
┌─ SIREN Data Collection
│  └─ download_entreprises.py → /data/company_data/sirene_searches/*.jsonl
│
├─ DuckDuckGo Web Discovery
│  └─ search_duckduckgo.py → /data/company_data/ddg_searches/ddg_search_{SIREN}_{slug}_{date}.json
│
└─ Triage & Decision Log (append-only)
   └─ /data/company_data/insights/status.csv
      Columns: timestamp, siren, company_name, status, reason, author
      Statuses: not_relevant, need_review, interesting
      Author: Human | Claude
```

## Design Decision: Manual Triage with AI Assistance

Rather than fully automating company evaluation:
- Claude reads SIREN data + DDG results
- Claude proposes a status (not_relevant / need_review / interesting) with reasoning
- Human reviews and confirms decision
- Decision appended to status.csv with "Human" author

This keeps the human in the loop while leveraging Claude to synthesize signals from multiple sources.

## Next Steps (Not Started)

### Short term:
1. **Claude Skill for Status Updates** — Build skill to:
   - Accept SIREN as input
   - Read SIREN record + latest DDG results
   - Propose status + reasoning
   - Append confirmed decision to status.csv
   
2. **Test end-to-end** — Download a small batch of companies, run DDG search, triage 5-10 entries to validate workflow

### Medium term:
3. Batch triage mode — process multiple SIRENs systematically
4. Query triage results — "show me all 'interesting' companies in NAF code X"
5. Wiki integration — promote shortlisted companies to `/wiki/organizations/`

### Long term:
6. Scoring system — weight different signals (web presence, team size, sector match)
7. Reporting — generate summaries by postal code, NAF category, interest level

## Technical Notes

- **Append-only CSV** — Provides audit trail; enables changing decisions later (new row, not update)
- **JSON metadata** — Epoch timestamp allows easy sorting/filtering programmatically
- **No database** — Text files + Claude queries keep the system lightweight and version-controllable
- **Offline-first** — Once SIREN + DDG data downloaded, full analysis works offline

## Decision Point: Skill Design

Before building Claude skill, need to finalize:
1. Workflow: propose-then-confirm vs. direct-append?
2. What signals drive Claude's proposals? (web presence, company age, size, sector, red flags?)
3. Batch mode: triage one at a time, or queue multiple SIRENs?
4. Output format: status text + links to raw data, or interactive prompt?

---

**Files Modified:**
- tools/download_entreprises.py (simplified, removed metadata logging)
- tools/view_entreprises.py (updated path to sirene_searches)
- tools/search_duckduckgo.py (added metadata, auto-save, region filter)
- tools/search_entreprises.py (deleted — consolidated)
- CLAUDE.md (updated directory structure + workflow)
- backlog/session_2026-04-25_1425.md (updated)

**Status:** Infrastructure ready for triage workflow. Skill design pending user clarification.
