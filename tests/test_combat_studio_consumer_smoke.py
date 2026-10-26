import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smoke_test_combat_studio_bundle import smoke
from build_combat_studio_v1_bundle_manifest import FILES
class ConsumerSmokeTests(unittest.TestCase):
 def populate(self,d):
  for f,s in FILES.items():(d/f).write_text(json.dumps([{s["identity"]:1,"name":"fixture"}]),encoding="utf-8")
 def test_all_contract_artifacts_pass_structural_smoke(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);r=smoke(d);self.assertEqual(r["status"],"passed_structural_smoke");self.assertEqual(r["checks_failed"],0)
 def test_missing_artifact_fails(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"weapons.json").unlink();self.assertEqual(smoke(d)["status"],"review_required")
 def test_empty_artifact_fails(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"quests.json").write_text("[]",encoding="utf-8");r=smoke(d);self.assertGreater(r["checks_failed"],0)
 def test_identity_field_missing_fails(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self.populate(d);(d/"items.json").write_text('[{"name":"no id"}]',encoding="utf-8");r=smoke(d);self.assertGreater(r["checks_failed"],0)
if __name__=="__main__":unittest.main()
