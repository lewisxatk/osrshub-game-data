#!/usr/bin/env python3
"""Turn source conflicts into a compact, actionable prioritization report."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INPUT = REPORTS / "source-conflicts.json"

def priority_for_field(field):
    return "high" if field.casefold() in {
        "equipment", "weapon", "attack_speed", "stances", "bonuses", "requirements",
        "combat_level", "hitpoints", "max_hit", "drops", "quest",
    } else "review"

def load_conflicts(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        conflicts = raw
    elif isinstance(raw, dict):
        conflicts = raw.get("conflicts", [])
    else:
        raise ValueError("source-conflicts.json must be an array or object containing conflicts")
    if not isinstance(conflicts, list):
        raise ValueError("source conflict collection must be an array")
    return conflicts

def summarize_conflicts(conflicts):
    by_field = Counter()
    by_category = Counter()
    field_categories = defaultdict(Counter)
    examples = defaultdict(list)
    invalid_records = 0
    for entry in conflicts:
        if not isinstance(entry, dict):
            invalid_records += 1
            continue
        field = entry.get("field")
        category = entry.get("category", "unknown")
        if not isinstance(field, str) or not field.strip():
            invalid_records += 1
            continue
        by_field[field] += 1
        by_category[str(category)] += 1
        field_categories[field][str(category)] += 1
        if len(examples[field]) < 3:
            examples[field].append({
                key: entry.get(key) for key in
                ("category", "id", "name", "field", "kept_source", "other_source", "kept_value", "other_value")
                if key in entry
            })
    ranked = []
    for field, count in by_field.most_common():
        ranked.append({
            "field": field,
            "conflict_count": count,
            "categories": dict(field_categories[field].most_common()),
            "examples": examples[field],
            "priority": priority_for_field(field),
        })
    return {
        "conflict_count": sum(by_field.values()),
        "invalid_record_count": invalid_records,
        "counts_by_category": dict(by_category.most_common()),
        "fields_ranked_by_conflict_count": ranked,
    }

def main():
    if not INPUT.exists():
        raise FileNotFoundError("reports/source-conflicts.json is missing; run scripts/build_dataset.py first")
    summary = summarize_conflicts(load_conflicts(INPUT))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if summary["invalid_record_count"] else "passed",
        "input": "reports/source-conflicts.json",
        **summary,
        "interpretation": "Conflict counts prioritize human review; they do not identify which source is correct.",
        "next_actions": [
            "Review high-priority game-mechanic fields against a trusted OSRS reference.",
            "Keep configured source precedence explicit until conflicts are adjudicated.",
            "Do not automatically choose a conflicting value solely because it appears more often.",
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "source-conflict-priorities.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if summary["invalid_record_count"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
