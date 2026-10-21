#!/usr/bin/env python3
"""Report normalized combat fields with source-level provenance and disagreement details."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
REPORTS = ROOT / "reports"
DIST = ROOT / "dist"

ITEM_SOURCES = ("community_items", "original_items")
MONSTER_SOURCES = ("community_monsters", "original_monsters")
ITEM_FIELDS = {
    "equipment": ("equipment",),
    "weapon": ("weapon",),
    "wiki_url": ("wiki_url",),
}
MONSTER_ALIASES = {
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


def load_rows(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        rows = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
        return rows
    raise ValueError(f"{path}: expected an array or object of records")


def record_id(row):
    for key in ("id", "item_id", "npc_id", "monster_id"):
        value = row.get(key)
        if isinstance(value, bool) or value is None:
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return None


def first_present(row, aliases):
    for alias in aliases:
        if alias in row and row[alias] is not None and row[alias] != "":
            return row[alias], alias
    return None, None


def json_value(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(value)


def audit_category(category, source_names, fields, raw_dir=RAW):
    errors = []
    sources_by_id = defaultdict(dict)
    source_counts = {}
    for source_name in source_names:
        path = raw_dir / f"{source_name}.json"
        if not path.is_file():
            errors.append(f"missing source file: {path.name}")
            continue
        try:
            rows = load_rows(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"cannot load {path.name}: {exc}")
            continue
        source_counts[source_name] = len(rows)
        for row in rows:
            rid = record_id(row)
            if rid is not None:
                sources_by_id[rid][source_name] = row

    field_counts = Counter()
    source_field_counts = {source: Counter() for source in source_names}
    conflicts = []
    missing_examples = defaultdict(list)
    total_records = len(sources_by_id)

    for rid, by_source in sorted(sources_by_id.items()):
        for output_field, aliases in fields.items():
            found = []
            for source_name in source_names:
                row = by_source.get(source_name)
                if row is None:
                    continue
                value, source_field = first_present(row, aliases)
                if value is not None:
                    found.append((source_name, source_field, value))
                    source_field_counts[source_name][output_field] += 1
            if found:
                field_counts[output_field] += 1
            elif len(missing_examples[output_field]) < 15:
                name = next((row.get("name") or row.get("npc_name") or row.get("item_name")
                             for row in by_source.values()
                             if isinstance(row.get("name") or row.get("npc_name") or row.get("item_name"), str)), "")
                missing_examples[output_field].append({"id": rid, "name": name})
            distinct = {json_value(value) for _, _, value in found}
            if len(distinct) > 1:
                conflicts.append({
                    "id": rid,
                    "name": next((row.get("name") or row.get("npc_name") or row.get("item_name") or ""
                                  for row in by_source.values()), ""),
                    "field": output_field,
                    "values": [
                        {"source": source, "source_field": source_field, "value": value}
                        for source, source_field, value in found
                    ],
                })

    return {
        "status": "failed" if errors else "passed",
        "source_record_counts": source_counts,
        "unique_record_count": total_records,
        "fields": {
            field: {
                "records_with_value": field_counts[field],
                "coverage_percent": round(field_counts[field] * 100 / total_records, 2) if total_records else 0.0,
                "source_record_counts": {source: source_field_counts[source][field] for source in source_names},
                "missing_examples": missing_examples[field],
            }
            for field in fields
        },
        "conflict_count": len(conflicts),
        "conflict_examples_capped_at": 100,
        "conflicts": conflicts[:100],
        "conflicts_truncated": len(conflicts) > 100,
        "errors": errors,
    }


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "meaning": (
            "Raw-source field presence and disagreements only. This report does not establish which "
            "source is correct and does not replace independent verification."
        ),
        "datasets": {
            "items": audit_category("items", ITEM_SOURCES, ITEM_FIELDS),
            "monsters": audit_category("monsters", MONSTER_SOURCES, MONSTER_ALIASES),
        },
    }
    if any(section["status"] == "failed" for section in report["datasets"].values()):
        report["status"] = "failed"
    (REPORTS / "field-provenance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
