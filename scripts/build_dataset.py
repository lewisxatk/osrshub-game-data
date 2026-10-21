#!/usr/bin/env python3
"""Merge OSRSBox/community snapshots into compact datasets with provenance."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, DIST, REPORTS = ROOT / "sources" / "raw", ROOT / "dist", ROOT / "reports"
INPUTS = {
    "community_items": "items",
    "original_items": "items",
    "community_monsters": "monsters",
    "original_monsters": "monsters",
}
IDENTITY_FIELDS = {
    "id", "item_id", "npc_id", "monster_id", "name", "item_name",
    "npc_name", "monster_name",
}
# Volatile or presentation-heavy fields create noise rather than useful data conflicts.
IGNORED_CONFLICT_FIELDS = {
    "last_updated", "last_updated_at", "updated_at", "created_at",
    "icon", "icon_large", "icon_url", "icon_large_url", "examine_image",
}


def load_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rows = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
        return rows
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    raise ValueError(f"Unsupported top-level JSON type in {path}: {type(data).__name__}")


def numeric_id(record):
    for key in ("id", "item_id", "npc_id", "monster_id"):
        value = record.get(key)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def name_of(record):
    for key in ("name", "item_name", "npc_name", "monster_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _is_ignored_conflict_field(field):
    lowered = field.casefold()
    return (
        field in IGNORED_CONFLICT_FIELDS
        or lowered.endswith(("_icon", "_icon_url", "_image_url", "_image"))
        or lowered in {"wiki_url", "wiki_image"}
    )


def _value_summary(value):
    """Keep reports compact; don't copy huge strings/base64 payloads into reports."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        encoded = repr(value)
    if len(encoded) > 240:
        return {"preview": encoded[:200], "truncated": True, "characters": len(encoded)}
    return value


def merge_category(category):
    merged = {}
    conflicts = []
    ignored_conflicts = Counter()
    missing_ids = []
    source_names = [name for name, cat in INPUTS.items() if cat == category]

    for source_name in source_names:
        path = RAW / f"{source_name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run scripts/download_sources.py first")
        for record in load_records(path):
            record_id = numeric_id(record)
            if record_id is None:
                missing_ids.append({
                    "category": category,
                    "source": source_name,
                    "reason": "missing_or_non_numeric_id",
                    "record_name": name_of(record),
                })
                continue

            key = str(record_id)
            if key not in merged:
                # Compact output: source names are retained, raw source snapshots remain
                # available under sources/raw and are indexed by SHA-256 in the manifest.
                normalized = {"id": record_id, "name": name_of(record), "sources": [source_name]}
                for field, value in record.items():
                    if field not in IDENTITY_FIELDS:
                        normalized[field] = value
                merged[key] = normalized
                continue

            target = merged[key]
            target["sources"] = sorted(set(target["sources"] + [source_name]))
            if not target.get("name") and name_of(record):
                target["name"] = name_of(record)

            for field, value in record.items():
                if field in IDENTITY_FIELDS:
                    continue
                if field not in target:
                    target[field] = value
                elif target[field] != value:
                    if _is_ignored_conflict_field(field):
                        ignored_conflicts[field] += 1
                        continue
                    conflicts.append({
                        "category": category,
                        "id": record_id,
                        "name": target.get("name", ""),
                        "field": field,
                        "kept_source": target["sources"][0],
                        "other_source": source_name,
                        "kept_value": _value_summary(target[field]),
                        "other_value": _value_summary(value),
                    })

    records = sorted(merged.values(), key=lambda row: row["id"])
    for row in records:
        row["sources"] = sorted(set(row["sources"]))
    return records, conflicts, missing_ids, dict(sorted(ignored_conflicts.items()))


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    all_conflicts, all_missing_ids = [], []
    counts, input_hashes, ignored_by_field = {}, {}, Counter()

    for path in sorted(RAW.glob("*.json")):
        if path.name != "manifest.json":
            input_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

    for category in ("items", "monsters"):
        records, conflicts, missing_ids, ignored = merge_category(category)
        (DIST / f"{category}.json").write_text(
            json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        counts[category] = len(records)
        all_conflicts.extend(conflicts)
        all_missing_ids.extend(missing_ids)
        ignored_by_field.update(ignored)

        if category == "items":
            equipment = [
                row for row in records
                if row.get("equipable") is True
                or isinstance(row.get("equipment"), dict)
                or (isinstance(row.get("equipable_by_player"), bool) and row.get("equipable_by_player"))
            ]
            (DIST / "equipment.json").write_text(
                json.dumps(equipment, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            counts["equipment_candidates"] = len(equipment)

    conflict_report = {
        "summary": {
            "meaningful_conflict_count": len(all_conflicts),
            "ignored_volatile_conflict_count": sum(ignored_by_field.values()),
            "ignored_volatile_conflicts_by_field": dict(sorted(ignored_by_field.items())),
            "records_missing_ids": len(all_missing_ids),
        },
        "conflicts": all_conflicts,
        "records_missing_ids": all_missing_ids,
        "note": (
            "First source listed for each category has field precedence. Raw source snapshots "
            "and their SHA-256 hashes are retained separately; this report omits volatile "
            "timestamp and presentation-image conflicts."
        ),
    }
    (REPORTS / "source-conflicts.json").write_text(
        json.dumps(conflict_report, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs_sha256": input_hashes,
        "counts": counts,
        "meaningful_conflict_count": len(all_conflicts),
        "ignored_volatile_conflict_count": sum(ignored_by_field.values()),
        "records_missing_ids": len(all_missing_ids),
        "source_precedence": {category: [name for name, cat in INPUTS.items() if cat == category]
                              for category in ("items", "monsters")},
        "note": "Compact merged records retain source names; raw snapshots and hashes provide source provenance.",
    }
    (DIST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
