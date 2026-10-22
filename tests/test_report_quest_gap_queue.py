import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from report_quest_gap_queue import build_queue
class QuestGapQueueTests(unittest.TestCase):
 def test_unknown_facts_are_prioritized_without_fabrication(self):
  q={"key":"a","name":"Quest A","source_url":None,"field_status":{"requirements":"unknown","skill_requirements":"unknown","rewards":"unknown","members":"unknown","difficulty":"unknown","quest_type":"unknown"}}
  r=build_queue([q],{"unresolved_requirement_count":2},{"record_count":1})
  self.assertEqual(r["status"],"review_required")
  self.assertEqual(r["prioritized_gaps"][0]["priority"],"critical")
  self.assertIn("requirements",r["prioritized_gaps"][0]["unknown_fields"])
  self.assertEqual(r["unresolved_prerequisite_reference_count"],2)
 def test_complete_source_backed_record_has_no_gap_row(self):
  fields=("requirements","skill_requirements","rewards","members","difficulty","quest_type")
  q={"key":"a","name":"Quest A","source_url":"https://example.org","field_status":{f:"known" for f in fields},"field_sources":{f:"https://example.org" for f in fields}}
  self.assertEqual(build_queue([q],{"unresolved_requirement_count":0},{"record_count":1})["prioritized_gaps"],[])
if __name__=="__main__":unittest.main()
