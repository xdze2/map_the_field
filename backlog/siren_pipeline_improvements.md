# SIREN pipeline improvements

## 1. Better LLM prompt (highest priority)

Current prompt produces summaries that repeat known fields (city, NAF label, legal form).

Changes:
- Explicitly tell the model: do not repeat location, NAF label, or legal form — those are already recorded
- Add `TYPE:` output field: `product-company` / `esn-consulting` / `research-lab` / `association` / `unclear`
- Add `KEYWORDS:` output field: 3–5 comma-separated tags (e.g. `NLP`, `open-source`, `B2B-SaaS`)
- For `BEST_URL`: only pick a URL if the title or snippet explicitly names the company (avoid wrong Wikipedia hits like Kagilum → Japanese ice skater)

## 2. Wikidata lookup (bonus enrichment before DDG)

For companies with a Wikipedia entry, structured data is much better than DDG snippets.

Flow: `SIREN → Wikidata SPARQL (P1616 = SIREN) → Q-item → Wikipedia article URL + extract`

- Wikidata property P1616 = numéro SIREN
- Free API, no auth, returns structured JSON
- Coverage is low (~5-10% of PMEs) but quality is high when it exists
- Add as optional pre-step: if Wikidata hit found, use it as primary source and skip or downrank DDG results
- Reference: https://www.wikidata.org/wiki/Q3508142?uselang=fr#identifiers

## 3. URL blacklist additions

Current blacklist misses several aggregators that pollute the prompt:
- `crunchbase.com`
- `airsaas.io`, `sortlist.com`
- `welovedevs.com` and other job boards (`indeed.fr`, `jooble.org`)
- `legalin.fr` and other legal announcement sites

Wikipedia guard: filter Wikipedia results where the article title doesn't contain the company name.

## 4. Commute distance field

SIREN API already returns lat/lon coordinates (`siege.latitude`, `siege.longitude`).
Add a `commute_km` field (straight-line distance from home) to each YAML card — mechanical to compute, useful filter without any judgment call.
