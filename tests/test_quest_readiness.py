"""Tests for honest quest readiness statuses."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from report_quest_readiness import build_report
class QuestReadinessTests(unittest.TestCase):
    def test_empty_catalogue_is_incomplete_not_ready(self):
        result=build_report([],[],{"status":"missing_source"},{"status":"passed","unresolved_requirement_count":0})
        self.assertEqual(result["status"],"incomplete"); self.assertTrue(result["warnings"])
    def test_missing_skill_and_reward_data_warns(self):
        q={"key":"a","name":"Quest A","source_url":"https://example.org","requirements":[],"skill_requirements":[],"rewards":[]}
        result=build_report([q],[],{"status":"passed"},{"status":"passed","unresolved_requirement_count":0})
        self.assertEqual(result["status"],"incomplete"); self.assertTrue(any("skill requirements" in x for x in result["warnings"])); self.assertTrue(any("rewards" in x for x in result["warnings"]))
    def test_relationship_failure_is_fatal(self):
        result=build_report([],[],{},{"status":"failed","unresolved_requirement_count":0})
        self.assertEqual(result["status"],"failed")
if __name__=="__main__": unittest.main()
