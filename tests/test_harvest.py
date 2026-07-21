import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import harvest


def study(nct_id):
    return {"protocolSection": {"identificationModule": {"nctId": nct_id}}}


class HarvestResumeTests(unittest.TestCase):
    def test_resume_preserves_existing_page_and_completes_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "run_failed"
            raw = run / "raw"
            raw.mkdir(parents=True)
            first = raw / "page_000001.json"
            first.write_text(json.dumps({"studies": [study("NCT00000001")], "nextPageToken": "resume-token"}), encoding="utf-8")
            original_bytes = first.read_bytes()
            (run / "HARVEST_FAILED.txt").write_text("network failure\n", encoding="utf-8")
            final_payload = {"studies": [study("NCT00000002")]}

            with patch("harvest.request_json", return_value=final_payload) as request:
                self.assertEqual(harvest.main(["--resume-run", str(run)]), 0)

            self.assertEqual(first.read_bytes(), original_bytes)
            self.assertEqual(request.call_count, 1)
            self.assertIn("pageToken=resume-token", request.call_args.args[0])
            manifest = json.loads((run / "manifest.json").read_text())
            self.assertTrue(manifest["snapshot_complete"])
            self.assertFalse(manifest["next_page_token_remaining"])
            self.assertIsNone(manifest["limit_pages"])
            self.assertEqual(manifest["resumed_from_page"], 1)
            self.assertEqual(manifest["page_count"], 2)
            self.assertEqual(manifest["raw_study_count"], 2)
            self.assertEqual(manifest["unique_nct_count"], 2)
            self.assertEqual(manifest["duplicate_nct_count"], 0)
            self.assertFalse((run / "HARVEST_FAILED.txt").exists())
            self.assertEqual(len(list(run.glob("HARVEST_FAILED_BEFORE_RESUME_*.txt"))), 1)


if __name__ == "__main__":
    unittest.main()
