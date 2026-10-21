"""Cross-dataset integrity tests."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_database_integrity import audit_datasets

def fixture():
    return {
      "items.json":[{"id":1,"name":"Test"},{"id":2,"name":"Missing profile"}],
      "equipment-stats.json":[{"id":1,"name":"Test","slot":"weapon"}],
      "weapons.json":[{"id":1,"name":"Test","attack_speed":4}],
      "item-requirements.json":[{"item_id":1,"requirements":[]}],
      "item-relationships.json":[{"item_id":1,"relationships":[{"type":"has_equipment_stats","record_id":1},{"type":"has_weapon_data","record_id":1}]}],
      "item-combat-profiles.json":[{"id":1,"equipment_record_present":True,"weapon_record_present":True,"skill_requirement_record_present":True}],
      "monsters-combat.json":[{"id":5,"name":"Test monster"}],
      "quests.json":[],
      "quest-relationships.json":[],
    }

class DatabaseIntegrityTests(unittest.TestCase):
    def test_valid_joins_with_empty_quests_are_review_required(self):
        report=audit_datasets(fixture())
        self.assertEqual(report["status"],"review_required")
        self.assertTrue(any(w["issue"]=="empty_quest_catalogue" for w in report["warnings"]))
        self.assertTrue(any(w["issue"]=="items_without_profile" for w in report["warnings"]))

    def test_orphan_relationship_target_fails(self):
        data=fixture()
        data["item-relationships.json"][0]["relationships"][0]["record_id"]=999
        report=audit_datasets(data)
        self.assertEqual(report["status"],"failed")
        self.assertTrue(any(e["issue"]=="orphan_join_target" for e in report["errors"]))

    def test_presence_flag_mismatch_fails(self):
        data=fixture()
        data["item-combat-profiles.json"][0]["weapon_record_present"]=False
        report=audit_datasets(data)
        self.assertTrue(any(e["issue"]=="presence_flag_join_mismatch" for e in report["errors"]))

    def test_orphan_requirements_fail(self):
        data=fixture()
        data["item-requirements.json"].append({"item_id":999,"requirements":[]})
        report=audit_datasets(data)
        self.assertTrue(any(e["issue"]=="orphan_item_requirement" for e in report["errors"]))

    def test_unknown_prerequisite_fails(self):
        data=fixture()
        data["quests.json"]=[{"id":10,"name":"Quest"}]
        data["quest-relationships.json"]=[{"quest_id":10,"prerequisite_quest_ids":[999]}]
        report=audit_datasets(data)
        self.assertTrue(any(e["issue"]=="unknown_prerequisite_quest_id" for e in report["errors"]))

    def test_duplicate_item_ids_fail(self):
        data=fixture()
        data["items.json"].append({"id":1,"name":"Duplicate"})
        report=audit_datasets(data)
        self.assertTrue(any(e["dataset"]=="items.json" and e["issue"]=="duplicate_id" for e in report["errors"]))

if __name__=="__main__": unittest.main()
