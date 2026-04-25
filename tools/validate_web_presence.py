#!/usr/bin/env python3
import click
import json
import csv
import yaml
from pathlib import Path
from datetime import datetime
from utils import slugify, is_directory

SCRIPT_DIR = Path(__file__).parent
SIREN_INFOS_DIR = SCRIPT_DIR / "siren_infos"
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
DDG_SEARCHES_DIR = COMPANY_DATA_DIR / "ddg_searches"
VALIDATIONS_DIR = COMPANY_DATA_DIR / "web_presence_validations"
NAF_CODES_FILE = SIREN_INFOS_DIR / "naf_codes.csv"


def load_naf_descriptions() -> dict:
	"""Load NAF code → description mapping from CSV."""
	naf_map = {}
	try:
		with open(NAF_CODES_FILE, 'r', encoding='utf-8') as f:
			reader = csv.reader(f)
			header = next(reader)
			for row in reader:
				if len(row) >= 2:
					code = row[1].strip()
					# Use column 3 (65 character description)
					description = row[3].strip() if len(row) > 3 else row[2].strip()
					description = description.replace('\n', ' ')
					if code and description and not description.startswith('Intitulés'):
						naf_map[code] = description
	except Exception as e:
		click.echo(f"Warning: Could not load NAF codes: {e}", err=True)
	return naf_map


def find_ddg_file(siren: str) -> Path:
	"""Find the most recent DDG search file for a SIREN."""
	if not DDG_SEARCHES_DIR.exists():
		raise click.ClickException(f"DDG searches directory not found: {DDG_SEARCHES_DIR}")

	files = sorted(DDG_SEARCHES_DIR.glob(f"ddg_search_{siren}_*.json"))
	if not files:
		raise click.ClickException(f"No DDG search found for SIREN {siren}")

	return files[-1]  # Most recent by filename sort


def load_ddg_data(filepath: Path) -> dict:
	"""Load DDG JSON file and validate presence of company_info."""
	try:
		with open(filepath, 'r', encoding='utf-8') as f:
			data = json.load(f)
	except Exception as e:
		raise click.ClickException(f"Failed to load {filepath}: {e}")

	if 'company_info' not in data:
		raise click.ClickException(
			f"DDG file {filepath.name} lacks company_info metadata.\n"
			"This file predates the metadata enhancement. Re-run search_duckduckgo.py to regenerate."
		)

	return data


def get_naf_description(naf_code: str, naf_map: dict) -> str:
	"""Look up NAF code description, handle variations (72.20Z, 72.20, etc)."""
	if naf_code in naf_map:
		return naf_map[naf_code]
	# Try without the Z suffix
	base_code = naf_code.rstrip('Z') if naf_code.endswith('Z') else naf_code
	if base_code in naf_map:
		return naf_map[base_code]
	return f"NAF {naf_code}"


def extract_official_data(company_info: dict, naf_map: dict) -> dict:
	"""Map raw SIREN fields into clean nested dict for YAML official_data section."""
	siege = company_info.get('siege', {})
	complements = company_info.get('complements', {})

	primary_naf = company_info.get('activite_principale', '')
	naf_description = get_naf_description(primary_naf, naf_map)

	return {
		'siren': company_info.get('siren'),
		'name': company_info.get('nom_complet'),
		'name_short': company_info.get('sigle'),
		'activity': {
			'code': primary_naf,
			'code_naf25': company_info.get('activite_principale_naf25'),
			'description': naf_description,
			'section': company_info.get('section_activite_principale'),
		},
		'legal_status': {
			'nature_juridique': company_info.get('nature_juridique'),
			'is_association': complements.get('est_association', False),
			'is_ess': complements.get('est_ess', False),
			'is_entrepreneur': complements.get('est_entrepreneur_individuel', False),
		},
		'location': {
			'address': siege.get('adresse', ''),
			'postal_code': siege.get('code_postal', ''),
			'city': siege.get('libelle_commune', ''),
			'department': siege.get('departement', ''),
			'region': siege.get('region', ''),
			'coordinates': {
				'latitude': siege.get('latitude'),
				'longitude': siege.get('longitude'),
			} if siege.get('latitude') else None,
		},
		'establishment': {
			'total': company_info.get('nombre_etablissements'),
			'active': company_info.get('nombre_etablissements_ouverts'),
			'siret': siege.get('siret', ''),
		},
		'timeline': {
			'created': company_info.get('date_creation'),
			'activity_started': siege.get('date_debut_activite'),
			'last_updated': company_info.get('date_mise_a_jour'),
		},
		'employment': {
			'headcount_band': company_info.get('tranche_effectif_salarie'),
			'headcount_year': company_info.get('annee_tranche_effectif_salarie'),
		},
	}


def get_domain_type(url: str) -> str:
	"""Classify domain type based on URL."""
	if is_directory(url):
		return "directory"
	# Heuristic: if domain contains company name (rough), likely official
	if any(x in url.lower() for x in ["site", "com", "fr", "net"]):
		return "potential_official"
	return "unknown"


def prepare_results(results: list) -> list:
	"""Annotate each DDG result with domain_type and relevance placeholder."""
	annotated = []
	for i, result in enumerate(results[:10], 1):  # Top 10 only
		annotated.append({
			'rank': i,
			'title': result.get('title', ''),
			'url': result.get('url', ''),
			'snippet': result.get('snippet', ''),
			'relevance': 'medium',  # Claude will assess
			'domain_type': get_domain_type(result.get('url', '')),
		})
	return annotated


def print_for_claude(siren: str, official_data: dict, results: list) -> None:
	"""Print structured data for Claude to analyze."""
	click.echo("\n" + "="*80, err=True)
	click.echo(f"VALIDATE WEB PRESENCE FOR SIREN {siren}", err=True)
	click.echo("="*80, err=True)
	click.echo("\nOFFICIAL REGISTRY DATA:", err=True)
	click.echo(json.dumps(official_data, indent=2, ensure_ascii=False, default=str), err=True)
	click.echo("\nWEB SEARCH RESULTS (from DuckDuckGo):", err=True)
	click.echo(json.dumps(results, indent=2, ensure_ascii=False), err=True)
	click.echo("\n" + "="*80, err=True)
	click.echo("Analyzing... (waiting for Claude assessment)", err=True)
	click.echo("="*80 + "\n", err=True)


def save_validation_yaml(siren: str, slug: str, confidence: str, yaml_data: dict) -> str:
	"""Save YAML validation report. Returns filepath."""
	VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)
	now = datetime.now()
	timestamp = now.strftime("%Y%m%dT%H%M%S")
	filepath = VALIDATIONS_DIR / f"{siren}_{slug}_{timestamp}_claude_{confidence}.yaml"

	with open(filepath, 'w', encoding='utf-8') as f:
		yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

	return str(filepath)


@click.command()
@click.argument("siren", required=True)
def validate(siren: str):
	"""Validate company web presence against SIREN registry data.

	Loads the latest DDG search results for SIREN, extracts official company data,
	prints both for Claude analysis. Claude will assess name/location/activity match,
	assign confidence (good/strange/wrong), and output a YAML validation report.
	"""

	# Step 1: Load data
	ddg_file = find_ddg_file(siren)
	ddg_data = load_ddg_data(ddg_file)

	naf_map = load_naf_descriptions()

	# Step 2: Extract and structure
	official_data = extract_official_data(ddg_data['company_info'], naf_map)
	annotated_results = prepare_results(ddg_data['results'])

	# Step 3: Print for Claude
	print_for_claude(siren, official_data, annotated_results)

	# Return data for skill to use
	click.echo(json.dumps({
		'siren': siren,
		'slug': ddg_data['slug'],
		'official_data': official_data,
		'web_results': annotated_results,
		'ddg_search_date': ddg_data.get('search_date'),
	}, ensure_ascii=False, default=str))


if __name__ == "__main__":
	validate()
