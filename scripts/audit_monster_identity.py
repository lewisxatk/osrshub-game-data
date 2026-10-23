#!/usr/bin/env python3
"""Audit monster ID/name identity and numeric combat-field integrity."""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "dist" / "monsters-combat.json"
DEFAULT_OUTPUT = ROOT / "reports" / "monster-identity-audit.json"
NUMERIC_FIELDS = ("combat_level", "hitpoints", "attack_level", "strength_level",
                  "defence_level", "magic_level", "ranged_level", "attack_speed",
                  "max_hit", "slayer_level", "size")

def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids, names = defaultdict(list), defaultdict(list)
    invalid_numeric = []
    missing_ids, missing_names = [], []
    for index, row in enumerate(rows):
        rid, name = row.get("id"), row.get("name")
        if isinstance(rid, int) and not isinstance(rid, bool) and rid >= 0:
            ids[rid].append(index)
        else:
            missing_ids.append({"index": index, "name": name if isinstance(name, str) else ""})
        if isinstance(name, str) and name.strip():
            names[name.strip().casefold()].append({"index": index, "id": rid, "name": name.strip()})
        else:
            missing_names.append({"index": index, "id": rid})
        for field in NUMERIC_FIELDS:
            value = row.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                invalid_numeric.append({"index": index, "id": rid, "name": name or "", "field": field, "value": value})
    duplicate_ids = [{"id": key, "row_indexes": indexes} for key, indexes in sorted(ids.items()) if len(indexes) > 1]
    duplicate_names = [{"normalized_name": key, "records": value} for key, value in sorted(names.items()) if len(value) > 1]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not (duplicate_ids or invalid_numeric or missing_ids) else "review_required",
        "record_count": len(rows),
        "unique_valid_id_count": len(ids),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_name_group_count": len(duplicate_names),
        "missing_id_count": len(missing_ids),
        "missing_name_count": len(missing_names),
        "invalid_numeric_value_count": len(invalid_numeric),
        "duplicate_ids": duplicate_ids[:500],
        "duplicate_names": duplicate_names[:500],
        "missing_ids": missing_ids[:500],
        "missing_names": missing_names[:500],
        "invalid_numeric_values": invalid_numeric[:500],
        "truncation_limit_per_detail_list": 500,
        "guardrails": ["Names are normalized only for duplicate detection; variants are not automatically merged.",
                       "Missing and malformed values are reported, not repaired.",
                       "Duplicate names can be legitimate variants and require manual/source review."]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        parser.error("Input must be a JSON array of objects")
    result = audit(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "record_count", "duplicate_id_count",
          "duplicate_name_group_count", "missing_id_count", "invalid_numeric_value_count")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
