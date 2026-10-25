"""Regression tests for indexed quest requirement tables."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from download_quest_requirement_evidence import extract_rows
class IndexedQuestEvidenceTests(unittest.TestCase):
 def test_recovers_ordinal_title_requirements_layout(self):
  html="""<table class="wikitable"><tr><th>No.</th><th>Quest</th><th>Requirements</th></tr><tr><td>12</td><td>Cook&#39;s Assistant</td><td>Cooking 10</td></tr><tr><td>13</td><td>Biohazard</td><td><a href="/w/Plague_City" title="Plague City">Plague City</a></td></tr></table>"""
  rows,diag=extract_rows(html,[{"id":1,"name":"Cook's Assistant"},{"id":2,"name":"Biohazard"}])
  self.assertEqual(len(rows),2);cook=next(x for x in rows if x["quest_name"]=="Cook's Assistant")
  self.assertEqual(cook["requirements_text"],"Cooking 10");self.assertEqual(cook["source_row_shape"],"ordinal_title_requirements")
  self.assertEqual(cook["quest_key"],"1");self.assertEqual(diag["source_rows_discarded_as_numeric_indices"],0)
 def test_numeric_index_is_not_quest_title(self):
  rows,_=extract_rows('<table class="wikitable"><tr><td>10</td><td>Prince Ali Rescue</td><td>Biohazard</td></tr></table>',[{"id":4,"name":"Prince Ali Rescue"}])
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]["quest_name"],"Prince Ali Rescue")
 def test_deduplicates_and_prefers_richer_requirement_evidence(self):
  html="""<table class="wikitable"><tr><td>1</td><td>Cook&#39;s Assistant</td><td>-</td></tr><tr><td>Cook&#39;s Assistant</td><td>Cooking 10</td></tr></table>"""
  rows,diag=extract_rows(html,[{"id":1,"name":"Cook's Assistant"}])
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]["requirements_text"],"Cooking 10");self.assertEqual(diag["duplicate_source_row_count"],1)
 def test_unicode_apostrophe_normalizes(self):
  rows,_=extract_rows('<table class="wikitable"><tr><td>Cook’s   Assistant</td><td>-</td></tr></table>',[{"id":1,"name":"Cook's Assistant"}])
  self.assertEqual(rows[0]["catalogue_match_status"],"matched")
if __name__=="__main__":unittest.main()
