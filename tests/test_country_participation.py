import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from country_participation import (
    aggregate_observations, chart_svg, completed_chart_rows, continent_chart_svg,
    eligible_observation, focused_percentage_chart_svg, load_continent_mapping,
    nexus_chart_svg, parse_start_year,
)


def study(nct_id, start_date, countries, *, study_type="INTERVENTIONAL",
          sponsor_class="INDUSTRY", intervention_types=("DRUG",)):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct_id},
        "designModule": {"studyType": study_type},
        "statusModule": {"startDateStruct": {"date": start_date}} if start_date is not None else {},
        "sponsorCollaboratorsModule": {"leadSponsor": {"class": sponsor_class}},
        "armsInterventionsModule": {"interventions": [{"type": value} for value in intervention_types]},
        "contactsLocationsModule": {"locations": [{"country": country} for country in countries]},
    }}


class CountryParticipationTests(unittest.TestCase):
    def test_completed_chart_rows_excludes_partial_snapshot_year(self):
        rows = [{"Year": 2024}, {"Year": 2025}, {"Year": 2026}]
        self.assertEqual(
            completed_chart_rows(rows, 2025),
            [{"Year": 2024}, {"Year": 2025}],
        )

    def test_start_year_accepts_supported_precision_and_rejects_invalid_dates(self):
        self.assertEqual(parse_start_year("2024"), 2024)
        self.assertEqual(parse_start_year("2024-02"), 2024)
        self.assertEqual(parse_start_year("2024-02-29"), 2024)
        for value in (None, "", "2024-13", "2023-02-29", "02/2024", "2024-Q1"):
            self.assertIsNone(parse_start_year(value), value)

    def test_broad_candidate_includes_mixed_drug_and_uses_only_registered_countries(self):
        observation = eligible_observation(study(
            "NCT1", "2020-01", [" United States ", "United States", "China", ""],
            intervention_types=("DEVICE", "DRUG", "DRUG"),
        ))
        self.assertIsNotNone(observation)
        self.assertEqual(observation["countries"], {"United States", "China"})
        self.assertIsNone(eligible_observation(study("NCT2", "2020", ["Germany"], study_type="OBSERVATIONAL")))
        self.assertIsNone(eligible_observation(study("NCT3", "2020", ["Germany"], sponsor_class="NIH")))
        self.assertIsNone(eligible_observation(study("NCT4", "2020", ["Germany"], intervention_types=("DEVICE",))))

    def test_annual_counts_zero_years_and_location_deduplication(self):
        observations = [
            eligible_observation(study("NCT1", "1991", ["Alpha", "Alpha", "Beta"])),
            eligible_observation(study("NCT2", "1991-05", ["Alpha"])),
            eligible_observation(study("NCT3", "1993-01-01", ["Gamma"])),
        ]
        result = aggregate_observations(observations, 1991, 1993)
        annual = {row["Year"]: row for row in result["annual_rows"]}
        self.assertEqual(annual[1991]["Eligible Studies Started"], 2)
        self.assertEqual(annual[1991]["Unique Countries Involved"], 2)
        self.assertEqual(annual[1992]["Eligible Studies Started"], 0)
        self.assertEqual(annual[1992]["Unique Countries Involved"], 0)
        self.assertEqual(annual[1991]["3-Year Rolling Active Countries"], 2)
        self.assertEqual(annual[1993]["3-Year Rolling Active Countries"], 3)
        percentages = {row["Year"]: row for row in result["focused_percentage_rows"]}
        self.assertEqual(percentages[1991]["Multi-Country Studies"], 1)
        self.assertEqual(percentages[1991]["Multi-Country Study Percentage"], 1 / 2)

    def test_focused_percentage_chart_has_markers_padding_and_full_frame(self):
        rows = [
            {"Year": year, "Percentage": value}
            for year, value in zip(range(2020, 2026), (0.30, 0.31, 0.29, 0.28, 0.27, 0.26))
        ]
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "chart.svg"
            focused_percentage_chart_svg(
                rows,
                path,
                title="Test Percentage, 2020-2025",
                y_axis_label="Studies (%)",
                percentage_field="Percentage",
                color="#146c94",
            )
            svg = path.read_text(encoding="utf-8")
        self.assertIn("Test Percentage, 2020-2025", svg)
        self.assertIn(">Start Year</text>", svg)
        self.assertEqual(svg.count("<circle "), 6)
        self.assertIn('fill="none" stroke="#000" stroke-width="2"', svg)
        self.assertNotIn('cx="140.0"', svg)
        self.assertNotIn('cx="1530.0"', svg)

    def test_focused_percentage_chart_supports_dense_fractional_ticks(self):
        rows = [
            {"Year": 2020, "Percentage": 0.044},
            {"Year": 2021, "Percentage": 0.077},
        ]
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "chart.svg"
            focused_percentage_chart_svg(
                rows,
                path,
                title="Dense ticks",
                y_axis_label="Studies (%)",
                percentage_field="Percentage",
                color="#146c94",
                tick_step=0.0025,
            )
            svg = path.read_text(encoding="utf-8")
        for label in ("4%", "4.25%", "4.5%", "4.75%", "8%"):
            self.assertIn(f">{label}</text>", svg)

    def test_focused_percentage_chart_can_omit_redundant_tick_percent_sign(self):
        rows = [
            {"Year": 2020, "Percentage": 0.044},
            {"Year": 2021, "Percentage": 0.077},
        ]
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "chart.svg"
            focused_percentage_chart_svg(
                rows,
                path,
                title="Dense ticks",
                y_axis_label="Studies (%)",
                percentage_field="Percentage",
                color="#146c94",
                tick_step=0.0025,
                show_tick_percent_sign=False,
            )
            svg = path.read_text(encoding="utf-8")
        for label in ("4", "4.25", "4.5", "4.75", "8"):
            self.assertIn(f">{label}</text>", svg)
        self.assertNotIn(">4.25%</text>", svg)

    def test_historical_charts_use_small_markers_at_every_annual_point(self):
        annual_rows = [
            {"Year": 2020, "Unique Countries Involved": 10,
             "3-Year Rolling Active Countries": 9},
            {"Year": 2021, "Unique Countries Involved": 12,
             "3-Year Rolling Active Countries": 11},
        ]
        nexus_rows = [
            {"Year": 2020, "NEXUS Studies": 5,
             "3-Year Moving Average NEXUS Studies": 4},
            {"Year": 2021, "NEXUS Studies": 7,
             "3-Year Moving Average NEXUS Studies": 6},
        ]
        continent_rows = [
            {"Year": year, "Continent": continent,
             "Percentage of All Eligible Studies": 0.1}
            for year in (2020, 2021) for continent in (
                "Africa", "Asia", "Europe", "North America", "South America", "Oceania"
            )
        ]
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            annual_path = directory / "annual.svg"
            continent_path = directory / "continent.svg"
            nexus_path = directory / "nexus.svg"
            chart_svg(annual_rows, annual_path, 2021)
            continent_chart_svg(continent_rows, continent_path, 2021)
            nexus_chart_svg(nexus_rows, nexus_path, 2021)
            annual_svg = annual_path.read_text(encoding="utf-8")
            continent_svg = continent_path.read_text(encoding="utf-8")
            nexus_svg = nexus_path.read_text(encoding="utf-8")
        self.assertEqual(annual_svg.count("<circle "), 4)
        self.assertEqual(continent_svg.count("<circle "), 12)
        self.assertEqual(nexus_svg.count("<circle "), 4)
        self.assertIn('r="4"', annual_svg)
        self.assertIn('r="5"', nexus_svg)
        self.assertIn('r="4.5"', continent_svg)

    def test_first_active_year_is_unique_and_counts_studies(self):
        observations = [
            eligible_observation(study("NCT1", "1991", ["Alpha"])),
            eligible_observation(study("NCT2", "1991", ["Alpha"])),
            eligible_observation(study("NCT3", "1992", ["Alpha", "Beta"])),
        ]
        result = aggregate_observations(observations, 1991, 1992)
        rows = {row["Country"]: row for row in result["first_rows"]}
        self.assertEqual(rows["Alpha"]["First Active Year"], 1991)
        self.assertEqual(rows["Alpha"]["Studies in First Active Year"], 2)
        self.assertEqual(rows["Beta"]["First Active Year"], 1992)
        self.assertEqual(len(rows), 2)

    def test_return_requires_at_least_one_missing_intervening_year(self):
        observations = [
            eligible_observation(study("NCT1", "1991", ["Alpha", "Beta"])),
            eligible_observation(study("NCT2", "1992", ["Alpha", "Beta"])),
            eligible_observation(study("NCT3", "1993", ["Beta"])),
            eligible_observation(study("NCT4", "1994", ["Alpha", "Beta"])),
        ]
        result = aggregate_observations(observations, 1991, 1994)
        self.assertEqual(result["return_rows"], [{
            "Return Year": 1994,
            "Country": "Alpha",
            "Previous Active Year": 1992,
            "Gap Length (Years)": 1,
            "Studies in Return Year": 1,
        }])

    def test_missing_start_and_out_of_period_studies_reconcile(self):
        observations = [
            eligible_observation(study("NCT1", None, [])),
            eligible_observation(study("NCT2", "1990", ["Alpha"])),
            eligible_observation(study("NCT3", "1991", [])),
            eligible_observation(study("NCT4", "1993", ["Beta"])),
        ]
        result = aggregate_observations(observations, 1991, 1992)
        self.assertEqual(result["eligible_study_count"], 4)
        self.assertEqual(result["missing_or_invalid_start_date_count"], 1)
        self.assertEqual(result["pre_1991_valid_start_count"], 1)
        self.assertEqual(result["future_start_year_count"], 1)
        self.assertEqual(result["primary_period_valid_start_count"], 1)
        self.assertTrue(all(result["validations"].values()))

    def test_continent_participation_uses_all_studies_and_is_nonexclusive(self):
        observations = [
            eligible_observation(study("NCT1", "1991", ["Alpha", "Beta"])),
            eligible_observation(study("NCT2", "1991", ["Alpha"])),
            eligible_observation(study("NCT3", "1991", [])),
        ]
        result = aggregate_observations(
            observations, 1991, 1991, {"Alpha": "Africa", "Beta": "Europe"}
        )
        rows = {row["Continent"]: row for row in result["continent_rows"]}
        self.assertEqual(rows["Africa"]["Studies with Continent Participation"], 2)
        self.assertEqual(rows["Africa"]["Percentage of All Eligible Studies"], 2 / 3)
        self.assertEqual(rows["Europe"]["Studies with Continent Participation"], 1)
        self.assertEqual(rows["Europe"]["Percentage of All Eligible Studies"], 1 / 3)
        self.assertEqual(rows["Africa"]["Known-Location Studies"], 2)
        self.assertEqual(rows["Africa"]["Percentage of Known-Location Studies"], 1.0)
        self.assertTrue(result["validations"]["known_location_studies_have_at_least_one_mapped_continent"])

    def test_repository_continent_mapping_is_unique_and_covers_special_values(self):
        mapping, document = load_continent_mapping(Path("continent_mapping.json"))
        self.assertEqual(len(mapping), 163)
        self.assertEqual(mapping["Puerto Rico"], "North America")
        self.assertEqual(mapping["French Guiana"], "South America")
        self.assertEqual(mapping["Reunion"], "Africa")
        self.assertEqual(mapping["Hong Kong"], "Asia")
        self.assertEqual(mapping["American Samoa"], "Oceania")
        self.assertIn("United Nations", document["source"])

    def test_annual_nexus_requires_exact_us_and_china_locations(self):
        observations = [
            eligible_observation(study("NCT1", "2020", ["United States", "China", "Canada"])),
            eligible_observation(study("NCT2", "2020", ["United States"])),
            eligible_observation(study("NCT3", "2020", ["China"])),
            eligible_observation(study("NCT4", "2021", ["United States", "Hong Kong"])),
        ]
        result = aggregate_observations(observations, 2020, 2021)
        rows = {row["Year"]: row for row in result["nexus_rows"]}
        self.assertEqual(rows[2020]["NEXUS Studies"], 1)
        self.assertEqual(rows[2020]["NEXUS Percentage of All Eligible Studies"], 1 / 3)
        self.assertEqual(rows[2020]["NEXUS Percentage of Known-Location Studies"], 1 / 3)
        self.assertEqual(rows[2021]["NEXUS Studies"], 0)
        self.assertEqual(rows[2021]["3-Year Moving Average NEXUS Studies"], 0.5)
        self.assertTrue(result["validations"]["annual_nexus_is_subset_of_known_location_studies"])


if __name__ == "__main__":
    unittest.main()
