import json
import unittest
from datetime import date
from pathlib import Path

from analyze import assign_time_cohort, build_time_analysis, classify, extract


REFERENCE = date(2026, 7, 16)


class TimeCohortTests(unittest.TestCase):
    def assert_cohort(self, raw, expected):
        self.assertEqual(assign_time_cohort(raw, REFERENCE)["time_cohort"], expected)

    def test_day_inside_recent_three_years(self):
        result = assign_time_cohort("2025-01-10", REFERENCE)
        self.assertEqual(result["start_date_precision"], "DAY")
        self.assertEqual(result["time_cohort"], "RECENT_3Y")

    def test_day_inside_four_to_six_years(self):
        self.assert_cohort("2022-03-20", "YEARS_4_TO_6_AGO")

    def test_older_than_six_years(self):
        self.assert_cohort("2019-12-31", "OLDER_THAN_6Y")

    def test_future_study(self):
        self.assert_cohort("2026-07-17", "FUTURE")

    def test_exact_three_year_boundary_belongs_to_older_cohort(self):
        self.assert_cohort("2023-07-16", "YEARS_4_TO_6_AGO")

    def test_exact_six_year_boundary_is_older_than_six_years(self):
        self.assert_cohort("2020-07-16", "OLDER_THAN_6Y")

    def test_month_precision_unambiguously_recent(self):
        result = assign_time_cohort("2024-02", REFERENCE)
        self.assertEqual(result["start_date_precision"], "MONTH")
        self.assertEqual(result["time_cohort"], "RECENT_3Y")

    def test_year_precision_unambiguously_four_to_six_years(self):
        result = assign_time_cohort("2022", REFERENCE)
        self.assertEqual(result["start_date_precision"], "YEAR")
        self.assertEqual(result["time_cohort"], "YEARS_4_TO_6_AGO")

    def test_missing_start_date(self):
        self.assert_cohort("", "TIME_UNKNOWN")

    def test_malformed_start_date(self):
        result = assign_time_cohort("2024-13-99", REFERENCE)
        self.assertEqual(result["start_date_precision"], "UNPARSEABLE")
        self.assertEqual(result["time_cohort"], "TIME_UNKNOWN")

    def test_partial_month_crossing_three_year_boundary_is_ambiguous(self):
        self.assert_cohort("2023-07", "TIME_AMBIGUOUS")

    def test_cohort_geographic_buckets_reconcile(self):
        rows = []
        for bucket in ("NEXUS", "PERMISSIBLE", "US_ONLY", "US_NON_CHINA_MULTI", "UNKNOWN"):
            rows.append({"bucket": bucket, "time_cohort": "RECENT_3Y"})
            rows.append({"bucket": bucket, "time_cohort": "YEARS_4_TO_6_AGO"})
        result = build_time_analysis(rows, REFERENCE)
        for cohort in ("RECENT_3Y", "YEARS_4_TO_6_AGO"):
            self.assertEqual(result["cohorts"][cohort]["denominator"], 5)
            self.assertEqual(result["cohorts"][cohort]["reconciliation_difference"], 0)
        self.assertEqual(
            result["cohort_geographic_reconciliation_differences"],
            {cohort: 0 for cohort in (
                "RECENT_3Y", "YEARS_4_TO_6_AGO", "OLDER_THAN_6Y",
                "FUTURE", "TIME_UNKNOWN", "TIME_AMBIGUOUS",
            )},
        )

    def test_geographic_classification_is_unchanged_by_start_date(self):
        cfg = json.loads(Path("config.json").read_text())
        expected_bucket, _ = classify(["United States", "China", "Canada"], cfg)
        study = {"protocolSection": {
            "identificationModule": {"nctId": "NCTTIME0001", "briefTitle": "fixture"},
            "designModule": {"studyType": "INTERVENTIONAL"},
            "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2025-01", "type": "ACTUAL"}},
            "contactsLocationsModule": {"locations": [{"country": "United States"}, {"country": "China"}, {"country": "Canada"}]},
        }}
        row, _ = extract(study, cfg, REFERENCE)
        self.assertEqual(expected_bucket, "NEXUS")
        self.assertEqual(row["bucket"], expected_bucket)
        self.assertEqual(row["time_cohort"], "RECENT_3Y")
        self.assertEqual(row["start_date_type"], "ACTUAL")

    def test_all_geographic_buckets_are_invariant_with_time_fields(self):
        cfg = json.loads(Path("config.json").read_text())
        cases = [
            ([], "UNKNOWN"),
            (["Germany"], "PERMISSIBLE"),
            (["United States"], "US_ONLY"),
            (["United States", "Canada"], "US_NON_CHINA_MULTI"),
            (["United States", "China"], "NEXUS"),
        ]
        for index, (countries, expected) in enumerate(cases, 1):
            study = {"protocolSection": {
                "identificationModule": {"nctId": f"NCTTIME{index:04d}"},
                "designModule": {"studyType": "INTERVENTIONAL"},
                "statusModule": {"startDateStruct": {"date": "2025-01-01", "type": "ACTUAL"}},
                "contactsLocationsModule": {"locations": [{"country": country} for country in countries]},
            }}
            row, _ = extract(study, cfg, REFERENCE)
            self.assertEqual(row["bucket"], expected)
            self.assertEqual(classify(countries, cfg)[0], expected)


if __name__ == "__main__":
    unittest.main()
