"""Regression tests for quest evidence reconciliation."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_quest_evidence_consistency import audit
SOURCE="https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"
def row(name="Cook's Assistant",key="1",text="-",links=None,matched="matched",shape="title_requirements"):
 return {"quest_name":name,"quest_key":key,"requirements_text":text,"requirement_links":links or [],"source_url":SOURCE,"evidence_status":"raw_source_extracted_needs_structured_review","catalogue_match_status":matched,"source_row_shape":shape}
class QuestEvidenceAuditTests(unittest.TestCase):
 def test_dash_is_review_only_not_verified_empty(self):
  r=audit([row()],[{"id":1,"name":"Cook's Assistant"}]);self.assertEqual(r["status"],"review_required")
  self.assertEqual(r["records_with_placeholder_or_empty_requirement_text"],1)
  self.assertIn("a dash is not proof of no requirements",r["interpretation_limits"])
 def test_rejects_untrusted_source_host(self):
  x=row();x["source_url"]="https://example.com/quest";r=audit([x],[{"id":1,"name":"Cook's Assistant"}])
  self.assertEqual(r["status"],"failed");self.assertIn("untrusted_source_url",{e["reason"] for e in r["errors"]})
 def test_rejects_catalogue_key_mismatch(self):
  r=audit([row(key="wrong")],[{"id":1,"name":"Cook's Assistant"}])
  self.assertIn("catalogue_key_mismatch",{e["reason"] for e in r["errors"]})
 def test_reports_missing_catalogue_evidence(self):
  r=audit([row()],[{"id":1,"name":"Cook's Assistant"},{"id":2,"name":"Biohazard"}])
  self.assertIn("biohazard",r["catalogue_titles_without_matched_evidence"])
 def test_rejects_untrusted_requirement_link(self):
  x=row(links=[{"title":"x","url":"https://evil.example/x"}]);r=audit([x],[{"id":1,"name":"Cook's Assistant"}])
  self.assertIn("untrusted_requirement_link",{e["reason"] for e in r["errors"]})
 def test_duplicate_normalized_titles_fail(self):
  r=audit([row(),row(name="Cook’s   Assistant")],[{"id":1,"name":"Cook's Assistant"}])
  self.assertIn("duplicate_normalized_evidence_titles",{e["reason"] for e in r["errors"]})
 def test_malformed_inputs_raise(self):
  with self.assertRaises(ValueError):audit({},[])
  with self.assertRaises(ValueError):audit([],{})
if __name__=="__main__":unittest.main()
