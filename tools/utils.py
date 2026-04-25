#!/usr/bin/env python3
"""Shared utilities for company research tools."""
import re
from urllib.parse import urlparse

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


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
    return parsed.netloc.lower()


def is_directory(url: str) -> bool:
    """Check if URL belongs to a known directory/annuaire."""
    domain = extract_domain(url)
    return domain in DIRECTORY_BLACKLIST or any(domain.endswith(f".{d}") for d in DIRECTORY_BLACKLIST)
