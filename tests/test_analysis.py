import json
import tempfile
import unittest
from pathlib import Path

import analyze

CONFIG = json.loads(Path("config.json").read_text())


def study(nct, countries, study_type="INTERVENTIONAL"):
    locations = [{"facility": f"Site {i}", "country": c} for i, c in enumerate(countries, 1)]
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": nct},
        "designModule": {"studyType": study_type},
        "statusModule": {"overallStatus": "COMPLETED"},
        "contactsLocationsModule": {"locations": locations},
    }}


class ClassificationTests(unittest.TestCase):
    # Expected labels below are manual business-rule expectations; they are not generated.
    cases = [
        (["United States", "China"], "NEXUS"),
        (["United States"], "US_ONLY"),
        (["China"], "PERMISSIBLE"),
        (["Germany", "France"], "PERMISSIBLE"),
        ([], "UNKNOWN"),
        (["Puerto Rico", "China"], "PERMISSIBLE"),
        (["United States", "Hong Kong"], "US_ONLY"),
        (["Taiwan", "Japan"], "PERMISSIBLE"),
    ]

    def test_hand_computed_cases(self):
        for i, (countries, expected) in enumerate(self.cases):
            with self.subTest(countries=countries):
                row, _ = analyze.extract(study(f"NCT{i:08d}", countries), CONFIG)
                self.assertEqual(expected, row["bucket"])

    def test_study_types_are_retained(self):
        for kind in ("OBSERVATIONAL", "INTERVENTIONAL"):
            row, _ = analyze.extract(study("NCT00000001", ["Germany"], kind), CONFIG)
            self.assertEqual(kind, row["study_type"])
            self.assertEqual("PERMISSIBLE", row["bucket"])

    def test_duplicate_is_counted_once_by_dedup_contract(self):
        records = [study("NCT00000001", ["China"]), study("NCT00000001", ["United States"])]
        unique = {}
        duplicates = 0
        for value in records:
            nct = value["protocolSection"]["identificationModule"]["nctId"]
            if nct in unique: duplicates += 1
            else: unique[nct] = value
        self.assertEqual(1, len(unique))
        self.assertEqual(1, duplicates)

    def test_blank_country_is_unknown(self):
        row, locations = analyze.extract(study("NCT00000001", [""]), CONFIG)
        self.assertEqual("UNKNOWN", row["bucket"])
        self.assertEqual(1, len(locations))

    def test_percentages(self):
        # Manual fixture: NEXUS=1, PERMISSIBLE=2, US_ONLY=1, UNKNOWN=1, total=5, known=4.
        self.assertEqual(0.2, analyze.pct(1, 5))
        self.assertEqual(0.4, analyze.pct(2, 5))
        self.assertEqual(0.25, analyze.pct(1, 4))
        self.assertEqual(0.5, analyze.pct(2, 4))

    def test_bucket_partition_manual_fixture(self):
        rows = [analyze.extract(study(f"NCT{i:08d}", countries), CONFIG)[0]
                for i, (countries, _) in enumerate(self.cases)]
        expected = {"NEXUS": 1, "PERMISSIBLE": 4, "US_ONLY": 2, "UNKNOWN": 1}
        actual = {bucket: sum(row["bucket"] == bucket for row in rows) for bucket in analyze.BUCKETS}
        self.assertEqual(expected, actual)
        self.assertEqual(8, sum(actual.values()))


if __name__ == "__main__":
    unittest.main()
