import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_combat_lab_readiness as audit

class CombatLabReadinessTests(unittest.TestCase):
    def test_cross_domain_gaps_are_explicit(self):
        fixture = {
            "items.json":[{"id":1,"name":"Test"}],
            "equipment-stats.json":[{"id":1,"name":"Test","slot":"weapon","bonuses":{"melee_strength":1},"requirements":[]}],
            "weapons.json":[{"id":1,"name":"Test","attack_speed":None,"weapon_type":"sword","stances":[]}],
            "item-combat-profiles.json":[{"id":1,"name":"Test","slot":"weapon","bonuses":{},"source_urls":[],"data_status":"partial"}],
            "item-requirements.json":[],
            "monsters-combat.json":[{"id":2,"name":"Boss","combat_level":300,"hitpoints":1000,"defence_level":None}],
            "quests.json":[{"id":3,"name":"Quest","field_status":{"requirements":"unknown","skill_requirements":"unknown"}}],
            "quest-relationships.json":[],
        }
        result = audit.build_report(lambda filename: fixture[filename])
        self.assertEqual(result["status"], "review_required")
        joins = result["cross_domain_joins"]
        self.assertEqual(joins["equipment_missing_combat_profile_ids"], [])
        self.assertEqual(joins["equipment_missing_requirement_record_ids"], [1])
        self.assertEqual(joins["quests_with_unknown_requirement_facts"], 1)
        findings = {row["area"]: row for row in result["findings"]}
        self.assertEqual(findings["weapon mechanics"]["count"], 1)
        self.assertEqual(findings["monster core combat data"]["count"], 1)
        self.assertTrue(result["guardrails"])

    def test_missing_dataset_fails_audit(self):
        result = audit.build_report(lambda filename: (_ for _ in ()).throw(ValueError("missing " + filename)))
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["errors"])

    def test_empty_complete_fixture_is_structurally_passed(self):
        fixture = {filename: [] for filename, _ in audit.DATASETS.values()}
        result = audit.build_report(lambda filename: fixture[filename])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["cross_domain_joins"]["equipment_record_count"], 0)

if __name__ == "__main__":
    unittest.main()
