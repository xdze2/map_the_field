#!/usr/bin/env python3
import click
import requests
import time
import json
import csv
import yaml
from typing import Optional
from pathlib import Path
from datetime import datetime

BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
RATE_LIMIT_DELAY = 0.15  # 7 requests/second = ~143ms between requests
SCRIPT_DIR = Path(__file__).parent
SIREN_INFOS_DIR = SCRIPT_DIR / "siren_infos"
NAF_FILE = SIREN_INFOS_DIR / "naf_codes.csv"
NAF_CATEGORIES_FILE = SIREN_INFOS_DIR / "naf_categories.yaml"
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
SIRENE_SEARCHES_DIR = COMPANY_DATA_DIR / "sirene_searches"


def load_naf_categories():
    """Load NAF categories from YAML config file."""
    if not NAF_CATEGORIES_FILE.exists():
        raise click.ClickException(f"NAF categories config not found: {NAF_CATEGORIES_FILE}")

    try:
        with open(NAF_CATEGORIES_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            # Extract just the codes from the config
            category_map = {}
            for category_name, category_data in config.get("categories", {}).items():
                codes = [item["code"] for item in category_data.get("codes", [])]
                category_map[category_name] = codes
            return category_map
    except Exception as e:
        raise click.ClickException(f"Could not load NAF categories: {e}")


def build_naf_filter(naf: tuple, naf_category: str) -> Optional[str]:
    """Build NAF filter string from CLI arguments."""
    naf_codes = []

    # Add codes from --naf arguments
    if naf:
        for n in naf:
            # Handle comma-separated values
            naf_codes.extend([code.strip() for code in n.split(",")])

    # Add codes from --naf-category
    if naf_category and naf_category != "all":
        categories = load_naf_categories()
        if naf_category in categories:
            naf_codes.extend(categories[naf_category])

    # Return comma-separated filter string
    if naf_codes:
        return ",".join(set(naf_codes))  # Remove duplicates
    return None


def check_rate_limit():
    """Implement basic rate limiting with delay between requests."""
    if not hasattr(check_rate_limit, "last_request"):
        check_rate_limit.last_request = 0

    elapsed = time.time() - check_rate_limit.last_request
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)

    check_rate_limit.last_request = time.time()


def generate_filename(postal_code: str, naf_filter: Optional[str], query: str) -> str:
    """Generate JSONL filename based on search parameters."""
    parts = [f"postal_{postal_code}"]

    if naf_filter:
        # Use first NAF code as identifier
        first_code = naf_filter.split(",")[0]
        parts.append(f"naf_{first_code.replace('.', '-')}")

    if query:
        parts.append(f"query_{query[:20]}")

    parts.append(datetime.now().strftime("%Y-%m-%d"))

    return "_".join(parts) + ".jsonl"


def download_all_pages(postal_code: str, naf_filter: Optional[str], query: str) -> tuple:
    """Download all pages for a search query. Returns (total_results, results_count)."""
    SIRENE_SEARCHES_DIR.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(postal_code, naf_filter, query)
    filepath = SIRENE_SEARCHES_DIR / filename

    click.echo(f"Downloading to {filepath}", err=True)

    all_results = []
    page = 1
    total_results = None

    while True:
        check_rate_limit()

        params = {
            "code_postal": postal_code,
            "q": query if query else None,
            "per_page": 25,  # Max per page
            "page": page,
        }

        if naf_filter:
            params["activite_principale"] = naf_filter

        try:
            click.echo(f"  Fetching page {page}...", err=True)
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"API request failed on page {page}: {e}")

        data = response.json()
        results = data.get("results", [])

        if total_results is None:
            total_results = data.get("total_results", 0)
            click.echo(f"  Total results available: {total_results}", err=True)

        if not results:
            break

        all_results.extend(results)

        # Check if we've reached the last page
        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break

        page += 1

    # Write JSONL file
    with open(filepath, "w", encoding="utf-8") as f:
        for result in all_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    click.echo(f"✓ Downloaded {len(all_results)} results to {filename}", err=True)

    return total_results, len(all_results)


@click.command()
@click.option(
    "--postal-code",
    "-p",
    required=True,
    help="Postal code (5 digits)",
)
@click.option(
    "--query",
    "-q",
    default="",
    help="Search query (company name, address, etc.)",
)
@click.option(
    "--naf",
    "-n",
    multiple=True,
    help="NAF code(s) to filter by (can be used multiple times or comma-separated)",
)
@click.option(
    "--naf-category",
    "-c",
    type=click.Choice(["core-tech", "data", "research", "consulting", "all"]),
    help="Filter by NAF category (see naf_categories.yaml for full list)",
)
def download(postal_code: str, query: str, naf: tuple, naf_category: str):
    """Download enterprises from API Recherche d'Entreprises and save to JSONL.

    Saves raw results to data/company_data/sirene_searches/{postal_code}_{filters}_{date}.jsonl
    (one enterprise per line). Use view_entreprises.py to browse or filter results.

    Respects API rate limits (7 req/s). NAF categories defined in naf_categories.yaml.

    Examples:
        python download_entreprises.py -p 75015
        python download_entreprises.py -p 75015 -c core-tech
        python download_entreprises.py -p 75015 -q "intelligence artificielle"
        python download_entreprises.py -p 75015 -n 62.01Z -n 62.02A
    """

    if len(postal_code) != 5 or not postal_code.isdigit():
        raise click.BadParameter("Postal code must be exactly 5 digits")

    naf_filter = build_naf_filter(naf, naf_category)

    click.echo(f"Downloading enterprises in {postal_code}...", err=True)
    if naf_filter:
        click.echo(f"NAF filter: {naf_filter}", err=True)

    total_results, downloaded_count = download_all_pages(postal_code, naf_filter, query)

    click.echo(f"\n✓ Complete: {downloaded_count}/{total_results} results saved", err=True)


if __name__ == "__main__":
    download()
