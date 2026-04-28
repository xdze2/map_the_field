# Project directory organisation

## Current layout

```
map_the_field_2026/
├── data/
│   ├── nodes/                  # active data model (node folders + index.jsonl)
│   └── company_data/           # legacy pipeline outputs
│       ├── sirene_searches/    # raw SIREN API results (input to bootstrap)
│       ├── ddg_searches/       # raw DDG results (no longer used)
│       ├── company_summaries/  # old YAML summaries (pre-node model, superseded)
│       ├── triage/             # old triage files (superseded by node triage.jsonl)
│       ├── wikidata_searches/
│       ├── postcode_searches/
│       ├── insights/
│       └── web_presence_validations_old/
├── tools/
│   ├── screening_app.py        # Flask backend
│   ├── bootstrap_nodes.py      # SIREN → node creation
│   ├── utils.py                # shared helpers
│   ├── search_duckduckgo.py
│   ├── search_cities.py
│   ├── download_entreprises.py
│   ├── export_naf.py
│   ├── view_entreprises.py
│   ├── add_company_summary.py  # old pipeline script, probably obsolete
│   ├── siren_infos/            # static NAF reference data
│   ├── assets/                 # Flask static assets
│   ├── requirements.txt
│   └── venv/                   # virtualenv (gitignored)
├── mtf_firefox_ext/            # Firefox sidebar extension
├── backlog/
└── CLAUDE.md
```

## Problems

- `data/company_data/` is a mix of live inputs (`sirene_searches/`) and dead legacy outputs
  (`company_summaries/`, `triage/`, `web_presence_validations_old/`). Unclear what's still needed.
- `tools/` mixes the app (`screening_app.py`), pipeline scripts, and shared library code (`utils.py`).
  Adding `node_store.py` here works but doesn't signal that it's a library, not a script.
- No `pyproject.toml` — `tools/` is not a package, so inter-script imports require running from `tools/`
  or `sys.path` hacks.
- `venv/` sits inside `tools/` — non-standard location.

## Options to consider

### Option A — minimal cleanup, keep flat

Move `venv/` to project root. Add `pyproject.toml` at root.
Keep all scripts flat in `tools/`. `node_store.py` lives alongside them, imported as a sibling.
Scripts are run as `python tools/screening_app.py` from project root.

Pros: least disruption, works today.  
Con: `tools/` stays a mixed bag of app + library + pipeline scripts.

### Option B — split tools into app / lib / pipeline

```
src/
  mtf/
    node_store.py     # library
    utils.py
app/
  screening_app.py    # Flask
pipeline/
  bootstrap_nodes.py
  search_duckduckgo.py
  ...
```

Pros: clear separation of concerns.  
Con: larger reorganisation, need to update imports everywhere.

### Option C — keep tools/ flat but add pyproject.toml

Add `pyproject.toml` at project root declaring `tools/` as the package source.
`node_store.py` and `utils.py` become `tools.node_store`, `tools.utils`.
Scripts stay in `tools/` but are declared as `[project.scripts]` entry points.

Pros: clean imports, minimal restructuring.  
Con: naming (`tools` as a package name) is a bit odd.

## Open questions

- What is still used in `data/company_data/`? Can legacy folders be archived or deleted?
- Is `add_company_summary.py` still needed, or superseded by the node model?
- Where should `venv/` live? (project root is conventional)
- Should the Firefox extension stay at root level or move into `app/` / `frontend/`?
- Which option for `pyproject.toml` / package structure?
