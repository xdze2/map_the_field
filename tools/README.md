# SIREN Search Tools

Search for French enterprises using the INSEE SIREN database via the free API Recherche d'Entreprises.

## Data Source

- **API**: [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr)
  - Free, open-access (no registration required)
  - Rate limit: 7 requests/second per user
  - Data: ~25 million companies and 36 million establishments in France

- **NAF Codes**: [INSEE NAF Nomenclature](https://www.insee.fr/fr/information/2406147)
  - Activity classification codes (Nomenclature d'activités française)
  - Source file: `int_courts_naf_rev_2.xls` → exported to `naf_codes.csv`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Search by Postal Code

```bash
python search_entreprises.py --postal-code 75015
```

### Search with Query Filter

```bash
python search_entreprises.py -p 75015 -q "restaurant"
```

### JSON Output

```bash
python search_entreprises.py -p 75015 --format json
```

### Custom Result Limit

```bash
python search_entreprises.py -p 75015 --limit 10
```

### All Options

```bash
python search_entreprises.py --help
```

```
Usage: search_entreprises.py [OPTIONS]

  Search for enterprises in a French city by postal code.

Options:
  -p, --postal-code TEXT     Postal code (5 digits)  [required]
  -q, --query TEXT           Search query (company name, address, etc.)
  -l, --limit INTEGER        Maximum results to return  [default: 20]
  -f, --format [json|text]   Output format  [default: text]
  --help                     Show this message and exit.
```

## Output Example

```
Found 3 entreprises:

1. LA POSTE
   SIREN: 356000000
   Activité: 53.10Z - Activités de poste dans le cadre d'une obligation de service universel
   Effectif: 53
   Adresse: DIRECTION GENERALE DE LA POSTE 9 RUE DU COLONEL PIERRE AVIA 75015 PARIS

2. ELECTRICITE DE FRANCE (EDF)
   SIREN: 552081317
   Activité: 35.11Z - Production d'électricité
   Effectif: 53
   Adresse: 22-30 22 AVENUE DE WAGRAM 75008 PARIS
```

## Features

- ✅ No registration required (free API)
- ✅ Automatic rate limiting (respects API limits)
- ✅ NAF code decoding (shows human-readable activity descriptions)
- ✅ Search by postal code or query
- ✅ Text and JSON output formats
- ✅ Configurable result limits
