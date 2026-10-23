#!/usr/bin/env python3
"""Measure how Combat Studio's top candidate changes as risk aversion varies.

This is a sensitivity analysis over an existing bounded scenario report. It does
not recalculate combat or discover candidates omitted by the source search.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "selected_item_ids", "weighted_average_dps", "worst_case_dps",
    "best_case_dps", "dps_spread", "total_cost_gp",
)


def _validate_candidates(report):
    if not isinstance(report, dict):
        raise ValueError("comparison report must be a JSON object")
    candidates = report.get("ranked_candidates")
    if not isinstance(candidates, list):
        raise ValueError("comparison report must contain ranked_candidates")
    normalized = []
    seen = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {index} must be an object")
        missing = [field for field in REQUIRED if field not in candidate]
        if missing:
            raise ValueError(f"candidate {index} missing fields: {', '.join(missing)}")
        ids = candidate["selected_item_ids"]
        if not isinstance(ids, list) or not ids or any(
            isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0 for item_id in ids
        ):
            raise ValueError(f"candidate {index} selected_item_ids must be a non-empty list of non-negative integers")
        key = tuple(ids)
        if key in seen:
            raise ValueError(f"duplicate candidate item IDs: {key}")
        seen.add(key)
        metrics = []
        for field in REQUIRED[1:5]:
            value = candidate[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"candidate {index} {field} must be finite and non-negative")
            metrics.append(float(value))
        cost = candidate["total_cost_gp"]
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise ValueError(f"candidate {index} total_cost_gp must be a non-negative integer")
        average, worst, best, spread = metrics
        if worst > average + 1e-8 or average > best + 1e-8 or abs(spread - (best - worst)) > 1e-6:
            raise ValueError(f"candidate {index} has inconsistent best/average/worst DPS or spread")
        normalized.append({
            "selected_item_ids": list(ids),
            "selected_items": candidate.get("selected_items", []),
            "total_cost_gp": cost,
            "weighted_average_dps": average,
            "worst_case_dps": worst,
            "best_case_dps": best,
            "dps_spread": spread,
        })
    return normalized


def analyze_sensitivity(report, step_percent=10, top_n=5):
    if isinstance(step_percent, bool) or not isinstance(step_percent, int) or step_percent not in (5, 10, 20, 25, 50, 100):
        raise ValueError("step_percent must be one of 5, 10, 20, 25, 50, or 100")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 20:
        raise ValueError("top_n must be an integer between 1 and 20")
    candidates = _validate_candidates(report)
    risks = [value / 100 for value in range(0, 101, step_percent)]
    if risks[-1] != 1.0:
        risks.append(1.0)

    profiles = []
    first_place_counts = {tuple(row["selected_item_ids"]): 0 for row in candidates}
    for risk in risks:
        ranked = []
        for row in candidates:
            score = (1 - risk) * row["weighted_average_dps"] + risk * row["worst_case_dps"]
            ranked.append({
                **row,
                "risk_adjusted_dps": round(score, 8),
                "risk_aversion": risk,
            })
        ranked.sort(key=lambda row: (
            -row["risk_adjusted_dps"], -row["worst_case_dps"],
            row["total_cost_gp"], tuple(row["selected_item_ids"]),
        ))
        winner = ranked[0]["selected_item_ids"] if ranked else None
        if winner is not None:
            first_place_counts[tuple(winner)] += 1
        profiles.append({
            "risk_aversion": risk,
            "winner_item_ids": winner,
            "winner_score": ranked[0]["risk_adjusted_dps"] if ranked else None,
            "top_candidates": ranked[:top_n],
        })

    unique_winners = []
    for profile in profiles:
        ids = profile["winner_item_ids"]
        key = tuple(ids) if ids is not None else None
        if key not in unique_winners:
            unique_winners.append(key)
    stability = []
    for ids, count in first_place_counts.items():
        stability.append({
            "selected_item_ids": list(ids),
            "first_place_profiles": count,
            "profile_count": len(risks),
            "first_place_share": round(count / len(risks), 4) if risks else 0,
        })
    stability.sort(key=lambda row: (-row["first_place_profiles"], tuple(row["selected_item_ids"])))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": report.get("status", "unknown"),
        "attack_style": report.get("attack_style"),
        "budget_gp": report.get("budget_gp"),
        "scenario_count": report.get("scenario_count"),
        "source_candidate_count": len(candidates),
        "risk_step_percent": step_percent,
        "risk_profile_count": len(risks),
        "top_n": top_n,
        "winner_change_count": max(0, len(unique_winners) - (1 if unique_winners and unique_winners[0] is None else 0)),
        "profiles": profiles,
        "winner_stability": stability,
        "interpretation": {
            "risk_aversion_0": "Ranks by weighted-average DPS before tie-breakers.",
            "risk_aversion_1": "Ranks by worst-case DPS before tie-breakers.",
            "winner_change_count": "Counts distinct winning loadouts observed across the tested risk settings, not the number of transitions between adjacent settings.",
            "first_place_share": "Share of sampled risk settings where a candidate ranked first; it is not a probability of winning a fight.",
        },
        "guardrails": [
            "This analysis reuses only candidates in the source report and cannot recover candidates omitted by bounded search.",
            "Risk settings are preference samples, not probabilities or empirical estimates of combat outcomes.",
            "The underlying DPS metrics retain all source-report assumptions and verification limitations.",
            "A stable winner means stable under the tested risk preferences only; it does not prove factual accuracy or global optimality.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Existing scenario-comparison JSON report")
    parser.add_argument("--step-percent", type=int, default=10, help="Risk-aversion sampling step: 5, 10, 20, 25, 50, or 100")
    parser.add_argument("--top-n", type=int, default=5, help="Number of candidates retained per risk profile (1-20)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        source = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = analyze_sensitivity(source, args.step_percent, args.top_n)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "passed", "source_candidate_count": result["source_candidate_count"],
        "risk_profile_count": result["risk_profile_count"],
        "winner_change_count": result["winner_change_count"], "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
