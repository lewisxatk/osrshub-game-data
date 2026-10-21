#!/usr/bin/env python3
"""Report source and raw-field provenance for normalized equipment and weapons."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILES = (
    ("community_items", ROOT / "sources/raw/community_items.json"),
    ("original_items", ROOT / "sources/raw/original_items.json"),
)
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
FIELD_PATHS = {
    "equipment-stats.json": {
        "slot": ("equipment", "slot"),
        **{field: ("equipment", field) for field in (
            "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
            "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
            "melee_strength", "ranged_strength", "magic_damage", "prayer",
        )},
        "requirements": ("equipment", "requirements"),
    },
    "weapons.json": {
        "attack_speed": ("weapon", "attack_speed"),
        "weapon_type": ("weapon", "weapon_type"),
        "stances": ("weapon", "stances"),
    },
}


def numeric_id(row):
    for key in ("id", "item_id"):
        try:
            if row.get(key) is not None:
                return int(row[key])
        except (TypeError, ValueError):
            pass
    return None


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
    raise ValueError(f"Unsupported JSON top-level type in {path}")


def get_path(row, path):
    value = row
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def build_source_index(raw_files):
    by_id = {}
    errors = []
    for source_name, path in raw_files:
        if not path.exists():
            errors.append(f"Missing raw source: {path}")
            continue
        for row in load_rows(path):
            rid = numeric_id(row)
            if rid is None:
                continue
            by_id.setdefault(rid, []).append((source_name, row))
    return by_id, errors


def audit_dataset(filename, raw_by_id, limit=25):
    path = DIST / filename
    if not path.exists():
        return {"status": "failed", "error": f"Missing dist/{filename}", "record_count": 0}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return {"status": "failed", "error": f"dist/{filename} must be a JSON array", "record_count": 0}
    mapping = FIELD_PATHS[filename]
    counts = {field: {"present": 0, "missing_source_record": 0, "source_counts": {}, "raw_field_counts": {}, "examples": []}
              for field in mapping}
    duplicate_ids = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if rid in seen:
            duplicate_ids.append(rid)
        seen.add(rid)
        candidates = raw_by_id.get(rid, [])
        for output_field, raw_path in mapping.items():
            value = row.get(output_field)
            if value is None or value == "" or value == [] or value == {}:
                continue
            counts[output_field]["present"] += 1
            chosen = None
            for source_name, raw in candidates:
                raw_value = get_path(raw, raw_path)
                if raw_value is not None and raw_value != "" and raw_value != [] and raw_value != {}:
                    chosen = (source_name, raw_value)
                    break
            if chosen is None:
                counts[output_field]["missing_source_record"] += 1
                continue
            source_name, raw_value = chosen
            counts[output_field]["source_counts"][source_name] = counts[output_field]["source_counts"].get(source_name, 0) + 1
            raw_label = ".".join(raw_path)
            counts[output_field]["raw_field_counts"][raw_label] = counts[output_field]["raw_field_counts"].get(raw_label, 0) + 1
            if len(counts[output_field]["examples"]) < limit:
                counts[output_field]["examples"].append({
                    "id": rid, "name": row.get("name", ""), "source": source_name,
                    "source_field": raw_label, "normalized_value": value,
                    "raw_value_matches": raw_value == value,
                })
    for field, item in counts.items():
        item["examples_capped_at"] = limit
    return {
        "status": "failed" if duplicate_ids else "passed",
        "record_count": len(rows),
        "duplicate_ids": sorted(set(duplicate_ids), key=str)[:100],
        "field_provenance": counts,
        "note": "Source selection follows configured community-first precedence and matching raw field paths. Value matching is diagnostic, not independent proof of factual accuracy.",
    }


def main():
    raw_by_id, errors = build_source_index(RAW_FILES)
    datasets = {}
    for filename in FIELD_PATHS:
        try:
            datasets[filename] = audit_dataset(filename, raw_by_id)
            if datasets[filename].get("status") == "failed":
                errors.append(f"Audit failed for {filename}")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            datasets[filename] = {"status": "failed", "error": str(exc)}
            errors.append(f"Cannot audit {filename}: {exc}")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "source_precedence": [name for name, _ in RAW_FILES],
        "datasets": datasets,
        "errors": errors,
        "meaning": "Tracks source-field lineage for normalized equipment and weapon fields; it does not independently verify the underlying OSRS facts.",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "normalized-combat-provenance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
