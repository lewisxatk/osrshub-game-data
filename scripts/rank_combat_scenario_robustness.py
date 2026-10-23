#!/usr/bin/env python3
"""Rank an existing bounded scenario-comparison report by configurable risk aversion.

This is a transparent decision aid, not a new combat evaluator. It uses only the
per-candidate DPS values already emitted by compare_combat_scenarios.py.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rank_report(report: dict, risk_aversion: float = 0.5, top_n: int = 20) -> dict:
    if not isinstance(report, dict):
        raise ValueError("comparison report must be a JSON object")
    if isinstance(risk_aversion, bool) or not isinstance(risk_aversion, (int, float)) or not math.isfinite(risk_aversion) or not 0 <= risk_aversion <= 1:
        raise ValueError("risk_aversion must be a finite number between 0 and 1")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be an integer between 1 and 50")
    candidates = report.get("ranked_candidates")
    if not isinstance(candidates, list):
        raise ValueError("comparison report must contain ranked_candidates")
    required = ("weighted_average_dps", "worst_case_dps", "best_case_dps", "dps_spread", "total_cost_gp", "selected_item_ids")
    ranked = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {index} must be an object")
        missing = [key for key in required if key not in candidate]
        if missing:
            raise ValueError(f"candidate {index} missing fields: {', '.join(missing)}")
        values = [candidate[key] for key in required[:4]]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in values):
            raise ValueError(f"candidate {index} DPS metrics must be finite non-negative numbers")
        cost = candidate["total_cost_gp"]
        ids = candidate["selected_item_ids"]
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise ValueError(f"candidate {index} total_cost_gp must be a non-negative integer")
        if not isinstance(ids, list) or any(isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0 for item_id in ids):
            raise ValueError(f"candidate {index} selected_item_ids must be a list of non-negative integers")
        average, worst, best, spread = values
        if worst > average + 1e-8 or average > best + 1e-8 or abs(spread - (best - worst)) > 1e-6:
            raise ValueError(f"candidate {index} has inconsistent best/average/worst DPS or spread")
        row = dict(candidate)
        row["risk_adjusted_dps"] = round((1 - risk_aversion) * average + risk_aversion * worst, 8)
        row["risk_aversion"] = float(risk_aversion)
        ranked.append(row)
    ranked.sort(key=lambda row: (
        -row["risk_adjusted_dps"], -row["worst_case_dps"],
        row["total_cost_gp"], tuple(row["selected_item_ids"]),
    ))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": report.get("status", "unknown"),
        "source_report_schema_version": report.get("schema_version"),
        "attack_style": report.get("attack_style"),
        "budget_gp": report.get("budget_gp"),
        "scenario_count": report.get("scenario_count"),
        "candidate_count": len(ranked),
        "risk_aversion": float(risk_aversion),
        "ranking_method": {
            "primary": "risk_adjusted_dps_descending",
            "formula": "(1 - risk_aversion) * weighted_average_dps + risk_aversion * worst_case_dps",
            "tie_breakers": ["worst_case_dps_descending", "total_cost_gp_ascending", "item_ids_ascending"],
            "interpretation": "0 favours weighted-average DPS; 1 ranks by worst-case DPS; intermediate values trade average performance for robustness."
        },
        "ranked_candidates": ranked[:top_n],
        "guardrails": [
            "This re-ranks only candidates already present in the input report; it does not search for new loadouts.",
            "Input candidate discovery is bounded and may be truncated; this output is not a global optimum.",
            "DPS values inherit the source report's assumptions and verification limitations.",
            "Risk aversion is a user-selected ranking preference, not a probability or a claim about real-world combat risk.",
            "Scenario weights and caller-supplied combat inputs are not independently verified by this ranking step."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Existing combat-studio-scenario-comparison JSON report")
    parser.add_argument("--risk-aversion", type=float, default=0.5, help="0=weighted-average DPS, 1=worst-case DPS")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        report = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = rank_report(report, args.risk_aversion, args.top_n)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "candidate_count": result["candidate_count"], "risk_aversion": result["risk_aversion"], "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
