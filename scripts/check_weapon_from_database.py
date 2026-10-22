#!/usr/bin/env python3
"""Inspect one weapon strictly from the generated OSRS Hub database; never fetch external sources."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DATASET = "item-combat-profiles.json"


def check_weapon(item_id: int, dist_dir: Path = DIST) -> dict[str, Any]:
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
        return {"status": "failed", "error": "item ID must be a non-negative integer"}
    path = dist_dir / DATASET
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "unavailable", "item_id": item_id, "error": f"{DATASET} is missing; run the data pipeline first"}
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "failed", "item_id": item_id, "error": f"cannot read {DATASET}: {exc}"}
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {"status": "failed", "item_id": item_id, "error": f"{DATASET} must be an array of objects"}
    matches = [row for row in rows if row.get("id") == item_id]
    if len(matches) > 1:
        return {"status": "failed", "item_id": item_id, "error": f"duplicate item ID {item_id} in {DATASET}"}
    if not matches:
        return {"status": "not_found", "item_id": item_id, "dataset": DATASET, "message": "No matching database record"}
    row = matches[0]
    is_weapon = row.get("slot") == "weapon" or row.get("weapon_record_present") is True
    if not is_weapon:
        return {"status": "not_a_weapon_record", "item_id": item_id, "name": row.get("name"), "dataset": DATASET}
    return {
        "status": "ok" if row.get("weapon_record_present") is True else "review_required",
        "dataset": DATASET,
        "item_id": row.get("id"),
        "name": row.get("name"),
        "slot": row.get("slot"),
        "bonuses": row.get("bonuses"),
        "attack_speed": row.get("attack_speed"),
        "weapon_type": row.get("weapon_type"),
        "stances": row.get("stances"),
        "skill_requirements": row.get("skill_requirements"),
        "weapon_record_present": row.get("weapon_record_present"),
        "data_status": row.get("data_status"),
        "sources": row.get("sources", []),
        "source_urls": row.get("source_urls", []),
        "guardrails": [
            "All displayed facts are read from the generated OSRS Hub dataset.",
            "Source URLs are provenance metadata only; this checker does not fetch external websites.",
            "Missing or null values remain unknown and are not replaced with guessed values.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", type=int, required=True, help="OSRS item ID to look up in dist/item-combat-profiles.json")
    args = parser.parse_args()
    result = check_weapon(args.id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"failed", "unavailable", "not_found", "not_a_weapon_record"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
