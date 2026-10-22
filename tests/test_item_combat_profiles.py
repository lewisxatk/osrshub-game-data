"""Tests for joined item combat profiles."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_item_combat_profiles as profiles

class ItemCombatProfileTests(unittest.TestCase):
    def test_joins_records_and_keeps_unknowns_null(self):
        items = [{"id": 4151, "name": "Abyssal whip", "wiki_url": "https://example.test/whip", "sources": ["wiki"]}]
        equipment = [{"id": 4151, "name": "Abyssal whip", "slot": "weapon", "bonuses": {"attack_slash": 82, "melee_strength": 82}, "source_url": "https://example.test/equipment", "sources": ["equipment-source"]}]
        weapons = [{"id": 4151, "name": "Abyssal whip", "attack_speed": 4, "weapon_type": "whip", "stances": [{"attack_style": "lash"}], "source_url": "https://example.test/weapon", "sources": ["weapon-source"]}]
        requirements = [{"item_id": 4151, "item_name": "Abyssal whip", "requirements": [{"skill": "Attack", "level": 70}], "source_url": None, "sources": ["requirements-source"]}]
        rows, summary = profiles.build_profiles(items, equipment, weapons, requirements)
        row = rows[0]
        self.assertEqual(row["attack_speed"], 4)
        self.assertEqual(row["bonuses"]["attack_slash"], 82)
        self.assertIsNone(row["bonuses"]["attack_stab"])
        self.assertEqual(row["skill_requirements"][0]["level"], 70)
        self.assertEqual(row["skill_requirements_status"], "unknown")
        self.assertEqual(row["data_status"], "partial")
        self.assertEqual(summary["profiles_with_attack_speed"], 1)
        self.assertIn("https://example.test/whip", row["source_urls"])

    def test_missing_join_records_are_not_fabricated(self):
        rows, summary = profiles.build_profiles([{"id": 1, "name": "Unknown"}], [], [], [])
        row = rows[0]
        self.assertIsNone(row["attack_speed"])
        self.assertIsNone(row["skill_requirements"])
        self.assertEqual(row["skill_requirements_status"], "unknown")
        self.assertEqual(summary["profiles_with_unknown_requirements"], 1)
        self.assertFalse(row["equipment_record_present"])
        self.assertEqual(row["bonuses"]["melee_strength"], None)
        self.assertEqual(summary["profiles_missing_weapon_record"], 1)

    def test_duplicate_ids_fail_loudly(self):
        with self.assertRaises(ValueError):
            profiles.build_profiles([{"id": 1}, {"id": 1}], [], [], [])

if __name__ == "__main__":
    unittest.main()
