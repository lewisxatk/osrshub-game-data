#!/usr/bin/env python3
"""Build a single, conservative Combat Studio decision packet from existing reports.

This joins existing reports for human review. It does not calculate combat,
change eligibility, promote evidence, or claim that a candidate is optimal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DEFAULTS = {
    "plan": REPORTS / "combat-studio-upgrade-plan.json",
    "readiness": REPORTS / "combat-upgrade-readiness.json",
    "mechanics": REPORTS / "combat-mechanics-readiness.json",
    "sensitivity": REPORTS / "combat-studio-risk-sensitivity.json",
    "output": REPORTS / "combat-studio-decision-packet.json",
}


def _object(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _finite_number(value: Any) -> bool:
    import math
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def _count(value: Any, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default


def _recommendation_summary(row: dict, readiness_by_rank: dict) -> dict:
    rank = row.get("rank")
    readiness_row = readiness_by_rank.get(str(rank), {})
    selected = row.get("selected_items", [])
    if not isinstance(selected, list):
        selected = []
    items = []
    for item in selected:
        if not isinstance(item, dict):
            continue
        items.append({
            "item_id": item.get("item_id"),
            "item_name": item.get("item_name"),
            "slot": item.get("slot"),
            "cost_gp": item.get("cost_gp"),
        })
    changes = row.get("slot_changes", [])
    if not isinstance(changes, list):
        changes = []
    slot_changes = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        slot_changes.append({
            "slot": change.get("slot"),
            "from_item_id": change.get("from_item_id"),
            "from_item_name": change.get("from_item_name"),
            "to_item_id": change.get("to_item_id"),
            "to_item_name": change.get("to_item_name"),
            "upgrade_cost_gp": change.get("upgrade_cost_gp"),
            "melee_strength_delta": change.get("melee_strength_delta"),
            "attack_bonus_delta": change.get("attack_bonus_delta"),
        })
    review_items = readiness_row.get("review_items", [])
    blockers = readiness_row.get("blockers", [])
    if not isinstance(review_items, list):
        review_items = []
    if not isinstance(blockers, list):
        blockers = []
    warnings = row.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    return {
        "rank": rank,
        "readiness": readiness_row.get("readiness", "not_audited"),
        "baseline_dps": row.get("baseline_dps"),
        "candidate_dps": row.get("candidate_dps"),
        "dps_gain": row.get("dps_gain"),
        "dps_gain_percent": row.get("dps_gain_percent"),
        "upgrade_cost_gp": row.get("upgrade_cost_gp"),
        "remaining_budget_gp": row.get("remaining_budget_gp"),
        "dps_gain_per_million_gp": row.get("dps_gain_per_million_gp"),
        "weapon": row.get("weapon"),
        "slot_changes": slot_changes,
        "selected_items": items,
        "blockers": sorted({str(x) for x in blockers}),
        "review_items": sorted({str(x) for x in review_items}),
        "planner_warnings": sorted({str(x) for x in warnings}),
    }


def build_decision_packet(plan: dict, readiness: dict, mechanics: dict, sensitivity: dict) -> dict:
    """Join existing reports into a reviewable decision packet with explicit gates."""
    plan = _object(plan, "upgrade plan")
    readiness = _object(readiness, "upgrade readiness report")
    mechanics = _object(mechanics, "mechanics readiness report")
    sensitivity = _object(sensitivity, "risk sensitivity report")
    raw_recommendations = _list(plan.get("recommendations", []), "plan recommendations")
    audited_recommendations = _list(readiness.get("recommendations", []), "readiness recommendations")
    profiles = _list(sensitivity.get("profiles", []), "risk sensitivity profiles")
    stability = _list(sensitivity.get("winner_stability", []), "risk winner stability")
    mechanics_total = _count((mechanics.get("mechanics_summary") or {}).get("total"))
    mechanics_verified = _count((mechanics.get("mechanics_summary") or {}).get("verified"))
    mechanics_unverified = _count((mechanics.get("mechanics_summary") or {}).get("unverified_or_in_review"))
    mechanics_unsupported = _count((mechanics.get("mechanics_summary") or {}).get("unsupported"))
    readiness_counts = readiness.get("recommendation_counts", {})
    if not isinstance(readiness_counts, dict):
        readiness_counts = {}
    readiness_by_rank = {
        str(row.get("rank")): row for row in audited_recommendations if isinstance(row, dict)
    }

    recommendations = [
        _recommendation_summary(row, readiness_by_rank)
        for row in raw_recommendations if isinstance(row, dict)
    ]
    recommendations.sort(key=lambda row: (
        row["rank"] if isinstance(row["rank"], int) else 10**9,
        str(row["rank"]),
    ))
    top_candidate = recommendations[0] if recommendations else None
    truncated = bool((plan.get("search") or {}).get("truncated", False))
    if not isinstance(plan.get("search"), dict):
        truncated = bool(readiness.get("search_truncated", False))

    first_stability = stability[0] if stability and isinstance(stability[0], dict) else None
    top_share = first_stability.get("first_place_share") if first_stability else None
    if not _finite_number(top_share):
        top_share = None

    gates = [
        {
            "gate": "recommendation_exists",
            "status": "passed" if top_candidate else "blocked",
            "detail": "At least one positive-DPS-gain candidate exists in the bounded plan."
                     if top_candidate else "No positive-DPS-gain recommendation was produced; this does not prove no upgrade exists.",
        },
        {
            "gate": "search_completeness",
            "status": "review_required" if truncated else "passed",
            "detail": "The candidate search was truncated; the results are not exhaustive."
                     if truncated else "The search did not report truncation; this still does not prove global optimality.",
        },
        {
            "gate": "combat_mechanics_verification",
            "status": "passed" if mechanics_total > 0 and mechanics_verified == mechanics_total else "review_required",
            "detail": f"{mechanics_verified} of {mechanics_total} registered mechanics are marked verified.",
        },
        {
            "gate": "unsupported_mechanics",
            "status": "review_required" if mechanics_unsupported else "passed",
            "detail": f"{mechanics_unsupported} mechanics are explicitly unsupported and remain outside the calculation model.",
        },
        {
            "gate": "recommendation_readiness",
            "status": "review_required" if _count(readiness_counts.get("review_required")) or _count(readiness_counts.get("blocked")) else "passed",
            "detail": f"{_count(readiness_counts.get('candidate_only'))} candidate-only, "
                      f"{_count(readiness_counts.get('review_required'))} review-required, "
                      f"{_count(readiness_counts.get('blocked'))} blocked recommendation(s).",
        },
        {
            "gate": "risk_preference_sensitivity",
            "status": "passed" if profiles else "review_required",
            "detail": f"Compared {len(profiles)} sampled risk-preference settings; "
                      f"{_count(sensitivity.get('winner_change_count'))} distinct winning loadout(s) were observed."
                      if profiles else "No risk sensitivity profiles were available.",
        },
    ]

    actions = []
    def add(priority: str, action_id: str, title: str, reason: str) -> None:
        actions.append({"priority": priority, "action_id": action_id, "title": title, "reason": reason})

    if mechanics_verified < mechanics_total:
        add("P0", "verify_combat_mechanics", "Verify combat-critical rules against maintained sources",
            f"{mechanics_total - mechanics_verified} registered mechanic(s) are not marked verified; source links alone are not proof.")
    if mechanics_unsupported:
        add("P0", "implement_supported_mechanics", "Implement and regression-test currently unsupported mechanics",
            f"{mechanics_unsupported} mechanic(s) are outside the current model; do not silently approximate them.")
    if truncated:
        add("P1", "expand_candidate_search", "Expand or partition the bounded candidate search",
            "The current result may omit stronger valid loadouts because the search hit a configured limit.")
    if _count(readiness_counts.get("blocked")):
        add("P1", "resolve_blocked_candidates", "Resolve blocked recommendation inputs",
            f"{_count(readiness_counts.get('blocked'))} recommendation(s) failed readiness checks.")
    if _count(readiness_counts.get("review_required")):
        add("P1", "review_candidate_evidence", "Review candidate provenance and eligibility evidence",
            f"{_count(readiness_counts.get('review_required'))} recommendation(s) still need manual review.")
    if not top_candidate:
        add("P1", "inspect_no_candidate_result", "Inspect why no positive upgrade was found",
            "No candidate in this bounded run improved the baseline; review candidate coverage and constraints before concluding none exists.")
    if len(profiles) and _count(sensitivity.get("winner_change_count")) > 1:
        add("P2", "review_risk_tradeoffs", "Review loadout changes across risk preferences",
            "The winning loadout varies across sampled preference settings; the best choice depends on the selected risk preference.")
    if not actions:
        add("P2", "review_scope_before_release", "Review scope before promoting recommendations",
            "All available report gates passed, but structural checks still do not prove game accuracy or global optimality.")

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    actions.sort(key=lambda row: (priority_order[row["priority"]], row["action_id"]))
    hard_block = not top_candidate
    status = "no_candidate" if hard_block else "review_required"
    if top_candidate and all(gate["status"] == "passed" for gate in gates):
        status = "candidate_only"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": status,
        "decision_scope": {
            "attack_style": plan.get("attack_style"),
            "budget_gp": plan.get("upgrade_budget_gp"),
            "candidate_count": len(recommendations),
            "search_truncated": truncated,
            "risk_profile_count": len(profiles),
            "distinct_risk_winners": _count(sensitivity.get("winner_change_count")),
        },
        "baseline": plan.get("baseline", {}),
        "top_candidate": top_candidate,
        "recommendations": recommendations,
        "mechanics": {
            "registry_status": mechanics.get("mechanics_registry_status", mechanics.get("registry_status", "unknown")),
            "total": mechanics_total,
            "verified": mechanics_verified,
            "unverified_or_in_review": mechanics_unverified,
            "unsupported": mechanics_unsupported,
            "verified_percent": mechanics.get("verified_percent"),
        },
        "risk_sensitivity": {
            "source_candidate_count": _count(sensitivity.get("source_candidate_count")),
            "profile_count": len(profiles),
            "winner_change_count": _count(sensitivity.get("winner_change_count")),
            "most_frequent_winner": first_stability.get("selected_item_ids") if first_stability else None,
            "most_frequent_winner_share_of_sampled_preferences": top_share,
            "interpretation": "Share of sampled preference settings only; not a probability of success or winning a fight.",
        },
        "gates": gates,
        "action_queue": actions,
        "warnings": sorted({
            *[str(x) for x in plan.get("warnings", []) if isinstance(x, str)],
            *[str(x) for x in readiness.get("warnings", []) if isinstance(x, str)],
            "This packet joins existing outputs; it does not recalculate combat or change item eligibility.",
            "Candidate prices and combat inputs are caller-supplied, not live Grand Exchange data.",
            "A candidate-only state is not proof of game accuracy, boss-specific DPS, best-in-slot status, or global optimality.",
        }),
        "guardrails": [
            "Never treat unknown or unsupported mechanics as zero-cost approximations.",
            "Never treat a source reference by itself as proof that a game rule is correct.",
            "Risk-preference stability is descriptive of sampled settings, not a probability.",
            "A bounded search that was not truncated still does not prove global optimality.",
            "The packet does not promote evidence status, mutate source reports, or change candidate rankings.",
            "A green CI run proves pipeline checks passed, not that all OSRS facts are verified.",
        ],
    }


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _object(value, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULTS["plan"])
    parser.add_argument("--readiness", type=Path, default=DEFAULTS["readiness"])
    parser.add_argument("--mechanics", type=Path, default=DEFAULTS["mechanics"])
    parser.add_argument("--sensitivity", type=Path, default=DEFAULTS["sensitivity"])
    parser.add_argument("--output", type=Path, default=DEFAULTS["output"])
    args = parser.parse_args()
    try:
        packet = build_decision_packet(
            read_json(args.plan), read_json(args.readiness),
            read_json(args.mechanics), read_json(args.sensitivity),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": packet["status"],
        "candidate_count": packet["decision_scope"]["candidate_count"],
        "gate_count": len(packet["gates"]),
        "action_count": len(packet["action_queue"]),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
