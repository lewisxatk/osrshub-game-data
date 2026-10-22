#!/usr/bin/env python3
"""Summarize conservative item eligibility results without overstating certainty."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
VALID_STATUSES = {"excluded", "ineligible_by_known_skill_requirement", "unknown"}


def summarize_eligibility(report):
    if not isinstance(report, dict):
        raise ValueError("eligibility report must be a JSON object")
    rows = report.get("results")
    if not isinstance(rows, list):
        raise ValueError("eligibility report results must be an array")

    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    errors = []
    missing_requirement = 0
    missing_skill_levels = 0
    malformed_requirements = 0
    incomplete_unlocks = 0
    with_sources = 0
    with_source_urls = 0
    manual_exclusions = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append({"index": index, "reason": "result_not_object"})
            continue
        status = row.get("overall_status")
        if status not in VALID_STATUSES:
            errors.append({"index": index, "reason": "invalid_overall_status", "value": status})
            continue
        counts[status] += 1
        reasons = row.get("reasons", [])
        if not isinstance(reasons, list):
            errors.append({"index": index, "reason": "reasons_not_array"})
            reasons = []
        reason_text = " ".join(x for x in reasons if isinstance(x, str)).casefold()
        if "no normalized skill requirement record" in reason_text:
            missing_requirement += 1
        if "player profile is missing skill levels" in reason_text:
            missing_skill_levels += 1
        if "requirement record is malformed" in reason_text or "requirement entry is malformed" in reason_text or "invalid requirement level" in reason_text:
            malformed_requirements += 1
        if "quest, unlock" in reason_text or "requirement-completeness" in reason_text:
            incomplete_unlocks += 1
        sources = row.get("requirement_sources", [])
        urls = row.get("requirement_source_urls", [])
        if not isinstance(sources, list):
            errors.append({"index": index, "reason": "requirement_sources_not_array"})
            sources = []
        if not isinstance(urls, list):
            errors.append({"index": index, "reason": "requirement_source_urls_not_array"})
            urls = []
        if any(isinstance(x, str) and x.strip() for x in sources):
            with_sources += 1
        if any(isinstance(x, str) and x.startswith("https://") for x in urls):
            with_source_urls += 1
        if row.get("manual_exclusion") is True:
            manual_exclusions += 1

    total = len(rows)
    status = "failed" if errors else "passed_with_warnings"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "item_count_evaluated": total,
        "counts": counts,
        "manual_exclusions": manual_exclusions,
        "items_missing_requirement_record": missing_requirement,
        "items_missing_player_skill_levels": missing_skill_levels,
        "items_with_malformed_requirement_data": malformed_requirements,
        "items_with_unverified_unlock_or_completeness_checks": incomplete_unlocks,
        "items_with_requirement_source_names": with_sources,
        "items_with_https_requirement_source_urls": with_source_urls,
        "source_name_coverage_percent": round(100 * with_sources / total, 2) if total else 0.0,
        "https_source_url_coverage_percent": round(100 * with_source_urls / total, 2) if total else 0.0,
        "errors": errors[:100],
        "guardrails": [
            "Items are not promoted to fully eligible by this summary.",
            "Unknown includes incomplete requirements, profile gaps, and unmodelled quest or unlock restrictions.",
            "Source presence is not proof that the source fact is correct or complete.",
            "The summary reads the eligibility report and does not mutate item data.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(REPORTS / "item-eligibility.json"))
    parser.add_argument("--output", default=str(REPORTS / "item-eligibility-coverage.json"))
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = summarize_eligibility(report)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "item_count_evaluated": 0,
            "counts": {status: 0 for status in sorted(VALID_STATUSES)},
            "manual_exclusions": 0,
            "items_missing_requirement_record": 0,
            "items_missing_player_skill_levels": 0,
            "items_with_malformed_requirement_data": 0,
            "items_with_unverified_unlock_or_completeness_checks": 0,
            "items_with_requirement_source_names": 0,
            "items_with_https_requirement_source_urls": 0,
            "source_name_coverage_percent": 0.0,
            "https_source_url_coverage_percent": 0.0,
            "errors": [{"reason": str(exc)}],
            "guardrails": ["Failed input validation; no eligibility conclusion is implied."],
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
