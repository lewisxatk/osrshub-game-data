#!/usr/bin/env python3
"""Build an explicit-ID cross-domain coverage graph without inferring game facts."""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "items": ("items.json", "id"),
    "equipment": ("equipment-stats.json", "id"),
    "weapons": ("weapons.json", "id"),
    "requirements": ("item-requirements.json", "item_id"),
    "combat_profiles": ("item-combat-profiles.json", "id"),
    "item_relationships": ("item-relationships.json", "item_id"),
    "monsters": ("monsters-combat.json", "id"),
    "quests": ("quests.json", "key"),
    "quest_relationships": ("quest-relationships.json", "quest_key"),
}
ITEM_EDGES = [
    ("items", "equipment", "item_has_equipment_stats"),
    ("items", "weapons", "item_has_weapon_record"),
    ("items", "requirements", "item_has_requirement_record"),
    ("items", "combat_profiles", "item_has_combat_profile"),
    ("items", "item_relationships", "item_has_relationship_summary"),
]
QUEST_EDGES = [("quests", "quest_relationships", "quest_has_prerequisite_record")]

def valid_id(value):
    if isinstance(value, bool): return False
    if isinstance(value, int): return value >= 0
    if isinstance(value, str): return bool(value.strip())
    return False

def load_datasets(directory: Path, filenames=None):
    datasets, errors = {}, []
    for name, (filename, id_field) in SPECS.items():
        if filenames is not None and filename not in filenames:
            continue
        path = directory / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{filename}: {exc}")
            continue
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            errors.append(f"{filename}: expected an array of objects")
            continue
        datasets[name] = data
    return datasets, errors

def build_report(datasets, input_errors=None):
    errors = list(input_errors or [])
    indexes, summaries = {}, {}
    for name, rows in datasets.items():
        filename, field = SPECS[name]
        ids, missing, invalid, duplicates = [], 0, 0, []
        seen = set()
        for row in rows:
            value = row.get(field)
            if value is None or value == "":
                missing += 1
            elif not valid_id(value):
                invalid += 1
            elif value in seen:
                duplicates.append(value)
            else:
                seen.add(value)
                ids.append(value)
        indexes[name] = set(ids)
        summaries[name] = {
            "file": filename, "identity_field": field, "record_count": len(rows),
            "unique_valid_id_count": len(seen), "missing_id_count": missing,
            "invalid_id_count": invalid, "duplicate_id_count": len(set(duplicates)),
            "duplicate_id_samples": sorted((str(x) for x in set(duplicates)))[:20],
        }
        if missing or invalid or duplicates:
            errors.append(f"{name}: missing={missing}, invalid={invalid}, duplicate={len(set(duplicates))}")
    edge_specs = ITEM_EDGES + QUEST_EDGES
    edges, gaps = [], []
    for source, target, kind in edge_specs:
        if source not in indexes or target not in indexes:
            gaps.append({"edge_type": kind, "source_domain": source, "target_domain": target,
                         "state": "not_assessed", "source_count": len(indexes.get(source, set())),
                         "target_count": len(indexes.get(target, set())),
                         "message": "One or both required datasets are unavailable; no zero-coverage claim made."})
            continue
        src, dst = indexes[source], indexes[target]
        shared = src & dst
        missing_targets = src - dst
        orphan_targets = dst - src
        edge = {"edge_type": kind, "source_domain": source, "target_domain": target,
                "source_count": len(src), "target_count": len(dst), "linked_source_count": len(shared),
                "source_without_target_count": len(missing_targets), "orphan_target_count": len(orphan_targets),
                "source_coverage_percent": round(100 * len(shared) / len(src), 2) if src else 0.0,
                "missing_source_id_samples": sorted((str(x) for x in missing_targets))[:25],
                "orphan_target_id_samples": sorted((str(x) for x in orphan_targets))[:25]}
        edges.append(edge)
        if missing_targets:
            gaps.append({"edge_type": kind, "source_domain": source, "target_domain": target,
                         "state": "missing_targets", "affected_records": len(missing_targets),
                         "priority": "high" if kind in {"item_has_equipment_stats", "item_has_weapon_record", "item_has_requirement_record", "item_has_combat_profile"} else "medium",
                         "sample_ids": edge["missing_source_id_samples"]})
        if orphan_targets:
            gaps.append({"edge_type": kind, "source_domain": source, "target_domain": target,
                         "state": "orphan_targets", "affected_records": len(orphan_targets),
                         "priority": "medium", "sample_ids": edge["orphan_target_id_samples"]})
    not_assessed = sum(g["state"] == "not_assessed" for g in gaps)
    status = "failed" if input_errors else "review_required" if errors or gaps or not_assessed else "passed"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "schema_version": "1.0.0",
        "status": status,
        "interpretation": "ID-join coverage only. Shared IDs show structural linkage, not factual correctness, quest unlock semantics, or game-mechanic verification.",
        "dataset_count": len(summaries), "datasets": summaries, "edge_count": len(edges),
        "edges": edges, "gap_count": len(gaps), "gaps": gaps,
        "input_error_count": len(input_errors or []), "integrity_issue_count": len(errors),
        "integrity_issues": errors[:200],
        "guardrails": [
            "No joins are inferred from matching names or descriptions.",
            "Missing records and unknown facts are not converted into zero or false.",
            "A shared numeric ID is a structural join only, not proof of an unlock or mechanic.",
            "A review_required report is an audit queue, not a claim that the database is unusable.",
            "Only the listed datasets and edge contracts are measured; this is not full OSRS graph coverage."
        ]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/domain-graph-health.json")
    args = parser.parse_args()
    datasets, input_errors = load_datasets(args.dist_dir)
    report = build_report(datasets, input_errors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Domain graph health: {report['status']} ({report['dataset_count']} datasets, {report['edge_count']} edges, {report['gap_count']} gaps)")
    if report["status"] == "failed":
        raise SystemExit(1)
if __name__ == "__main__":
    main()
