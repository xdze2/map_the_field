"""
Bootstrap nodes from existing SIREN + DDG data.

Creates data/nodes/{node_id}/ folders with:
  meta.json, triage.jsonl, sources/, summary_history/

Writes an initial summary from SIREN fields + DDG snippets (or a Google search link).
Updates data/nodes/index.jsonl.

Usage:
    python tools/bootstrap_nodes.py
    python tools/bootstrap_nodes.py --dry-run
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SIRENE_DIR = ROOT / "data/company_data/sirene_searches"
DDG_DIR = ROOT / "data/company_data/ddg_searches"
NODES_DIR = ROOT / "data/nodes"
INDEX_FILE = NODES_DIR / "index.jsonl"

NAF_LABELS = {
    "62.01Z": "Programmation informatique",
    "62.02A": "Conseil en systèmes et logiciels informatiques",
    "62.02B": "Tierce maintenance de systèmes et applications informatiques",
    "62.03Z": "Gestion d'installations informatiques",
    "62.09Z": "Autres activités informatiques",
    "63.11Z": "Traitement de données, hébergement et activités connexes",
    "63.12Z": "Portails Internet",
    "72.19Z": "Autre recherche-développement en sciences physiques et naturelles",
    "72.20Z": "Recherche-développement en sciences humaines et sociales",
    "85.59B": "Autres enseignements",
}


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:50]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def tranche_label(code: str | None) -> str | None:
    table = {
        "00": "0 salarié",
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
    return table.get(code) if code else None


def load_ddg(siren: str) -> dict | None:
    matches = sorted(DDG_DIR.glob(f"ddg_search_{siren}_*.json"))
    if not matches:
        return None
    with open(matches[-1]) as f:
        return json.load(f)


def build_meta(record: dict) -> dict:
    siege = record.get("siege", {})
    return {
        "node_id": f"siren{record['siren']}",
        "type": "company",
        "name": record.get("nom_complet") or record.get("nom_raison_sociale"),
        "identifiers": {
            "siren": record["siren"],
        },
        "naf": record.get("activite_principale"),
        "naf_label": NAF_LABELS.get(record.get("activite_principale", ""), None),
        "address": siege.get("adresse"),
        "city": siege.get("libelle_commune"),
        "postal_code": siege.get("code_postal"),
        "headcount_range": tranche_label(siege.get("tranche_effectif_salarie")),
        "created_at": now_iso(),
        "source": "siren_bootstrap",
    }


def build_summary(record: dict, ddg: dict | None) -> str:
    name = record.get("nom_complet") or record.get("nom_raison_sociale")
    siege = record.get("siege", {})
    naf = record.get("activite_principale", "")
    naf_label = NAF_LABELS.get(naf, naf)
    city = siege.get("libelle_commune", "")
    headcount = tranche_label(siege.get("tranche_effectif_salarie"))
    est_ess = record.get("complements", {}).get("est_ess", False)
    est_association = record.get("complements", {}).get("est_association", False)

    lines = [f"# {name}", ""]
    tags = []
    if est_ess:
        tags.append("ESS")
    if est_association:
        tags.append("association")
    if tags:
        lines += [f"**Tags:** {', '.join(tags)}", ""]

    lines += [
        "## Info",
        f"- **Activité:** {naf_label} ({naf})",
        f"- **Ville:** {city}",
    ]
    if headcount:
        lines.append(f"- **Effectif:** {headcount} salariés")
    lines.append("")

    if ddg:
        results = ddg.get("results", [])[:10]
        if results:
            lines += ["## Sources DDG", ""]
            for r in results:
                title = r.get("title", r["url"])
                url = r["url"]
                snippet = r.get("snippet", "")
                lines.append(f"- [{title}]({url})")
                if snippet:
                    lines.append(f"  {snippet}")
            lines.append("")
        else:
            lines += _google_fallback(name)
    else:
        lines += _google_fallback(name)

    return "\n".join(lines)


def _google_fallback(name: str) -> list[str]:
    query = name.replace(" ", "+")
    url = f"https://www.google.com/search?q={query}"
    return ["## Sources", "", f"- [Google: {name}]({url})", ""]


def bootstrap_node(record: dict, dry_run: bool) -> tuple[str, str]:
    """Returns (node_id, action) where action is 'created' or 'skipped'."""
    node_id = f"siren{record['siren']}"
    node_dir = NODES_DIR / node_id

    if node_dir.exists():
        return node_id, "skipped"

    if dry_run:
        return node_id, "would_create"

    node_dir.mkdir(parents=True)
    (node_dir / "sources").mkdir()
    (node_dir / "summary_history").mkdir()

    meta = build_meta(record)
    (node_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    (node_dir / "triage.jsonl").write_text("")

    ddg = load_ddg(record["siren"])
    summary = build_summary(record, ddg)
    ts = now_iso()
    summary_file = node_dir / "summary_history" / f"summary_{ts}_siren_bootstrap.md"
    summary_file.write_text(summary)

    return node_id, "created"


def rebuild_index(dry_run: bool) -> list[dict]:
    entries = []
    for meta_file in sorted(NODES_DIR.glob("*/meta.json")):
        meta = json.loads(meta_file.read_text())
        node_dir = meta_file.parent

        # current rank: last entry in triage.jsonl
        triage_file = node_dir / "triage.jsonl"
        current_rank = None
        if triage_file.exists():
            lines = [l for l in triage_file.read_text().splitlines() if l.strip()]
            if lines:
                current_rank = json.loads(lines[-1]).get("rank")

        # last updated: latest summary timestamp or meta created_at
        summaries = sorted((node_dir / "summary_history").glob("summary_*.md"))
        updated_at = summaries[-1].stem.split("_")[1] if summaries else meta.get("created_at", "")

        entries.append({
            "node_id": meta["node_id"],
            "name": meta["name"],
            "type": meta["type"],
            "current_rank": current_rank,
            "updated_at": updated_at,
        })

    if not dry_run:
        NODES_DIR.mkdir(parents=True, exist_ok=True)
        with open(INDEX_FILE, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if not SIRENE_DIR.exists():
        print(f"ERROR: {SIRENE_DIR} not found", file=sys.stderr)
        sys.exit(1)

    NODES_DIR.mkdir(parents=True, exist_ok=True)

    created = skipped = 0
    for jsonl_file in sorted(SIRENE_DIR.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                node_id, action = bootstrap_node(record, dry_run=args.dry_run)
                if action == "created":
                    created += 1
                    print(f"  created  {node_id}")
                elif action == "would_create":
                    created += 1
                    print(f"  [dry-run] would create  {node_id}")
                else:
                    skipped += 1

    print(f"\n{created} nodes created, {skipped} skipped (already exist)")

    if not args.dry_run:
        entries = rebuild_index(dry_run=False)
        print(f"index.jsonl updated — {len(entries)} nodes")
    else:
        print("[dry-run] index.jsonl not written")


if __name__ == "__main__":
    main()
