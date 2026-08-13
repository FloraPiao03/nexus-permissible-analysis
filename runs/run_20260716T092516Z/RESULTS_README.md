# Final Results — ClinicalTrials.gov snapshot 2026-07-16

This directory contains the final, verified Nexus and Permissible analysis for the completed ClinicalTrials.gov API snapshot harvested on 2026-07-16.

## Snapshot

- Unique NCT IDs: 594,066
- Registered facility/location rows: 3,488,092
- Snapshot complete: yes
- Duplicate NCT IDs: 0
- Raw page files verified by SHA-256: 595/595

## Primary all-study results

- NEXUS: 2,521 (0.4244%)
- PERMISSIBLE: 340,665 (57.3446%)
- US_ONLY: 191,025 (32.1555%)
- UNKNOWN: 59,855 (10.0755%)

The Excel workbook is published as a GitHub Release asset because its approximately 226 MB size exceeds GitHub's normal 100 MB repository file limit:

[Download nexus_permissible_results.xlsx](https://github.com/FloraPiao03/nexus-permissible-analysis/releases/download/results-20260716/nexus_permissible_results.xlsx)

The committed summary and country files are small enough to review directly on GitHub. Raw API pages and large row-level CSV files are intentionally excluded from Git.

## Interventional-only results

The additional analysis scope is exactly `study_type == "INTERVENTIONAL"` and reuses the validated five-category study-level classifications from this frozen snapshot.

- Total Interventional studies: 453,297
- Known-location studies: 411,859
- UNKNOWN: 41,438
- PERMISSIBLE: 250,059 (55.1645% of all Interventional studies)
- US_ONLY: 138,498
- US_NON_CHINA_MULTI: 20,925
- NEXUS: 2,377 (0.5244% of all Interventional studies)
- HAS_US: 161,800

[Review the committed Interventional summary](out_interventional/summary_interventional.md).

[Download nexus_permissible_interventional.xlsx](https://github.com/FloraPiao03/nexus-permissible-analysis/releases/download/results-interventional-20260716/nexus_permissible_interventional.xlsx).

Workbook SHA-256: `697b80cab03bc55c57863ffd47ecc7fbbad696deb6f8077db66071e84e9f45ce`.

The workbook is published as a Release asset. The 88 MB row-level Interventional CSV, raw API pages, and full raw snapshot remain excluded from Git.

## Interpretation limitation

ClinicalTrials.gov locations represent registered or planned study facilities. They do not confirm participant nationality or actual enrollment by country.
