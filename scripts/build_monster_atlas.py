#!/usr/bin/env python3
"""Build a source-preserving monster atlas and a reproducibly selectable database fact.

This tool reports only fields already present in dist/monsters-combat.json. A
record's presence is not an independent accuracy claim. It never fills missing
stats, guesses combat style, infers weaknesses, or calculates player DPS.
"""
from __future__ import annotations
import argparse, json, random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "dist" / "monsters-combat.json"
DEFAULT_OUTPUT = ROOT / "reports" / "monster-atlas.json"
DEFAULT_FACT_OUTPUT = ROOT / "reports" / "monster-random-fact.json"
FACT_FIELDS = ("combat_level", "hitpoints", "attack_level", "strength_level",
               "defence_level", "magic_level", "ranged_level", "attack_speed",
               "max_hit", "slayer_level", "size")
NUMERIC_FIELDS = FACT_FIELDS
BANDS = (
    ("unknown", lambda n: n is None),
    ("0-49", lambda n: n is not None and 0 <= n < 50),
    ("50-99", lambda n: n is not None and 50 <= n < 100),
    ("100-199", lambda n: n is not None and 100 <= n < 200),
    ("200-499", lambda n: n is not None and 200 <= n < 500),
    ("500+", lambda n: n is not None and n >= 500),
)

def load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read monster dataset {path}: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("Monster dataset must be a JSON array of objects")
    return value

def present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}

def build_atlas(rows: list[dict[str, Any]], seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    ids = [row.get("id") for row in rows]
    valid_ids = [x for x in ids if isinstance(x, int) and not isinstance(x, bool)]
    id_counts = Counter(valid_ids)
    duplicate_ids = sorted(x for x, count in id_counts.items() if count > 1)
    field_coverage = {}
    for field in ("name", "sources", *NUMERIC_FIELDS):
        count = sum(1 for row in rows if present(row.get(field)))
        field_coverage[field] = {
            "present_records": count,
            "missing_records": len(rows) - count,
            "coverage_percent": round(count * 100 / len(rows), 2) if rows else 0.0,
        }
    bins = Counter()
    for row in rows:
        level = row.get("combat_level")
        level = level if isinstance(level, (int, float)) and not isinstance(level, bool) and level >= 0 else None
        for label, predicate in BANDS:
            if predicate(level):
                bins[label] += 1
                break
    with_hp = [r for r in rows if isinstance(r.get("hitpoints"), (int, float))
               and not isinstance(r.get("hitpoints"), bool) and r["hitpoints"] >= 0]
    largest_hp = sorted(with_hp, key=lambda r: (-r["hitpoints"], str(r.get("name", "")), r.get("id", -1)))[:20]
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    eligible = []
    for row in rows:
        facts = [(field, row.get(field)) for field in FACT_FIELDS if present(row.get(field))]
        if facts:
            eligible.append((row, facts))
    if eligible:
        record, facts = rng.choice(eligible)
        field, value = rng.choice(facts)
        fact = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "found",
            "fact_type": "random_existing_database_field",
            "monster": {"id": record.get("id"), "name": record.get("name", "")},
            "field": field,
            "value": value,
            "source_names": record.get("sources", []),
            "verification_status": "not_independently_verified_by_this_report",
            "explanation": "This value was selected from the generated monster dataset. Source presence is provenance, not proof of correctness.",
            "selection_seed": seed,
        }
    else:
        fact = {
            "generated_at": datetime.now(timezone.utc).isoformat(), "status": "not_found",
            "fact_type": "random_existing_database_field", "monster": None, "field": None,
            "value": None, "source_names": [], "verification_status": "unknown",
            "explanation": "No monster record contains a selectable non-empty combat field.",
            "selection_seed": seed,
        }
    atlas = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "dataset": "dist/monsters-combat.json",
        "record_count": len(rows),
        "unique_numeric_id_count": len(set(valid_ids)),
        "records_without_numeric_id": sum(1 for row in rows if not isinstance(row.get("id"), int) or isinstance(row.get("id"), bool)),
        "duplicate_numeric_ids": duplicate_ids,
        "duplicate_numeric_id_count": len(duplicate_ids),
        "combat_level_bands": {label: bins.get(label, 0) for label, _ in BANDS},
        "field_coverage": field_coverage,
        "highest_hitpoint_records": [
            {"id": r.get("id"), "name": r.get("name", ""), "hitpoints": r.get("hitpoints"),
             "sources": r.get("sources", [])} for r in largest_hp
        ],
        "random_fact": fact,
        "guardrails": [
            "Counts and values describe the generated dataset snapshot only.",
            "A non-empty field is not proof of factual correctness.",
            "Unknown fields remain unknown; no missing values are inferred.",
            "Combat-level bands are descriptive groupings, not difficulty ratings.",
            "This atlas does not calculate DPS, accuracy, drop probabilities, or kill times."
        ],
    }
    return atlas, fact

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fact-output", type=Path, default=DEFAULT_FACT_OUTPUT)
    parser.add_argument("--seed", type=int, default=None, help="Optional seed for a reproducible random fact")
    args = parser.parse_args()
    try:
        rows = load_rows(args.input)
        atlas, fact = build_atlas(rows, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    for path, value in ((args.output, atlas), (args.fact_output, fact)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": atlas["status"], "record_count": atlas["record_count"],
                      "random_fact": fact}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
