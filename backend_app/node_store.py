"""
Node data access — single interface for all node I/O.
No direct file access to data/nodes/ outside this module.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend_app.utils import now_iso, now_ts

NODES_DIR = Path(__file__).parent.parent / "data/nodes"
INDEX_FILE = NODES_DIR / "index.jsonl"


@dataclass
class IndexEntry:
    node_id: str
    name: str
    type: str
    naf: str | None = None
    city: str | None = None
    headcount: str | None = None
    tags: list[str] = field(default_factory=list)
    current_rank: int | None = None
    updated_at: str = ""


def parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def read_node(node_id: str) -> dict | None:
    node_dir = NODES_DIR / node_id
    if not node_dir.exists():
        return None

    meta = json.loads((node_dir / "meta.json").read_text(encoding="utf-8"))

    summaries = sorted((node_dir / "summary_history").glob("summary_*.md"))
    summary_md = summaries[-1].read_text(encoding="utf-8") if summaries else ""
    summary_file = summaries[-1].name if summaries else None

    triage_entries = _read_triage(node_dir)
    current_rank = triage_entries[-1].get("rank") if triage_entries else None

    sources = _read_sources(node_dir)

    return {
        "node_id": node_id,
        "meta": meta,
        "summary_md": summary_md,
        "summary_file": summary_file,
        "current_rank": current_rank,
        "triage": triage_entries,
        "sources": sources,
    }


def write_summary(node_id: str, content: str, author: str) -> str:
    """Save summary file, append triage entry, rebuild index. Returns filename."""
    node_dir = NODES_DIR / node_id
    summary_dir = node_dir / "summary_history"
    summary_dir.mkdir(parents=True, exist_ok=True)

    ts = now_ts()
    filename = f"summary_{ts}_{author}.md"
    (summary_dir / filename).write_text(content, encoding="utf-8")

    _append_triage(node_dir, {"timestamp": now_iso(), "action": "summary", "author": author})

    rebuild_index()
    return filename


def write_rank(node_id: str, rank: int, note: str = "") -> dict:
    """Append rank to triage, rebuild index. Returns the triage entry."""
    node_dir = NODES_DIR / node_id
    entry = {"timestamp": now_iso(), "rank": rank, "note": note}
    _append_triage(node_dir, entry)
    rebuild_index()
    return entry


def write_capture(node_id: str, url: str, markdown: str | None, meta: dict) -> str:
    """Save source files (markdown + json). Returns base filename."""
    import hashlib
    from urllib.parse import urlparse

    node_dir = NODES_DIR / node_id
    sources_dir = node_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    parsed = urlparse(url)
    slug = re.sub(r"[^a-z0-9]+", "-", (parsed.netloc + parsed.path).lower()).strip("-")[:40]
    base = f"{url_hash}_{slug}_{now_ts()}"

    if markdown:
        (sources_dir / f"{base}.md").write_text(markdown, encoding="utf-8")
    (sources_dir / f"{base}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return base


def rebuild_index() -> list[dict]:
    """Full recompute of index.jsonl from disk."""
    entries = []
    for meta_file in sorted(NODES_DIR.glob("*/meta.json")):
        node_dir = meta_file.parent
        meta = json.loads(meta_file.read_text(encoding="utf-8"))

        triage_entries = _read_triage(node_dir)
        current_rank = triage_entries[-1].get("rank") if triage_entries else None

        summaries = sorted((node_dir / "summary_history").glob("summary_*.md"))
        if summaries:
            fm = parse_frontmatter(summaries[-1].read_text(encoding="utf-8"))
            updated_at = summaries[-1].stem.split("_")[1]
        else:
            fm = {}
            updated_at = meta.get("created_at", "")

        entry = IndexEntry(
            node_id=meta["node_id"],
            name=meta["name"],
            type=meta["type"],
            naf=meta.get("naf"),
            city=meta.get("city"),
            headcount=meta.get("headcount_range"),
            tags=fm.get("tags") or [],
            current_rank=current_rank,
            updated_at=updated_at,
        )
        entries.append(entry.__dict__)

    NODES_DIR.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, ensure_ascii=False) for e in entries]
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


# ── Internal helpers ───────────────────────────────────────────────────────────

def _read_triage(node_dir: Path) -> list[dict]:
    triage_file = node_dir / "triage.jsonl"
    if not triage_file.exists():
        return []
    entries = []
    for line in triage_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def _read_sources(node_dir: Path) -> list[dict]:
    sources_dir = node_dir / "sources"
    if not sources_dir.exists():
        return []
    sources = []
    for f in sorted(sources_dir.glob("*.json")):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
            s["_file"] = f.name
            sources.append(s)
        except json.JSONDecodeError:
            pass
    return sources


def _append_triage(node_dir: Path, entry: dict) -> None:
    triage_file = node_dir / "triage.jsonl"
    with triage_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
