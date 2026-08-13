# Nexus and Permissible Analysis — Five-Category Model — FINAL — COMPLETE SNAPSHOT

## Overall population

- Analysis mode: **SUMMARY_ONLY_STREAMING**
- Study product filter: **drug**
- Drug candidate definition: **LeadSponsorClass == INDUSTRY AND contains at least one InterventionType == DRUG**
- Total studies: **83,159**
- Known-location studies: **73,776**
- UNKNOWN: **9,383 (11.28% of all studies)**

## High-level geographic split

- NO_US / PERMISSIBLE: **34,480 (41.46% of all; 46.74% of known-location)**
- HAS_US: **39,296 (47.25% of all; 53.26% of known-location)**

## Breakdown of HAS_US studies

- US_ONLY: **22,289 (26.80% of all; 30.21% of known-location; 56.72% of HAS_US)**
- US_NON_CHINA_MULTI: **14,862 (17.87% of all; 20.14% of known-location; 37.82% of HAS_US)**
- NEXUS: **2,145 (2.58% of all; 2.91% of known-location; 5.46% of HAS_US)**

## Reconciliation checks

- Five buckets equal total: **83,159 = 83,159**
- PERMISSIBLE + HAS_US = known-location: **34,480 + 39,296 = 73,776**
- US_ONLY + US_NON_CHINA_MULTI + NEXUS = HAS_US: **22,289 + 14,862 + 2,145 = 39,296**

## Start-date period comparison

- Reference date: **2026-07-22**
- RECENT_3Y: **2023-07-22 < Start Date <= 2026-07-22**
- YEARS_4_TO_6_AGO: **2020-07-22 < Start Date <= 2023-07-22**
- TIME_UNKNOWN: **1,541**; TIME_AMBIGUOUS: **114**

### All time-cohort counts

| Time cohort | Count |
|---|---:|
| RECENT_3Y | 11,724 |
| YEARS_4_TO_6_AGO | 12,116 |
| OLDER_THAN_6Y | 57,278 |
| FUTURE | 386 |
| TIME_UNKNOWN | 1,541 |
| TIME_AMBIGUOUS | 114 |

| Cohort | Denominator | Known location | NEXUS | NEXUS % cohort | NEXUS % known | PERMISSIBLE | PERMISSIBLE % cohort | PERMISSIBLE % known |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RECENT_3Y | 11,724 | 10,822 | 712 | 6.07% | 6.58% | 5,851 | 49.91% | 54.07% |
| YEARS_4_TO_6_AGO | 12,116 | 11,652 | 588 | 4.85% | 5.05% | 5,863 | 48.39% | 50.32% |

### Full geographic distribution within primary cohorts

| Cohort | Bucket | Count | % of cohort | % of known-location cohort |
|---|---|---:|---:|---:|
| RECENT_3Y | NEXUS | 712 | 6.07% | 6.58% |
| RECENT_3Y | PERMISSIBLE | 5,851 | 49.91% | 54.07% |
| RECENT_3Y | US_ONLY | 2,516 | 21.46% | 23.25% |
| RECENT_3Y | US_NON_CHINA_MULTI | 1,743 | 14.87% | 16.11% |
| RECENT_3Y | UNKNOWN | 902 | 7.69% | N/A |
| RECENT_3Y | HAS_US | 4,971 | 42.40% | 45.93% |
| YEARS_4_TO_6_AGO | NEXUS | 588 | 4.85% | 5.05% |
| YEARS_4_TO_6_AGO | PERMISSIBLE | 5,863 | 48.39% | 50.32% |
| YEARS_4_TO_6_AGO | US_ONLY | 2,899 | 23.93% | 24.88% |
| YEARS_4_TO_6_AGO | US_NON_CHINA_MULTI | 2,302 | 19.00% | 19.76% |
| YEARS_4_TO_6_AGO | UNKNOWN | 464 | 3.83% | N/A |
| YEARS_4_TO_6_AGO | HAS_US | 5,789 | 47.78% | 49.68% |

### Direct Recent 3Y vs 4–6 Years Ago comparison

| Metric | Recent 3Y | 4–6 Years Ago | Change | Change unit |
|---|---:|---:|---:|---|
| Cohort denominator | 11,724 | 12,116 | -392 | count |
| Known-location denominator | 10,822 | 11,652 | -830 | count |
| NEXUS count | 712 | 588 | +124 | count |
| NEXUS % of all cohort | 6.07% | 4.85% | 1.22% | percentage points |
| NEXUS % of known-location | 6.58% | 5.05% | 1.53% | percentage points |
| PERMISSIBLE count | 5,851 | 5,863 | -12 | count |
| PERMISSIBLE % of all cohort | 49.91% | 48.39% | 1.52% | percentage points |
| PERMISSIBLE % of known-location | 54.07% | 50.32% | 3.75% | percentage points |
| US_ONLY % of all cohort | 21.46% | 23.93% | -2.47% | percentage points |
| US_NON_CHINA_MULTI % of all cohort | 14.87% | 19.00% | -4.13% | percentage points |
| UNKNOWN % of all cohort | 7.69% | 3.83% | 3.86% | percentage points |
| HAS_US count | 4,971 | 5,789 | -818 | count |
| HAS_US % of all cohort | 42.40% | 47.78% | -5.38% | percentage points |
| HAS_US % of known-location | 45.93% | 49.68% | -3.75% | percentage points |

Registered Start Date is a registry field, not confirmed first-participant enrollment. Period comparisons are descriptive and do not imply causation.

## Industry Drug-containing intervention-type audit

- Lead Sponsor filter: **INDUSTRY**
- Total Industry studies: **131,059**
- Industry Drug-containing studies: **83,159**
- Industry studies not containing DRUG: **47,900**
- Industry studies with missing intervention type: **6,355**
- Device-involved Industry Drug studies: **941**

| Intervention Type Combination | Unique Study Count | % of Industry Drug-containing Studies |
|---|---:|---:|
| DRUG | 75,375 | 90.64% |
| DRUG + OTHER | 3,222 | 3.87% |
| DRUG + BIOLOGICAL | 2,123 | 2.55% |
| DRUG + DEVICE | 826 | 0.99% |
| DRUG + PROCEDURE | 428 | 0.51% |
| DRUG + RADIATION | 206 | 0.25% |
| DRUG + COMBINATION_PRODUCT | 180 | 0.22% |
| DRUG + DIETARY_SUPPLEMENT | 139 | 0.17% |
| DRUG + BEHAVIORAL | 110 | 0.13% |
| DRUG + BIOLOGICAL + OTHER | 106 | 0.13% |
| DRUG + GENETIC | 54 | 0.06% |
| DRUG + DIAGNOSTIC_TEST | 49 | 0.06% |
| DRUG + DEVICE + OTHER | 43 | 0.05% |
| DRUG + BIOLOGICAL + RADIATION | 41 | 0.05% |
| DRUG + DEVICE + PROCEDURE | 34 | 0.04% |
| DRUG + BIOLOGICAL + PROCEDURE | 31 | 0.04% |
| DRUG + OTHER + PROCEDURE | 23 | 0.03% |
| DRUG + PROCEDURE + RADIATION | 20 | 0.02% |
| DRUG + BIOLOGICAL + DEVICE | 13 | 0.02% |
| DRUG + COMBINATION_PRODUCT + OTHER | 12 | 0.01% |
| DRUG + DIETARY_SUPPLEMENT + OTHER | 12 | 0.01% |
| DRUG + BIOLOGICAL + GENETIC | 11 | 0.01% |
| DRUG + BIOLOGICAL + COMBINATION_PRODUCT | 9 | 0.01% |
| DRUG + BIOLOGICAL + DIETARY_SUPPLEMENT | 9 | 0.01% |
| DRUG + OTHER + RADIATION | 9 | 0.01% |
| DRUG + COMBINATION_PRODUCT + DEVICE | 8 | 0.01% |
| DRUG + BIOLOGICAL + PROCEDURE + RADIATION | 6 | 0.01% |
| DRUG + DEVICE + RADIATION | 6 | 0.01% |
| DRUG + BEHAVIORAL + PROCEDURE | 5 | 0.01% |
| DRUG + DIAGNOSTIC_TEST + OTHER | 5 | 0.01% |
| DRUG + BEHAVIORAL + BIOLOGICAL | 4 | 0.00% |
| DRUG + GENETIC + OTHER | 4 | 0.00% |
| DRUG + BEHAVIORAL + DIETARY_SUPPLEMENT | 3 | 0.00% |
| DRUG + COMBINATION_PRODUCT + PROCEDURE | 3 | 0.00% |
| DRUG + DIAGNOSTIC_TEST + PROCEDURE | 3 | 0.00% |
| DRUG + BEHAVIORAL + DEVICE | 2 | 0.00% |
| DRUG + BEHAVIORAL + OTHER | 2 | 0.00% |
| DRUG + BIOLOGICAL + COMBINATION_PRODUCT + OTHER | 2 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + PROCEDURE | 2 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST + OTHER | 2 | 0.00% |
| DRUG + DEVICE + GENETIC | 2 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST + OTHER | 1 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST + RADIATION | 1 | 0.00% |
| DRUG + BIOLOGICAL + DEVICE + PROCEDURE | 1 | 0.00% |
| DRUG + BIOLOGICAL + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + BIOLOGICAL + DIETARY_SUPPLEMENT + PROCEDURE + RADIATION | 1 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + PROCEDURE + RADIATION | 1 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + RADIATION | 1 | 0.00% |
| DRUG + COMBINATION_PRODUCT + DEVICE + PROCEDURE | 1 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST + PROCEDURE | 1 | 0.00% |
| DRUG + DEVICE + OTHER + PROCEDURE | 1 | 0.00% |
| DRUG + DIAGNOSTIC_TEST + OTHER + PROCEDURE | 1 | 0.00% |
| DRUG + DIETARY_SUPPLEMENT + OTHER + PROCEDURE | 1 | 0.00% |
| DRUG + GENETIC + RADIATION | 1 | 0.00% |

### Highlighted combination counts

| Category | Unique Study Count |
|---|---:|
| DRUG only | 75,375 |
| DRUG + OTHER | 3,222 |
| DRUG + DEVICE | 826 |
| DRUG + PROCEDURE | 428 |
| DRUG + BEHAVIORAL | 110 |
| DRUG + DIETARY_SUPPLEMENT | 139 |
| Other observed combinations containing DRUG | 3,059 |

The final exclusion rule for non-drug intervention combinations has NOT yet been fixed. It will be decided after reviewing the actual intervention-type combination distribution.

## All vs Industry Drug-containing candidate diagnostic comparison

| Metric | All Studies | Industry Drug-containing Candidates |
|---|---:|---:|
| Recent 3Y denominator | 118,517 | 11,724 |
| Recent 3Y Nexus % | 0.67% | 6.07% |
| Recent 3Y Permissible % | 64.68% | 49.91% |
| 4–6Y denominator | 114,062 | 12,116 |
| 4–6Y Nexus % | 0.58% | 4.85% |
| 4–6Y Permissible % | 66.99% | 48.39% |

## Definitions and limitations

- US_ONLY means the complete unique country set is exactly {United States}.
- US_NON_CHINA_MULTI contains United States plus at least one other non-China country.
- NEXUS contains both United States and China and may contain other countries.
- PERMISSIBLE has a known country set with no United States; NEXUS and PERMISSIBLE alone do not partition the registry.
- US definition: United States
- China definition: China
- Unit of analysis: one unique NCT ID
- Harvest timestamp: 2026-07-22T02:25:19.846228+00:00
- Analysis timestamp: 2026-07-22T02:26:22.160636+00:00
- Denominator: unique Industry-sponsored DRUG-containing NCT IDs when study_product_filter is drug; otherwise all unique NCT IDs.
- Location-proxy limitation: registered or planned facilities do not confirm participant nationality or actual country-level enrollment.
