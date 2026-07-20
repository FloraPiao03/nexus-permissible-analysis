import unittest

from analyze_interventional import aggregate, comparison_rows


def row(bucket, group):
    return {"bucket": bucket, "us_presence_group": group}


class InterventionalAggregationTests(unittest.TestCase):
    def test_five_bucket_aggregation_and_reconciliation(self):
        rows = [
            row("UNKNOWN", "UNKNOWN"),
            row("PERMISSIBLE", "NO_US"),
            row("US_ONLY", "HAS_US"),
            row("US_NON_CHINA_MULTI", "HAS_US"),
            row("NEXUS", "HAS_US"),
        ]
        result = aggregate(rows)
        self.assertEqual(result["total_studies"], 5)
        self.assertEqual(result["known_location_studies"], 4)
        self.assertEqual(result["us_presence_groups"]["HAS_US"]["count"], 3)
        self.assertTrue(all(value == 0 for value in result["reconciliation_differences"]["row_group_counts_match_bucket_groups"].values()))

    def test_percentages_use_interventional_denominators(self):
        rows = [row("PERMISSIBLE", "NO_US"), row("US_ONLY", "HAS_US"), row("NEXUS", "HAS_US")]
        result = aggregate(rows)
        self.assertEqual(result["buckets"]["NEXUS"]["percentage_total_interventional"], 1 / 3)
        self.assertEqual(result["buckets"]["NEXUS"]["percentage_known_location_interventional"], 1 / 3)
        self.assertEqual(result["buckets"]["NEXUS"]["percentage_interventional_has_us"], 1 / 2)

    def test_comparison_percentage_difference_uses_same_scope_denominator_type(self):
        interventional = aggregate([row("PERMISSIBLE", "NO_US"), row("NEXUS", "HAS_US")])
        all_summary = {
            "total_studies": 4,
            "known_location_studies": 4,
            "buckets": {name: {"count": 0, "percentage_total": 0.0} for name in ("UNKNOWN", "PERMISSIBLE", "US_ONLY", "US_NON_CHINA_MULTI", "NEXUS")},
            "us_presence_groups": {"HAS_US": {"count": 0, "percentage_total": 0.0}},
        }
        all_summary["buckets"]["NEXUS"] = {"count": 1, "percentage_total": 0.25}
        comparison = {item["metric"]: item for item in comparison_rows(all_summary, interventional)}
        self.assertEqual(comparison["NEXUS"]["percentage_point_difference"], 0.25)
        self.assertEqual(comparison["NEXUS"]["percentage_denominator"], "Each scope's total denominator")


if __name__ == "__main__":
    unittest.main()
