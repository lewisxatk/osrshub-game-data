"""Unit tests for source-backed combat reference fixture checks."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from check_combat_reference import validate_fixture,run_cases
class CombatReferenceTests(unittest.TestCase):
    def test_fixture_requires_source_url_and_real_date(self):
        fixture={"version":1,"cases":[{"dataset":"weapons.json","id":1,"expected":{"name":"x"},"source":{"url":"https://example.org","checked_on":"2026-02-30"}}]}
        self.assertTrue(any("real calendar date" in error for error in validate_fixture(fixture)))
    def test_duplicate_dataset_ids_rejected(self):
        case={"dataset":"weapons.json","id":1,"expected":{"name":"x"},"source":{"url":"https://example.org","checked_on":"2026-10-21"}}
        self.assertTrue(any("duplicates" in error for error in validate_fixture({"version":1,"cases":[case,case]})))
    def test_unexpected_dataset_rejected(self):
        case={"dataset":"unknown.json","id":1,"expected":{"name":"x"},"source":{"url":"https://example.org","checked_on":"2026-10-21"}}
        self.assertTrue(any("unsupported dataset" in error for error in validate_fixture({"version":1,"cases":[case]})))
    def test_missing_fixture_record_fails_cleanly(self):
        case={"dataset":"weapons.json","id":999999999,"expected":{"name":"missing"},"source":{"url":"https://example.org","checked_on":"2026-10-21"}}
        result=run_cases({"version":1,"cases":[case]},Path("/definitely/missing"))
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["failed_count"],1)
if __name__=="__main__":unittest.main()
