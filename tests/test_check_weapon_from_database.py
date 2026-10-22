"""Tests proving the weapon checker reads only the local generated database."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_weapon_from_database import check_weapon


class DatabaseWeaponCheckerTests(unittest.TestCase):
    def test_returns_weapon_facts_from_local_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "item-combat-profiles.json").write_text(json.dumps([{
                "id": 4587, "name": "Dragon scimitar", "slot": "weapon",
                "bonuses": {"attack_slash": 67, "melee_strength": 66},
                "attack_speed": 4, "weapon_type": "scimitar",
                "skill_requirements": [{"skill": "attack", "level": 60}],
                "weapon_record_present": True, "data_status": "joined_fields_present",
                "sources": ["fixture"], "source_urls": ["https://example.invalid/record"]
            }]), encoding="utf-8")
            result = check_weapon(4587, root)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["name"], "Dragon scimitar")
        self.assertEqual(result["bonuses"]["attack_slash"], 67)
        self.assertIn("does not fetch external websites", " ".join(result["guardrails"]))

    def test_missing_dataset_is_not_filled_from_web(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = check_weapon(4587, Path(tmp))
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("bonuses", result)

    def test_duplicate_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"id": 4587, "name": "Dragon scimitar", "slot": "weapon"}
            (root / "item-combat-profiles.json").write_text(json.dumps([row, row]), encoding="utf-8")
            result = check_weapon(4587, root)
        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
