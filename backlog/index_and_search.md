# Node index evolution & search

## Current state

`index.jsonl` is a flat cache mixing two concerns:
- **Node metadata** (stable: id, name, naf, city) — source of truth is `meta.json`
- **Research state** (mutable: rank, updated_at, frontmatter fields) — patched in-place by `_update_index_entry`

This causes sync bugs when the two get out of step.

## Decision: index as recomputable flat cache

The index should be a **pure snapshot**, always recomputable from disk via `rebuild_index()`.
`_update_index_entry()` goes away — Flask calls `rebuild_index()` after every save/rank.

Schema is defined as a dataclass (see `backlog/node_store.md`).

## Filtering & search options considered

| Option | Fits when |
|---|---|
| In-memory filter on index fields | rank, tags, naf, city — structured metadata |
| sqlite FTS on summary text | "find nodes mentioning climate / open-source" |
| Filesystem-first (no index) | eliminates sync entirely, fine at <2000 nodes |

## Recommendation

Keep `index.jsonl` as a flat metadata cache with a fixed schema.
Tags come from YAML frontmatter and are the primary filter surface.
Add sqlite FTS later if keyword search across summary text becomes useful.

## Open question

**Filesystem-first as an alternative:** at ~200 nodes, Flask could skip the index entirely and read each
`meta.json` + latest summary on every `/nodes` request. This eliminates the sync problem completely.
Worth benchmarking before committing to index maintenance complexity.

## Future filtering needs (expected)

- `rank >= 5` — structured, covered by index
- ESS / association filter — covered by index (`tags` field)
- City / region filter — covered by index
- "companies doing climate tech" — needs `tags` in frontmatter, or FTS
- Keyword in summary text — FTS (sqlite, no extra infra)
