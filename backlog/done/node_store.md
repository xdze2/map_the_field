# node_store — data access interface

## Motivation

Data-access logic is currently split across `bootstrap_nodes.py` and `screening_app.py`:
duplicated path constants, two `slugify()` implementations, `_parse_frontmatter` only in Flask,
`rebuild_index` only in bootstrap. Adding features requires touching both files.

## Proposed module: `tools/node_store.py`

Single interface object for all node I/O. No direct file access outside this module.

### Index schema (dataclass)

```python
@dataclass
class IndexEntry:
    node_id: str
    name: str
    type: str                    # always "company" for now
    naf: str | None
    city: str | None
    headcount: str | None        # e.g. "10-19 salariés"
    tags: list[str]              # from YAML frontmatter
    current_rank: int | None
    updated_at: str              # ISO timestamp of latest summary
```

### Responsibilities

| Function | Notes |
|---|---|
| `parse_frontmatter(content) -> dict` | extracted from `screening_app.py` |
| `read_node(node_id) -> dict` | meta + latest summary + triage + sources |
| `write_summary(node_id, content, author)` | saves file, appends triage entry, rebuilds index |
| `write_rank(node_id, rank, note)` | appends triage entry, rebuilds index |
| `write_capture(node_id, url, html)` | saves source files |
| `build_meta(siren_record) -> dict` | SIREN-specific, belongs here (node metadata) |
| `rebuild_index()` | always full recompute from disk — replaces `_update_index_entry` |

### What stays outside node_store

- `build_summary(siren_record)` — SIREN-specific content builder, stays in `bootstrap_nodes.py`
- Flask routes — `screening_app.py` calls node_store functions
- NAF loading, domain blacklist — stay in `utils.py`
- `now_iso()`, `slugify()` — move to `utils.py`

## pyproject.toml

The project is not currently a Python package. Adding a minimal `pyproject.toml` would allow:
- `tools/` to be importable as a package (so `node_store` can be imported by both scripts cleanly)
- declaring dependencies formally (currently in `tools/requirements.txt`)

Without it, scripts must either be run from `tools/` or use `sys.path` hacks to import siblings.
Recommend adding a minimal `pyproject.toml` with `[tool.setuptools]` before implementing node_store.

> **Open question:** Make `tools/` an installable package (`pip install -e .`, `from tools.node_store import ...`),
> or keep scripts standalone with `node_store.py` as a sibling file imported via relative import?
> The package approach is cleaner but requires the `pyproject.toml` / directory layout decision to be made first
> (see `backlog/project_directory.md`).

## Open questions

**`tags` in IndexEntry:** bootstrap summaries have no frontmatter tags yet.
Should `rebuild_index` fall back to `est_ess` / `est_association` from `meta.json` when frontmatter has no tags,
or always start with `[]` and let the user fill them in?

**`rebuild_index` on every save:** full recompute reads all `meta.json` + triage files on each Flask save/rank call.
Fine at ~200 nodes. At what scale would we switch to a hybrid (patch entry in place for rank/summary, full rebuild only at bootstrap)?
