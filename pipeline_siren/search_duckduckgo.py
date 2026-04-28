#!/usr/bin/env python3
import click
import json
from pathlib import Path
from datetime import datetime
from ddgs import DDGS
from backend.utils import (
    slugify,
    domain_name_blacklist,
    load_naf_descriptions,
    get_naf_description,
)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
SIRENE_SEARCHES_DIR = COMPANY_DATA_DIR / "sirene_searches"
DDG_SEARCHES_DIR = COMPANY_DATA_DIR / "ddg_searches"


def find_company_in_local_data(siren: str) -> dict:
    """Find company by SIREN in local JSONL files. Returns company dict or raises error."""
    if not SIRENE_SEARCHES_DIR.exists():
        raise click.ClickException(f"No data directory found: {SIRENE_SEARCHES_DIR}")

    jsonl_files = sorted(SIRENE_SEARCHES_DIR.glob("*.jsonl"))
    if not jsonl_files:
        raise click.ClickException(
            f"No downloaded data found in {SIRENE_SEARCHES_DIR}\n"
            "Use download_entreprises.py to fetch companies first."
        )

    for jsonl_file in jsonl_files:
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        company = json.loads(line)
                        if company.get("siren") == siren:
                            return company
        except Exception as e:
            click.echo(f"Warning: Could not read {jsonl_file}: {e}", err=True)

    raise click.ClickException(
        f"SIREN {siren} not found in local data.\n"
        f"Download it first with: python download_entreprises.py"
    )


def build_search_query(company_name: str, naf_label: str, city: str) -> str:
    # Actually works better only with company name
    # NAF & city label inject a lot of annuaire sites
    # --> tarket linkeding
    return f"{company_name}"


def search_company_website(
    query: str, max_results: int = 25, region: str = "fr-fr"
) -> list:
    """Search for company website using DuckDuckGo."""
    try:
        results = DDGS().text(query, max_results=max_results, region=region)
        return results if results else []
    except Exception as e:
        raise click.ClickException(f"Search failed: {e}")


def build_result_dict(result: dict, exclusion_reason: str = None) -> dict:
    """Build standardized result dict from raw search result."""
    data = {
        "url": result.get("href", ""),
        "title": result.get("title", ""),
        "snippet": result.get("body", ""),
    }
    if exclusion_reason:
        data["exclusion_reason"] = exclusion_reason
    return data


def filter_results(results: list) -> tuple:
    """Filter results: exclude directories, return (filtered, excluded) tuples."""
    filtered = []
    excluded = []

    for result in results:
        if domain_name_blacklist(result.get("href", "")):
            excluded.append(build_result_dict(result, "blacklisted_directory"))
        else:
            filtered.append(build_result_dict(result))

    return filtered, excluded


def already_searched(siren: str) -> bool:
    """Return True if a DDG result file already exists for this SIREN."""
    return (
        bool(list(DDG_SEARCHES_DIR.glob(f"ddg_search_{siren}_*.json")))
        if DDG_SEARCHES_DIR.exists()
        else False
    )


def save_ddg_results(siren: str, company_name: str, search_data: dict) -> None:
    """Save full DDG results to JSON file with metadata."""
    DDG_SEARCHES_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(company_name)
    now = datetime.now()
    search_date_iso = now.strftime("%Y-%m-%d")
    search_date_epoch = int(now.timestamp())
    filepath = DDG_SEARCHES_DIR / f"ddg_search_{siren}_{slug}_{search_date_iso}.json"

    output = {
        "siren": siren,
        "company_name": company_name,
        "slug": slug,
        "search_date": search_date_epoch,
        "search_date_iso": search_date_iso,
        "company_info": search_data["company_info"],
        "ddg_query": search_data["ddg_query"],
        "filtering": search_data["filtering"],
        "results": search_data["results"],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    click.echo(f"Saved DDG results to {filepath}", err=True)


def truncate(text: str, max_len: int = 100) -> str:
    """Truncate text with ellipsis if longer than max_len."""
    return text[:max_len] + "..." if len(text) > max_len else text


def print_candidates(company_name: str, siren: str, candidates: list):
    """Print top 2 search results."""
    click.echo(f"\nSIREN: {siren}")
    click.echo(f"Company: {company_name}")
    click.echo(f"\nCandidates:\n")

    if not candidates:
        click.echo("  [No results found]")
        return

    for i, candidate in enumerate(candidates[:2], 1):
        click.echo(f"{i}. {candidate['url']}")
        click.echo(f"   Title: {candidate['title']}")
        click.echo(f"   {truncate(candidate['snippet'])}")
        click.echo()


@click.command()
@click.argument("siren", required=True)
@click.option(
    "--show-all",
    is_flag=True,
    help="Show all results (including directories)",
)
@click.option(
    "--max-results",
    type=int,
    default=25,
    help="Maximum number of results to fetch (default: 25)",
)
@click.option(
    "--region",
    type=str,
    default="fr-fr",
    help="DuckDuckGo region code (default: fr-fr)",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    default=True,
    help="Skip SIRENs that already have a DDG result file (default: on)",
)
def search(
    siren: str, show_all: bool, max_results: int, region: str, skip_existing: bool
):
    """Search for a company website by SIREN.

    Looks up company in local downloads, then searches for website using postal code + company name.
    By default, filters out known directories (societe.com, etc).

    Auto-saves full DDG results to /data/company_data/ddg_searches/ as JSON with metadata.

    Exits with code 1 on any error (compatible with xargs -I{} sh -c '... || exit 255').
    """
    if skip_existing and already_searched(siren):
        click.echo(f"[skip] {siren} — DDG file already exists", err=True)
        return

    company = find_company_in_local_data(siren)

    nom = company.get("nom_complet", "")
    siege = company.get("siege", {})
    city = siege.get("libelle_commune", siege.get("code_postal", ""))
    naf_code = company.get("activite_principale", "")
    naf_map = load_naf_descriptions()
    naf_label = get_naf_description(naf_code, naf_map)

    if not nom:
        raise click.ClickException(f"Company name not found for SIREN {siren}")

    click.echo(f"Found: {nom} ({city})", err=True)

    query = build_search_query(nom, naf_label, city)
    click.echo(f"Searching: {query}", err=True)

    raw_results = search_company_website(query, max_results=max_results, region=region)
    if not raw_results:
        raise click.ClickException("No search results found")

    filtered_results, excluded_results = filter_results(raw_results)

    search_data = {
        "company_info": company,
        "ddg_query": {
            "query": query,
            "region": region,
            "max_results": max_results,
        },
        "filtering": {
            "total_results": len(raw_results),
            "filtered_results": len(filtered_results),
            "excluded_results": len(excluded_results),
        },
        "results": filtered_results,
    }

    save_ddg_results(siren, nom, search_data)

    candidates = (
        filtered_results
        if not show_all
        else [build_result_dict(r) for r in raw_results]
    )
    print_candidates(nom, siren, candidates)


if __name__ == "__main__":
    search()
