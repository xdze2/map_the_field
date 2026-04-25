#!/usr/bin/env python3
import click
import json
import time
from pathlib import Path
from datetime import datetime
from ddgs import DDGS
import re

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
SIRENE_SEARCHES_DIR = COMPANY_DATA_DIR / "sirene_searches"
DDG_SEARCHES_DIR = COMPANY_DATA_DIR / "ddg_searches"

# Known directory/annuaire domains to filter out
DIRECTORY_BLACKLIST = {
    "societe.com",
    "verif.com",
    "sirene.data.gouv.fr",
    "infogreffe.fr",
    "pagesjaunes.fr",
    "kompass.com",
    "europages.fr",
    "viadeo.com",
    "linkedin.com",
    "pappers.fr",
    "lefigaro.fr",
    "infonet.fr",
    "lagazettefrance.fr",
    "hoodspot.fr",
    "eterritoire.fr",
    "gouv.fr",
}


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


def slugify(text: str) -> str:
    """Convert company name to URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def build_search_query(company_name: str, postal_code: str) -> str:
    """Build DuckDuckGo search query."""
    # Include postal code for geographic context
    query = f"{company_name} {postal_code} france"
    return query


def search_company_website(query: str) -> dict:
    """Search for company website using DuckDuckGo. Returns dict with results and query metadata."""
    try:
        max_results = 25
        region = "fr-fr"
        results = DDGS().text(query, max_results=max_results, region=region)
        return {
            "results": results if results else [],
            "query": query,
            "region": region,
            "max_results": max_results,
        }
    except Exception as e:
        raise click.ClickException(f"Search failed: {e}")


def is_directory(url: str) -> bool:
    """Check if URL is a known directory/annuaire domain."""
    for domain in DIRECTORY_BLACKLIST:
        if domain in url.lower():
            return True
    return False


def filter_results(results: list) -> tuple:
    """Filter results: exclude directories, return (filtered, excluded) tuples.

    Returns a tuple of (filtered_results, excluded_results) where each is a list of dicts
    with url, title, snippet, and exclusion_reason.
    """
    filtered = []
    excluded = []

    for result in results:
        url = result.get("href", "")
        title = result.get("title", "")
        body = result.get("body", "")

        if is_directory(url):
            excluded.append(
                {
                    "url": url,
                    "title": title,
                    "snippet": body,
                    "exclusion_reason": "blacklisted_directory",
                }
            )
        else:
            filtered.append(
                {
                    "url": url,
                    "title": title,
                    "snippet": body,
                }
            )

    return filtered, excluded


def save_ddg_results(
    siren: str,
    company_name: str,
    search_metadata: dict,
    company_info: dict,
    filtered_results: list,
    excluded_results: list,
) -> None:
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
        "company_info": company_info,
        "ddg_query": {
            "query": search_metadata.get("query"),
            "region": search_metadata.get("region"),
            "max_results": search_metadata.get("max_results"),
        },
        "filtering": {
            "blacklist_domains": list(DIRECTORY_BLACKLIST),
            "total_results": len(search_metadata.get("results", [])),
            "filtered_results": len(filtered_results),
            "excluded_results": len(excluded_results),
        },
        "results": {
            "included": filtered_results,
            "excluded": excluded_results,
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    click.echo(f"Saved DDG results to {filepath}", err=True)


def print_candidates(company_name: str, siren: str, candidates: list):
    """Print search results in a readable format."""
    click.echo(f"\nSIREN: {siren}")
    click.echo(f"Company: {company_name}")
    click.echo(f"\nCandidates:\n")

    if not candidates:
        click.echo("  [No non-directory results found]")
        click.echo("  Tip: Directories may be the only option; check manually.")
        return

    for i, candidate in enumerate(candidates[:2], 1):
        url = candidate["url"]
        title = candidate["title"]
        snippet = (
            candidate["snippet"][:100] + "..."
            if len(candidate["snippet"]) > 100
            else candidate["snippet"]
        )

        click.echo(f"{i}. {url}")
        click.echo(f"   Title: {title}")
        click.echo(f"   {snippet}")
        click.echo()


@click.command()
@click.argument("siren", required=True)
@click.option(
    "--show-all",
    is_flag=True,
    help="Show all results (including directories)",
)
def search(siren: str, show_all: bool):
    """Search for a company website by SIREN.

    Looks up company in local downloads, then searches for website using postal code + company name.
    By default, filters out known directories (societe.com, etc).

    Auto-saves full DDG results to /data/company_data/ddg_searches/ as JSON with metadata
    (SIREN, company name, slug, epoch timestamp).
    """

    # Step 1: Find company in local data
    try:
        company = find_company_in_local_data(siren)
    except click.ClickException as e:
        raise e

    nom = company.get("nom_complet", "")
    postal_code = company.get("siege", {}).get("code_postal", "")

    if not nom:
        raise click.ClickException(f"Company name not found for SIREN {siren}")

    click.echo(f"Found: {nom} ({postal_code})", err=True)

    # Step 2: Build and execute search
    query = build_search_query(nom, postal_code)
    click.echo(f"Searching: {query}", err=True)

    search_metadata = search_company_website(query)

    if not search_metadata.get("results"):
        raise click.ClickException("No search results found")

    # Step 3: Filter results
    filtered_results, excluded_results = filter_results(
        search_metadata.get("results", [])
    )

    # Step 4: Save full results
    save_ddg_results(siren, nom, search_metadata, company, filtered_results, excluded_results)

    # Step 5: Filter results for display
    if show_all:
        candidates = [
            {
                "url": r.get("href", ""),
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
            }
            for r in search_metadata.get("results", [])
        ]
    else:
        candidates = filtered_results

    # Step 5: Print results
    print_candidates(nom, siren, candidates)


if __name__ == "__main__":
    search()
