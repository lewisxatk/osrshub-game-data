#!/usr/bin/env python3
"""Validate generated datasets against the repository's JSON Schemas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SCHEMAS = ROOT / "schemas"
REPORTS = ROOT / "reports"
TARGETS = (
    ("items.json", "item.schema.json"),
    ("monsters-combat.json", "monster-combat.schema.json"),
    ("equipment-stats.json", "equipment-stats.schema.json"),
    ("weapons.json", "weapon.schema.json"),
)


def main():
    errors = []
    checked = {}
    for data_name, schema_name in TARGETS:
        data_path = DIST / data_name
        schema_path = SCHEMAS / schema_name
        if not data_path.exists():
            errors.append({"file": str(data_path.relative_to(ROOT)), "error": "missing dataset"})
            continue
        if not schema_path.exists():
            errors.append({"file": str(schema_path.relative_to(ROOT)), "error": "missing schema"})
            continue
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append({"file": str(schema_path.relative_to(ROOT)), "error": f"invalid JSON/schema: {exc}"})
            continue
        validator = Draft202012Validator(schema)
        if not isinstance(data, list):
            errors.append({"file": str(data_path.relative_to(ROOT)), "error": "expected a JSON array"})
            continue
        checked[data_name] = {"records": len(data), "invalid_records": 0}
        for index, row in enumerate(data):
            record_errors = sorted(validator.iter_errors(row), key=lambda err: list(map(str, err.path)))
            if record_errors:
                checked[data_name]["invalid_records"] += 1
                for err in record_errors[:5]:
                    errors.append({
                        "file": str(data_path.relative_to(ROOT)),
                        "record_index": index,
                        "record_id": row.get("id") if isinstance(row, dict) else None,
                        "path": ".".join(str(part) for part in err.path),
                        "error": err.message,
                    })
                if len(errors) >= 100:
                    errors.append({"error": "Further errors omitted after 100 reported issues"})
                    break
    result = {
        "status": "failed" if errors else "passed",
        "datasets": checked,
        "error_count": len(errors),
        "errors": errors,
        "note": "Schema validation checks record shape and types; it does not prove OSRS values are factually correct.",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "schema-validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
