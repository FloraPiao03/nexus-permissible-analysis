import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from china_involvement_charts import (
    aggregate_china_involvement, combined_phase_pies_svg, footprint_chart_svg,
    phase_pie_chart_svg,
)


def observation(nct_id, year, countries, phases):
    return {
        "nct_id": nct_id,
        "start_year": year,
        "countries": set(countries),
        "phases": set(phases),
    }


class ChinaInvolvementChartTests(unittest.TestCase):
    def test_footprint_is_mutually_exclusive_and_phase_overlap_is_preserved(self):
        observations = [
            observation("NCT1", 2020, ["China"], ["PHASE1"]),
            observation("NCT2", 2020, ["China", "Japan"], ["PHASE1", "PHASE2"]),
            observation("NCT3", 2020, ["China", "United States"], ["PHASE2"]),
            observation("NCT4", 2020, ["Germany"], ["PHASE1"]),
            observation("NCT5", 2019, ["China"], ["PHASE1"]),
        ]
        footprint, phases = aggregate_china_involvement(observations)
        row_2020 = footprint[0]
        self.assertEqual(row_2020["China only"], 1)
        self.assertEqual(row_2020["China and Other Countries (No US)"], 1)
        self.assertEqual(row_2020["China and US"], 1)
        self.assertEqual(row_2020["All China-Involved Studies"], 3)
        by_phase = {row["Phase"]: row for row in phases}
        self.assertEqual(by_phase["PHASE1"]["China-Involved Studies"], 2)
        self.assertEqual(by_phase["PHASE1"]["Non China-Involved Studies"], 1)
        self.assertEqual(by_phase["PHASE2"]["China-Involved Studies"], 2)

    def test_footprint_chart_has_three_series_markers_frame_and_boxed_legend(self):
        rows = [
            {
                "Year": year,
                "China only": year - 2010,
                "China and Other Countries (No US)": year - 2015,
                "China and US": year - 2000,
                "All China-Involved Studies": 3 * year - 6025,
            }
            for year in range(2020, 2026)
        ]
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "footprint.svg"
            footprint_chart_svg(rows, path)
            svg = path.read_text(encoding="utf-8")
        self.assertEqual(svg.count("<polyline "), 3)
        self.assertEqual(svg.count("<circle "), 21)  # 18 points + 3 legend markers
        self.assertIn('fill="#fff" stroke="#9b9b9b"', svg)
        self.assertNotIn('fill="#f2f2f2"', svg)
        self.assertNotIn('rx="5" fill="#fff" stroke="#9b9b9b"', svg)
        self.assertIn('fill="none" stroke="#000" stroke-width="2"', svg)

    def test_phase_pie_reports_both_counts_and_percentages(self):
        row = {
            "Phase": "PHASE1",
            "Phase Label": "Phase 1",
            "China-Involved Studies": 25,
            "Non China-Involved Studies": 75,
            "Total Studies": 100,
            "China-Involved Percentage": 0.25,
            "Non China-Involved Percentage": 0.75,
        }
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "phase.svg"
            phase_pie_chart_svg(row, path)
            svg = path.read_text(encoding="utf-8")
        self.assertIn("25.0%", svg)
        self.assertIn("75.0%", svg)
        self.assertIn("China-Involved (n=25)", svg)
        self.assertIn("Non China-Involved (n=75)", svg)
        self.assertIn('fill="#fff" stroke="#9b9b9b"', svg)
        self.assertNotIn('rx="6"', svg)

    def test_combined_phase_chart_contains_phase1_to_phase4_only(self):
        rows = []
        for phase, label in zip(
            ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"),
            ("Early Phase 1", "Phase 1", "Phase 2", "Phase 3", "Phase 4"),
        ):
            rows.append({
                "Phase": phase,
                "Phase Label": label,
                "China-Involved Studies": 25,
                "Non China-Involved Studies": 75,
                "Total Studies": 100,
            })
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "combined.svg"
            combined_phase_pies_svg(rows, path)
            svg = path.read_text(encoding="utf-8")
        self.assertEqual(svg.count("<path "), 8)
        self.assertNotIn("Early Phase 1 (n=", svg)
        for phase in ("Phase 1", "Phase 2", "Phase 3", "Phase 4"):
            self.assertIn(f"{phase} (n=100)", svg)
        self.assertNotIn('fill="#f2f2f2"', svg)
        self.assertNotIn('rx="5"', svg)
        self.assertIn('.note{font-size:20px', svg)
        self.assertIn('<rect x="55" y="160" width="290" height="88"', svg)
        self.assertIn('<rect x="90" y="176" width="20" height="20"', svg)
        self.assertIn('<rect x="90" y="212" width="20" height="20"', svg)


if __name__ == "__main__":
    unittest.main()
