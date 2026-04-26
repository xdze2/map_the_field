#!/usr/bin/env python3
import click
import json
import csv
import yaml
from typing import Optional
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SIREN_INFOS_DIR = SCRIPT_DIR / "siren_infos"
NAF_FILE = SIREN_INFOS_DIR / "naf_codes.csv"
NAF_CATEGORIES_FILE = SIREN_INFOS_DIR / "naf_categories.yaml"
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
SIRENE_SEARCHES_DIR = COMPANY_DATA_DIR / "sirene_searches"


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
                label = row.get(
                    " Intitulés de la  NAF rév. 2, version finale ", ""
                ).strip()
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


SIZE_BUCKETS = {
    "solo": {"tranches": {"01"}, "range": "1–2"},
    "team": {"tranches": {"02", "03", "11"}, "range": "3–19"},
    "small": {"tranches": {"12", "21"}, "range": "20–99"},
    "medium": {"tranches": {"22", "31", "32", "41"}, "range": "100–499"},
    "large": {"tranches": {"42", "51", "52", "53"}, "range": "500+"},
}

# Ordered list used for sorting (unknown/empty sorts last)
_TRANCHE_ORDER = [
    "01",
    "02",
    "03",
    "11",
    "12",
    "21",
    "22",
    "31",
    "32",
    "41",
    "42",
    "51",
    "52",
    "53",
]


def get_size_category(tranche_code: str) -> str:
    """Map official INSEE effectif bracket codes to readable categories."""
    size_map = {
        "NN": "Unknown",
        "00": "0 employees",
        "01": "1-2",
        "02": "3-5",
        "03": "6-9",
        "11": "10-19",
        "12": "20-49",
        "21": "50-99",
        "22": "100-199",
        "31": "200-249",
        "32": "250-499",
        "41": "500-999",
        "42": "1000-1999",
        "51": "2000-4999",
        "52": "5000-9999",
        "53": "10000+",
    }
    return size_map.get(tranche_code, tranche_code)


def filter_by_size(results: list, sizes: tuple) -> tuple:
    """Filter enterprises by coarse size bucket. Returns (filtered_results, excluded_count).

    Sizes: solo (1-2), team (3-19), small (20-99), medium (100-499), large (500+).
    Entries with unknown/missing headcount are excluded when a filter is active.
    """
    allowed_tranches = set()
    for size in sizes:
        bucket = SIZE_BUCKETS.get(size)
        if bucket:
            allowed_tranches |= bucket["tranches"]

    filtered = [
        e for e in results if e.get("tranche_effectif_salarie", "") in allowed_tranches
    ]
    excluded = len(results) - len(filtered)
    return filtered, excluded


def sort_by_size(results: list) -> list:
    """Sort enterprises from smallest to largest by INSEE tranche code."""
    order = {code: i for i, code in enumerate(_TRANCHE_ORDER)}
    return sorted(
        results,
        key=lambda e: order.get(
            e.get("tranche_effectif_salarie", ""), len(_TRANCHE_ORDER)
        ),
    )


def load_jsonl(filepath: Path) -> list:
    """Load enterprises from JSONL file."""
    results = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except Exception as e:
        raise click.ClickException(f"Could not load {filepath}: {e}")
    return results


def filter_active_only(results: list) -> tuple:
    """Filter out closed companies. Returns (active_results, excluded_count).

    etat_administratif: "A" = Actif, "F" = Fermé
    """
    active = []
    excluded = 0
    for enterprise in results:
        etat = enterprise.get("etat_administratif", "").upper()
        if etat == "A":
            active.append(enterprise)
        else:
            excluded += 1
    return active, excluded


def print_condensed_results(results: list, naf_dict: dict):
    """Print condensed CSV view: siren, name, naf_label, naf_code, city_name, city_code."""
    click.echo("siren,name,naf_label,naf_code,city_name,city_code")
    for enterprise in results:
        siren = enterprise.get("siren", "")
        nom = enterprise.get("nom_complet", "")
        activite_code = enterprise.get("activite_principale", "")
        activite_label = decode_naf(activite_code, naf_dict)
        siege = enterprise.get("siege", {})
        city_name = siege.get("libelle_commune", "")
        city_code = siege.get("commune", "")

        row = [siren, nom, activite_label, activite_code, city_name, city_code]
        click.echo(",".join(f'"{v}"' for v in row))


def print_full_results(results: list, naf_dict: dict):
    """Print full verbose view with all details."""
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
                    click.echo(
                        f"   Finances ({latest_year}): CA={ca:,}€ | Résultat net={resultat:,}€"
                        if resultat
                        else f"   Finances ({latest_year}): CA={ca:,}€"
                    )

        click.echo()


SIZE_CHOICES = click.Choice(list(SIZE_BUCKETS.keys()))
_SIZE_HELP = (
    "Filter by company size (repeatable). "
    "Buckets: solo=1-2, team=3-19, small=20-99, medium=100-499, large=500+. "
    "Example: --size team --size small"
)


@click.command()
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    help="Path to JSONL file or directory (defaults to data/company_data/sirene_searches/)",
)
@click.option(
    "--limit",
    "-l",
    default=None,
    type=int,
    help="Maximum results to display",
)
@click.option(
    "--format",
    type=click.Choice(["condensed", "full"]),
    default="condensed",
    help="Output format: condensed (name, age, activity, size, directors) or full (all details)",
)
@click.option(
    "--size",
    "-s",
    type=SIZE_CHOICES,
    multiple=True,
    help=_SIZE_HELP,
)
@click.option(
    "--sirens-only",
    is_flag=True,
    help="Output only SIREN numbers, one per line (for piping to xargs)",
)
def view(file: Optional[str], limit: Optional[int], format: str, size: tuple, sirens_only: bool):
    """View downloaded SIREN enterprise data from JSONL files.

    Pass a file path to view a single file, or a directory to load all JSONL files.
    If neither is specified, defaults to data/company_data/sirene_searches/.
    Filters out closed companies by default.

    \b
    Size buckets (--size):
      solo    1-2 employees       (INSEE 01)
      team    3-19 employees      (INSEE 02, 03, 11)
      small   20-99 employees     (INSEE 12, 21)
      medium  100-499 employees   (INSEE 22, 31, 32, 41)
      large   500+ employees      (INSEE 42, 51, 52, 53)
    """

    # Determine which path to use
    if file:
        filepath = Path(file)
        if not filepath.exists():
            raise click.ClickException(f"Path not found: {file}")
    else:
        filepath = SIRENE_SEARCHES_DIR
        if not filepath.exists():
            click.echo(
                "No data downloaded yet. Use download_entreprises.py to download data.",
                err=True,
            )
            return

    # Load results
    if filepath.is_file():
        # Single file
        click.echo(f"Loading {filepath.name}...", err=True)
        results = load_jsonl(filepath)
    else:
        # Directory - load all JSONL files
        jsonl_files = sorted(filepath.glob("*.jsonl"))
        if not jsonl_files:
            click.echo(f"No JSONL files found in {filepath}", err=True)
            return

        click.echo(f"Loading {len(jsonl_files)} file(s) from {filepath}...", err=True)
        results = []
        for jsonl_file in jsonl_files:
            click.echo(f"  {jsonl_file.name}", err=True)
            results.extend(load_jsonl(jsonl_file))

    total_results = len(results)

    if not results:
        click.echo("No results found.", err=True)
        return

    # Filter out closed companies
    results, excluded_closed = filter_active_only(results)

    # Filter by size bucket
    excluded_size = 0
    if size:
        results, excluded_size = filter_by_size(results, size)

    # Sort condensed output by size (smallest first)
    if format == "condensed":
        results = sort_by_size(results)

    # Apply limit
    if limit:
        results = results[:limit]

    summary = f"Displaying {len(results)}/{total_results} results"
    if excluded_closed:
        summary += f" ({excluded_closed} closed excluded)"
    if excluded_size:
        summary += f" ({excluded_size} filtered by size)"
    click.echo(f"{summary}\n", err=True)

    if sirens_only:
        for enterprise in results:
            click.echo(enterprise.get("siren", ""))
        return

    naf_dict = load_naf_codes()

    if format == "full":
        print_full_results(results, naf_dict)
    else:
        print_condensed_results(results, naf_dict)


if __name__ == "__main__":
    view()
