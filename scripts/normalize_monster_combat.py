#!/usr/bin/env python3
"""Create normalized monster combat records from fields already present in source datasets."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_MONSTER_FILES = (ROOT / "sources/raw/community_monsters.json", ROOT / "sources/raw/original_monsters.json")
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

ALIASES = {
    "combat_level": ("combat_level", "combat", "level"),
    "hitpoints": ("hitpoints", "hitpoints_level", "hp"),
    "attack_level": ("attack_level", "attack"),
    "strength_level": ("strength_level", "strength"),
    "defence_level": ("defence_level", "defense_level", "defence", "defense"),
    "magic_level": ("magic_level", "magic"),
    "ranged_level": ("ranged_level", "range_level", "ranged"),
    "attack_speed": ("attack_speed", "attackSpeed"),
    "max_hit": ("max_hit", "maxhit", "maxHit"),
    "slayer_level": ("slayer_level", "slayerLevel"),
    "size": ("size", "npc_size"),
}

def numeric_id(row):
    for key in ("id", "npc_id", "monster_id"):
        try:
            if row.get(key) is not None:
                return int(row[key])
        except (TypeError, ValueError):
            pass
    return None

def first_value(row, aliases):
    for key in aliases:
        value = row.get(key)
        if value is not None and value != "":
            return value, key
    return None, None

def load_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        rows = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
        return rows
    raise ValueError(f"Unsupported JSON top-level type in {path}")

def main():
    sources = {}
    source_counts = {}
    errors = []
    for path in RAW_MONSTER_FILES:
        if not path.exists():
            errors.append(f"Missing raw source: {path.relative_to(ROOT)}")
            continue
        rows = load_rows(path)
        source_counts[path.stem] = len(rows)
        for row in rows:
            rid = numeric_id(row)
            if rid is None:
                continue
            record = sources.setdefault(rid, {"id": rid, "name": "", "sources": [], "_raw": {}})
            name = row.get("name") or row.get("npc_name") or row.get("monster_name")
            if not record["name"] and isinstance(name, str):
                record["name"] = name
            record["sources"].append(path.stem)
            record["_raw"][path.stem] = row

    output = []
    coverage = {key: 0 for key in ALIASES}
    field_source_counts = {key: {} for key in ALIASES}
    missing_examples = {key: [] for key in ALIASES}
    for rid, base in sorted(sources.items()):
        normalized = {"id": rid, "name": base["name"], "sources": sorted(set(base["sources"]))}
        raw_by_source = base["_raw"]
        for field, aliases in ALIASES.items():
            value = None
            source_key = None
            # Respect existing configured source order: community first, then original.
            for source_name in ("community_monsters", "original_monsters"):
                raw = raw_by_source.get(source_name, {})
                value, source_key = first_value(raw, aliases)
                if value is not None:
                    if isinstance(value, bool) or not isinstance(value, (int, float, str, list, dict)):
                        value = None
                    else:
                        field_source_counts[field][source_name] = field_source_counts[field].get(source_name, 0) + 1
                    break
            normalized[field] = value
            if value is not None:
                coverage[field] += 1
            elif len(missing_examples[field]) < 15:
                missing_examples[field].append({"id": rid, "name": base["name"]})
        output.append(normalized)

    (DIST / "monsters-combat.json").write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    total = len(output)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "source_record_counts": source_counts,
        "normalized_monster_count": total,
        "field_coverage": {
            key: {
                "present": coverage[key],
                "missing": total - coverage[key],
                "coverage_percent": round(coverage[key] * 100 / total, 2) if total else 0.0,
                "source_counts": field_source_counts[key],
            }
            for key in ALIASES
        },
        "missing_examples_capped_at": 15,
        "missing_examples": missing_examples,
        "errors": errors,
        "note": "Aliases map only existing source fields; no missing combat values are guessed. Source disagreement resolution follows community-first precedence.",
    }
    (REPORTS / "monster-combat-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
