#!/usr/bin/env python3
"""Explain one OSRS game-data record with provenance and explicit uncertainty.

This is a database-only fact card. It never fetches the web or fills missing
fields with inferred values. A record can be structurally valid and still need
independent factual verification.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
DATASETS = {
    "items": "items.json",
    "equipment-stats": "equipment-stats.json",
    "weapons": "weapons.json",
    "item-requirements": "item-requirements.json",
    "item-combat-profiles": "item-combat-profiles.json",
    "monsters-combat": "monsters-combat.json",
    "quests": "quests.json",
    "quest-relationships": "quest-relationships.json",
    "item-relationships": "item-relationships.json",
}

def present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}

def load_rows(dataset: str, dist_dir: Path = DIST) -> list[dict[str, Any]]:
    if dataset not in DATASETS:
        raise ValueError(f"Unsupported dataset: {dataset}. Choose from: {', '.join(sorted(DATASETS))}")
    path = dist_dir / DATASETS[dataset]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Dataset '{dataset}' is unavailable or unreadable at {path}: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"Dataset '{dataset}' must contain a JSON array of objects")
    return value

def find_record(rows: list[dict[str, Any]], record_id: int | None = None, search: str | None = None) -> dict[str, Any] | None:
    if record_id is not None:
        for row in rows:
            candidate = row.get("id", row.get("item_id", row.get("quest_id")))
            if candidate == record_id:
                return row
        return None
    needle = (search or "").casefold().strip()
    if not needle:
        raise ValueError("Supply either --id or --search")
    matches = []
    for row in rows:
        searchable = " ".join(str(row.get(k, "")) for k in ("name", "key", "title", "id", "item_id", "quest_id"))
        if needle in searchable.casefold():
            matches.append(row)
    return matches[0] if matches else None

def provenance(record: dict[str, Any]) -> dict[str, Any]:
    urls = record.get("source_urls")
    if not present(urls):
        urls = [record.get(k) for k in ("source_url", "url") if present(record.get(k))]
    return {
        "source_urls": urls if present(urls) else [],
        "source_fields_present": [k for k in record if k.startswith("source_") or k in ("retrieved_at", "source_sha256", "provenance")],
        "has_source_url": bool(present(urls)),
        "warning": "A retained source URL is provenance, not proof of independent verification."
    }

def build_fact_card(dataset: str, record: dict[str, Any] | None) -> dict[str, Any]:
    if record is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "not_found",
            "dataset": dataset,
            "record": None,
            "fact_count": 0,
            "known_fields": [],
            "unknown_fields": [],
            "provenance": {"source_urls": [], "source_fields_present": [], "has_source_url": False},
            "guardrails": ["A missing record is unknown, not evidence that the game entity or mechanic does not exist."]
        }
    known = sorted(k for k, v in record.items() if v is not None and v != "" and not k.startswith("_"))
    known_empty = sorted(k for k, v in record.items() if v in ([], {}) and not k.startswith("_"))
    unknown = sorted(k for k, v in record.items() if (v is None or v == "") and not k.startswith("_"))
    p = provenance(record)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "found",
        "dataset": dataset,
        "record": record,
        "fact_count": len(known),
        "known_fields": known,
        "known_empty_fields": known_empty,
        "unknown_fields": unknown,
        "provenance": p,
        "guardrails": [
            "Values are read directly from the generated dataset; no missing fact is inferred.",
            "Known means present in this record, not independently verified as correct.",
            "Prices, eligibility, DPS and unlocks must not be inferred unless explicit fields and verified rules support them."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=sorted(DATASETS))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", type=int)
    group.add_argument("--search")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    try:
        rows = load_rows(args.dataset)
        record = find_record(rows, record_id=args.id, search=args.search)
    except ValueError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    card = build_fact_card(args.dataset, record)
    print(json.dumps(card, ensure_ascii=False, indent=2))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if record is not None else 2

if __name__ == "__main__":
    raise SystemExit(main())
