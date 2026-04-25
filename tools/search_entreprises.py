#!/usr/bin/env python3
import click
import requests
import time
import json
import csv
from typing import Optional
from pathlib import Path

BASE_URL = "https://recherche-entreprises.api.gouv.fr/search"
RATE_LIMIT_DELAY = 0.15  # 7 requests/second = ~143ms between requests
SCRIPT_DIR = Path(__file__).parent
NAF_FILE = SCRIPT_DIR / "naf_codes.csv"


def load_naf_codes():
    """Load NAF codes from CSV into a dictionary."""
    naf_dict = {}
    if not NAF_FILE.exists():
        return naf_dict

    try:
        with open(NAF_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("Code", "").strip()
                label = row.get(" Intitulés de la  NAF rév. 2, version finale ", "").strip()
                if code and label:
                    naf_dict[code] = label
    except Exception as e:
        click.echo(f"Warning: Could not load NAF codes: {e}", err=True)

    return naf_dict


def decode_naf(code: str, naf_dict: dict) -> str:
    """Decode NAF code to human-readable label."""
    if not code:
        return "N/A"
    return naf_dict.get(code, code)


def check_rate_limit():
    """Implement basic rate limiting with delay between requests."""
    if not hasattr(check_rate_limit, "last_request"):
        check_rate_limit.last_request = 0

    elapsed = time.time() - check_rate_limit.last_request
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)

    check_rate_limit.last_request = time.time()


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
    "--limit",
    "-l",
    default=20,
    type=int,
    help="Maximum results to return",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
def search(postal_code: str, query: str, limit: int, format: str):
    """Search for enterprises in a French city by postal code."""

    if len(postal_code) != 5 or not postal_code.isdigit():
        raise click.BadParameter("Postal code must be exactly 5 digits")

    naf_dict = load_naf_codes()

    click.echo(f"Searching for enterprises in {postal_code}...", err=True)

    check_rate_limit()

    try:
        response = requests.get(
            BASE_URL,
            params={
                "code_postal": postal_code,
                "q": query if query else None,
                "per_page": min(limit, 25),  # API max is 25
                "page": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"API request failed: {e}")

    data = response.json()
    results = data.get("results", [])

    if not results:
        click.echo("No enterprises found.", err=True)
        return

    # Limit results
    results = results[:limit]

    if format == "json":
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # Text output
        click.echo(f"\nFound {len(results)} entreprises:\n")
        for i, enterprise in enumerate(results, 1):
            siren = enterprise.get("siren", "N/A")
            nom = enterprise.get("nom_complet", "N/A")
            activite_code = enterprise.get("activite_principale", "N/A")
            activite_label = decode_naf(activite_code, naf_dict)
            effectif = enterprise.get("tranche_effectif_salarie", "N/A")

            siege = enterprise.get("siege", {})
            adresse = siege.get("adresse", "N/A")

            click.echo(f"{i}. {nom}")
            click.echo(f"   SIREN: {siren}")
            click.echo(f"   Activité: {activite_code} - {activite_label}")
            click.echo(f"   Effectif: {effectif}")
            click.echo(f"   Adresse: {adresse}")
            click.echo()


if __name__ == "__main__":
    search()
