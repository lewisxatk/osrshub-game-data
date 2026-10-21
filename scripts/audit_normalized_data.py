#!/usr/bin/env python3
"""Audit normalized combat datasets for structural defects and actionable gaps."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)
MONSTER_FIELDS = (
    "combat_level", "hitpoints", "attack_level", "strength_level", "defence_level",
    "magic_level", "ranged_level", "max_hit", "attack_speed", "slayer_level", "size",
)
TARGETS = {
    "equipment-stats": ("equipment-stats.json", "equipment"),
    "weapons": ("weapons.json", "weapon"),
    "monsters-combat": ("monsters-combat.json", "monster"),
}

def nonempty(value):
    return value is not None and value != "" and value != [] and value != {}

def audit_records(dataset, rows):
    """Audit one normalized dataset; missing metadata is reported, not fabricated."""
    errors, warnings = [], []
    if not isinstance(rows, list):
        return {"record_count": 0, "errors": [f"{dataset} must be a JSON array"], "warnings": []}
    seen_ids = set()
    missing_id = missing_name = missing_sources = 0
    duplicate_ids = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{dataset}[{index}] is not an object")
            continue
        rid = row.get("id")
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            missing_id += 1
            errors.append(f"{dataset}[{index}] has an invalid non-negative integer id")
        elif rid in seen_ids:
            duplicate_ids.append(rid)
        else:
            seen_ids.add(rid)
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            missing_name += 1
        if not isinstance(row.get("sources"), list) or not row["sources"]:
            missing_sources += 1
    if duplicate_ids:
        errors.append(f"{dataset} has duplicate IDs: {sorted(set(duplicate_ids))[:20]}")
    if missing_name:
        warnings.append(f"{missing_name} records have missing/blank names")
    if missing_sources:
        warnings.append(f"{missing_sources} records have no source attribution")

    details = {"record_count": len(rows), "missing_id_count": missing_id,
               "missing_name_count": missing_name, "missing_sources_count": missing_sources}
    if dataset == "equipment-stats":
        missing_slot = missing_bonuses = partial_bonuses = missing_requirements = missing_url = 0
        invalid_bonus_values = invalid_requirement_levels = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if not nonempty(row.get("slot")):
                missing_slot += 1
            bonuses = row.get("bonuses")
            if not isinstance(bonuses, dict) or not bonuses:
                missing_bonuses += 1
            elif any(field not in bonuses or bonuses[field] is None for field in BONUS_FIELDS):
                partial_bonuses += 1
            if isinstance(bonuses, dict):
                for field, value in bonuses.items():
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        invalid_bonus_values += 1
            requirements = row.get("requirements")
            if not isinstance(requirements, dict) or not requirements:
                missing_requirements += 1
            elif any(isinstance(level, bool) or not isinstance(level, int) or level < 0
                     for level in requirements.values()):
                invalid_requirement_levels += 1
            if not nonempty(row.get("source_url")):
                missing_url += 1
        details.update({"missing_slot_count": missing_slot, "missing_bonus_object_count": missing_bonuses,
                        "partial_bonus_field_count": partial_bonuses, "missing_requirements_count": missing_requirements,
                        "missing_source_url_count": missing_url, "invalid_bonus_value_count": invalid_bonus_values,
                        "invalid_requirement_level_count": invalid_requirement_levels})
        if missing_slot or missing_bonuses or partial_bonuses or missing_url:
            warnings.append("Equipment metadata gaps found; inspect source coverage before using records in optimization.")
    elif dataset == "weapons":
        missing_speed = invalid_speed = missing_type = missing_stances = malformed_stances = missing_url = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            speed = row.get("attack_speed")
            if speed is None:
                missing_speed += 1
            elif isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
                invalid_speed += 1
            if not nonempty(row.get("weapon_type")):
                missing_type += 1
            if not isinstance(row.get("stances"), list) or not row["stances"]:
                missing_stances += 1
            elif any(not isinstance(stance, dict) or not nonempty(stance.get("name")) for stance in row["stances"]):
                malformed_stances += 1
            if not nonempty(row.get("source_url")):
                missing_url += 1
        details.update({"missing_attack_speed_count": missing_speed, "invalid_attack_speed_count": invalid_speed,
                        "missing_weapon_type_count": missing_type, "missing_stances_count": missing_stances, "malformed_stances_count": malformed_stances,
                        "missing_source_url_count": missing_url})
        if missing_speed or invalid_speed or missing_type or missing_stances or malformed_stances or missing_url:
            warnings.append("Weapon metadata gaps found; do not infer missing speed, type, or stance values.")
    elif dataset == "monsters-combat":
        invalid_values = {}
        for field in MONSTER_FIELDS:
            invalid_values[field] = sum(
                1 for row in rows if isinstance(row, dict) and row.get(field) is not None
                and (isinstance(row.get(field), bool) or not isinstance(row.get(field), (int, float))
                     or row.get(field) < 0)
            )
        details["invalid_numeric_value_count_by_field"] = invalid_values
        if any(invalid_values.values()):
            warnings.append("Monster combat fields contain non-numeric or negative values; review source normalization.")
        for field in MONSTER_FIELDS:
            present = sum(1 for row in rows if isinstance(row, dict) and nonempty(row.get(field)))
            details.setdefault("field_coverage", {})[field] = {
                "records_with_value": present,
                "coverage_percent": round(present * 100 / len(rows), 2) if rows else 0.0,
            }
        if any(value["records_with_value"] < len(rows) for value in details["field_coverage"].values()):
            warnings.append("Some monster combat fields are absent; unknown values must remain unknown.")
    details["errors"] = errors
    details["warnings"] = warnings
    return details

def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "meaning": "Structural checks and metadata coverage only; passing does not prove OSRS values are correct.",
              "datasets": {}, "errors": []}
    for dataset, (filename, _) in TARGETS.items():
        path = DIST / filename
        # This audit runs after the normalizers in CI. Missing outputs indicate
        # a broken pipeline; malformed records are audited separately below.
        if not path.exists():
            report["errors"].append(f"Missing dist/{filename}; run the corresponding normalizer before this audit")
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["errors"].append(f"Cannot read dist/{filename}: {exc}")
            continue
        result = audit_records(dataset, rows)
        report["datasets"][dataset] = result
        report["errors"].extend(result["errors"])
    report["status"] = "failed" if report["errors"] else "passed_with_warnings" if any(
        value.get("warnings") for value in report["datasets"].values()
    ) else "passed"
    (REPORTS / "normalized-data-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
