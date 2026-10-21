#!/usr/bin/env python3
"""Small, explicitly scoped OSRS combat formula primitives.

These functions implement core roll/max-hit relationships only. They do not
simulate all boosts, prayers, equipment effects, style bonuses, special attacks,
NPC phases, immunities, or rounding exceptions. Callers must supply verified
effective levels and bonuses from their own source-backed rules.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FORMULA_VERSION = "core-rolls-v1"
FORMULA_SCOPE = ("Core roll and max-hit arithmetic from supplied effective levels and bonuses. "
    "Not a complete end-to-end DPS calculator; all upstream effective-level and special-mechanic inputs must be verified separately.")

def _non_negative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value

def attack_roll(effective_attack: int, attack_bonus: int) -> int:
    """Standard attack roll: effective attack × (attack bonus + 64)."""
    return _non_negative_int("effective_attack", effective_attack) * (_non_negative_int("attack_bonus", attack_bonus) + 64)

def defence_roll(effective_defence: int, defence_bonus: int) -> int:
    """Standard defence roll: effective defence × (defence bonus + 64)."""
    return _non_negative_int("effective_defence", effective_defence) * (_non_negative_int("defence_bonus", defence_bonus) + 64)

def hit_chance(attack: int, defence: int) -> float:
    """Standard roll-comparison hit chance in [0, 1]."""
    attack = _non_negative_int("attack roll", attack)
    defence = _non_negative_int("defence roll", defence)
    chance = 1.0 - (defence + 2) / (2.0 * (attack + 1)) if attack > defence else attack / (2.0 * (defence + 1))
    return min(1.0, max(0.0, chance))

def max_hit(effective_strength: int, strength_bonus: int) -> int:
    """Standard max hit from a precomputed effective strength and bonus."""
    level = _non_negative_int("effective_strength", effective_strength)
    bonus = _non_negative_int("strength_bonus", strength_bonus)
    return math.floor(0.5 + level * (bonus + 64) / 640)

def average_damage(maximum_hit: int) -> float:
    """Expected damage for a uniform 0..max-hit roll before target mechanics."""
    return _non_negative_int("maximum_hit", maximum_hit) / 2.0

def expected_damage_per_attack(maximum_hit: int, chance_to_hit: float) -> float:
    maximum_hit = _non_negative_int("maximum_hit", maximum_hit)
    if isinstance(chance_to_hit, bool) or not isinstance(chance_to_hit, (int, float)) or not math.isfinite(chance_to_hit) or not 0 <= chance_to_hit <= 1:
        raise ValueError("chance_to_hit must be finite and between 0 and 1")
    return average_damage(maximum_hit) * chance_to_hit

def dps(expected_damage: float, attack_speed_ticks: int, ticks_per_second: float = 0.6) -> float:
    """Convert expected damage per attack to DPS using supplied attack speed."""
    if isinstance(expected_damage, bool) or not isinstance(expected_damage, (int, float)) or not math.isfinite(expected_damage) or expected_damage < 0:
        raise ValueError("expected_damage must be finite and non-negative")
    speed = _non_negative_int("attack_speed_ticks", attack_speed_ticks)
    if speed == 0:
        raise ValueError("attack_speed_ticks must be greater than zero")
    if isinstance(ticks_per_second, bool) or not isinstance(ticks_per_second, (int, float)) or not math.isfinite(ticks_per_second) or ticks_per_second <= 0:
        raise ValueError("ticks_per_second must be finite and greater than zero")
    return expected_damage / (speed / ticks_per_second)

def calculate_core(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compute transparent baseline arithmetic from precomputed inputs."""
    required = ("effective_attack", "attack_bonus", "effective_defence", "defence_bonus", "effective_strength", "strength_bonus", "attack_speed_ticks")
    missing = [key for key in required if key not in inputs]
    if missing:
        raise ValueError("missing required inputs: " + ", ".join(missing))
    ar = attack_roll(inputs["effective_attack"], inputs["attack_bonus"])
    dr = defence_roll(inputs["effective_defence"], inputs["defence_bonus"])
    chance = hit_chance(ar, dr)
    maximum = max_hit(inputs["effective_strength"], inputs["strength_bonus"])
    expected = expected_damage_per_attack(maximum, chance)
    speed = inputs["attack_speed_ticks"]
    return {
        "formula_version": FORMULA_VERSION, "status": "baseline_only",
        "inputs": {key: inputs[key] for key in required},
        "attack_roll": ar, "defence_roll": dr, "hit_chance": round(chance, 8),
        "max_hit": maximum, "average_damage_on_hit": average_damage(maximum),
        "expected_damage_per_attack": round(expected, 8), "attack_speed_ticks": speed,
        "dps": round(dps(expected, speed), 8),
        "limitations": [
            "Effective levels and equipment bonuses are supplied inputs, not derived from player settings.",
            "No prayers, potions, special attacks, style-specific max-hit effects, NPC phases, immunities, or damage caps are modelled.",
            "Damage is approximated as a uniform integer roll from zero to max hit; mechanics that change the distribution require explicit modelling.",
            "This baseline is not a verified boss-specific loadout DPS result."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file containing precomputed effective levels, bonuses and attack speed")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()
    try:
        inputs = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(inputs, dict):
            raise ValueError("input JSON root must be an object")
        result = calculate_core(inputs)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["scope"] = FORMULA_SCOPE
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
