import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_monster_atlas import build_atlas, load_rows
from audit_monster_coverage_matrix import build_matrix, band_for
from analyze_monster_dps_envelope import analyze
from audit_monster_identity import audit
from audit_monster_drop_links import audit_links, explicit_id

class MonsterAtlasTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"id": 1, "name": "Fixture Goblin", "combat_level": 2, "hitpoints": 5,
             "attack_level": 1, "sources": ["fixture"]},
            {"id": 2, "name": "Fixture Dragon", "combat_level": 200, "hitpoints": 300,
             "defence_level": 100, "attack_speed": 4, "sources": ["fixture", "second"]},
            {"id": 3, "name": "Unknown Fixture", "combat_level": None, "hitpoints": None,
             "sources": []},
        ]

    def test_atlas_counts_records_and_ids(self):
        atlas, fact = build_atlas(self.rows, seed=7)
        self.assertEqual(atlas["record_count"], 3)
        self.assertEqual(atlas["unique_numeric_id_count"], 3)
        self.assertEqual(atlas["duplicate_numeric_id_count"], 0)
        self.assertEqual(fact["status"], "found")

    def test_seed_makes_random_fact_reproducible(self):
        self.assertEqual(build_atlas(self.rows, seed=42)[1]["monster"],
                         build_atlas(self.rows, seed=42)[1]["monster"])
        self.assertEqual(build_atlas(self.rows, seed=42)[1]["field"],
                         build_atlas(self.rows, seed=42)[1]["field"])
        self.assertEqual(build_atlas(self.rows, seed=42)[1]["value"],
                         build_atlas(self.rows, seed=42)[1]["value"])

    def test_atlas_retains_unknowns_and_does_not_infer(self):
        atlas, _ = build_atlas(self.rows, seed=1)
        self.assertEqual(atlas["field_coverage"]["hitpoints"]["missing_records"], 1)
        self.assertIn("no missing values are inferred", " ".join(atlas["guardrails"]))

    def test_empty_atlas_is_safe(self):
        atlas, fact = build_atlas([], seed=1)
        self.assertEqual(atlas["record_count"], 0)
        self.assertEqual(atlas["field_coverage"]["hitpoints"]["coverage_percent"], 0)
        self.assertEqual(fact["status"], "not_found")

    def test_load_rows_rejects_object_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"id": 1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rows(p)

    def test_combat_level_bands_boundaries(self):
        self.assertEqual(band_for({"combat_level": 49}), "0-49")
        self.assertEqual(band_for({"combat_level": 50}), "50-99")
        self.assertEqual(band_for({"combat_level": 99}), "50-99")
        self.assertEqual(band_for({"combat_level": 100}), "100-199")
        self.assertEqual(band_for({"combat_level": 500}), "500+")
        self.assertEqual(band_for({"combat_level": None}), "unknown")

    def test_coverage_matrix_denominators_are_per_band(self):
        matrix = build_matrix(self.rows)
        self.assertEqual(matrix["bands"]["0-49"]["record_count"], 1)
        self.assertEqual(matrix["bands"]["200-499"]["record_count"], 1)
        self.assertEqual(matrix["bands"]["unknown"]["record_count"], 1)
        self.assertEqual(matrix["bands"]["0-49"]["fields"]["hitpoints"]["coverage_percent"], 100)
        self.assertEqual(matrix["bands"]["unknown"]["fields"]["hitpoints"]["coverage_percent"], 0)

    def test_coverage_counts_zero_as_present(self):
        matrix = build_matrix([{"id": 1, "combat_level": 0, "hitpoints": 0}])
        self.assertEqual(matrix["bands"]["0-49"]["fields"]["hitpoints"]["present"], 1)

    def test_dps_envelope_uses_database_hitpoints(self):
        result = analyze([{"scenario_id": "a", "monster_id": 2, "player_dps": 10}],
                         self.rows)
        row = result["results"][0]
        self.assertEqual(row["status"], "estimated")
        self.assertEqual(row["target_hitpoints"], 300)
        self.assertEqual(row["time_to_kill_seconds_estimate"], 30)
        self.assertEqual(row["time_to_kill_ticks_estimate"], 50)
        self.assertEqual(row["hitpoints_source"], "dist/monsters-combat.json")

    def test_dps_envelope_supports_explicit_fixture_target(self):
        result = analyze([{"scenario_id": "fixture", "target_name": "Synthetic target",
                           "target_hitpoints": 100, "player_dps": 5}], [])
        self.assertEqual(result["results"][0]["time_to_kill_seconds_estimate"], 20)
        self.assertEqual(result["results"][0]["theoretical_kills_per_hour"], 180)

    def test_dps_unknown_monster_does_not_fall_back_to_scenario_hp(self):
        result = analyze([{"scenario_id": "missing", "monster_id": 999,
                           "target_hitpoints": 100, "player_dps": 5}], self.rows)
        self.assertEqual(result["results"][0]["status"], "unknown_monster_id")
        self.assertIsNone(result["results"][0]["time_to_kill_seconds_estimate"])

    def test_dps_missing_hp_is_unresolved(self):
        result = analyze([{"scenario_id": "unknown-hp", "monster_id": 3, "player_dps": 5}], self.rows)
        self.assertEqual(result["results"][0]["status"], "missing_monster_hitpoints")
        self.assertEqual(result["unresolved_count"], 1)

    def test_dps_requires_positive_finite_value(self):
        for value in (0, -1, True, float("nan"), float("inf"), "10"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    analyze([{"scenario_id": "bad", "target_hitpoints": 100, "player_dps": value}], [])

    def test_dps_requires_scenario_id(self):
        with self.assertRaises(ValueError):
            analyze([{"target_hitpoints": 100, "player_dps": 5}], [])

    def test_dps_rejects_invalid_monster_id(self):
        with self.assertRaises(ValueError):
            analyze([{"scenario_id": "bad", "monster_id": True, "player_dps": 5}], self.rows)

    def test_identity_reports_duplicate_ids_and_names(self):
        result = audit([{"id": 1, "name": "Goblin", "hitpoints": 5},
                        {"id": 1, "name": "goblin", "hitpoints": 6}])
        self.assertEqual(result["duplicate_id_count"], 1)
        self.assertEqual(result["duplicate_name_group_count"], 1)
        self.assertEqual(result["status"], "review_required")

    def test_identity_accepts_zero_and_null(self):
        result = audit([{"id": 0, "name": "Fixture", "combat_level": 0, "hitpoints": None}])
        self.assertEqual(result["invalid_numeric_value_count"], 0)
        self.assertEqual(result["missing_id_count"], 0)

    def test_identity_reports_negative_and_boolean_numbers(self):
        result = audit([{"id": 1, "name": "Fixture", "hitpoints": -1, "attack_speed": True}])
        self.assertEqual(result["invalid_numeric_value_count"], 2)

    def test_explicit_drop_ids_only(self):
        self.assertEqual(explicit_id({"npc_id": "12"}), 12)
        self.assertIsNone(explicit_id({"source_key": "12", "name": "No join"}))

    def test_drop_link_audit_separates_linked_unresolved_orphaned(self):
        result = audit_links([{"id": 1}, {"id": 2}],
                             [{"npc_id": 1}, {"source_key": "2"}, {"npc_id": 99}])
        self.assertEqual(result["explicit_link_count"], 1)
        self.assertEqual(result["unresolved_drop_record_count"], 1)
        self.assertEqual(result["orphan_explicit_link_count"], 1)
        self.assertEqual(result["status"], "review_required")

    def test_drop_link_audit_does_not_call_unknown_id_an_orphan(self):
        result = audit_links([{"id": 1}], [{"source_key": "a"}])
        self.assertEqual(result["orphan_explicit_link_count"], 0)
        self.assertEqual(result["unresolved_drop_record_count"], 1)

    def test_drop_link_empty_data_safe(self):
        result = audit_links([], [])
        self.assertEqual(result["explicit_link_coverage_percent"], 0)
        self.assertEqual(result["status"], "passed")

if __name__ == "__main__":
    unittest.main()
