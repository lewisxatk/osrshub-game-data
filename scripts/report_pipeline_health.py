#!/usr/bin/env python3
"""Summarize generated data-pipeline checks without treating coverage as correctness."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
INPUTS = {
    "validation": "validation.json",
    "coverage": "coverage.json",
    "normalized_data_audit": "normalized-data-audit.json",
    "schema_validation": "schema-validation.json",
    "domain_consistency": "domain-consistency-audit.json",
    "combat_readiness": "combat-readiness.json",
    "equipment_shortlist": "equipment-shortlist.json",
    "equipment_loadout_candidate": "equipment-loadout-candidate.json",
    "weapon_baseline_comparison": "weapon-baseline-comparison.json",
    "source_conflict_priorities": "source-conflict-priorities.json",
    "source_integrity": "source-integrity.json",
    "field_provenance": "field-provenance.json",
    "item_identity": "item-identity.json",
    "item_requirements": "item-requirements-coverage.json",
    "combat_categories": "combat-category-coverage.json",
    "combat_reference_checks": "combat-reference-checks.json",
    "quest_catalog": "quest-catalog-coverage.json",
    "weapon_profile_coverage": "weapon-profile-coverage.json",
    "weapon_database_comparison": "weapon-database-comparison.json",
}

def read_report(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"unreadable: {exc}"

def summarize_reports(reports):
    checks, missing, failures, reviews = {}, [], [], []
    for key, (data, error) in reports.items():
        if error:
            checks[key] = {"status": "missing" if error == "missing" else "unreadable", "detail": error}
            (missing if error == "missing" else failures).append(key)
            continue
        if not isinstance(data, dict):
            checks[key] = {"status": "invalid_report", "detail": "Report root must be a JSON object."}
            failures.append(key)
            continue
        status = data.get("status", "informational")
        checks[key] = {"status": status}
        if status in {"failed", "error", "invalid_report"}:
            failures.append(key)
        elif status in {"review_required", "warning", "warnings"}:
            reviews.append(key)
    overall = "failed" if failures else "review_required" if reviews else "incomplete" if missing else "passed"
    return {
        "status": overall,
        "checks": checks,
        "missing_reports": missing,
        "failed_reports": failures,
        "review_required_reports": reviews,
    }

def main():
    loaded = {key: read_report(REPORTS / filename) for key, filename in INPUTS.items()}
    summary = summarize_reports(loaded)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **summary,
        "interpretation": "This is a roll-up of pipeline report statuses, not proof that every OSRS mechanic is complete or factually verified.",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "pipeline-health.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if summary["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
