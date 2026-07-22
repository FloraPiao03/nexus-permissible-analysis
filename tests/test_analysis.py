import json
import tempfile
import unittest
from pathlib import Path

import analyze

CONFIG = json.loads(Path("config.json").read_text())


def study(nct, countries=None, study_type="INTERVENTIONAL", include_locations_module=True,
          sponsor_class=None, intervention_types=None):
    locations = [{"facility": f"Site {i}", "country": c} for i, c in enumerate(countries or [], 1)]
    protocol = {
        "identificationModule": {"nctId": nct, "briefTitle": nct},
        "designModule": {"studyType": study_type},
        "statusModule": {"overallStatus": "COMPLETED"},
    }
    if include_locations_module:
        protocol["contactsLocationsModule"] = {"locations": locations}
    if sponsor_class is not None:
        protocol["sponsorCollaboratorsModule"] = {"leadSponsor": {"class": sponsor_class}}
    if intervention_types is not None:
        protocol["armsInterventionsModule"] = {
            "interventions": [{"type": value} for value in intervention_types]
        }
    return {"protocolSection": {
        **protocol,
    }}


class ClassificationTests(unittest.TestCase):
    # Expected labels below are manual business-rule expectations; they are not generated.
    cases = [
        ([], "UNKNOWN"),
        (["China"], "PERMISSIBLE"),
        (["Germany", "France"], "PERMISSIBLE"),
        (["Puerto Rico", "China"], "PERMISSIBLE"),
        (["United States"], "US_ONLY"),
        (["United States", "Canada"], "US_NON_CHINA_MULTI"),
        (["United States", "Germany", "Japan"], "US_NON_CHINA_MULTI"),
        (["United States", "China"], "NEXUS"),
        (["United States", "China", "Canada"], "NEXUS"),
        (["United States", "Hong Kong"], "US_NON_CHINA_MULTI"),
        (["Taiwan", "Japan"], "PERMISSIBLE"),
        (["Macau"], "PERMISSIBLE"),
        (["Macao"], "PERMISSIBLE"),
        (["Guam", "American Samoa", "Northern Mariana Islands", "Virgin Islands (U.S.)"], "PERMISSIBLE"),
    ]

    def test_hand_computed_cases(self):
        for i, (countries, expected) in enumerate(self.cases):
            with self.subTest(countries=countries):
                row, _ = analyze.extract(study(f"NCT{i:08d}", countries), CONFIG)
                self.assertEqual(expected, row["bucket"])
                expected_group = "UNKNOWN" if expected == "UNKNOWN" else "NO_US" if expected == "PERMISSIBLE" else "HAS_US"
                self.assertEqual(expected_group, row["us_presence_group"])

    def test_us_plus_canada_is_not_us_only(self):
        row, _ = analyze.extract(study("NCT00000001", ["United States", "Canada"]), CONFIG)
        self.assertEqual("US_NON_CHINA_MULTI", row["bucket"])
        self.assertNotEqual("US_ONLY", row["bucket"])

    def test_us_china_canada_remains_nexus(self):
        row, _ = analyze.extract(study("NCT00000001", ["United States", "China", "Canada"]), CONFIG)
        self.assertEqual("NEXUS", row["bucket"])

    def test_safe_whitespace_trimming(self):
        row, _ = analyze.extract(study("NCT00000001", [" United States ", " China "]), CONFIG)
        self.assertEqual("NEXUS", row["bucket"])
        self.assertEqual("China|United States", row["countries_pipe"])

    def test_exact_country_matching(self):
        for value in ("US", "USA", "United States of America", "the US", "PRC", "Mainland China", "People's Republic of China"):
            row, _ = analyze.extract(study("NCT00000001", [value]), CONFIG)
            self.assertEqual("PERMISSIBLE", row["bucket"], value)
            self.assertFalse(row["has_us"], value)
            self.assertFalse(row["has_china"], value)

    def test_study_types_are_retained(self):
        for kind in ("OBSERVATIONAL", "INTERVENTIONAL"):
            row, _ = analyze.extract(study("NCT00000001", ["Germany"], kind), CONFIG)
            self.assertEqual(kind, row["study_type"])
            self.assertEqual("PERMISSIBLE", row["bucket"])

    def test_interventional_study_type_filter_is_exact(self):
        self.assertTrue(analyze.study_type_is_eligible(study("NCT1", study_type="INTERVENTIONAL"), "interventional"))
        self.assertFalse(analyze.study_type_is_eligible(study("NCT2", study_type="OBSERVATIONAL"), "interventional"))
        self.assertFalse(analyze.study_type_is_eligible(study("NCT3", study_type="EXPANDED_ACCESS"), "interventional"))
        self.assertTrue(analyze.study_type_is_eligible(study("NCT4", study_type="OBSERVATIONAL"), "all"))

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
        for countries in ([""], ["  "], []):
            row, locations = analyze.extract(study("NCT00000001", countries), CONFIG)
            self.assertEqual("UNKNOWN", row["bucket"])
        row, locations = analyze.extract(study("NCT00000001", [""]), CONFIG)
        self.assertEqual(1, len(locations))

    def test_missing_location_structure_is_unknown(self):
        row, locations = analyze.extract(study("NCT00000001", include_locations_module=False), CONFIG)
        self.assertEqual("UNKNOWN", row["bucket"])
        self.assertEqual("UNKNOWN", row["us_presence_group"])
        self.assertEqual([], locations)

    def test_percentages(self):
        # Manually specified arithmetic expectations, independent of classification code.
        self.assertEqual(0.2, analyze.pct(1, 5))
        self.assertEqual(0.4, analyze.pct(2, 5))
        self.assertEqual(0.25, analyze.pct(1, 4))
        self.assertEqual(0.5, analyze.pct(2, 4))

    def test_bucket_partition_manual_fixture(self):
        rows = [analyze.extract(study(f"NCT{i:08d}", countries), CONFIG)[0]
                for i, (countries, _) in enumerate(self.cases)]
        expected = {"NEXUS": 2, "PERMISSIBLE": 7, "US_ONLY": 1, "US_NON_CHINA_MULTI": 3, "UNKNOWN": 1}
        actual = {bucket: sum(row["bucket"] == bucket for row in rows) for bucket in analyze.BUCKETS}
        self.assertEqual(expected, actual)
        self.assertEqual(14, sum(actual.values()))

    def test_industry_drug_candidate_filter_uses_structured_fields(self):
        cases = [
            ("INDUSTRY", ["DRUG"], True),
            ("INDUSTRY", ["DRUG", "DEVICE"], True),
            ("INDUSTRY", ["DRUG", "OTHER"], True),
            ("INDUSTRY", ["DEVICE"], False),
            ("NIH", ["DRUG"], False),
            ("INDUSTRY", [], False),
        ]
        for index, (sponsor_class, intervention_types, expected) in enumerate(cases, 1):
            with self.subTest(sponsor_class=sponsor_class, intervention_types=intervention_types):
                item = study(f"NCTDRUG{index:04d}", ["United States", "China"],
                             sponsor_class=sponsor_class, intervention_types=intervention_types)
                self.assertEqual(analyze.product_is_eligible(item, "drug"), expected)
                row, _ = analyze.extract(item, CONFIG, analyze.date(2026, 7, 16))
                self.assertEqual(row["bucket"], "NEXUS")
                self.assertEqual(row["time_cohort"], "TIME_UNKNOWN")

    def test_intervention_combination_audit_is_set_based_and_deterministic(self):
        counts = analyze.Counter()
        combinations = analyze.Counter()
        items = [
            study("NCT1", sponsor_class="INDUSTRY", intervention_types=["DRUG"]),
            study("NCT2", sponsor_class="INDUSTRY", intervention_types=["DEVICE", "DRUG", "DRUG"]),
            study("NCT3", sponsor_class="INDUSTRY", intervention_types=["OTHER", "DRUG"]),
            study("NCT4", sponsor_class="INDUSTRY", intervention_types=["DEVICE"]),
            study("NCT5", sponsor_class="OTHER", intervention_types=["DRUG"]),
            study("NCT6", sponsor_class="INDUSTRY", intervention_types=[]),
        ]
        for item in items:
            analyze.update_intervention_type_audit(counts, combinations, item)
        audit = analyze.build_intervention_type_audit(counts, combinations)
        self.assertEqual(audit["total_industry_studies"], 5)
        self.assertEqual(audit["industry_drug_containing_studies"], 3)
        self.assertEqual(audit["industry_not_drug_containing_studies"], 2)
        self.assertEqual(audit["device_involved_drug_studies"], 1)
        observed = {row["combination"]: row["unique_study_count"] for row in audit["combination_counts"]}
        self.assertEqual(observed, {"DRUG": 1, "DRUG + DEVICE": 1, "DRUG + OTHER": 1})
        self.assertEqual(analyze.sponsor_and_intervention_types(items[1])[1], ("DRUG", "DEVICE"))


if __name__ == "__main__":
    unittest.main()
