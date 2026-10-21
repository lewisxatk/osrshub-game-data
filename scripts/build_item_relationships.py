#!/usr/bin/env python3
"""Build explicit item-to-equipment/weapon relationships from normalized records."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def load_array(filename):
    path = DIST / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"dist/{filename} must be a JSON array")
    return data


def index_by_id(rows, filename):
    indexed = {}
    duplicates = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{filename}[{index}] must be an object")
        rid = row.get("id")
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            raise ValueError(f"{filename}[{index}] must have a non-negative integer id")
        if rid in indexed:
            duplicates.append(rid)
        indexed[rid] = row
    if duplicates:
        raise ValueError(f"{filename} contains duplicate IDs: {sorted(set(duplicates))[:25]}")
    return indexed


def build_relationships(items, equipment, weapons):
    equipment_by_id = index_by_id(equipment, "equipment-stats.json")
    weapons_by_id = index_by_id(weapons, "weapons.json")
    relationships = []
    summary = {
        "item_count": len(items),
        "items_with_equipment_stats": 0,
        "items_with_weapon_data": 0,
        "items_with_both": 0,
        "equipment_records_without_item": 0,
        "weapon_records_without_item": 0,
    }
    item_index = index_by_id(items, "items.json")
    for rid, item in sorted(item_index.items()):
        equipment_record = equipment_by_id.get(rid)
        weapon_record = weapons_by_id.get(rid)
        links = []
        if equipment_record is not None:
            links.append({
                "type": "has_equipment_stats",
                "dataset": "equipment-stats.json",
                "record_id": rid,
                "slot": equipment_record.get("slot"),
            })
            summary["items_with_equipment_stats"] += 1
        if weapon_record is not None:
            links.append({
                "type": "has_weapon_data",
                "dataset": "weapons.json",
                "record_id": rid,
                "weapon_type": weapon_record.get("weapon_type"),
                "attack_speed": weapon_record.get("attack_speed"),
            })
            summary["items_with_weapon_data"] += 1
        if equipment_record is not None and weapon_record is not None:
            summary["items_with_both"] += 1
        if links:
            relationships.append({
                "item_id": rid,
                "item_name": item.get("name", ""),
                "relationships": links,
                "sources": item.get("sources", []),
            })
    summary["equipment_records_without_item"] = len(set(equipment_by_id) - set(item_index))
    summary["weapon_records_without_item"] = len(set(weapons_by_id) - set(item_index))
    return relationships, summary


def main():
    try:
        items = load_array("items.json")
        equipment = load_array("equipment-stats.json")
        weapons = load_array("weapons.json")
        relationships, summary = build_relationships(items, equipment, weapons)
        errors = []
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        relationships, summary, errors = [], {}, [str(exc)]
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (DIST / "item-relationships.json").write_text(
        json.dumps(relationships, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "summary": summary,
        "relationship_record_count": len(relationships),
        "errors": errors,
        "meaning": "Only explicit links to existing normalized records are emitted. Missing relationships are not inferred, and this is not a full item lifecycle or recipe graph.",
    }
    (REPORTS / "item-relationship-coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
