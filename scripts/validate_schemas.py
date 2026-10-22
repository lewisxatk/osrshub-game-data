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
    ("item-combat-profiles.json", "item-combat-profile.schema.json"),
    ("weapons.json", "weapon.schema.json"),
    ("item-relationships.json", "item-relationships.schema.json"),
    ("item-requirements.json", "item-requirements.schema.json"),
    ("quests.json", "quests.schema.json"),
    ("quest-relationships.json", "quest-relationships.schema.json"),
)
REPORT_TARGETS = (
    ("item-eligibility.json", "item-eligibility.schema.json"),
    ("item-eligibility-coverage.json", "item-eligibility-coverage.schema.json"),
    ("equipment-shortlist.json", "equipment-shortlist.schema.json"),
    ("weapon-baseline-comparison.json", "weapon-baseline-comparison.schema.json"),
    ("equipment-loadout-candidate.json", "equipment-loadout-candidate.schema.json"),
    ("combat-input-audit.json", "combat-input-audit.schema.json"),
    ("item-requirement-quality.json", "item-requirement-quality.schema.json"),
    ("equipment-recommendation-audit.json", "equipment-recommendation-audit.schema.json"),
    ("item-combat-profile-audit.json", "item-combat-profile-audit.schema.json"),
    ("combat-loadout-evaluation-audit.json", "combat-loadout-evaluation-audit.schema.json"),
    ("combat-loadout-evaluation.json", "combat-loadout-evaluation.schema.json"),
    ("ranged-loadout-evaluation.json", "ranged-loadout-evaluation.schema.json"),
    ("loadout-comparison.json", "loadout-comparison.schema.json"),
    ("normalized-player-profile.json", "normalized-player-profile.schema.json"),
    ("database-scorecard.json", "database-scorecard.schema.json"),
    ("database-integrity.json", "database-integrity.schema.json"),
    ("database-gap-queue.json", "database-gap-queue.schema.json"),
    ("numeric-provenance-audit.json", "numeric-provenance-audit.schema.json"),
    ("item-relationship-audit.json", "item-relationship-audit.schema.json"),
    ("weapon-profile-coverage.json", "weapon-profile-coverage.schema.json"),
    ("weapon-database-comparison.json", "weapon-database-comparison.schema.json"),
    ("loadout-compatibility.json", "loadout-compatibility.schema.json"),
    ("domain-consistency-audit.json", "domain-consistency-audit.schema.json"),
    ("quest-gap-queue.json", "quest-gap-queue.schema.json"),
    ("quest-fact-quality.json", "quest-fact-quality.schema.json"),
    ("quest-skill-requirement-candidates.json", "quest-skill-requirement-candidates.schema.json"),
    ("quest-skill-candidate-audit.json", "quest-skill-candidate-audit.schema.json"),
    ("account-quest-progression.json", "account-quest-progression.schema.json"),
    ("combat-lab-readiness.json", "combat-lab-readiness.schema.json"),
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
    validate_file(ROOT / "sources" / "raw" / "quest-requirement-evidence.json", SCHEMAS / "quest-requirement-evidence.schema.json", errors, checked, True)
    validate_file(REPORTS / "quest-skill-requirement-candidates.json", SCHEMAS / "quest-skill-requirement-candidates.schema.json", errors, checked, False)
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
