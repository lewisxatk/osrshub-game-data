"""Tests for quest fact state and evidence coverage audit."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_quest_fact_quality import audit_quest_facts

def record(key, states=None, sources=None, **values):
    row={"key":key,"name":key.title(),"requirements":[],"skill_requirements":[],"rewards":[],"members":None,"difficulty":None,"quest_type":None,
         "field_status":states or {f:"unknown" for f in ("requirements","skill_requirements","rewards","members","difficulty","quest_type")},
         "field_sources":sources or {}}
    row.update(values)
    return row

class QuestFactQualityTests(unittest.TestCase):
    def test_known_empty_is_separate_from_unknown(self):
        states={f:"unknown" for f in ("requirements","skill_requirements","rewards","members","difficulty","quest_type")}
        states["requirements"]="known"
        result=audit_quest_facts([record("a",states)])
        self.assertEqual(result["fields"]["requirements"]["known_empty_count"],1)
        self.assertEqual(result["fields"]["requirements"]["unknown_count"],0)
        self.assertEqual(result["fields"]["rewards"]["unknown_count"],1)
    def test_field_level_evidence_is_counted(self):
        states={f:"known" for f in ("requirements","skill_requirements","rewards","members","difficulty","quest_type")}
        result=audit_quest_facts([record("a",states,{"requirements":"https://oldschool.runescape.wiki/w/A"})])
        self.assertEqual(result["fields"]["requirements"]["source_url_count"],1)
        self.assertEqual(result["fields"]["rewards"]["known_without_field_source_count"],1)
        self.assertEqual(result["status"],"review_required")
    def test_duplicate_keys_fail_and_names_warn(self):
        result=audit_quest_facts([record("a"),record("a")])
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["duplicate_key_count"],1)
    def test_unresolved_prerequisites_are_visible(self):
        result=audit_quest_facts([record("a")],{"unresolved_requirement_count":3})
        self.assertEqual(result["unresolved_prerequisite_reference_count"],3)
        self.assertTrue(any(w["issue"]=="unresolved_prerequisite_references" for w in result["warnings"]))
    def test_empty_dataset_does_not_pass(self):
        self.assertEqual(audit_quest_facts([])["status"],"review_required")
    def test_missing_field_status_is_not_assumed_known(self):
        result=audit_quest_facts([{"key":"a","name":"A"}])
        self.assertTrue(any(w["issue"]=="field_status_missing" for w in result["warnings"]))
        self.assertEqual(result["status"],"review_required")

if __name__=="__main__": unittest.main()
