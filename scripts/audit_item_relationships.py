#!/usr/bin/env python3
"""Audit explicit item relationship links against their normalized source datasets."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

RELATION_TYPES = {
    "has_equipment_stats": ("equipment-stats.json", "id"),
    "has_weapon_data": ("weapons.json", "id"),
    "has_skill_requirements": ("item-requirements.json", "item_id"),
    "has_combat_profile": ("item-combat-profiles.json", "id"),
}


def load_array(name):
    try:
        value = json.loads((DIST / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read dist/{name}: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"dist/{name} must be an array of objects")
    return value


def unique_index(rows, dataset, id_field="id"):
    result = {}
    for index, row in enumerate(rows):
        value = row.get(id_field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{dataset}[{index}] has invalid {id_field}")
        if value in result:
            raise ValueError(f"{dataset} contains duplicate {id_field} {value}")
        result[value] = row
    return result


def audit_relationships(datasets):
    required = ("items.json", "item-relationships.json", *[v[0] for v in RELATION_TYPES.values()])
    missing = [name for name in required if name not in datasets]
    if missing:
        raise ValueError("Missing input datasets: " + ", ".join(missing))

    item_index = unique_index(datasets["items.json"], "items.json")
    target_indexes = {
        relation_type: unique_index(datasets[filename], filename, id_field)
        for relation_type, (filename, id_field) in RELATION_TYPES.items()
    }
    errors = []
    warnings = []
    observed = {}
    for index, row in enumerate(datasets["item-relationships.json"]):
        item_id = row.get("item_id")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id not in item_index:
            errors.append({"index": index, "issue": "orphan_or_invalid_item_id", "item_id": item_id})
            continue
        if item_id in observed:
            errors.append({"index": index, "issue": "duplicate_relationship_item", "item_id": item_id})
            continue
        rels = row.get("relationships")
        if not isinstance(rels, list):
            errors.append({"index": index, "issue": "relationships_not_array", "item_id": item_id})
            continue
        seen_types = set()
        observed[item_id] = seen_types
        if row.get("item_name") != item_index[item_id].get("name", ""):
            errors.append({"index": index, "issue": "item_name_mismatch", "item_id": item_id})
        if not isinstance(row.get("sources"), list):
            errors.append({"index": index, "issue": "sources_not_array", "item_id": item_id})
        elif not row["sources"]:
            warnings.append({"index": index, "issue": "item_source_labels_missing", "item_id": item_id})
        for rel_index, rel in enumerate(rels):
            if not isinstance(rel, dict):
                errors.append({"index": index, "relationship_index": rel_index, "issue": "relationship_not_object"})
                continue
            kind = rel.get("type")
            if kind not in RELATION_TYPES:
                errors.append({"index": index, "relationship_index": rel_index, "issue": "unknown_relationship_type", "type": kind})
                continue
            if kind in seen_types:
                errors.append({"index": index, "relationship_index": rel_index, "issue": "duplicate_relationship_type", "item_id": item_id, "type": kind})
            seen_types.add(kind)
            expected_dataset, _ = RELATION_TYPES[kind]
            if rel.get("dataset") != expected_dataset:
                errors.append({"index": index, "relationship_index": rel_index, "issue": "relationship_dataset_mismatch", "item_id": item_id, "type": kind})
            record_id = rel.get("record_id")
            if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id not in target_indexes[kind]:
                errors.append({"index": index, "relationship_index": rel_index, "issue": "orphan_relationship_target", "item_id": item_id, "type": kind, "record_id": record_id})
            elif record_id != item_id:
                errors.append({"index": index, "relationship_index": rel_index, "issue": "cross_item_join_mismatch", "item_id": item_id, "type": kind, "record_id": record_id})

    expected_links = 0
    missing_links = []
    for item_id in item_index:
        expected = {kind for kind, index in target_indexes.items() if item_id in index}
        expected_links += len(expected)
        actual = observed.get(item_id, set())
        for kind in sorted(expected - actual):
            missing_links.append({"item_id": item_id, "type": kind})
        for kind in sorted(actual - expected):
            errors.append({"issue": "unexpected_relationship", "item_id": item_id, "type": kind})
    if missing_links:
        errors.extend({"issue": "missing_relationship", **entry} for entry in missing_links[:300])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("review_required" if warnings else "passed"),
        "counts": {
            "items": len(item_index),
            "relationship_records": len(datasets["item-relationships.json"]),
            "expected_links": expected_links,
            "missing_links": len(missing_links),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
        "errors": errors[:500],
        "warnings": warnings[:200],
        "guardrails": [
            "Only explicit matching numeric IDs are validated; no game facts are inferred.",
            "Missing requirements or profiles are not interpreted as proof that none exist.",
            "A passing graph audit proves join consistency, not OSRS factual accuracy.",
        ],
    }


def main():
    try:
        names = ("items.json", "item-relationships.json", "equipment-stats.json", "weapons.json",
                 "item-requirements.json", "item-combat-profiles.json")
        report = audit_relationships({name: load_array(name) for name in names})
    except ValueError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "item-relationship-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
