#!/usr/bin/env python3
"""Check normalized combat datasets against reviewed, source-backed regression fixtures."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "combat-reference.json"
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def validate_fixture(fixture):
    errors = []
    if not isinstance(fixture, dict):
        return ["fixture root must be an object"]
    if fixture.get("version") != 1:
        errors.append("fixture version must be 1")
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        errors.append("cases must be an array")
        return errors
    seen = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"cases[{index}] must be an object")
            continue
        dataset = case.get("dataset")
        record_id = case.get("id")
        expected = case.get("expected")
        source = case.get("source")
        if dataset not in {"equipment-stats.json", "weapons.json", "monsters-combat.json"}:
            errors.append(f"cases[{index}] has unsupported dataset")
        if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id < 0:
            errors.append(f"cases[{index}] has invalid non-negative integer id")
        if not isinstance(expected, dict) or not expected:
            errors.append(f"cases[{index}] expected must be a non-empty object")
        if not isinstance(source, dict) or not source.get("url") or not source.get("checked_on"):
            errors.append(f"cases[{index}] needs source.url and source.checked_on")
        key = (dataset, record_id)
        if key in seen:
            errors.append(f"cases[{index}] duplicates dataset/id {key}")
        seen.add(key)
    return errors


def get_field(record, path):
    value = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def run_cases(fixture, dist_dir: Path):
    errors = validate_fixture(fixture)
    if errors:
        return {"status": "failed", "case_count": 0, "passed_count": 0, "failed_count": 0, "errors": errors}
    datasets = {}
    cases = fixture["cases"]
    failures = []
    passed = 0
    for case in cases:
        filename = case["dataset"]
        if filename not in datasets:
            path = dist_dir / filename
            try:
                rows = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(rows, list):
                    raise ValueError("dataset must be a JSON array")
                indexed = {}
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    rid = row.get("id")
                    if isinstance(rid, bool):
                        continue
                    indexed[rid] = row
                datasets[filename] = indexed
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                failures.append({"dataset": filename, "error": str(exc)})
                datasets[filename] = None
        records = datasets[filename]
        if records is None:
            continue
        record = records.get(case["id"])
        if record is None:
            failures.append({"dataset": filename, "id": case["id"], "error": "record not found"})
            continue
        mismatch = {}
        for field, expected_value in case["expected"].items():
            actual_value = get_field(record, field)
            if actual_value != expected_value:
                mismatch[field] = {"expected": expected_value, "actual": actual_value}
        if mismatch:
            failures.append({"dataset": filename, "id": case["id"], "mismatches": mismatch})
        else:
            passed += 1
    return {
        "status": "failed" if failures else "passed",
        "case_count": len(cases),
        "passed_count": passed,
        "failed_count": len(failures),
        "failures": failures[:100],
        "failures_truncated": len(failures) > 100,
        "fixture_version": fixture["version"],
    }


def main():
    try:
        fixture = json.loads(FIXTURES.read_text(encoding="utf-8"))
        result = run_cases(fixture, DIST)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"status": "failed", "case_count": 0, "passed_count": 0,
                  "failed_count": 0, "errors": [f"cannot load fixtures: {exc}"]}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
        "meaning": "Regression checks verify only explicitly reviewed fixture fields; they do not prove full dataset accuracy.",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "combat-reference-checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
