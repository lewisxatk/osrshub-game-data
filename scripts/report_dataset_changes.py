#!/usr/bin/env python3
"""Compare two JSON-array datasets by ID and report added, removed, and changed records."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def load_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array")
    records = {}
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"{path}[{index}]: expected an object")
        record_id = row.get("id")
        if isinstance(record_id, bool) or not isinstance(record_id, (int, str)):
            raise ValueError(f"{path}[{index}]: record needs an integer or string id")
        key = str(record_id)
        if key in records:
            raise ValueError(f"{path}: duplicate id {key}")
        records[key] = row
    return records


def compare_records(before, after, example_limit=20):
    before_ids, after_ids = set(before), set(after)
    added_ids = sorted(after_ids - before_ids)
    removed_ids = sorted(before_ids - after_ids)
    changed = []
    changed_fields = Counter()
    for record_id in sorted(before_ids & after_ids):
        old, new = before[record_id], after[record_id]
        fields = sorted(
            field for field in set(old) | set(new)
            if old.get(field) != new.get(field) or (field in old) != (field in new)
        )
        if fields:
            changed.append({"id": record_id, "fields": fields})
            changed_fields.update(fields)
    return {
        "before_record_count": len(before),
        "after_record_count": len(after),
        "added_count": len(added_ids),
        "removed_count": len(removed_ids),
        "changed_record_count": len(changed),
        "added_ids": added_ids[:example_limit],
        "removed_ids": removed_ids[:example_limit],
        "changed_records": changed[:example_limit],
        "changed_field_counts": dict(changed_fields.most_common()),
        "examples_truncated": (
            len(added_ids) > example_limit or len(removed_ids) > example_limit
            or len(changed) > example_limit
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="previous JSON array")
    parser.add_argument("after", type=Path, help="new JSON array")
    parser.add_argument("--output", type=Path, help="optional report output path")
    parser.add_argument("--example-limit", type=int, default=20)
    args = parser.parse_args()
    if args.example_limit < 0:
        parser.error("--example-limit must be non-negative")
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "before": str(args.before),
        "after": str(args.after),
        "status": "passed",
        "meaning": "Structural record diff only; changes are not proof of factual corrections.",
        **compare_records(load_records(args.before), load_records(args.after), args.example_limit),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
