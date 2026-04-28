# Map the Field 2026

Structured exploration of the tech × social impact job market to inform a career move.

The goal is not to build a perfect database — it's to make good decisions with limited time. Starting from 2000+ French companies (SIREN data), the process is: triage fast, dig deeper on what looks interesting, accumulate context over several weeks.

See [map_the_field_project.md](map_the_field_project.md) for the full project definition, data model, and workflow.

## What's here

- `backend_app/` — Flask app + node store library
- `pipeline_siren/` — scripts to download and explore SIREN data
- `firefox_ext/` — Firefox sidebar for browsing and ranking nodes
- `data/nodes/` — one folder per tracked company/org/project
- `backlog/` — design notes and future improvements


## Usage

**Setup:**
```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

**Launch dedicated Firefox profile** (profile dir must exist first):
```bash
mkdir -p ~/.mozilla/firefox/map_the_field
firefox --profile ~/.mozilla/firefox/map_the_field --no-remote
```
`--no-remote` forces a new window even if Firefox is already open. Keep this instance separate from normal browsing — extension is installed here only.

**Load extension:**
1. `about:debugging` → This Firefox → Load Temporary Add-on → select `firefox_ext/manifest.json`
2. Sidebar: View → Sidebar → Map the Field
3. To reload after code changes: `about:debugging` → Reload button

**Flask backend:**
```bash
source venv/bin/activate
mtf-app
```
Must be running for the ping button to work. CORS is set to `*` in `after_request` hook.