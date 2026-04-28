# Outdated bootstrap summaries

Bootstrap-generated summaries (`author=siren_bootstrap`) use an old format:

```markdown
# COMPANY NAME

## Info
- **Activité:** ...
- **Ville:** ...

## Sources DDG
- [title](url)
  snippet
```

The expected format is YAML frontmatter + a `## Sources` section with a Google search link:

```markdown
---
name: COMPANY NAME
naf: 62.01Z
city: TOULOUSE
headcount: 10-19 salariés
tags: []
---

## Sources

- [Google: COMPANY NAME](https://www.google.com/search?q=COMPANY+NAME)
```

## What needs to happen

- `bootstrap_nodes.py`: updated to emit the new format (done when issue filed)
- Existing nodes (~200): need a re-bootstrap pass that appends a new `summary_{ts}_bootstrap.md`
  to each node's `summary_history/` — leaving the old file in place as history.
  The new summary becomes the latest (alphabetically last) and gets picked up by the UI.

## Why DDG was removed from bootstrap

DDG snippets add noise and low-signal directory links. The Google search link is more useful
as a one-click starting point for manual research.
