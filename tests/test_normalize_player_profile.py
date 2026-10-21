import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from normalize_player_profile import normalize_profile
class ProfileTests(unittest.TestCase):
 def test_partial_and_normalization(self):
  r=normalize_profile({"skills":{" attack ":80,"Ranged":93}})
  self.assertEqual(r["skills"],{"Attack":80,"Ranged":93}); self.assertEqual(r["import_status"],"partial")
 def test_bool_and_range_rejected(self):
  r=normalize_profile({"skills":{"Attack":True,"Strength":100}})
  self.assertEqual(r["import_status"],"invalid")
 def test_duplicate_skill_error(self):
  self.assertTrue(normalize_profile({"skills":{"Attack":80," attack ":81}})["errors"])
 def test_quest_deduplication(self):
  r=normalize_profile({"completed_quests":["Dragon Slayer"," dragon slayer "]})
  self.assertEqual(r["completed_quests"],["Dragon Slayer"])
 def test_invalid_excluded_id(self):
  self.assertEqual(normalize_profile({"excluded_item_ids":[True]})["import_status"],"invalid")
if __name__=="__main__": unittest.main()
