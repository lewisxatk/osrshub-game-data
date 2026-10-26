import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from report_quest_unlock_coverage import build_report

class QuestUnlockCoverageTests(unittest.TestCase):
 def sample(self):
  return ([{"key":"a","name":"Quest A","requirements":[],"field_status":{"requirements":"known_empty","rewards":"known"},"field_sources":{"requirements":"https://wiki.example/a","rewards":"https://wiki.example/a"},"rewards":["Sword"]},
           {"key":"b","name":"Quest B","requirements":["Quest A"],"field_status":{"requirements":"unknown","rewards":"unknown"},"field_sources":{},"rewards":[]}],
          [{"id":1,"name":"Sword"},{"id":2,"name":"Shield"}],
          [{"item_id":1,"requirements_status":"known","required_quests":["Quest A"],"source_url":"https://wiki.example/item"},
           {"item_id":2,"requirements_status":"unknown","required_quests":[],"source_url":None}],
          [{"quest_key":"a","prerequisites":[],"source_url":"https://wiki.example/a"},
           {"quest_key":"b","prerequisites":[{"quest_key":"a","resolution_status":"resolved"}]}])
 def test_unknowns_stay_visible(self):
  r=build_report(*self.sample())
  self.assertEqual(r["status"],"review_required")
  self.assertEqual(r["review_queue"]["unknown_or_unspecified_quest_requirement_count"],1)
  self.assertEqual(r["review_queue"]["unknown_or_unspecified_item_unlock_count"],1)
 def test_missing_unlock_record_not_treated_as_no_requirement(self):
  q,i,u,rel=self.sample(); u=u[:1]
  r=build_report(q,i,u,rel)
  self.assertEqual(r["item_unlock_evidence"]["items_without_unlock_record_count"],1)
 def test_orphan_item_unlock_is_counted(self):
  q,i,u,rel=self.sample(); u.append({"item_id":999,"requirements_status":"unknown","required_quests":[]})
  r=build_report(q,i,u,rel)
  self.assertEqual(r["item_unlock_evidence"]["unlock_records_without_item_count"],1)
 def test_unresolved_quest_prerequisite_is_visible(self):
  q,i,u,rel=self.sample(); rel[1]["prerequisites"].append({"quest_key":"missing","resolution_status":"not_found"})
  r=build_report(q,i,u,rel)
  self.assertIn("unresolved_prerequisite_edges",r["review_queue"]["issue_categories"])
 def test_duplicate_quest_keys_are_flagged(self):
  q,i,u,rel=self.sample(); q.append(dict(q[0]))
  r=build_report(q,i,u,rel)
  self.assertEqual(r["quest_requirements"]["duplicate_keys"],["a"])
 def test_no_requirements_only_when_explicitly_known_empty(self):
  q,i,u,rel=self.sample(); q[0]["field_status"]["requirements"]="unknown"
  r=build_report(q,i,u,rel)
  self.assertEqual(r["quest_requirements"]["requirement_state_counts"]["unknown"],1)
if __name__=="__main__": unittest.main()
