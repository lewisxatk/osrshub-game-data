#!/usr/bin/env python3
"""Measure monster-field coverage by combat-level band without guessing missing values."""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "dist" / "monsters-combat.json"
DEFAULT_OUTPUT = ROOT / "reports" / "monster-coverage-matrix.json"
FIELDS = ("combat_level", "hitpoints", "attack_level", "strength_level", "defence_level",
          "magic_level", "ranged_level", "attack_speed", "max_hit", "slayer_level", "size")
BANDS = (("unknown", None, None), ("0-49", 0, 49), ("50-99", 50, 99),
         ("100-199", 100, 199), ("200-499", 200, 499), ("500+", 500, None))

def valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0

def load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError("Input must be a JSON array of objects")
    return data

def band_for(row: dict[str, Any]) -> str:
    level = row.get("combat_level")
    if not valid_number(level):
        return "unknown"
    for label, lower, upper in BANDS[1:]:
        if level >= lower and (upper is None or level <= upper):
            return label
    return "unknown"

def build_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {label: [] for label, _, _ in BANDS}
    for row in rows:
        grouped[band_for(row)].append(row)
    bands = {}
    for label, _, _ in BANDS:
        subset = grouped[label]
        fields = {}
        for field in FIELDS:
            count = sum(1 for row in subset if valid_number(row.get(field)))
            fields[field] = {"present": count, "missing_or_invalid": len(subset)-count,
                             "coverage_percent": round(100*count/len(subset), 2) if subset else 0.0}
        bands[label] = {"record_count": len(subset), "fields": fields}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "dataset": "dist/monsters-combat.json",
        "record_count": len(rows),
        "field_names": list(FIELDS),
        "bands": bands,
        "interpretation": "Coverage is field presence among records in each observed combat-level band. It is not a measure of combat accuracy or encounter difficulty.",
        "guardrails": ["Invalid and missing numbers are counted as missing, not replaced.",
                       "A zero numeric value is present and retained.",
                       "Band boundaries are reporting buckets only, not game categories."]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_matrix(load_rows(args.input))
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "record_count": report["record_count"],
                      "band_counts": {k: v["record_count"] for k, v in report["bands"].items()}}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
