"""Regression tests for explicit cross-dataset item relationships."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_item_relationships as builder


class ItemRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.items = [{"id": 4151, "name": "Abyssal whip", "sources": ["fixture"]}]
        self.equipment = [{"id": 4151, "slot": "weapon"}]
        self.weapons = [{"id": 4151, "weapon_type": "whip", "attack_speed": 4}]
        self.requirements = [{"item_id": 4151, "requirements": [{"skill": "attack", "level": 70}]}]
        self.profiles = [{"id": 4151, "data_status": "joined_fields_present"}]

    def test_links_all_explicit_records_without_inference(self):
        rows, summary = builder.build_relationships(
            self.items, self.equipment, self.weapons, self.requirements, self.profiles
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            {rel["type"] for rel in rows[0]["relationships"]},
            {"has_equipment_stats", "has_weapon_data", "has_skill_requirements", "has_combat_profile"},
        )
        self.assertEqual(summary["items_with_skill_requirement_record"], 1)
        self.assertEqual(summary["items_with_combat_profile"], 1)
        self.assertEqual(summary["items_with_both"], 1)

    def test_missing_requirement_or_profile_stays_unlinked(self):
        rows, summary = builder.build_relationships(self.items, self.equipment, self.weapons, [], [])
        types = {rel["type"] for rel in rows[0]["relationships"]}
        self.assertNotIn("has_skill_requirements", types)
        self.assertNotIn("has_combat_profile", types)
        self.assertEqual(summary["items_with_skill_requirement_record"], 0)
        self.assertEqual(summary["items_with_combat_profile"], 0)

    def test_orphan_records_are_reported_in_summary(self):
        _, summary = builder.build_relationships(
            self.items, self.equipment + [{"id": 999, "slot": "head"}],
            self.weapons, self.requirements + [{"item_id": 998, "requirements": []}],
            self.profiles + [{"id": 997, "data_status": "partial"}],
        )
        self.assertEqual(summary["equipment_records_without_item"], 1)
        self.assertEqual(summary["requirement_records_without_item"], 1)
        self.assertEqual(summary["combat_profiles_without_item"], 1)

    def test_duplicate_item_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            builder.build_relationships(self.items + self.items, self.equipment, self.weapons)

    def test_boolean_id_is_not_accepted_as_integer(self):
        with self.assertRaisesRegex(ValueError, "non-negative integer id"):
            builder.index_by_id([{"id": True}], "fixture.json")


if __name__ == "__main__":
    unittest.main()
