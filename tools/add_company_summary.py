#!/usr/bin/env python3
"""Build company summary cards from DDG search results using a local LLM."""
import json
import re
import time
from datetime import datetime
from pathlib import Path

import click
import yaml
from utils import load_naf_descriptions, get_naf_description

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
DDG_SEARCHES_DIR = COMPANY_DATA_DIR / "ddg_searches"
VALIDATIONS_DIR = COMPANY_DATA_DIR / "web_presence_validations"

OLLAMA_MODEL = "qwen3:4b"
LLAMACPP_MODEL = "qwen2.5-3b-instruct-q4_k_m.gguf"
LLAMACPP_URL = "http://localhost:8083/v1"

PROMPT_TEMPLATE = """You are building a company description card from web search results, for a company from the French official registry (SIREN).

Official registry data:
- Name: {name}
- Activity (NAF code): {naf_code} — {naf_description}
- City: {city} ({postal_code})
- Legal: {legal}

Web search results:
{results_block}

Write a short factual summary (1-3 sentences) of what this company does, based on the search results.
If the results clearly don't match this company or are too vague, explain why.
Pick the single best URL that gives the most information about this company (official site or Wikipedia preferred over aggregators like Jooble, AirSaas, Motherbase).

Reply in exactly this format (3 lines, no other text):
BEST_URL: <url from the results above, or NONE>
CONFIDENCE: <good|maybe|weak>
SUMMARY: <1-3 sentences>
"""



def load_ddg_file(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_ddg_files() -> list[Path]:
    return sorted(DDG_SEARCHES_DIR.glob("ddg_search_*.json"))


def extract_official_data(company_info: dict, naf_map: dict) -> dict:
    """Map raw SIREN fields into clean nested dict for YAML official_data section."""
    siege = company_info.get("siege", {})
    complements = company_info.get("complements", {})
    primary_naf = company_info.get("activite_principale", "")
    naf_description = get_naf_description(primary_naf, naf_map)

    return {
        "siren": company_info.get("siren"),
        "name": company_info.get("nom_complet"),
        "size_category": company_info.get("categorie_entreprise"),
        "activity": {
            "code": primary_naf,
            "code_naf25": company_info.get("activite_principale_naf25"),
            "description": naf_description,
            "section": company_info.get("section_activite_principale"),
        },
        "legal_status": {
            "nature_juridique": company_info.get("nature_juridique"),
            "is_association": complements.get("est_association", False),
            "is_ess": complements.get("est_ess", False),
            "is_entrepreneur": complements.get("est_entrepreneur_individuel", False),
        },
        "location": {
            "address": siege.get("adresse", ""),
            "postal_code": siege.get("code_postal", ""),
            "city": siege.get("libelle_commune", ""),
            "department": siege.get("departement", ""),
            "region": siege.get("region", ""),
        },
        "establishment": {
            "total": company_info.get("nombre_etablissements"),
            "active": company_info.get("nombre_etablissements_ouverts"),
            "siret": siege.get("siret", ""),
        },
        "timeline": {
            "created": company_info.get("date_creation"),
            "activity_started": siege.get("date_debut_activite"),
        },
        "employment": {
            "headcount_band": company_info.get("tranche_effectif_salarie"),
            "headcount_year": company_info.get("annee_tranche_effectif_salarie"),
        },
    }


def build_prompt(company_info: dict, results: list, naf_map: dict) -> str:
    siege = company_info.get("siege", {})
    complements = company_info.get("complements", {})

    naf_code = company_info.get("activite_principale", "")
    naf_description = get_naf_description(naf_code, naf_map)
    city = siege.get("libelle_commune", siege.get("commune", ""))
    postal_code = siege.get("code_postal", "")

    legal_parts = []
    if complements.get("est_association"):
        legal_parts.append("association")
    if complements.get("est_ess"):
        legal_parts.append("ESS")
    if complements.get("est_entrepreneur_individuel"):
        legal_parts.append("entrepreneur individuel")
    legal = ", ".join(legal_parts) if legal_parts else "société"

    results_block_lines = []
    for i, r in enumerate(results[:8], 1):
        title = r.get("title", "").strip()
        url = r.get("url", "").strip()
        snippet = r.get("snippet", "").strip()[:120]
        results_block_lines.append(f"{i}. {title}\n   {url}\n   {snippet}")
    results_block = "\n".join(results_block_lines)

    return PROMPT_TEMPLATE.format(
        name=company_info.get("nom_complet", ""),
        naf_code=naf_code,
        naf_description=naf_description,
        city=city,
        postal_code=postal_code,
        legal=legal,
        results_block=results_block,
        n_results=min(len(results), 8),
    )


def parse_response(text: str) -> tuple[str, str, str]:
    """Parse BEST_URL / CONFIDENCE / SUMMARY from model output."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    best_url, confidence, summary = "NONE", "weak", ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("BEST_URL:"):
            best_url = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            raw = line.split(":", 1)[1].strip().lower()
            if raw in ("good", "maybe", "weak"):
                confidence = raw
        elif line.startswith("SUMMARY:"):
            summary = line.split(":", 1)[1].strip()
    return best_url, confidence, summary


def call_ollama(model: str, prompt: str) -> str:
    import ollama

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "num_ctx": 2048},
    )
    return response["message"]["content"]


def call_llamacpp(model: str, url: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=url, api_key="none")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=200,
    )
    return response.choices[0].message.content


def save_summary_yaml(
    siren: str,
    slug: str,
    confidence: str,
    official_data: dict,
    web_results: list,
    best_url: str,
    summary: str,
    author_tag: str,
    search_date: str | None,
    raw_response: str = "",
    elapsed_s: float | None = None,
) -> Path:
    VALIDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

    grp_size = (official_data.get("size_category") or "").lower() or "unk"
    city = (official_data.get("location", {}).get("city") or "").lower().replace(" ", "-") or "unk"
    filepath = VALIDATIONS_DIR / f"{siren}_{slug}_{grp_size}_{city}_{confidence}_{timestamp}.yaml"

    yaml_data = {
        "meta": {
            "siren": siren,
            "slug": slug,
            "generated_at": timestamp,
            "author": author_tag,
            "ddg_search_date": search_date,
        },
        "company": {
            "name": official_data.get("name"),
            "city": official_data.get("location", {}).get("city"),
            "size_category": official_data.get("size_category"),
            "naf_code": official_data.get("activity", {}).get("code"),
            "naf_label": official_data.get("activity", {}).get("description"),
            "is_ess": official_data.get("legal_status", {}).get("is_ess"),
            "is_association": official_data.get("legal_status", {}).get("is_association"),
        },
        "summary": {
            "confidence": confidence,
            "best_url": best_url,
            "summary": summary,
            "elapsed_s": round(elapsed_s, 2) if elapsed_s is not None else None,
        },
        "search_results": [
            {"url": r.get("url"), "title": r.get("title"), "snippet": r.get("snippet")}
            for r in web_results
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(
            yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False
        )

    return filepath


def already_summarized(siren: str) -> bool:
    return bool(list(VALIDATIONS_DIR.glob(f"{siren}_*.yaml"))) if VALIDATIONS_DIR.exists() else False


@click.command()
@click.option(
    "--provider",
    default="llamacpp",
    type=click.Choice(["ollama", "llamacpp"]),
    help="Inference backend",
)
@click.option("--model", default=None, help="Model name (defaults to provider default)")
@click.option("--llamacpp-url", default=LLAMACPP_URL, help="llama.cpp server base URL")
@click.option("--dry-run", is_flag=True, help="Print prompts without calling the LLM")
@click.option(
    "--skip-existing",
    is_flag=True,
    default=True,
    help="Skip SIRENs that already have a summary YAML",
)
@click.argument("sirens", nargs=-1)
def validate(provider, model, llamacpp_url, skip_existing, dry_run, sirens):
    """Build company summary cards from DDG search results using a local LLM.

    If SIRENs are provided, process only those. Otherwise process all DDG files.
    YAML cards are saved to data/company_data/web_presence_validations/.
    """
    if model is None:
        model = OLLAMA_MODEL if provider == "ollama" else LLAMACPP_MODEL
    author_tag = f"llm:{provider}:{model}"
    click.echo(f"LLM engine: {author_tag}")

    naf_map = load_naf_descriptions()

    if sirens:
        files = []
        for siren in sirens:
            matches = sorted(DDG_SEARCHES_DIR.glob(f"ddg_search_{siren}_*.json"))
            if not matches:
                click.echo(f"No DDG file for SIREN {siren}, skipping.", err=True)
            else:
                files.append(matches[-1])
    else:
        files = find_ddg_files()

    click.echo(f"Found {len(files)} DDG file(s) to process.", err=True)

    for path in files:
        data = load_ddg_file(path)
        company_info = data.get("company_info", {})
        siren = company_info.get("siren") or data.get("siren", path.stem.split("_")[2])
        name = company_info.get("nom_complet", siren)
        slug = data.get("slug", siren)

        if skip_existing and already_summarized(siren):
            click.echo(f"[skip]  {siren} {name} — already summarized", err=True)
            continue

        results = data.get("results", [])
        if not results:
            click.echo(f"[skip]  {siren} {name} — no search results", err=True)
            continue

        prompt = build_prompt(company_info, results, naf_map)

        if dry_run:
            click.echo(f"\n--- PROMPT for {siren} ({name}) ---")
            click.echo(prompt)
            continue

        click.echo(f"[llm]   {siren} {name} ...", err=True)
        t0 = time.perf_counter()
        try:
            if provider == "ollama":
                raw = call_ollama(model, prompt)
            else:
                raw = call_llamacpp(model, llamacpp_url, prompt)
        except Exception as e:
            click.echo(f"  ERROR calling {provider}: {e}", err=True)
            continue
        elapsed_s = time.perf_counter() - t0

        best_url, confidence, summary = parse_response(raw)
        click.echo(f"  → {confidence.upper():8s}  {elapsed_s:.1f}s  {summary[:80]}", err=True)

        official_data = extract_official_data(company_info, naf_map)
        yaml_path = save_summary_yaml(
            siren=siren,
            slug=slug,
            confidence=confidence,
            official_data=official_data,
            web_results=results[:8],
            best_url=best_url,
            summary=summary,
            author_tag=author_tag,
            search_date=data.get("search_date"),
            elapsed_s=elapsed_s,
        )
        click.echo(f"  → YAML: {yaml_path.name}", err=True)

    if not dry_run:
        click.echo(f"\nDone. YAMLs saved to {VALIDATIONS_DIR}", err=True)


if __name__ == "__main__":
    validate()
