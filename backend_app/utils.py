#!/usr/bin/env python3
"""Shared utilities for company research tools."""
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).parent
NAF_CODES_FILE = SCRIPT_DIR / "siren_infos" / "naf_codes.csv"

DIRECTORY_BLACKLIST = {
    # French company registries & legal directories
    "societe.com",
    "verif.com",
    "sirene.data.gouv.fr",
    "infogreffe.fr",
    "pagesjaunes.fr",
    "kompass.com",
    "europages.fr",
    "pappers.fr",
    "infonet.fr",
    "lagazettefrance.fr",
    "hoodspot.fr",
    "eterritoire.fr",
    "gouv.fr",
    "annuairefrancais.fr",
    "datalegal.fr",
    "codes-naf.com",
    "rubypayeur.com",
    "manageo.fr",
    "legalin.fr",
    "adr-st-o.com",
    "mappy.com",
    "grokipedia.com",
    "youtube.com",
    "pinterest.com",
    "alibaba.com",
    # Professional networks
    "viadeo.com",
    "viadeo.journaldunet.com",
    # Startup & company aggregators
    "crunchbase.com",
    "airsaas.io",
    "sortlist.com",
    "lespepitestech.com",
    "motherbase.io",
    # Job boards
    "welovedevs.com",
    "indeed.fr",
    "indeed.com",
    "jooble.org",
    "jobteaser.com",
    "welcometothejungle.com",
    "apec.fr",
    "cadremploi.fr",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_ts() -> str:
    """Compact UTC timestamp for filenames: 20260428T120000Z"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(
        url if url.startswith(("http://", "https://")) else f"https://{url}"
    )
    return parsed.netloc.lower()


def domain_name_blacklist(url: str) -> bool:
    domain = extract_domain(url)
    return domain in DIRECTORY_BLACKLIST or any(
        domain.endswith(f".{d}") for d in DIRECTORY_BLACKLIST
    )


def load_naf_descriptions() -> dict:
    naf_map = {}
    try:
        with open(NAF_CODES_FILE, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 4:
                    code = row[1].strip()
                    description = row[3].strip().replace("\n", " ")
                    if code and description and not description.startswith("Intitulés"):
                        naf_map[code] = description
    except Exception as e:
        import click

        click.echo(f"Warning: could not load NAF codes: {e}", err=True)
    return naf_map


def get_naf_description(naf_code: str, naf_map: dict) -> str:
    if naf_code in naf_map:
        return naf_map[naf_code]
    base = naf_code.rstrip("Z")
    return naf_map.get(base, f"NAF {naf_code}")
