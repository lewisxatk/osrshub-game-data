"""Regression tests for fail-closed item-to-quest evidence in Combat Studio."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_combat_studio_plan import build_plan, valid_unlock_evidence_record


class CombatStudioQuestUnlockGateTests(unittest.TestCase):
    def setUp(self):
        self.equipment = [{"id": 4151, "name": "Abyssal whip", "slot": "weapon",
                           "bonuses": {"melee_strength": 82}, "source_urls": ["https://oldschool.runescape.wiki/w/Abyssal_whip"]}]
        self.requirements = [{"item_id": 4151, "requirements_status": "known_empty", "requirements": [],
                              "source_url": "https://oldschool.runescape.wiki/w/Abyssal_whip"}]
        self.profile = {"skills": {"attack": 70, "strength": 70}, "completed_quests": []}
        self.costs = {"4151": 1000}

    def plan(self, unlock_rows):
        return build_plan(self.equipment, self.requirements, unlock_rows, self.profile,
                          self.costs, 10000, "melee_strength", 10, 1000)

    def test_verified_known_empty_unlock_evidence_can_pass_gate(self):
        row = {"item_id": 4151, "requirements_status": "known_empty", "required_quests": [],
               "source_url": "https://oldschool.runescape.wiki/w/Abyssal_whip"}
        self.assertTrue(valid_unlock_evidence_record(row))
        self.assertEqual(self.plan([row])["audit"][0]["status"], "eligible")

    def test_placeholder_source_is_unknown_and_excluded_from_candidates(self):
        row = {"item_id": 4151, "requirements_status": "known_empty", "required_quests": [],
               "source_url": "https://example.test/abyssal-whip"}
        self.assertFalse(valid_unlock_evidence_record(row))
        result = self.plan([row])
        self.assertEqual(result["audit"][0]["status"], "unknown")
        self.assertEqual(result["candidate_counts"]["eligible_candidates"], 0)

    def test_missing_or_duplicate_unlock_records_are_unknown(self):
        self.assertEqual(self.plan([])["audit"][0]["status"], "unknown")
        row = {"item_id": 4151, "requirements_status": "known_empty", "required_quests": [],
               "source_url": "https://oldschool.runescape.wiki/w/Abyssal_whip"}
        self.assertEqual(self.plan([row, row])["audit"][0]["status"], "unknown")

    def test_contradictory_known_empty_record_is_unknown(self):
        row = {"item_id": 4151, "requirements_status": "known_empty", "required_quests": ["Dragon Slayer"],
               "source_url": "https://oldschool.runescape.wiki/w/Abyssal_whip"}
        self.assertFalse(valid_unlock_evidence_record(row))
        self.assertEqual(self.plan([row])["audit"][0]["status"], "unknown")

    def test_uncompleted_required_quest_is_ineligible(self):
        row = {"item_id": 4151, "requirements_status": "known", "required_quests": ["Dragon Slayer"],
               "source_url": "https://oldschool.runescape.wiki/w/Abyssal_whip"}
        self.assertEqual(self.plan([row])["audit"][0]["status"], "ineligible")


if __name__ == "__main__":
    unittest.main()
