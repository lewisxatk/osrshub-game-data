"""Tests for quest requirement evidence extraction."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from download_quest_requirement_evidence import extract_rows
class EvidenceTests(unittest.TestCase):
 def test_matches_known_quests_and_preserves_raw_links(self):
  html="""<table class="wikitable"><tr><th>Quest</th><th>Requirements</th></tr><tr><td>Cook's Assistant</td><td>-</td></tr><tr><td>Biohazard</td><td><a href="/w/Plague_City" title="Plague City">Plague City</a></td></tr></table>"""
  rows=extract_rows(html,[{"id":1,"name":"Cook's Assistant"},{"id":2,"name":"Biohazard"}])
  self.assertEqual(len(rows),2)
  bio=next(x for x in rows if x["quest_name"]=="Biohazard")
  self.assertEqual(bio["requirements_text"],"Plague City")
  self.assertEqual(bio["requirement_links"][0]["title"],"Plague City")
 def test_ignores_unmatched_rows(self):
  self.assertEqual(extract_rows('<table class="wikitable"><tr><td>Other</td><td>Thing</td></tr></table>',[{"name":"Cook's Assistant"}]),[])
 def test_dash_is_raw_evidence_not_assertion_of_no_requirements(self):
  row=extract_rows('<table class="wikitable"><tr><td>Cook&#39;s Assistant</td><td>-</td></tr></table>',[{"name":"Cook's Assistant"}])[0]
  self.assertEqual(row["requirements_text"],"-")
if __name__=="__main__":unittest.main()
