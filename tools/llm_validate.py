#!/usr/bin/env python3
"""Batch validate company web presence using a local LLM (Ollama or llama.cpp)."""
import csv
import json
from datetime import datetime
from pathlib import Path

import click

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMPANY_DATA_DIR = DATA_DIR / "company_data"
DDG_SEARCHES_DIR = COMPANY_DATA_DIR / "ddg_searches"
STATUS_CSV = COMPANY_DATA_DIR / "insights" / "status.csv"
NAF_CODES_FILE = SCRIPT_DIR / "siren_infos" / "naf_codes.csv"

OLLAMA_MODEL = "qwen3:4b"
LLAMACPP_MODEL = "qwen2.5-3b-instruct-q4_k_m.gguf"
LLAMACPP_URL = "http://localhost:8083/v1"

PROMPT_TEMPLATE = """You are validating whether web search results match a company from the French official registry (SIREN).

Official registry data:
- Name: {name}
- Activity (NAF code): {naf_code} — {naf_description}
- City: {city} ({postal_code})
- Legal: {legal}

Web search results:
{results_block}

Does any result clearly match this company (same name, same city, same activity)?

Reply in exactly this format (3 lines, no other text):
MATCH: <result number 1-{n_results} or NONE>
CONFIDENCE: <good|strange|wrong>
REASON: <one sentence>
"""


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
        click.echo(f"Warning: could not load NAF codes: {e}", err=True)
    return naf_map


def get_naf_description(naf_code: str, naf_map: dict) -> str:
    if naf_code in naf_map:
        return naf_map[naf_code]
    base = naf_code.rstrip("Z")
    return naf_map.get(base, f"NAF {naf_code}")


def load_ddg_file(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_ddg_files() -> list[Path]:
    return sorted(DDG_SEARCHES_DIR.glob("ddg_search_*.json"))


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
    """Parse MATCH / CONFIDENCE / REASON from model output. Returns (match, confidence, reason)."""
    # Strip <think>...</think> block if thinking leaked into content
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    match, confidence, reason = "NONE", "strange", ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("MATCH:"):
            match = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            raw = line.split(":", 1)[1].strip().lower()
            if raw in ("good", "strange", "wrong"):
                confidence = raw
        elif line.startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    return match, confidence, reason


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


def append_status(siren: str, confidence: str, reason: str, name: str, author_tag: str) -> None:
    STATUS_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not STATUS_CSV.exists()
    with open(STATUS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["siren", "status", "reason", "notes", "date", "author"])
        writer.writerow([
            siren,
            confidence,
            reason,
            name,
            datetime.now().strftime("%Y-%m-%d"),
            author_tag,
        ])


def already_validated(siren: str) -> bool:
    if not STATUS_CSV.exists():
        return False
    with open(STATUS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return any(row["siren"] == siren for row in reader)


@click.command()
@click.option("--provider", default="llamacpp", type=click.Choice(["ollama", "llamacpp"]), help="Inference backend")
@click.option("--model", default=None, help="Model name (defaults to provider default)")
@click.option("--llamacpp-url", default=LLAMACPP_URL, help="llama.cpp server base URL")
@click.option("--skip-existing", is_flag=True, default=True, help="Skip SIRENs already in status.csv")
@click.option("--dry-run", is_flag=True, help="Print prompts without calling the LLM")
@click.argument("sirens", nargs=-1)
def validate(provider, model, llamacpp_url, skip_existing, dry_run, sirens):
    """Validate company web presence using a local LLM (Ollama or llama.cpp).

    If SIRENs are provided, validate only those. Otherwise validate all DDG files.
    Results are appended to data/company_data/insights/status.csv.
    """
    if model is None:
        model = OLLAMA_MODEL if provider == "ollama" else LLAMACPP_MODEL
    author_tag = f"llm:{provider}:{model}"

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

        if skip_existing and already_validated(siren):
            click.echo(f"[skip]  {siren} {name} — already in status.csv", err=True)
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
        try:
            if provider == "ollama":
                raw = call_ollama(model, prompt)
            else:
                raw = call_llamacpp(model, llamacpp_url, prompt)
        except Exception as e:
            click.echo(f"  ERROR calling {provider}: {e}", err=True)
            continue

        match, confidence, reason = parse_response(raw)
        click.echo(f"  → {confidence.upper():8s}  match={match}  {reason}", err=True)

        append_status(siren, confidence, reason, name, author_tag)

    if not dry_run:
        click.echo(f"\nDone. Results appended to {STATUS_CSV}", err=True)


if __name__ == "__main__":
    validate()
