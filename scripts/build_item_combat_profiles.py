#!/usr/bin/env python3
"""Join normalized item, equipment, weapon and skill-requirement records for combat facts."""
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

def load_array(directory, filename):
    path = directory / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{filename} must contain an array of objects")
    return data

def index_by_id(rows, label, id_field="id"):
    result = {}
    for row in rows:
        rid = row.get(id_field)
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            continue
        if rid in result:
            raise ValueError(f"{label} has duplicate ID {rid}")
        result[rid] = row
    return result

def build_profiles(items, equipment, weapons, requirements):
    items_by_id = index_by_id(items, "items")
    equipment_by_id = index_by_id(equipment, "equipment")
    weapons_by_id = index_by_id(weapons, "weapons")
    requirements_by_id = index_by_id(requirements, "requirements", "item_id")
    profiles = []
    summary = {
        "item_count": len(items_by_id), "profiles_with_equipment_stats": 0,
        "profiles_with_weapon_data": 0, "profiles_with_skill_requirements": 0,
        "profiles_with_attack_speed": 0, "profiles_with_all_bonus_fields": 0,
        "profiles_missing_equipment_record": 0, "profiles_missing_weapon_record": 0,
        "profiles_missing_skill_requirement_record": 0,
    }
    for item_id, item in sorted(items_by_id.items()):
        equip = equipment_by_id.get(item_id)
        weapon = weapons_by_id.get(item_id)
        req = requirements_by_id.get(item_id)
        bonuses = equip.get("bonuses", {}) if isinstance(equip, dict) else {}
        bonuses = bonuses if isinstance(bonuses, dict) else {}
        requirements_list = req.get("requirements") if isinstance(req, dict) else None
        profile = {
            "id": item_id,
            "name": item.get("name", ""),
            "slot": equip.get("slot") if equip else None,
            "bonuses": {field: bonuses.get(field) for field in BONUS_FIELDS},
            "attack_speed": weapon.get("attack_speed") if weapon else None,
            "weapon_type": weapon.get("weapon_type") if weapon else None,
            "stances": weapon.get("stances", []) if weapon else [],
            "skill_requirements": requirements_list if isinstance(requirements_list, list) else None,
            "equipment_record_present": equip is not None,
            "weapon_record_present": weapon is not None,
            "skill_requirement_record_present": req is not None,
            "source_urls": sorted({url for url in (
                item.get("wiki_url"), equip.get("source_url") if equip else None,
                weapon.get("source_url") if weapon else None, req.get("source_url") if req else None
            ) if isinstance(url, str) and url}),
            "sources": sorted({source for collection in (
                item.get("sources", []), equip.get("sources", []) if equip else [],
                weapon.get("sources", []) if weapon else [], req.get("sources", []) if req else []
            ) if isinstance(collection, list) for source in collection if isinstance(source, str)}),
            "data_status": "partial",
        }
        summary["profiles_with_equipment_stats"] += equip is not None
        summary["profiles_with_weapon_data"] += weapon is not None
        summary["profiles_with_skill_requirements"] += req is not None
        summary["profiles_with_attack_speed"] += bool(weapon and isinstance(weapon.get("attack_speed"), int) and not isinstance(weapon.get("attack_speed"), bool) and weapon["attack_speed"] > 0)
        summary["profiles_with_all_bonus_fields"] += bool(equip and all(isinstance(bonuses.get(field), (int, float)) and not isinstance(bonuses.get(field), bool) for field in BONUS_FIELDS))
        summary["profiles_missing_equipment_record"] += equip is None
        summary["profiles_missing_weapon_record"] += weapon is None
        summary["profiles_missing_skill_requirement_record"] += req is None
        if equip and weapon and req and profile["attack_speed"] and all(profile["bonuses"][field] is not None for field in ("attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged", "melee_strength", "ranged_strength", "magic_damage", "prayer")):
            profile["data_status"] = "joined_fields_present"
        profiles.append(profile)
    summary["profile_count"] = len(profiles)
    summary["note"] = "This joins available source-backed records; null means unknown/not supplied, not zero. No DPS is calculated here, and record presence does not prove factual completeness."
    return profiles, summary

def main():
    try:
        items = load_array(DIST, "items.json")
        equipment = load_array(DIST, "equipment-stats.json")
        weapons = load_array(DIST, "weapons.json")
        requirements = load_array(DIST, "item-requirements.json")
        profiles, summary = build_profiles(items, equipment, weapons, requirements)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (DIST / "item-combat-profiles.json").write_text(json.dumps(profiles, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "passed", **summary}
    (REPORTS / "item-combat-profile-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
