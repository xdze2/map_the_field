#!/usr/bin/env python3
import click
import csv
import requests
import yaml
from datetime import datetime
from pathlib import Path
from utils import slugify

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
WIKIDATA_DIR = DATA_DIR / "company_data" / "wikidata_searches"
NO_ENTRY_CSV = WIKIDATA_DIR / "no_wiki_entry.csv"

QUERY = """
SELECT ?item ?itemLabel ?article WHERE {{
  ?item wdt:P1616 "{siren}" .
  OPTIONAL {{
    ?article schema:about ?item ;
             schema:isPartOf <https://fr.wikipedia.org/> .
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
}}
"""


def query_wikidata(siren: str) -> list:
    try:
        response = requests.get(
            SPARQL_ENDPOINT,
            params={"query": QUERY.format(siren=siren), "format": "json"},
            headers={"User-Agent": "map-the-field/1.0 (xdze2.me@gmail.com)"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["results"]["bindings"]
    except requests.exceptions.Timeout:
        raise click.ClickException(f"Wikidata SPARQL timed out for SIREN {siren}")


def fetch_wikipedia_summary(page_title: str) -> dict:
    url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_title)}"
    response = requests.get(
        url,
        headers={"User-Agent": "map-the-field/1.0 (xdze2.me@gmail.com)"},
        timeout=10,
    )
    if response.status_code != 200:
        return {}
    return response.json()


def first_n_words(text: str, n: int = 100) -> str:
    words = text.split()
    truncated = " ".join(words[:n])
    if len(words) > n:
        truncated += " [...]"
    return truncated


def download_thumbnail(url: str, dest: Path) -> None:
    response = requests.get(
        url,
        headers={"User-Agent": "map-the-field/1.0 (xdze2.me@gmail.com)"},
        timeout=10,
    )
    response.raise_for_status()
    dest.write_bytes(response.content)


def save_results(siren: str, slug: str, page_title: str, data: dict) -> None:
    WIKIDATA_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{siren}_{slug}_{page_title}"

    yaml_path = WIKIDATA_DIR / f"{stem}.yaml"
    yaml_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    click.echo(f"Saved {yaml_path}", err=True)

    thumbnail_url = data.get("thumbnail")
    if thumbnail_url:
        jpeg_path = WIKIDATA_DIR / f"{stem}.jpeg"
        download_thumbnail(thumbnail_url, jpeg_path)
        click.echo(f"Saved {jpeg_path}", err=True)


def log_no_entry(siren: str, slug: str) -> None:
    WIKIDATA_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not NO_ENTRY_CSV.exists()
    with open(NO_ENTRY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["siren", "slug", "timestamp"])
        writer.writerow([siren, slug, datetime.now().isoformat(timespec="seconds")])


def already_searched(siren: str) -> bool:
    if WIKIDATA_DIR.exists() and list(WIKIDATA_DIR.glob(f"{siren}_*.yaml")):
        return True
    if NO_ENTRY_CSV.exists():
        with open(NO_ENTRY_CSV, newline="", encoding="utf-8") as f:
            return any(row["siren"] == siren for row in csv.DictReader(f))
    return False


@click.command()
@click.argument("siren", required=True)
def search(siren: str):
    """Look up a SIREN number on Wikidata. Prints and saves summary + thumbnail if found."""
    if already_searched(siren):
        click.echo(f"[skip] {siren} — already searched", err=True)
        return

    click.echo(f"Querying Wikidata for SIREN {siren}...", err=True)

    results = query_wikidata(siren)

    if not results:
        click.echo(f"[not found] No Wikidata entry for SIREN {siren}")
        log_no_entry(siren, "")
        return

    for row in results:
        qid_url = row["item"]["value"]
        label = row.get("itemLabel", {}).get("value", "(no label)")
        wikipedia = row.get("article", {}).get("value", None)

        click.echo(f"\nLabel:     {label}")
        click.echo(f"Wikidata:  {qid_url}")

        if not wikipedia:
            click.echo("Wikipedia: (no French article)")
            continue

        click.echo(f"Wikipedia: {wikipedia}")

        page_title = wikipedia.split("/wiki/")[-1]
        summary = fetch_wikipedia_summary(page_title)

        extract = summary.get("extract", "")
        thumbnail = summary.get("thumbnail", {}).get("source")

        if extract:
            click.echo(f"\n{first_n_words(extract)}")
        if thumbnail:
            click.echo(f"\nImage:     {thumbnail}")

        data = {
            "siren": siren,
            "label": label,
            "wikidata": qid_url,
            "wikipedia": wikipedia,
            "extract": extract,
            "thumbnail": thumbnail,
        }
        save_results(siren, slugify(label), page_title, data)


if __name__ == "__main__":
    search()
