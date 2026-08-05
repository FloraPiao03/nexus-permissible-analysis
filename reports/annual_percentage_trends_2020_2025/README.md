# Focused Study Trends, 2020–2025

All figures use the existing cohort:

`StudyType == INTERVENTIONAL AND LeadSponsorClass == INDUSTRY AND contains at least one InterventionType == DRUG`

The year range is inclusive: 2020–2025 represents six complete Start Year cohorts. Locations are based only on registered values in `protocolSection.contactsLocationsModule.locations[].country`.

## Charts 1–2: annual percentages

These figures use the complete validated snapshot `runs/run_20260722T020135Z`.

Each percentage is calculated separately for its Start Year. The denominator is all eligible studies starting in that year, including studies without usable registered location-country data.

- **Multi-country Study Percentage:** studies with at least two distinct usable registered location countries / all eligible studies starting that year.
- **US & China Involved Studies Percentage:** studies with both exact `United States` and exact `China` registered location countries / all eligible studies starting that year.

The underlying counts and unrounded percentages are in `annual_percentage_data_2020_2025.csv`.

## Chart 3: China-involved footprint by year

This figure uses the complete Phase-enabled snapshot `runs/run_20260730T061844Z`. For each Start Year, every eligible study with an exact registered `China` location is assigned to exactly one mutually exclusive group:

- **China only:** the usable country set is exactly `{China}`.
- **China and Other Countries (No US):** China and at least one other country are present, but `United States` is absent.
- **China and US:** both exact `China` and exact `United States` are present; additional countries may also be present.

The line chart reports study counts, not percentages. A study contributes at most once per year and to only one line. The underlying counts are in `china_footprint_by_year_2020_2025.csv`.

## Chart 4: China involvement by phase

The five pie charts use the same complete Phase-enabled snapshot `runs/run_20260730T061844Z` and pool all six Start Year cohorts from 2020 through 2025.

Within each Phase chart:

- **China-Involved:** the study has an exact registered `China` location.
- **Non China-Involved:** the study does not have an exact registered `China` location, including records without usable registered countries.
- The denominator is all eligible studies assigned to that Phase.
- Missing/blank Phase values and `NA` are excluded.
- A multi-Phase study is counted once in each applicable Phase chart, so Phase totals must not be summed as mutually exclusive studies.

The five displayed groups are `EARLY_PHASE1`, `PHASE1`, `PHASE2`, `PHASE3`, and `PHASE4`. The underlying counts and unrounded percentages are in `china_involvement_by_phase_2020_2025.csv`.

The individual Phase charts are retained. An additional 2×2 figure, `china_involvement_phase1_to_phase4_combined_2020_2025`, places Phase 1–4 together for direct visual comparison; Early Phase 1 remains available only as its separate chart.

## Interpretation limitation

"Involved" means a registered study-location footprint. It does not infer geography from the sponsor, title, description, responsible party, or organization. Conversely, "Non China-Involved" means that no exact `China` location appears in the downloaded location metadata; it is not proof that a study has no operational or scientific relationship with China.
