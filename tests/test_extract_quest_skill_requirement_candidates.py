"""Regression tests for conservative skill-level candidate extraction."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from extract_quest_skill_requirement_candidates import extract_candidates
class SkillCandidateTests(unittest.TestCase):
 def test_extracts_explicit_level_and_skill(self):
  rows=extract_candidates([{"quest_key":"1","quest_name":"Example","requirements_text":"Level 35 Crafting and 20 Agility required","source_url":"https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest","catalogue_match_status":"matched"}])
  self.assertEqual([(x["skill"],x["level"]) for x in rows],[("Agility",20),("Crafting",35)])
  self.assertTrue(all(x["candidate_status"]=="raw_text_candidate_needs_manual_review" for x in rows))
 def test_ignores_out_of_range_and_unstructured_text(self):
  rows=extract_candidates([{"quest_key":"x","quest_name":"Example","requirements_text":"100 Magic, Magic level unknown, 5 bananas"}])
  self.assertEqual(rows,[])
 def test_does_not_claim_start_vs_completion_or_boostability(self):
  rows=extract_candidates([{"quest_key":"x","quest_name":"Example","requirements_text":"50 Mining"}])
  self.assertIn("does_not_distinguish_starting_from_completion_requirement",rows[0]["interpretation_limits"])
  self.assertIn("does_not_infer_boostability",rows[0]["interpretation_limits"])
 def test_unmatched_catalogue_record_remains_unmatched(self):
  rows=extract_candidates([{"quest_key":"unmatched-example","quest_name":"Example","requirements_text":"25 Thieving","catalogue_match_status":"unmatched_catalogue_title"}])
  self.assertEqual(rows[0]["catalogue_match_status"],"unmatched_catalogue_title")
if __name__=="__main__":unittest.main()
