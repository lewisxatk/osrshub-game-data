#!/usr/bin/env python3
"""Audit upgrade recommendations for evidence gaps and calculation guardrails.

This report is a release-readiness aid, not a probability/confidence score or a
claim that baseline combat arithmetic is fully OSRS-accurate.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REGISTRY = ROOT / "data" / "combat-mechanics-registry.json"


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def audit_plan(plan: Any, registry: Any) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(plan, dict):
        raise ValueError("upgrade plan must be a JSON object")
    if not isinstance(registry, dict) or not isinstance(registry.get("mechanics"), list):
        raise ValueError("mechanics registry must contain a mechanics array")
    recommendations = plan.get("recommendations")
    if not isinstance(recommendations, list):
        raise ValueError("upgrade plan recommendations must be an array")

    mechanics = [row for row in registry["mechanics"] if isinstance(row, dict)]
    verified = [row for row in mechanics if row.get("verification_status") == "verified"]
    unverified = [row for row in mechanics if row.get("verification_status") in ("unverified", "in_review")]
    unsupported = [row for row in mechanics if row.get("verification_status") == "unsupported"]
    search = plan.get("search") if isinstance(plan.get("search"), dict) else {}
    truncated = search.get("truncated") is True or search.get("status") in ("truncated", "search_truncated")
    budget = plan.get("upgrade_budget_gp")
    if not is_number(budget) or budget < 0:
        errors.append("Upgrade plan has no valid non-negative upgrade budget.")
    recommendation_rows = []
    for index, row in enumerate(recommendations):
        if not isinstance(row, dict):
            errors.append(f"Recommendation at index {index} is not an object.")
            continue
        rank = row.get("rank", index + 1)
        gain = row.get("dps_gain")
        cost = row.get("upgrade_cost_gp")
        remaining = row.get("remaining_budget_gp")
        blockers, review_items = [], []
        if not is_number(gain):
            blockers.append("DPS gain is missing or non-numeric.")
        elif gain <= 0:
            blockers.append("Candidate does not produce a positive DPS gain over baseline.")
        if not is_number(cost) or cost < 0:
            blockers.append("Upgrade cost is missing or invalid.")
        if not is_number(remaining) or remaining < 0:
            blockers.append("Remaining budget is missing or invalid.")
        elif is_number(budget) and is_number(cost) and cost + remaining != budget:
            review_items.append("Reported upgrade cost and remaining budget do not reconcile to the plan budget.")
        if truncated:
            review_items.append("Candidate search was truncated; this recommendation is not proven globally optimal.")
        row_warnings = row.get("warnings", [])
        if isinstance(row_warnings, list):
            review_items.extend(f"Planner warning: {item}" for item in row_warnings if isinstance(item, str))
        selected = row.get("selected_items", [])
        if not isinstance(selected, list) or not selected:
            blockers.append("No selected item records were supplied.")
            selected = []
        selected_summary = []
        for item in selected:
            if not isinstance(item, dict):
                review_items.append("A selected item entry is malformed.")
                continue
            item_id = item.get("item_id", item.get("id"))
            name = item.get("item_name", item.get("name"))
            source_urls = item.get("source_urls")
            if not isinstance(source_urls, list) or not any(
                isinstance(url, str) and url.startswith("https://") for url in source_urls
            ):
                review_items.append(f"Selected item {item_id if item_id is not None else name!r} has no retained HTTPS source URL.")
            req_status = item.get("skill_requirements_status", item.get("requirements_status"))
            if req_status not in ("known", "known_empty"):
                review_items.append(f"Selected item {item_id if item_id is not None else name!r} has unconfirmed or missing skill-requirement knowledge status.")
            selected_summary.append({"item_id": item_id, "item_name": name, "source_url_present": bool(
                isinstance(source_urls, list) and any(isinstance(url, str) and url.startswith("https://") for url in source_urls)
            ), "requirements_status": req_status if isinstance(req_status, str) else "unknown"})
        if unverified:
            review_items.append(f"{len(unverified)} combat mechanics are unverified or in review in the registry.")
        if unsupported:
            review_items.append(f"{len(unsupported)} combat mechanics are explicitly unsupported; the estimate does not cover them.")
        readiness = "blocked" if blockers else "review_required" if review_items else "candidate_only"
        recommendation_rows.append({
            "rank": rank,
            "readiness": readiness,
            "dps_gain": gain if is_number(gain) else None,
            "upgrade_cost_gp": cost if is_number(cost) else None,
            "remaining_budget_gp": remaining if is_number(remaining) else None,
            "blockers": sorted(set(blockers)),
            "review_items": sorted(set(review_items)),
            "selected_items": selected_summary,
        })
    counts = {key: sum(row["readiness"] == key for row in recommendation_rows)
              for key in ("candidate_only", "review_required", "blocked")}
    if truncated:
        warnings.append("Candidate search was truncated; do not interpret the ranked list as exhaustive.")
    if unverified:
        warnings.append("One or more registered combat mechanics remain unverified.")
    if unsupported:
        warnings.append("Unsupported mechanics remain outside the current calculation model.")
    if not recommendations:
        warnings.append("No upgrade recommendations were produced; this is not proof that no upgrade exists.")
    status = "failed" if errors else "review_required" if warnings or counts["review_required"] or counts["blocked"] else "candidate_only"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": status,
        "plan_status": plan.get("status", "unknown"),
        "mechanics_registry_status": registry.get("registry_status", "unknown"),
        "mechanics_summary": {
            "total": len(mechanics), "verified": len(verified),
            "unverified_or_in_review": len(unverified), "unsupported": len(unsupported),
        },
        "search_truncated": truncated,
        "upgrade_budget_gp": budget if is_number(budget) else None,
        "recommendation_counts": counts,
        "recommendations": recommendation_rows,
        "errors": errors,
        "warnings": warnings,
        "guardrails": [
            "Readiness labels are deterministic review states, not statistical confidence scores.",
            "A candidate-only result is not proof of game accuracy, best-in-slot status, or boss-specific DPS.",
            "The audit does not alter planner recommendations or invent missing source facts.",
            "Caller-supplied prices and combat inputs are not independently verified by this audit.",
        ],
    }


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default=str(REPORTS / "combat-studio-upgrade-plan.json"))
    parser.add_argument("--registry", default=str(REGISTRY))
    parser.add_argument("--output", default=str(REPORTS / "combat-upgrade-readiness.json"))
    args = parser.parse_args()
    try:
        result = audit_plan(read_json(args.plan), read_json(args.registry))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
