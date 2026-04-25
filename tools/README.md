# SIREN Search Tools

Search for French enterprises using the INSEE SIREN database via the free API Recherche d'Entreprises.

Two-script workflow:
1. **download_entreprises.py** — Download all results to JSONL files (handles pagination, respects rate limits)
2. **view_entreprises.py** — Explore downloaded data (condensed or full view)

## Data Source

- **API**: [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr)
  - Free, open-access (no registration required)
  - Rate limit: 7 requests/second per user
  - Data: ~25 million companies and 36 million establishments in France

- **NAF Codes**: [INSEE NAF Nomenclature](https://www.insee.fr/fr/information/2406147)
  - Activity classification codes (Nomenclature d'activités française)
  - Source file: `siren_infos/int_courts_naf_rev_2.xls` → exported to `siren_infos/naf_codes.csv`

## Installation

```bash
pip install -r requirements.txt
```

## Workflow

### 1. Download Data

Download all enterprises matching your criteria into JSONL files:

```bash
# Basic: all enterprises in postal code
python download_entreprises.py -p 75015

# With NAF category filter (see siren_infos/naf_categories.yaml)
python download_entreprises.py -p 75015 -c core-tech

# With specific NAF codes
python download_entreprises.py -p 75015 -n 62.01Z -n 62.02A

# With search query
python download_entreprises.py -p 75015 -q "intelligence artificielle"
```

Files are saved to `data/raw/searches/` with automatic pagination. Metadata is logged to `data/raw/metadata/search_log.jsonl`.

**Available NAF categories** (in `siren_infos/naf_categories.yaml`):
- `core-tech` — Software development, IT consulting, software publishing
- `data` — Data processing, cloud hosting, market research
- `research` — Biotech, science, social science R&D
- `consulting` — Management consulting, advertising/ad tech

### 2. View Data

Browse downloaded data (condensed by default):

```bash
# View all files in default directory (data/raw/searches/)
python view_entreprises.py

# View a single file
python view_entreprises.py --file data/raw/searches/postal_75015_2026-04-25.jsonl

# View all files in a directory
python view_entreprises.py --file data/raw/searches/

# View with full details
python view_entreprises.py --file data/raw/searches/ --format full

# Limit results
python view_entreprises.py --file data/raw/searches/ --limit 10

# Output as JSON
python view_entreprises.py --file data/raw/searches/ --json
```

## Output Examples

### Condensed View (default)
```
1. LA POSTE (356000000)
   Age: 35y | Activité: 53.10Z Activités de poste | Size: 1000-1999 | Dirigeants: N/A

2. ACME CORP (123456789)
   Age: 5y | Activité: 62.01Z Développement de logiciels | Size: 20-49 | Dirigeants: Jean Dupont, Marie Martin
```

### Full View
```
1. LA POSTE
   SIREN: 356000000
   Statut: A | Créée: 1991-01-01
   Catégorie juridique: 5210
   Activité: 53.10Z - Activités de poste dans le cadre d'une obligation de service universel
   Établissements: 12734 | Effectif: 42
   Adresse: DIRECTION GENERALE DE LA POSTE 9 RUE DU COLONEL PIERRE AVIA 75015 PARIS
   Coordonnées: 48.83002, 2.275688
   Labels: Service public
```

## Options

### download_entreprises.py

```bash
python download_entreprises.py --help
```

```
Options:
  -p, --postal-code TEXT      Postal code (5 digits)  [required]
  -q, --query TEXT            Search query (company name, address, etc.)
  -n, --naf TEXT              NAF code(s) (can be used multiple times or comma-separated)
  -c, --naf-category TEXT     Filter by category (see siren_infos/naf_categories.yaml)
  --help                      Show this message and exit.
```

### view_entreprises.py

```bash
python view_entreprises.py --help
```

```
Options:
  -f, --file PATH             Path to JSONL file or directory (if not specified, uses data/raw/searches/)
  -l, --limit INTEGER         Maximum results to display
  --format [condensed|full]   Output format  [default: condensed]
  --json                      Output as JSON
  --help                      Show this message and exit.
```

## NAF Categories for Data Science

Predefined NAF categories with codes relevant for data science job search:

| Category | NAF Codes | Description |
|----------|-----------|-------------|
| **core-tech** | 62.01Z, 62.02A, 62.09Z, 58.29B | Software dev, IT consulting, software publishing |
| **data** | 63.11Z, 63.12Z, 84.13Z | Data processing, cloud hosting, market research |
| **research** | 72.11Z, 72.19Z, 72.20Z | Biotech, science, social science R&D |
| **consulting** | 70.22Z, 73.11Z | Management consulting, advertising/ad tech |

See [naf_codes.csv](siren_infos/naf_codes.csv) for the full list with details.

## Features

- ✅ No registration required (free API)
- ✅ Automatic rate limiting (respects API limits)
- ✅ NAF code decoding (shows human-readable activity descriptions)
- ✅ **Filter by NAF category or code** (for targeted job search)
- ✅ Search by postal code or query
- ✅ Text and JSON output formats
- ✅ Configurable result limits
