#!/usr/bin/env python3
"""Audit joined item combat profiles for structural gaps and suspicious values."""
from __future__ import annotations
import json
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
def audit_profiles(rows):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("profiles must be an array of objects")
    errors, warnings = [], []
    ids = set()
    counts = {
        "profile_count": len(rows), "with_equipment": 0, "with_weapon": 0,
        "with_requirements_record": 0, "with_positive_attack_speed": 0,
        "with_all_numeric_bonuses": 0, "with_source_urls": 0,
        "partial_profiles": 0, "joined_fields_present": 0,
    }
    for index, row in enumerate(rows):
        label = {"index": index, "item_id": row.get("id"), "item_name": row.get("name", "")}
        rid = row.get("id")
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            errors.append({**label, "issue": "invalid_item_id"})
        elif rid in ids:
            errors.append({**label, "issue": "duplicate_item_id"})
        else:
            ids.add(rid)
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            errors.append({**label, "issue": "missing_item_name"})
        bonuses = row.get("bonuses")
        if not isinstance(bonuses, dict):
            errors.append({**label, "issue": "bonuses_not_object"})
            bonuses = {}
        bad_bonus = False
        for field in BONUS_FIELDS:
            value = bonuses.get(field)
            if value is None or value == "":
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                errors.append({**label, "field": field, "issue": "invalid_bonus_type"})
                bad_bonus = True
            elif isinstance(value, str):
                try:
                    float(value)
                except ValueError:
                    errors.append({**label, "field": field, "issue": "non_numeric_bonus_string"})
                    bad_bonus = True
        if not all(bonuses.get(field) is not None and bonuses.get(field) != "" for field in BONUS_FIELDS):
            warnings.append({**label, "issue": "incomplete_bonus_coverage"})
        else:
            counts["with_all_numeric_bonuses"] += not bad_bonus
        speed = row.get("attack_speed")
        if speed is not None:
            if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
                errors.append({**label, "field": "attack_speed", "issue": "invalid_attack_speed"})
            else:
                counts["with_positive_attack_speed"] += 1
        elif row.get("weapon_record_present"):
            warnings.append({**label, "issue": "weapon_record_without_attack_speed"})
        for key, count_key in (("equipment_record_present", "with_equipment"), ("weapon_record_present", "with_weapon"), ("skill_requirement_record_present", "with_requirements_record")):
            if not isinstance(row.get(key), bool):
                errors.append({**label, "field": key, "issue": "presence_flag_not_boolean"})
            elif row[key]:
                counts[count_key] += 1
        reqs = row.get("skill_requirements")
        if reqs is not None:
            if not isinstance(reqs, list):
                errors.append({**label, "field": "skill_requirements", "issue": "requirements_not_array_or_null"})
            else:
                seen_skills = set()
                for req in reqs:
                    if not isinstance(req, dict) or not isinstance(req.get("skill"), str) or not req["skill"].strip() or isinstance(req.get("level"), bool) or not isinstance(req.get("level"), int) or req["level"] < 0:
                        errors.append({**label, "field": "skill_requirements", "issue": "invalid_requirement"})
                        continue
                    key = " ".join(req["skill"].casefold().split())
                    if key in seen_skills:
                        errors.append({**label, "field": "skill_requirements", "issue": "duplicate_skill_requirement", "skill": req["skill"]})
                    seen_skills.add(key)
        if row.get("skill_requirement_record_present") and reqs is None:
            errors.append({**label, "issue": "requirement_presence_flag_conflicts_with_null"})
        urls = row.get("source_urls")
        if not isinstance(urls, list) or any(not isinstance(url, str) or not url.startswith(("https://", "http://")) for url in urls):
            errors.append({**label, "field": "source_urls", "issue": "invalid_source_urls"})
        elif urls:
            counts["with_source_urls"] += 1
        else:
            warnings.append({**label, "issue": "no_source_url"})
        status = row.get("data_status")
        if status == "partial":
            counts["partial_profiles"] += 1
        elif status == "joined_fields_present":
            counts["joined_fields_present"] += 1
        else:
            errors.append({**label, "field": "data_status", "issue": "unsupported_data_status"})
        if row.get("equipment_record_present") and row.get("weapon_record_present") and speed is None:
            warnings.append({**label, "issue": "equipment_and_weapon_joined_but_speed_unknown"})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("review_required" if warnings else "passed"),
        "purpose": "Structural and coverage audit only; not an OSRS factual accuracy score.",
        **counts, "error_count": len(errors), "warning_count": len(warnings),
        "errors": errors[:200], "warnings": warnings[:300],
        "guardrails": [
            "Null bonus values remain unknown and are not converted to zero.",
            "An absent requirement record is not evidence that an item has no requirements.",
            "Source links and structural checks do not independently verify game mechanics.",
            "This audit does not calculate DPS or certify an item as usable."
        ]
    }
def main():
    try:
        rows = json.loads((DIST / "item-combat-profiles.json").read_text(encoding="utf-8"))
        report = audit_profiles(rows)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "item-combat-profile-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0
if __name__ == "__main__":
    raise SystemExit(main())
