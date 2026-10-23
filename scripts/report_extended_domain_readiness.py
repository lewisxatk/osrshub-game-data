#!/usr/bin/env python3
"""Inventory extended OSRS source domains without guessing joins or game facts."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
DOMAINS = {
    "prayers": "prayers.json",
    "npc_drops": "npc-drops.json",
    "drop_subtables": "drop-subtables.json",
    "shops_by_shop": "shops-by-shop.json",
    "shops_by_npc": "shops-by-npc.json",
    "slayer_tasks": "slayer-tasks.json",
    "npc_interactions": "npc-interactions.json",
    "npc_dialogues": "npc-dialogues.json",
    "npcs": "npcs-summary.json",
    "objects": "objects-summary.json",
    "models": "models-summary.json",
}


def nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def collect_paths(value: Any, prefix: str = "") -> Counter:
    """Count non-empty leaf/container paths; array indices are deliberately omitted."""
    counts = Counter()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if nonempty(child):
                counts[path] += 1
            if isinstance(child, (dict, list)):
                counts.update(collect_paths(child, path))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                counts.update(collect_paths(child, prefix + "[]"))
    return counts


def summarize_domain(rows: Any, filename: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError(f"{filename} must contain a JSON array")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{filename} contains a non-object record")
    keys = [row.get("source_key") for row in rows]
    invalid_keys = sum(not isinstance(key, str) or not key.strip() for key in keys)
    key_counts = Counter(key for key in keys if isinstance(key, str) and key.strip())
    duplicate_keys = sorted(key for key, count in key_counts.items() if count > 1)
    missing_urls = sum(not isinstance(row.get("source_snapshot_url"), str) or not row["source_snapshot_url"].strip() for row in rows)
    paths = Counter()
    for row in rows:
        paths.update(collect_paths(row))
    field_coverage = {
        path: {"records_with_value": count, "coverage_percent": round(100 * count / len(rows), 2) if rows else 0.0}
        for path, count in sorted(paths.items())
    }
    return {
        "dataset": filename,
        "record_count": len(rows),
        "unique_source_key_count": len(key_counts),
        "duplicate_source_keys": duplicate_keys[:50],
        "duplicate_source_key_count": len(duplicate_keys),
        "invalid_source_key_count": invalid_keys,
        "missing_source_url_count": missing_urls,
        "field_path_count": len(field_coverage),
        "field_coverage": field_coverage,
    }


def build_report(dist_dir: Path = DIST) -> dict[str, Any]:
    domains = {}
    errors = []
    for name, filename in DOMAINS.items():
        try:
            rows = json.loads((dist_dir / filename).read_text(encoding="utf-8"))
            summary = summarize_domain(rows, filename)
            domains[name] = summary
            if summary["invalid_source_key_count"] or summary["duplicate_source_key_count"] or summary["missing_source_url_count"]:
                errors.append(f"{filename} has invalid/duplicate source keys or missing source URLs")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(str(exc))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "domain_count": len(domains),
        "domains": domains,
        "errors": errors,
        "guardrails": [
            "Field-path coverage is an inventory of preserved source payloads, not a factual completeness score.",
            "Numeric-looking keys and nested fields are not treated as item/NPC joins without a documented source contract.",
            "Source URLs establish lineage to a snapshot, not independent verification of OSRS mechanics.",
            "Empty and absent values remain unknown; this report does not fill them.",
        ],
    }


def main() -> int:
    result = build_report()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "extended-domain-readiness.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
