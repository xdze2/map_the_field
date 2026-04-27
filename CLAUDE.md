# Map the Field 2026

> **Full project definition and spec:** [map_the_field_project.md](map_the_field_project.md)

## Data model

One folder per node (`data/nodes/{node_id}/`): summary with YAML frontmatter, sources, append-only triage log. `data/nodes/index.jsonl` is a derived flat index — recomputable from node folders.

Node fields live in the **YAML frontmatter** of the latest summary file. `index.jsonl` is kept in sync by Flask on every summary save. Fields are schemaless — add any key at any time. See [backlog/structured_node_fields.md](backlog/structured_node_fields.md).

## Python scripts (`tools/`)

- Use **Click** for all CLI interfaces
- Design for **idempotence**: running twice produces the same result
- Each script has a clearly identified input and output
- Data access goes through an **interface object** (load / save / search) — no direct file I/O scattered across scripts
- All scripts require `tools/venv/` activated

## Backlog

Design notes and future work in `backlog/`:
- [siren_pipeline_improvements.md](backlog/siren_pipeline_improvements.md)
- [structured_node_fields.md](backlog/structured_node_fields.md)
