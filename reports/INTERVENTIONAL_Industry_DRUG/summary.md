# Nexus and Permissible Analysis — Five-Category Model — FINAL — COMPLETE SNAPSHOT

## Overall population

- Analysis mode: **SUMMARY_ONLY_STREAMING**
- Study type filter: **interventional**
- Study product filter: **drug**
- Drug candidate definition: **StudyType == INTERVENTIONAL AND LeadSponsorClass == INDUSTRY AND contains at least one InterventionType == DRUG**
- Total studies: **78,893**
- Known-location studies: **70,564**
- UNKNOWN: **8,329 (10.56% of all studies)**

## High-level geographic split

- NO_US / PERMISSIBLE: **32,188 (40.80% of all; 45.62% of known-location)**
- HAS_US: **38,376 (48.64% of all; 54.38% of known-location)**

## Breakdown of HAS_US studies

- US_ONLY: **21,601 (27.38% of all; 30.61% of known-location; 56.29% of HAS_US)**
- US_NON_CHINA_MULTI: **14,645 (18.56% of all; 20.75% of known-location; 38.16% of HAS_US)**
- NEXUS: **2,130 (2.70% of all; 3.02% of known-location; 5.55% of HAS_US)**

## Reconciliation checks

- Five buckets equal total: **78,893 = 78,893**
- PERMISSIBLE + HAS_US = known-location: **32,188 + 38,376 = 70,564**
- US_ONLY + US_NON_CHINA_MULTI + NEXUS = HAS_US: **21,601 + 14,645 + 2,130 = 38,376**

## Start-date period comparison

- Reference date: **2026-07-22**
- RECENT_3Y: **2023-07-22 < Start Date <= 2026-07-22**
- YEARS_4_TO_6_AGO: **2020-07-22 < Start Date <= 2023-07-22**
- TIME_UNKNOWN: **979**; TIME_AMBIGUOUS: **113**

### All time-cohort counts

| Time cohort | Count |
|---|---:|
| RECENT_3Y | 11,242 |
| YEARS_4_TO_6_AGO | 11,591 |
| OLDER_THAN_6Y | 54,599 |
| FUTURE | 369 |
| TIME_UNKNOWN | 979 |
| TIME_AMBIGUOUS | 113 |

| Cohort | Denominator | Known location | NEXUS | NEXUS % cohort | NEXUS % known | PERMISSIBLE | PERMISSIBLE % cohort | PERMISSIBLE % known |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RECENT_3Y | 11,242 | 10,367 | 708 | 6.30% | 6.83% | 5,539 | 49.27% | 53.43% |
| YEARS_4_TO_6_AGO | 11,591 | 11,142 | 585 | 5.05% | 5.25% | 5,501 | 47.46% | 49.37% |

### Full geographic distribution within primary cohorts

| Cohort | Bucket | Count | % of cohort | % of known-location cohort |
|---|---|---:|---:|---:|
| RECENT_3Y | NEXUS | 708 | 6.30% | 6.83% |
| RECENT_3Y | PERMISSIBLE | 5,539 | 49.27% | 53.43% |
| RECENT_3Y | US_ONLY | 2,395 | 21.30% | 23.10% |
| RECENT_3Y | US_NON_CHINA_MULTI | 1,725 | 15.34% | 16.64% |
| RECENT_3Y | UNKNOWN | 875 | 7.78% | N/A |
| RECENT_3Y | HAS_US | 4,828 | 42.95% | 46.57% |
| YEARS_4_TO_6_AGO | NEXUS | 585 | 5.05% | 5.25% |
| YEARS_4_TO_6_AGO | PERMISSIBLE | 5,501 | 47.46% | 49.37% |
| YEARS_4_TO_6_AGO | US_ONLY | 2,774 | 23.93% | 24.90% |
| YEARS_4_TO_6_AGO | US_NON_CHINA_MULTI | 2,282 | 19.69% | 20.48% |
| YEARS_4_TO_6_AGO | UNKNOWN | 449 | 3.87% | N/A |
| YEARS_4_TO_6_AGO | HAS_US | 5,641 | 48.67% | 50.63% |

### Direct Recent 3Y vs 4–6 Years Ago comparison

| Metric | Recent 3Y | 4–6 Years Ago | Change | Change unit |
|---|---:|---:|---:|---|
| Cohort denominator | 11,242 | 11,591 | -349 | count |
| Known-location denominator | 10,367 | 11,142 | -775 | count |
| NEXUS count | 708 | 585 | +123 | count |
| NEXUS % of all cohort | 6.30% | 5.05% | 1.25% | percentage points |
| NEXUS % of known-location | 6.83% | 5.25% | 1.58% | percentage points |
| PERMISSIBLE count | 5,539 | 5,501 | +38 | count |
| PERMISSIBLE % of all cohort | 49.27% | 47.46% | 1.81% | percentage points |
| PERMISSIBLE % of known-location | 53.43% | 49.37% | 4.06% | percentage points |
| US_ONLY % of all cohort | 21.30% | 23.93% | -2.63% | percentage points |
| US_NON_CHINA_MULTI % of all cohort | 15.34% | 19.69% | -4.34% | percentage points |
| UNKNOWN % of all cohort | 7.78% | 3.87% | 3.91% | percentage points |
| HAS_US count | 4,828 | 5,641 | -813 | count |
| HAS_US % of all cohort | 42.95% | 48.67% | -5.72% | percentage points |
| HAS_US % of known-location | 46.57% | 50.63% | -4.06% | percentage points |

Registered Start Date is a registry field, not confirmed first-participant enrollment. Period comparisons are descriptive and do not imply causation.

## Industry Drug-containing intervention-type audit

- Lead Sponsor filter: **INDUSTRY**
- Total Industry studies: **112,203**
- Industry Drug-containing studies: **78,893**
- Industry studies not containing DRUG: **33,310**
- Industry studies with missing intervention type: **0**
- Device-involved Industry Drug studies: **886**

| Intervention Type Combination | Unique Study Count | % of Industry Drug-containing Studies |
|---|---:|---:|
| DRUG | 71,337 | 90.42% |
| DRUG + OTHER | 3,160 | 4.01% |
| DRUG + BIOLOGICAL | 2,063 | 2.61% |
| DRUG + DEVICE | 779 | 0.99% |
| DRUG + PROCEDURE | 414 | 0.52% |
| DRUG + RADIATION | 201 | 0.25% |
| DRUG + COMBINATION_PRODUCT | 176 | 0.22% |
| DRUG + DIETARY_SUPPLEMENT | 138 | 0.17% |
| DRUG + BIOLOGICAL + OTHER | 103 | 0.13% |
| DRUG + BEHAVIORAL | 99 | 0.13% |
| DRUG + GENETIC | 52 | 0.07% |
| DRUG + DIAGNOSTIC_TEST | 46 | 0.06% |
| DRUG + BIOLOGICAL + RADIATION | 41 | 0.05% |
| DRUG + DEVICE + OTHER | 39 | 0.05% |
| DRUG + BIOLOGICAL + PROCEDURE | 31 | 0.04% |
| DRUG + DEVICE + PROCEDURE | 31 | 0.04% |
| DRUG + OTHER + PROCEDURE | 22 | 0.03% |
| DRUG + PROCEDURE + RADIATION | 19 | 0.02% |
| DRUG + BIOLOGICAL + DEVICE | 13 | 0.02% |
| DRUG + COMBINATION_PRODUCT + OTHER | 12 | 0.02% |
| DRUG + DIETARY_SUPPLEMENT + OTHER | 12 | 0.02% |
| DRUG + BIOLOGICAL + GENETIC | 11 | 0.01% |
| DRUG + BIOLOGICAL + COMBINATION_PRODUCT | 9 | 0.01% |
| DRUG + BIOLOGICAL + DIETARY_SUPPLEMENT | 9 | 0.01% |
| DRUG + OTHER + RADIATION | 9 | 0.01% |
| DRUG + COMBINATION_PRODUCT + DEVICE | 8 | 0.01% |
| DRUG + BIOLOGICAL + PROCEDURE + RADIATION | 6 | 0.01% |
| DRUG + DEVICE + RADIATION | 6 | 0.01% |
| DRUG + BEHAVIORAL + PROCEDURE | 5 | 0.01% |
| DRUG + DIAGNOSTIC_TEST + OTHER | 4 | 0.01% |
| DRUG + GENETIC + OTHER | 4 | 0.01% |
| DRUG + BEHAVIORAL + DIETARY_SUPPLEMENT | 3 | 0.00% |
| DRUG + COMBINATION_PRODUCT + PROCEDURE | 3 | 0.00% |
| DRUG + DIAGNOSTIC_TEST + PROCEDURE | 3 | 0.00% |
| DRUG + BEHAVIORAL + DEVICE | 2 | 0.00% |
| DRUG + BIOLOGICAL + COMBINATION_PRODUCT + OTHER | 2 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + PROCEDURE | 2 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST + OTHER | 2 | 0.00% |
| DRUG + DEVICE + GENETIC | 2 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST + OTHER | 1 | 0.00% |
| DRUG + BEHAVIORAL + DIAGNOSTIC_TEST + RADIATION | 1 | 0.00% |
| DRUG + BEHAVIORAL + OTHER | 1 | 0.00% |
| DRUG + BIOLOGICAL + DEVICE + PROCEDURE | 1 | 0.00% |
| DRUG + BIOLOGICAL + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + BIOLOGICAL + DIETARY_SUPPLEMENT + PROCEDURE + RADIATION | 1 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + PROCEDURE + RADIATION | 1 | 0.00% |
| DRUG + BIOLOGICAL + OTHER + RADIATION | 1 | 0.00% |
| DRUG + COMBINATION_PRODUCT + DEVICE + PROCEDURE | 1 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST | 1 | 0.00% |
| DRUG + DEVICE + DIAGNOSTIC_TEST + PROCEDURE | 1 | 0.00% |
| DRUG + DIAGNOSTIC_TEST + OTHER + PROCEDURE | 1 | 0.00% |
| DRUG + DIETARY_SUPPLEMENT + OTHER + PROCEDURE | 1 | 0.00% |
| DRUG + GENETIC + RADIATION | 1 | 0.00% |

### Highlighted combination counts

| Category | Unique Study Count |
|---|---:|
| DRUG only | 71,337 |
| DRUG + OTHER | 3,160 |
| DRUG + DEVICE | 779 |
| DRUG + PROCEDURE | 414 |
| DRUG + BEHAVIORAL | 99 |
| DRUG + DIETARY_SUPPLEMENT | 138 |
| Other observed combinations containing DRUG | 2,966 |

The final exclusion rule for non-drug intervention combinations has NOT yet been fixed. It will be decided after reviewing the actual intervention-type combination distribution.

## All vs Industry Drug-containing candidate diagnostic comparison

| Metric | All INTERVENTIONAL Studies | Industry Drug-containing Candidates |
|---|---:|---:|
| Recent 3Y denominator | 90,809 | 11,242 |
| Recent 3Y Nexus % | 0.86% | 6.30% |
| Recent 3Y Permissible % | 62.69% | 49.27% |
| 4–6Y denominator | 84,461 | 11,591 |
| 4–6Y Nexus % | 0.76% | 5.05% |
| 4–6Y Permissible % | 63.73% | 47.46% |

## Definitions and limitations

- US_ONLY means the complete unique country set is exactly {United States}.
- US_NON_CHINA_MULTI contains United States plus at least one other non-China country.
- NEXUS contains both United States and China and may contain other countries.
- PERMISSIBLE has a known country set with no United States; NEXUS and PERMISSIBLE alone do not partition the registry.
- US definition: United States
- China definition: China
- Unit of analysis: one unique NCT ID
- Harvest timestamp: 2026-07-22T02:25:19.846228+00:00
- Analysis timestamp: 2026-07-22T03:07:20.777498+00:00
- Study type filter: interventional
- Denominator: unique NCT IDs after applying study_type_filter=interventional and study_product_filter=drug.
- Location-proxy limitation: registered or planned facilities do not confirm participant nationality or actual country-level enrollment.
