set shell := ["bash", "-c"]
venv := "source tools/venv/bin/activate"

# Search DDG for all companies of a given size bucket (solo/team/small/medium/large)
ddg-search size="team":
    {{venv}} && \
    python3 tools/view_entreprises.py -s {{size}} --sirens-only \
      | xargs -I{} sh -c 'python3 tools/search_duckduckgo.py {} && sleep 2 || exit 255'

# Build LLM summary cards for all DDG results
summarize:
    {{venv}} && python3 tools/add_company_summary.py --all

# Full pipeline: search then summarize
pipeline size="team":
    just ddg-search {{size}}
    just summarize
