import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_combat_studio_v1_bundle_manifest import build_manifest,FILES
class BundleManifestTests(unittest.TestCase):
 def populate(self,d):
  for f,s in FILES.items():(d/f).write_text(json.dumps([{s["identity"]:1,"name":"sample"}]),encoding="utf-8")
 def test_clean_bundle(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);r=build_manifest(d);self.assertEqual(r["status"],"bundle_integrity_passed");self.assertEqual(r["ready_file_count"],len(FILES))
 def test_missing_file_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"weapons.json").unlink();self.assertEqual(build_manifest(d)["status"],"blocked")
 def test_duplicate_id_requires_review(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"items.json").write_text('[{"id":1},{"id":1}]',encoding="utf-8");r=build_manifest(d);self.assertEqual(r["status"],"review_required");self.assertEqual(r["datasets"]["items.json"]["duplicate_identity_count"],1)
 def test_empty_file_is_review_not_clean(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"quests.json").write_text("[]",encoding="utf-8");self.assertEqual(build_manifest(d)["datasets"]["quests.json"]["state"],"review_required")
 def test_invalid_json(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"items.json").write_text("{",encoding="utf-8");self.assertEqual(build_manifest(d)["datasets"]["items.json"]["state"],"invalid_json")
 def test_hash_changes_when_contents_change(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);a=build_manifest(d)["datasets"]["items.json"]["sha256"];(d/"items.json").write_text('[{"id":2}]',encoding="utf-8");b=build_manifest(d)["datasets"]["items.json"]["sha256"];self.assertNotEqual(a,b)
if __name__=="__main__":unittest.main()
