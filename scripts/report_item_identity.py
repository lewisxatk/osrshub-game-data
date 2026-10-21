#!/usr/bin/env python3
"""Audit item-name identity collisions without merging distinct item IDs."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def normalize_name(value):
    """Normalize spacing/case/punctuation for diagnostics only, never for identity."""
    value = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(value.split())


def audit_items(items, example_limit=100):
    if not isinstance(items, list):
        raise ValueError("items dataset must be a JSON array")
    exact_names = defaultdict(list)
    normalized_names = defaultdict(list)
    missing_name_ids = []
    invalid_rows = []
    seen_ids = set()
    duplicate_ids = []
    source_counts = defaultdict(int)

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            invalid_rows.append({"index": index, "reason": "record_not_object"})
            continue
        item_id = item.get("id")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            invalid_rows.append({"index": index, "reason": "invalid_id", "id": item_id})
        elif item_id in seen_ids:
            duplicate_ids.append(item_id)
        else:
            seen_ids.add(item_id)
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            missing_name_ids.append(item_id if isinstance(item_id, int) and not isinstance(item_id, bool) else None)
            continue
        name = " ".join(name.split())
        exact_names[name.casefold()].append({"id": item_id, "name": name})
        normalized_names[normalize_name(name)].append({"id": item_id, "name": name})
        sources = item.get("sources", [])
        if isinstance(sources, list):
            for source in set(s for s in sources if isinstance(s, str) and s):
                source_counts[source] += 1

    def groups_for(index, include_single=False):
        groups = []
        for normalized, rows in index.items():
            unique_ids = {row["id"] for row in rows if row["id"] is not None}
            if len(rows) > 1 and (include_single or len(unique_ids) > 1):
                groups.append({
                    "normalized_name": normalized,
                    "record_count": len(rows),
                    "distinct_id_count": len(unique_ids),
                    "items": sorted(rows, key=lambda row: (str(row["name"]).casefold(), str(row["id"])))[:10],
                    "items_truncated": len(rows) > 10,
                })
        return sorted(groups, key=lambda group: (-group["distinct_id_count"], group["normalized_name"]))

    exact_duplicates = groups_for(exact_names)
    normalized_collisions = groups_for(normalized_names)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if duplicate_ids or invalid_rows else "passed",
        "item_record_count": len(items),
        "valid_unique_id_count": len(seen_ids),
        "duplicate_id_count": len(set(duplicate_ids)),
        "duplicate_ids": sorted(set(duplicate_ids))[:example_limit],
        "invalid_record_count": len(invalid_rows),
        "invalid_record_examples": invalid_rows[:example_limit],
        "missing_name_count": len(missing_name_ids),
        "missing_name_id_examples": missing_name_ids[:example_limit],
        "exact_name_collision_group_count": len(exact_duplicates),
        "exact_name_collisions": exact_duplicates[:example_limit],
        "normalized_name_collision_group_count": len(normalized_collisions),
        "normalized_name_collisions": normalized_collisions[:example_limit],
        "source_record_counts": dict(sorted(source_counts.items())),
        "examples_truncated": any(len(rows) > example_limit for rows in [exact_duplicates, normalized_collisions, invalid_rows, missing_name_ids]),
        "note": "Name collisions are review candidates, not instructions to merge records. Item ID remains the identity key; similar names can represent variants, charges, or distinct game objects.",
    }
    return summary


def main():
    source = DIST / "items.json"
    try:
        items = json.loads(source.read_text(encoding="utf-8"))
        result = audit_items(items)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "item_record_count": 0,
            "valid_unique_id_count": 0,
            "duplicate_id_count": 0,
            "duplicate_ids": [],
            "invalid_record_count": 1,
            "invalid_record_examples": [{"reason": str(exc)}],
            "missing_name_count": 0,
            "missing_name_id_examples": [],
            "exact_name_collision_group_count": 0,
            "exact_name_collisions": [],
            "normalized_name_collision_group_count": 0,
            "normalized_name_collisions": [],
            "source_record_counts": {},
            "examples_truncated": False,
            "note": "Item identity audit could not be completed.",
        }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "item-identity.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
