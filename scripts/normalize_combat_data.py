#!/usr/bin/env python3
"""Extract compact, purpose-specific equipment bonus and weapon datasets."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "dist" / "items.json"
DIST = ROOT / "dist"
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)

def normalize_equipment(row):
    bonus = row.get("equipment")
    if not isinstance(bonus, dict) or not bonus:
        return None
    result = {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "slot": bonus.get("slot"),
        "bonuses": {field: bonus.get(field) for field in BONUS_FIELDS if field in bonus},
        "requirements": bonus.get("requirements") if isinstance(bonus.get("requirements"), dict) else {},
        "sources": row.get("sources", []),
        "source_url": row.get("wiki_url"),
    }
    return result

def normalize_weapon(row):
    weapon = row.get("weapon")
    if not isinstance(weapon, dict) or not weapon:
        return None
    stances = weapon.get("stances")
    if not isinstance(stances, list):
        stances = []
    normalized_stances = []
    for stance in stances:
        if not isinstance(stance, dict):
            continue
        normalized_stances.append({
            "name": stance.get("name"),
            "combat_style": stance.get("combat_style"),
            "attack_type": stance.get("attack_type"),
            "attack_style": stance.get("attack_style"),
            "experience": stance.get("experience"),
            "boosts": stance.get("boosts"),
        })
    speed = weapon.get("attack_speed")
    return {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "attack_speed": speed if isinstance(speed, int) and not isinstance(speed, bool) and speed > 0 else None,
        "weapon_type": weapon.get("weapon_type"),
        "stances": normalized_stances,
        "sources": row.get("sources", []),
        "source_url": row.get("wiki_url"),
    }

def main():
    if not ITEMS.exists():
        raise FileNotFoundError("dist/items.json is missing; run scripts/build_dataset.py first")
    items = json.loads(ITEMS.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("dist/items.json must be a JSON array")
    equipment = []
    weapons = []
    for row in items:
        if not isinstance(row, dict):
            continue
        equip = normalize_equipment(row)
        if equip is not None:
            equipment.append(equip)
        weapon = normalize_weapon(row)
        if weapon is not None:
            weapons.append(weapon)
    equipment.sort(key=lambda row: (row["id"] is None, row["id"] if row["id"] is not None else 0))
    weapons.sort(key=lambda row: (row["id"] is None, row["id"] if row["id"] is not None else 0))
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "equipment-stats.json").write_text(json.dumps(equipment, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (DIST / "weapons.json").write_text(json.dumps(weapons, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_item_count": len(items),
        "equipment_stat_records": len(equipment),
        "weapon_records": len(weapons),
        "weapons_with_attack_speed": sum(row["attack_speed"] is not None for row in weapons),
        "weapons_with_stances": sum(bool(row["stances"]) for row in weapons),
        "note": "Values are copied from upstream item records, not independently verified. Missing values remain null or absent.",
    }
    (ROOT / "reports" / "combat-data-summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
