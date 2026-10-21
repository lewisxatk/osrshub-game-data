"""Regression and boundary tests for scoped OSRS combat arithmetic."""
import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import combat_math as combat

class CombatMathTests(unittest.TestCase):
    def test_attack_and_defence_rolls(self):
        self.assertEqual(combat.attack_roll(100, 80), 14400)
        self.assertEqual(combat.defence_roll(75, 100), 12300)
    def test_hit_chance_both_roll_branches(self):
        self.assertAlmostEqual(combat.hit_chance(100, 50), 1 - 52 / 202)
        self.assertAlmostEqual(combat.hit_chance(50, 100), 50 / 202)
    def test_hit_chance_edges(self):
        self.assertEqual(combat.hit_chance(0, 0), 0)
        self.assertAlmostEqual(combat.hit_chance(1000, 0), 1 - 2 / 2002)
    def test_max_hit_known_arithmetic(self):
        self.assertEqual(combat.max_hit(100, 80), math.floor(0.5 + 100 * 144 / 640))
        self.assertEqual(combat.max_hit(0, 0), 0)
    def test_expected_damage_and_dps(self):
        self.assertEqual(combat.average_damage(20), 10)
        self.assertEqual(combat.expected_damage_per_attack(20, 0.5), 5)
        self.assertAlmostEqual(combat.dps(5, 4), 5 * 0.6 / 4)
    def test_calculate_core_reports_scope(self):
        result = combat.calculate_core({"effective_attack":100,"attack_bonus":80,"effective_defence":75,"defence_bonus":100,"effective_strength":100,"strength_bonus":80,"attack_speed_ticks":4})
        self.assertEqual(result["formula_version"], combat.FORMULA_VERSION)
        self.assertEqual(result["status"], "baseline_only")
        self.assertTrue(result["limitations"])
    def test_missing_input_fails(self):
        with self.assertRaisesRegex(ValueError, "missing required inputs"):
            combat.calculate_core({"effective_attack":99})
    def test_invalid_values_rejected(self):
        for call in (lambda: combat.attack_roll(-1,10), lambda: combat.defence_roll(10,-1), lambda: combat.max_hit(10,-1), lambda: combat.dps(1,0), lambda: combat.expected_damage_per_attack(10,1.1), lambda: combat.attack_roll(True,10)):
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()

if __name__ == "__main__":
    unittest.main()
