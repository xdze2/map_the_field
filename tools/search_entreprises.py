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


def load_naf_categories():
    """Load NAF categories for data science relevant codes."""
    category_map = {
        "core-tech": ["62.01Z", "62.02A", "62.09Z", "58.29B"],
        "data": ["63.11Z", "63.12Z", "84.13Z"],
        "research": ["72.11Z", "72.19Z", "72.20Z"],
        "consulting": ["70.22Z", "73.11Z"],
    }
    return category_map


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
    type=click.Choice(["core-tech", "data", "research", "consulting", "all"]),
    help="Filter by NAF category (data science relevant codes)",
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
def search(postal_code: str, query: str, naf: tuple, naf_category: str, limit: int, format: str):
    """Search for enterprises in a French city by postal code."""

    if len(postal_code) != 5 or not postal_code.isdigit():
        raise click.BadParameter("Postal code must be exactly 5 digits")

    naf_dict = load_naf_codes()
    naf_filter = build_naf_filter(naf, naf_category)

    click.echo(f"Searching for enterprises in {postal_code}...", err=True)
    if naf_filter:
        click.echo(f"NAF filter: {naf_filter}", err=True)

    check_rate_limit()

    params = {
        "code_postal": postal_code,
        "q": query if query else None,
        "per_page": min(limit, 25),  # API max is 25
        "page": 1,
    }

    # Add NAF filter if specified
    if naf_filter:
        params["activite_principale"] = naf_filter

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"API request failed: {e}")

    data = response.json()
    results = data.get("results", [])
    total_results = data.get("total_results", 0)

    if not results:
        click.echo("No enterprises found.", err=True)
        return

    # Limit results
    results = results[:limit]

    if format == "json":
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # Text output
        displayed = len(results)
        click.echo(f"\nFound {displayed} entreprises (total: {total_results}):\n")
        for i, enterprise in enumerate(results, 1):
            siren = enterprise.get("siren", "N/A")
            nom = enterprise.get("nom_complet", "N/A")
            activite_code = enterprise.get("activite_principale", "N/A")
            activite_label = decode_naf(activite_code, naf_dict)
            nature_juridique = enterprise.get("nature_juridique", "N/A")
            effectif = enterprise.get("tranche_effectif_salarie", "N/A")
            nb_etablissements = enterprise.get("nombre_etablissements", "N/A")
            date_creation = enterprise.get("date_creation", "N/A")
            etat = enterprise.get("etat_administratif", "N/A")

            siege = enterprise.get("siege", {})
            adresse = siege.get("adresse", "N/A")
            latitude = siege.get("latitude")
            longitude = siege.get("longitude")

            finances = enterprise.get("finances", {})
            dirigeants = enterprise.get("dirigeants", [])

            complements = enterprise.get("complements", {})
            est_ess = complements.get("est_ess", False)
            est_societe_mission = complements.get("est_societe_mission", False)
            est_association = complements.get("est_association", False)
            est_service_public = complements.get("est_service_public", False)

            # Main info
            click.echo(f"{i}. {nom}")
            click.echo(f"   SIREN: {siren}")
            click.echo(f"   Statut: {etat} | Créée: {date_creation}")
            click.echo(f"   Catégorie juridique: {nature_juridique}")

            # Activity
            click.echo(f"   Activité: {activite_code} - {activite_label}")

            # Size
            click.echo(f"   Établissements: {nb_etablissements} | Effectif: {effectif}")

            # Address & Location
            click.echo(f"   Adresse: {adresse}")
            if latitude and longitude:
                click.echo(f"   Coordonnées: {latitude}, {longitude}")

            # Labels & Certifications
            labels = []
            if est_ess:
                labels.append("ESS")
            if est_societe_mission:
                labels.append("Société à mission")
            if est_association:
                labels.append("Association")
            if est_service_public:
                labels.append("Service public")
            if labels:
                click.echo(f"   Labels: {', '.join(labels)}")

            # Directors
            if dirigeants:
                click.echo(f"   Dirigeants: {len(dirigeants)}")
                for d in dirigeants[:2]:  # Show first 2
                    nom_d = f"{d.get('prenoms', '')} {d.get('nom', '')}".strip()
                    qualite = d.get("qualite", "")
                    if nom_d:
                        click.echo(f"     - {nom_d} ({qualite})")
                if len(dirigeants) > 2:
                    click.echo(f"     ... et {len(dirigeants) - 2} autre(s)")

            # Finances
            if finances:
                latest_year = max(finances.keys(), default=None)
                if latest_year:
                    ca = finances[latest_year].get("ca")
                    resultat = finances[latest_year].get("resultat_net")
                    if ca:
                        click.echo(f"   Finances ({latest_year}): CA={ca:,}€ | Résultat net={resultat:,}€" if resultat else f"   Finances ({latest_year}): CA={ca:,}€")

            click.echo()


if __name__ == "__main__":
    search()
