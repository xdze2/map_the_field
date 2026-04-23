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

**Raw sources** (immutable):
- `/raw_source/` — raw collected sources (numbered 001, 002, etc.)

**Wiki** (LLM-maintained):
- `/wiki/` — knowledge base with entity pages, concept pages, synthesis
  - `index.md` — catalog of all wiki pages
  - `organizations/` — organization pages
  - `concepts/` — topics, themes, trends
  - `people/` — key people and their roles
  - etc.

**Content for Quartz site**:
- `/content/` — root directory for the static site
  - `wiki/` — symlink or copies from `/wiki/`
  - `articles/` — refined, narrative pieces (longer-form synthesis)
  - `sources/` — index of ingested documents with summaries
  - `log.md` — project timeline and changelog

## Workflow

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
