"""Tests for source snapshot integrity auditing."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_source_integrity as audit


class SourceIntegrityTests(unittest.TestCase):
    def test_valid_snapshot_passes_hash_size_and_json_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b'[{"id":1}]'
            (root / "items.json").write_bytes(payload)
            manifest = {"sources": {"items": {
                "file": "items.json", "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(), "top_level_type": "list"
            }}}
            result = audit.audit_manifest(manifest, root)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["checked_source_count"], 1)

    def test_tampered_snapshot_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "items.json").write_text('[{"id":2}]', encoding="utf-8")
            manifest = {"sources": {"items": {
                "file": "items.json", "bytes": 10, "sha256": "bad", "top_level_type": "list"
            }}}
            result = audit.audit_manifest(manifest, root)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("SHA-256 mismatch" in error for error in result["errors"]))

    def test_missing_snapshot_fails(self):
        result = audit.audit_manifest({"sources": {"items": {
            "file": "items.json", "bytes": 0, "sha256": "bad"
        }}}, Path("/definitely/not/a/real/source/directory"))
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing snapshot" in error for error in result["errors"]))

    def test_unsafe_filename_is_rejected(self):
        result = audit.audit_manifest({"sources": {"items": {
            "file": "../items.json", "bytes": 0, "sha256": "bad"
        }}}, Path("/tmp"))
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("unsafe filename" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
