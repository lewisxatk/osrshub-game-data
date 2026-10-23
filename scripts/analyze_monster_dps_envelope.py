#!/usr/bin/env python3
"""Estimate target time-to-kill from explicit DPS inputs and known monster hitpoints.

This is an arithmetic envelope, not a combat simulator. DPS must be supplied by
the caller; this tool never derives player DPS from incomplete monster records.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "examples" / "monster-dps-scenarios.example.json"
DEFAULT_MONSTERS = ROOT / "dist" / "monsters-combat.json"
DEFAULT_OUTPUT = ROOT / "reports" / "monster-dps-envelope.json"

def read_array(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {label} {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{label} must be a JSON array of objects")
    return data

def finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0

def analyze(scenarios: list[dict[str, Any]], monsters: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {row.get("id"): row for row in monsters if isinstance(row.get("id"), int) and not isinstance(row.get("id"), bool)}
    output = []
    for scenario in scenarios:
        sid = scenario.get("scenario_id")
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError("Every scenario needs a non-empty scenario_id")
        dps_value = scenario.get("player_dps")
        if not finite_positive(dps_value):
            raise ValueError(f"Scenario {sid!r}: player_dps must be finite and greater than zero")
        monster_id = scenario.get("monster_id")
        source = "explicit_scenario_hitpoints"
        target = None
        hp = scenario.get("target_hitpoints")
        if monster_id is not None:
            if isinstance(monster_id, bool) or not isinstance(monster_id, int) or monster_id < 0:
                raise ValueError(f"Scenario {sid!r}: monster_id must be a non-negative integer")
            target = by_id.get(monster_id)
            if target is None:
                output.append({"scenario_id": sid, "status": "unknown_monster_id",
                               "monster_id": monster_id, "target_name": scenario.get("target_name", ""),
                               "player_dps": dps_value, "time_to_kill_seconds_estimate": None,
                               "time_to_kill_ticks_estimate": None, "theoretical_kills_per_hour": None,
                               "hitpoints_source": "unknown",
                               "limitations": ["Monster ID was not found in the generated dataset; no target stats were guessed."]})
                continue
            target_hp = target.get("hitpoints")
            if finite_positive(target_hp):
                hp, source = target_hp, "dist/monsters-combat.json"
            else:
                output.append({"scenario_id": sid, "status": "missing_monster_hitpoints",
                               "monster_id": monster_id, "target_name": target.get("name", ""),
                               "player_dps": dps_value, "time_to_kill_seconds_estimate": None,
                               "time_to_kill_ticks_estimate": None, "theoretical_kills_per_hour": None,
                               "hitpoints_source": "unknown",
                               "limitations": ["The database record has no positive hitpoints value; a time-to-kill estimate was withheld."]})
                continue
        if not finite_positive(hp):
            raise ValueError(f"Scenario {sid!r}: target_hitpoints must be finite and greater than zero when no valid database HP is available")
        seconds = hp / dps_value
        output.append({
            "scenario_id": sid, "status": "estimated",
            "monster_id": monster_id,
            "target_name": target.get("name", "") if target else scenario.get("target_name", "Scenario target"),
            "player_dps": dps_value, "target_hitpoints": hp,
            "time_to_kill_seconds_estimate": round(seconds, 3),
            "time_to_kill_ticks_estimate": round(seconds / 0.6, 3),
            "theoretical_kills_per_hour": round(3600 / seconds, 3),
            "hitpoints_source": source,
            "limitations": ["Constant supplied DPS is assumed for the entire encounter.",
                             "No phases, healing, immunity, defence changes, downtime, movement, supplies, respawn, or travel are modelled.",
                             "Theoretical kills per hour excludes all non-combat time and is not a farming-rate prediction."]
        })
    statuses = [r["status"] for r in output]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if output and all(s == "estimated" for s in statuses) else ("partial" if output else "empty"),
        "scenario_count": len(output),
        "estimated_count": sum(1 for r in output if r["status"] == "estimated"),
        "unresolved_count": sum(1 for r in output if r["status"] != "estimated"),
        "tick_seconds_assumption": 0.6,
        "results": output,
        "guardrails": ["DPS is an explicit scenario input, never invented by this tool.",
                       "Database hitpoints are used only when the monster ID and positive HP are present.",
                       "Time-to-kill is a constant-DPS arithmetic estimate, not a boss-accurate simulator.",
                       "An unresolved monster ID is reported as unknown, not silently replaced by scenario HP."]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--monsters", type=Path, default=DEFAULT_MONSTERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        scenarios = read_array(args.input, "scenarios")
        monsters = read_array(args.monsters, "monster dataset")
        report = analyze(scenarios, monsters)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "scenario_count": report["scenario_count"],
                      "estimated_count": report["estimated_count"], "unresolved_count": report["unresolved_count"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
