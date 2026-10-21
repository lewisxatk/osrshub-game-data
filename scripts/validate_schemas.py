#!/usr/bin/env python3
"""Validate generated datasets and selected reports against repository JSON Schemas."""
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SCHEMAS = ROOT / "schemas"
REPORTS = ROOT / "reports"
DATA_TARGETS = (
    ("items.json", "item.schema.json"),
    ("monsters-combat.json", "monster-combat.schema.json"),
    ("equipment-stats.json", "equipment-stats.schema.json"),
    ("weapons.json", "weapon.schema.json"),
    ("item-relationships.json", "item-relationships.schema.json"),
    ("item-requirements.json", "item-requirements.schema.json"),
    ("quests.json", "quests.schema.json"),
    ("quest-relationships.json", "quest-relationships.schema.json"),
)
REPORT_TARGETS = (
    ("item-eligibility.json", "item-eligibility.schema.json"),
    ("equipment-shortlist.json", "equipment-shortlist.schema.json"),
    ("weapon-baseline-comparison.json", "weapon-baseline-comparison.schema.json"),
    ("equipment-loadout-candidate.json", "equipment-loadout-candidate.schema.json"),
    ("combat-input-audit.json", "combat-input-audit.schema.json"),
)

def load_schema(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)

def validate_file(data_path, schema_path, errors, checked, is_array):
    if not data_path.exists():
        errors.append({"file": str(data_path.relative_to(ROOT)), "error": "missing dataset/report"})
        return
    if not schema_path.exists():
        errors.append({"file": str(schema_path.relative_to(ROOT)), "error": "missing schema"})
        return
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        validator = load_schema(schema_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append({"file": str(data_path.relative_to(ROOT)), "error": f"invalid JSON/schema: {exc}"})
        return
    if is_array and not isinstance(data, list):
        errors.append({"file": str(data_path.relative_to(ROOT)), "error": "expected a JSON array"})
        return
    records = data if is_array else [data]
    checked[str(data_path.relative_to(ROOT))] = {"records": len(records), "invalid_records": 0}
    for index, row in enumerate(records):
        record_errors = sorted(validator.iter_errors(row), key=lambda err: list(map(str, err.path)))
        if record_errors:
            checked[str(data_path.relative_to(ROOT))]["invalid_records"] += 1
            for err in record_errors[:5]:
                errors.append({
                    "file": str(data_path.relative_to(ROOT)),
                    "record_index": index if is_array else None,
                    "record_id": row.get("id") if isinstance(row, dict) else None,
                    "path": ".".join(str(part) for part in err.path),
                    "error": err.message,
                })
        if len(errors) >= 100:
            errors.append({"error": "Further errors omitted after 100 reported issues"})
            return

def main():
    errors, checked = [], {}
    for data_name, schema_name in DATA_TARGETS:
        validate_file(DIST / data_name, SCHEMAS / schema_name, errors, checked, True)
    for data_name, schema_name in REPORT_TARGETS:
        validate_file(REPORTS / data_name, SCHEMAS / schema_name, errors, checked, False)
    result = {
        "status": "failed" if errors else "passed",
        "datasets": checked, "error_count": len(errors), "errors": errors,
        "note": "Schema validation checks record shape and types; it does not prove OSRS values are factually correct."
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "schema-validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
