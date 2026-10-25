#!/usr/bin/env python3
"""Audit only explicit NPC/monster ID links between the generated drop and monster datasets."""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MONSTERS = ROOT / "dist" / "monsters-combat.json"
DEFAULT_DROPS = ROOT / "dist" / "npc-drops.json"
DEFAULT_OUTPUT = ROOT / "reports" / "monster-drop-link-audit.json"
ID_KEYS = ("npc_id", "monster_id", "npcId", "monsterId", "id")

def read_array(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{path} must contain a JSON array of objects")
    return data

def explicit_id(row: dict[str, Any]) -> int | None:
    for key in ID_KEYS:
        value = row.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None

def audit_links(monsters: list[dict[str, Any]], drops: list[dict[str, Any]]) -> dict[str, Any]:
    known = {row.get("id") for row in monsters if isinstance(row.get("id"), int) and not isinstance(row.get("id"), bool)}
    linked, unresolved, orphaned = [], [], []
    for index, row in enumerate(drops):
        rid = explicit_id(row)
        item = {"index": index, "explicit_npc_id": rid, "source_key": row.get("source_key")}
        if rid is None:
            unresolved.append(item)
        elif rid in known:
            linked.append(item)
        else:
            orphaned.append(item)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "review_required" if orphaned else "passed",
        "monster_record_count": len(monsters),
        "monster_numeric_id_count": len(known),
        "drop_record_count": len(drops),
        "explicit_link_count": len(linked),
        "unresolved_drop_record_count": len(unresolved),
        "orphan_explicit_link_count": len(orphaned),
        "explicit_link_coverage_percent": round(100*len(linked)/len(drops), 2) if drops else 0.0,
        "linked_examples": linked[:100],
        "unresolved_examples": unresolved[:100],
        "orphan_examples": orphaned[:100],
        "details_limit_per_group": 100,
        "guardrails": ["Only explicit numeric IDs are joined; names and source keys are not treated as IDs.",
                       "Unresolved rows are not automatically called orphans.",
                       "Different source datasets can use different ID domains; reported orphan links need review.",
                       "This audit does not infer or generate drop rates."]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monsters", type=Path, default=DEFAULT_MONSTERS)
    parser.add_argument("--drops", type=Path, default=DEFAULT_DROPS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = audit_links(read_array(args.monsters), read_array(args.drops))
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "monster_record_count", "drop_record_count",
          "explicit_link_count", "unresolved_drop_record_count", "orphan_explicit_link_count")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
