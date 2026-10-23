#!/usr/bin/env python3
"""Compute the non-dominated cost/DPS trade-off frontier from a bounded upgrade plan.

This report reuses the plan's existing DPS and cost estimates. It never recalculates
combat, adds candidates, or asserts that the frontier is globally optimal.
"""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "reports" / "combat-studio-upgrade-plan.json"
DEFAULT_OUTPUT = ROOT / "reports" / "combat-studio-upgrade-frontier.json"


def _number(value: Any, label: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if nonnegative and value < 0:
        raise ValueError(f"{label} must be non-negative")
    return float(value)


def analyze_frontier(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("plan must be a JSON object")
    recommendations = plan.get("recommendations")
    if not isinstance(recommendations, list):
        raise ValueError("plan recommendations must be an array")
    budget = plan.get("upgrade_budget_gp")
    if budget is not None:
        budget = _number(budget, "upgrade_budget_gp")
    candidates, seen = [], set()
    excluded = {"malformed": 0, "non_positive_gain": 0, "over_budget": 0}
    for index, row in enumerate(recommendations):
        if not isinstance(row, dict):
            excluded["malformed"] += 1
            continue
        gain = row.get("dps_gain")
        cost = row.get("upgrade_cost_gp")
        if not isinstance(gain, (int, float)) or isinstance(gain, bool) or not math.isfinite(gain):
            raise ValueError(f"recommendation {index} dps_gain must be finite numeric")
        if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0:
            raise ValueError(f"recommendation {index} upgrade_cost_gp must be a non-negative integer")
        if gain <= 0:
            excluded["non_positive_gain"] += 1
            continue
        if budget is not None and cost > budget:
            excluded["over_budget"] += 1
            continue
        selected = row.get("selected_items", [])
        if not isinstance(selected, list):
            selected = []
        item_ids = []
        for item in selected:
            if isinstance(item, dict):
                item_id = item.get("item_id")
                if isinstance(item_id, int) and not isinstance(item_id, bool) and item_id >= 0:
                    item_ids.append(item_id)
        key = tuple(sorted(item_ids)) if item_ids else ("rank", str(row.get("rank", index + 1)))
        if key in seen:
            raise ValueError(f"duplicate recommendation loadout identity: {key}")
        seen.add(key)
        efficiency = float(gain) * 1_000_000 / cost if cost else None
        candidates.append({
            "rank": row.get("rank", index + 1),
            "item_ids": list(sorted(item_ids)),
            "weapon": row.get("weapon"),
            "dps_gain": round(float(gain), 8),
            "dps_gain_percent": row.get("dps_gain_percent"),
            "upgrade_cost_gp": cost,
            "remaining_budget_gp": row.get("remaining_budget_gp"),
            "dps_gain_per_million_gp": round(efficiency, 8) if efficiency is not None else None,
            "slot_changes": row.get("slot_changes", []) if isinstance(row.get("slot_changes", []), list) else [],
            "warnings": row.get("warnings", []) if isinstance(row.get("warnings", []), list) else [],
        })

    def dominates(a: dict, b: dict) -> bool:
        return (a["dps_gain"] >= b["dps_gain"] and a["upgrade_cost_gp"] <= b["upgrade_cost_gp"]
                and (a["dps_gain"] > b["dps_gain"] or a["upgrade_cost_gp"] < b["upgrade_cost_gp"]))

    frontier, dominated = [], []
    for candidate in candidates:
        dominators = [other for other in candidates if other is not candidate and dominates(other, candidate)]
        if dominators:
            best = sorted(dominators, key=lambda row: (row["upgrade_cost_gp"], -row["dps_gain"]))[0]
            dominated.append({
                **candidate,
                "dominated_by_rank": best["rank"],
                "dominated_by_cost_gp": best["upgrade_cost_gp"],
                "dominated_by_dps_gain": best["dps_gain"],
            })
        else:
            frontier.append(candidate)
    frontier.sort(key=lambda row: (row["upgrade_cost_gp"], -row["dps_gain"], str(row["rank"])))
    dominated.sort(key=lambda row: (row["upgrade_cost_gp"], -row["dps_gain"], str(row["rank"])))
    by_gain = sorted(candidates, key=lambda row: (-row["dps_gain"], row["upgrade_cost_gp"], str(row["rank"])))
    by_efficiency = sorted(candidates, key=lambda row: (
        -(row["dps_gain_per_million_gp"] if row["dps_gain_per_million_gp"] is not None else math.inf),
        row["upgrade_cost_gp"], -row["dps_gain"], str(row["rank"])
    ))
    zero_cost = [row for row in candidates if row["upgrade_cost_gp"] == 0]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": "frontier_available" if frontier else "no_positive_candidate",
        "attack_style": plan.get("attack_style"),
        "budget_gp": budget,
        "source_plan_status": plan.get("status", "unknown"),
        "source_candidate_count": len(recommendations),
        "eligible_candidate_count": len(candidates),
        "frontier_count": len(frontier),
        "frontier": frontier,
        "dominated_candidates": dominated,
        "best_dps_gain_candidate": by_gain[0] if by_gain else None,
        "best_efficiency_candidate": by_efficiency[0] if by_efficiency else None,
        "zero_cost_positive_gain_candidates": zero_cost,
        "excluded_counts": excluded,
        "interpretation": [
            "A candidate is dominated only when another supplied candidate has at least as much estimated DPS gain at no greater GP cost, with one strict improvement.",
            "The frontier expresses a cost-versus-estimated-DPS trade-off, not factual accuracy or best-in-slot status.",
            "Candidates omitted by the bounded source search cannot appear on this frontier.",
            "Cost and DPS gain are copied from the source plan and are not recalculated here.",
            "A zero-cost candidate is reported separately because cost-efficiency division is undefined; inspect the source plan for why its upgrade cost is zero."
        ],
        "guardrails": [
            "This is a Pareto comparison of the source plan only; it does not prove global optimality.",
            "Caller-provided prices and combat inputs are not live Grand Exchange values.",
            "The source plan's unsupported mechanics and verification limitations remain applicable.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        plan = json.loads(args.input.read_text(encoding="utf-8"))
        result = analyze_frontier(plan)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "source_candidate_count": result["source_candidate_count"],
        "eligible_candidate_count": result["eligible_candidate_count"],
        "frontier_count": result["frontier_count"], "output": str(args.output)
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
