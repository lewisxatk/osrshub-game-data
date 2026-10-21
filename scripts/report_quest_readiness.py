#!/usr/bin/env python3
"""Summarize whether imported quest data is usable for account restrictions."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def build_report(quests, relationships, import_report, relationship_report):
    errors = []
    warnings = []
    if not isinstance(quests, list):
        errors.append("Quest dataset must be a JSON array")
        quests = []
    if not isinstance(relationships, list):
        errors.append("Quest relationship dataset must be a JSON array")
        relationships = []
    if not isinstance(import_report, dict):
        errors.append("Quest import report is missing or malformed")
        import_report = {}
    if not isinstance(relationship_report, dict):
        errors.append("Quest relationship report is missing or malformed")
        relationship_report = {}
    names = set()
    duplicate_names = 0
    with_source = with_prereqs = with_skills = with_rewards = 0
    for index, row in enumerate(quests):
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"].strip():
            errors.append(f"Invalid quest record at index {index}")
            continue
        name = " ".join(row["name"].casefold().split())
        if name in names:
            duplicate_names += 1
        names.add(name)
        with_source += bool(row.get("source_url"))
        with_prereqs += bool(row.get("requirements"))
        with_skills += bool(row.get("skill_requirements"))
        with_rewards += bool(row.get("rewards"))
    if duplicate_names:
        warnings.append(f"{duplicate_names} duplicate normalized quest names need review")
    if not quests:
        warnings.append("No quest records are available; account restrictions must not assume quest access")
    if len(relationships) != len(quests):
        warnings.append("Quest relationship record count does not match the quest dataset")
    unresolved = relationship_report.get("unresolved_requirement_count", 0)
    if not isinstance(unresolved, int) or unresolved < 0:
        warnings.append("Quest relationship unresolved count is invalid")
        unresolved = None
    if unresolved:
        warnings.append(f"{unresolved} quest prerequisite references remain unresolved")
    count = len(quests)
    coverage = lambda n: round(n * 100 / count, 2) if count else 0.0
    ready = bool(count) and not errors and with_source == count and unresolved == 0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "ready_for_review" if ready else "incomplete",
        "quest_count": count,
        "relationship_count": len(relationships),
        "source_url_coverage_percent": coverage(with_source),
        "prerequisite_coverage_percent": coverage(with_prereqs),
        "skill_requirement_coverage_percent": coverage(with_skills),
        "reward_coverage_percent": coverage(with_rewards),
        "unresolved_requirement_count": unresolved,
        "duplicate_normalized_name_count": duplicate_names,
        "import_status": import_report.get("status"),
        "relationship_status": relationship_report.get("status"),
        "account_restriction_safe_to_assume_unlisted_quests_complete": False,
        "errors": errors,
        "warnings": warnings,
        "note": "Coverage describes field presence only. Even ready_for_review requires human source verification; missing quest records never imply completion or access."
    }


def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    result = build_report(
        read_json(DIST / "quests.json", []),
        read_json(DIST / "quest-relationships.json", []),
        read_json(REPORTS / "quest-coverage.json", {}),
        read_json(REPORTS / "quest-relationship-coverage.json", {}),
    )
    (REPORTS / "quest-readiness.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
