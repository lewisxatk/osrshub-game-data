"""Broader invariant tests for the deliberately scoped combat arithmetic.

These are mathematical contract checks, not evidence that every OSRS mechanic is
implemented or independently source-verified.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import combat_math as combat


class CombatMathInvariantTests(unittest.TestCase):
    def test_hit_chance_is_bounded_for_small_roll_grid(self):
        for attack in range(0, 51):
            for defence in range(0, 51):
                with self.subTest(attack=attack, defence=defence):
                    chance = combat.hit_chance(attack, defence)
                    self.assertTrue(math.isfinite(chance))
                    self.assertGreaterEqual(chance, 0.0)
                    self.assertLessEqual(chance, 1.0)

    def test_hit_chance_is_monotonic_in_attack_roll(self):
        for defence in (0, 1, 10, 50, 100, 1000):
            chances = [combat.hit_chance(attack, defence) for attack in range(101)]
            self.assertEqual(chances, sorted(chances), msg=f"defence={defence}")

    def test_hit_chance_is_non_increasing_in_defence_roll(self):
        for attack in (0, 1, 10, 50, 100, 1000):
            chances = [combat.hit_chance(attack, defence) for defence in range(101)]
            self.assertEqual(chances, sorted(chances, reverse=True), msg=f"attack={attack}")

    def test_rolls_scale_linearly_with_effective_level(self):
        self.assertEqual(combat.attack_roll(20, 35), 20 * (35 + 64))
        self.assertEqual(combat.attack_roll(40, 35), 2 * combat.attack_roll(20, 35))
        self.assertEqual(combat.defence_roll(25, 12), 25 * (12 + 64))
        self.assertEqual(combat.defence_roll(50, 12), 2 * combat.defence_roll(25, 12))

    def test_max_hit_is_monotonic_over_supported_integer_inputs(self):
        for bonus in (0, 1, 10, 64, 100, 200):
            values = [combat.max_hit(level, bonus) for level in range(301)]
            self.assertEqual(values, sorted(values), msg=f"bonus={bonus}")
        for level in (0, 1, 10, 50, 100, 200):
            values = [combat.max_hit(level, bonus) for bonus in range(301)]
            self.assertEqual(values, sorted(values), msg=f"level={level}")

    def test_dps_scales_with_attack_interval_and_tick_rate(self):
        damage = 12.5
        self.assertAlmostEqual(combat.dps(damage, 8), combat.dps(damage, 4) / 2)
        self.assertAlmostEqual(combat.dps(damage, 4, 1.2), 2 * combat.dps(damage, 4, 0.6))

    def test_average_damage_matches_uniform_zero_to_max_model(self):
        for maximum in range(101):
            self.assertEqual(combat.average_damage(maximum), maximum / 2.0)

    def test_core_rejects_zero_speed_and_non_integer_levels(self):
        base = {
            "effective_attack": 100,
            "attack_bonus": 80,
            "effective_defence": 75,
            "defence_bonus": 100,
            "effective_strength": 100,
            "strength_bonus": 80,
            "attack_speed_ticks": 4,
        }
        invalid_cases = [
            {**base, "attack_speed_ticks": 0},
            {**base, "effective_attack": 1.5},
            {**base, "strength_bonus": True},
        ]
        for inputs in invalid_cases:
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                combat.calculate_core(inputs)


if __name__ == "__main__":
    unittest.main()
