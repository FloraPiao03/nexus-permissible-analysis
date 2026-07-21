# ClinicalTrials.gov Nexus / Permissible Time-Period Analysis

**Final Full-Snapshot Report**  
**Snapshot date:** 20 July 2026 (UTC)  
**Report date:** 21 July 2026  
**Unit of analysis:** One unique ClinicalTrials.gov NCT ID

## 中文摘要

本报告比较了 ClinicalTrials.gov 中注册 Start Date 位于最近三年（RECENT_3Y）与此前四至六年（YEARS_4_TO_6_AGO）的研究，其注册或计划 facility-location country 组合如何变化。

在 594,543 项唯一研究的完整快照中，589,195 项（99.10%）具有可解析 Start Date。Recent 3Y 的 NEXUS 比例为 0.6705%，高于 4–6 Years Ago 的 0.5811%，增加 0.0894 个百分点；使用 known-location denominator 后，差异为 0.1452 个百分点，方向不变。US_ONLY 与 US_NON_CHINA_MULTI 占比下降，而 Recent 3Y 的 UNKNOWN-location 比例由 5.93% 上升到 12.12%。因此，NEXUS 上升方向相对稳健，但 PERMISSIBLE 的方向取决于是否排除 UNKNOWN：以全部 cohort 为分母时下降 2.36 个百分点，以 known-location 为分母时上升 2.33 个百分点。

这些结果属于描述性注册数据分析。Location 表示注册或计划的研究设施，不代表参与者国籍或实际国家级 enrollment；Start Date 也不等于各国家站点的实际启动日期。结果不能解释为因果变化，也不能直接代表全球全部临床试验。

## Executive Summary

This analysis evaluates whether the geographic distribution of registered ClinicalTrials.gov study locations differs between studies with registered Start Dates in two non-overlapping three-year periods:

- **Recent 3Y:** 20 July 2023 < Start Date ≤ 20 July 2026.
- **4–6 Years Ago:** 20 July 2020 < Start Date ≤ 20 July 2023.

The completed API v2 snapshot contains **594,543 unique NCT IDs**. Start Date was usable for **589,195 studies (99.10%)**. All raw pages were present, all SHA-256 hashes passed, and all geographic and time-cohort reconciliation differences were zero.

The principal result is a modest increase in the NEXUS share: **0.5811% to 0.6705% of the full cohort**, a change of **+0.0894 percentage points**. Restricting the denominator to studies with known location data produced the same direction: **0.6177% to 0.7630%**, or **+0.1452 percentage points**.

Interpretation of PERMISSIBLE is less stable. Its share decreased using the full cohort denominator but increased among known-location studies. This difference is explained by the materially higher UNKNOWN-location share in Recent 3Y (**12.12% versus 5.93%**). The denominator and missing-location pattern must therefore be reported alongside any time comparison.

> **Bottom line:** The observed direction of the NEXUS difference is robust to the two planned denominators, but the absolute change is small. The PERMISSIBLE comparison is sensitive to missing location metadata. Results are descriptive and should not be interpreted causally.

## 1. Objective and Scope

The analysis addresses the following question:

> Among studies whose registered ClinicalTrials.gov Start Date falls in different periods, how has the distribution of registered or planned study-facility locations changed?

The five mutually exclusive geographic categories are:

| Category | Definition |
|---|---|
| UNKNOWN | No usable registered location-country value. |
| PERMISSIBLE | At least one usable country and no exact “United States” location. |
| US_ONLY | The complete unique country set is exactly {United States}. |
| US_NON_CHINA_MULTI | Contains exact United States, does not contain exact China, and contains at least one additional non-US country. |
| NEXUS | Contains exact United States and exact China, with or without additional countries. |

Baseline definitions are exact string matches: **US = United States** and **China = China**. US territories are not included in baseline US. Hong Kong, Macau/Macao, and Taiwan are not included in baseline China.

## 2. Data and Audit Status

The source is a completed ClinicalTrials.gov API v2 snapshot harvested on 20 July 2026. The workflow retained immutable raw JSON pages and a manifest containing request parameters, counts, pagination status, and page-level SHA-256 hashes.

| Audit item | Result |
|---|---:|
| Snapshot complete | Yes |
| Next-page token remaining | No |
| Page limit | None |
| Raw pages | 595 |
| Raw records | 594,543 |
| Unique NCT IDs | 594,543 |
| Duplicate NCT IDs | 0 |
| Missing NCT IDs | 0 |
| Missing raw pages | 0 |
| SHA-256 failures | 0 |
| Raw snapshot size | 601,337,516 bytes (approximately 575 MB on disk) |

The full run initially encountered repeated TLS EOF failures during long sequential pagination. A minimal resume mechanism was added and tested so that already written pages remained byte-for-byte unchanged and harvesting continued from the last saved next-page token. The final manifest records that the successful run resumed after page 413.

## 3. Temporal Variable and Cohort Definitions

The temporal source is:

`protocolSection.statusModule.startDateStruct.date`

The accompanying type is:

`protocolSection.statusModule.startDateStruct.type`

The deterministic reference date is the UTC harvest date in the manifest: **20 July 2026**. Calendar-year subtraction is used rather than 365-day approximations.

| Cohort | Exact definition | Count |
|---|---|---:|
| RECENT_3Y | 20 Jul 2023 < Start Date ≤ 20 Jul 2026 | 118,419 |
| YEARS_4_TO_6_AGO | 20 Jul 2020 < Start Date ≤ 20 Jul 2023 | 114,102 |
| OLDER_THAN_6Y | Start Date ≤ 20 Jul 2020 | 351,491 |
| FUTURE | Start Date > 20 Jul 2026 | 4,168 |
| TIME_UNKNOWN | Missing or unparseable Start Date | 5,348 |
| TIME_AMBIGUOUS | Partial-date interval crosses a cohort boundary | 1,015 |

Partial dates are handled conservatively as intervals. A month represents its first through last calendar day, and a year represents 1 January through 31 December. A partial date is assigned only when its entire possible interval falls within one cohort.

## 4. Start Date Coverage

| Date precision | Count |
|---|---:|
| DAY | 371,214 |
| MONTH | 217,981 |
| YEAR | 0 |
| MISSING | 5,348 |
| UNPARSEABLE | 0 |

Overall, **589,195 studies (99.10%)** had a usable registered Start Date. Observed StartDateType values were ACTUAL (347,984), ESTIMATED (60,254), and missing (186,305). A missing StartDateType does not necessarily mean that the date itself is missing.

## 5. Geographic Results by Time Period

### Recent 3Y

The cohort contains **118,419 studies**, of which **104,069** have known location data.

| Geographic category | Count | % of cohort | % of known-location |
|---|---:|---:|---:|
| UNKNOWN | 14,350 | 12.1180% | N/A |
| PERMISSIBLE | 76,519 | 64.6172% | 73.5272% |
| US_ONLY | 24,020 | 20.2839% | 23.0808% |
| US_NON_CHINA_MULTI | 2,736 | 2.3104% | 2.6290% |
| NEXUS | 794 | 0.6705% | 0.7630% |
| HAS_US | 27,550 | 23.2648% | 26.4728% |

HAS_US is exactly US_ONLY + US_NON_CHINA_MULTI + NEXUS.

### 4–6 Years Ago

The cohort contains **114,102 studies**, of which **107,331** have known location data.

| Geographic category | Count | % of cohort | % of known-location |
|---|---:|---:|---:|
| UNKNOWN | 6,771 | 5.9342% | N/A |
| PERMISSIBLE | 76,419 | 66.9743% | 71.1994% |
| US_ONLY | 26,602 | 23.3142% | 24.7850% |
| US_NON_CHINA_MULTI | 3,647 | 3.1963% | 3.3979% |
| NEXUS | 663 | 0.5811% | 0.6177% |
| HAS_US | 30,912 | 27.0915% | 28.8006% |

## 6. Direct Period Comparison

All percentage changes below are **percentage-point changes**, calculated as Recent 3Y minus 4–6 Years Ago. They are not percent growth rates.

| Metric | Recent 3Y | 4–6 Years Ago | Change |
|---|---:|---:|---:|
| Cohort denominator | 118,419 | 114,102 | +4,317 |
| Known-location denominator | 104,069 | 107,331 | −3,262 |
| NEXUS count | 794 | 663 | +131 |
| NEXUS % of cohort | 0.6705% | 0.5811% | +0.0894 pp |
| NEXUS % of known-location | 0.7630% | 0.6177% | +0.1452 pp |
| PERMISSIBLE count | 76,519 | 76,419 | +100 |
| PERMISSIBLE % of cohort | 64.6172% | 66.9743% | −2.3571 pp |
| PERMISSIBLE % of known-location | 73.5272% | 71.1994% | +2.3278 pp |
| US_ONLY % of cohort | 20.2839% | 23.3142% | −3.0303 pp |
| US_NON_CHINA_MULTI % of cohort | 2.3104% | 3.1963% | −0.8858 pp |
| UNKNOWN % of cohort | 12.1180% | 5.9342% | +6.1838 pp |

## 7. Statistical Interpretation

The comparison is statistically reasonable as a **descriptive registry analysis** because the cohorts are non-overlapping, equal in duration, based on deterministic calendar boundaries, and contain one observation per unique NCT ID. Counts, proportions, denominator definitions, and percentage-point differences are the primary estimands.

If the cohorts are treated as observations from a broader underlying process, a conventional two-proportion approximation indicates that the NEXUS difference is statistically distinguishable from zero. The approximate 95% interval for the full-cohort difference is **+0.025 to +0.154 percentage points**; for the known-location comparison it is approximately **+0.075 to +0.216 percentage points**. These inferential results are secondary because the dataset is close to a census of studies accessible through the API at a fixed snapshot date rather than a random sample.

Large denominators make small effects statistically detectable. The practical interpretation should therefore emphasize the absolute effect size: the NEXUS share increased by about **0.09 percentage points** of the full cohort. The direction is consistent under both planned denominators, but the absolute difference remains modest.

PERMISSIBLE requires particular caution. Its full-cohort share decreased, while its known-location share increased. The Recent 3Y UNKNOWN share is more than twice that of the earlier cohort. This denominator sensitivity prevents a simple, unconditional claim that PERMISSIBLE studies increased or decreased over time.

## 8. Key Findings

1. **NEXUS is modestly higher in Recent 3Y.** The increase is visible using both the all-study and known-location denominators.
2. **Overall US presence is lower.** HAS_US decreased from 27.09% to 23.26% of the cohort.
3. **NEXUS represents a larger share within HAS_US studies.** It increased from approximately 2.14% to 2.88% of HAS_US studies, even though HAS_US itself declined.
4. **US_ONLY declined materially.** Its cohort share fell by approximately 3.03 percentage points.
5. **US_NON_CHINA_MULTI also declined.** The reduction was approximately 0.89 percentage points.
6. **UNKNOWN is the main interpretive constraint.** Its 6.18-point increase materially affects the apparent PERMISSIBLE direction.

## 9. Limitations

- **Registered locations are a proxy.** They represent registered or planned facilities, not participant nationality, actual country-level recruitment, or enrollment volume.
- **Start Date is study-level.** It is not the opening date of each US or China site and is not necessarily confirmed first-patient-in.
- **Missing locations are unlikely to be random.** More recent studies may have incomplete or evolving site information. Restricting to known locations is useful as a sensitivity analysis but can itself introduce selection bias.
- **StartDateType is incomplete.** Many records have a date but no ACTUAL/ESTIMATED label.
- **Registry coverage is selective.** ClinicalTrials.gov does not contain every clinical trial globally, and registration requirements and practices vary by jurisdiction and over time.
- **Study-mix confounding is not controlled.** Differences in study type, phase, therapeutic area, sponsor, status, and intervention profile may contribute to the observed geographic distribution.
- **No causal inference is supported.** The results do not identify why the distribution changed.

## 10. Recommended Use and Next Analyses

The current results are appropriate for a mentor-facing descriptive finding when the denominator and metadata limitations are stated explicitly. Recommended follow-up analyses are:

1. Report the all-cohort result as primary and known-location result as a planned sensitivity analysis.
2. Show annual trends rather than only two pooled periods to determine whether the change is gradual or concentrated in particular years.
3. Stratify by study type, status, phase, therapeutic area, and sponsor type where fields are available.
4. Repeat the comparison using ACTUAL Start Dates only, while reporting the loss of records caused by missing StartDateType.
5. Track UNKNOWN-location coverage by Start Date year to assess registration-lag effects.
6. Avoid interpreting NEXUS as participant-level US–China enrollment without additional enrollment data.

## 11. Conclusion

Among ClinicalTrials.gov studies with registered Start Dates in the respective periods, the proportion with registered facility locations in both the United States and China was modestly higher in Recent 3Y than in 4–6 Years Ago: **0.67% versus 0.58%**, an increase of approximately **0.09 percentage points**. The same direction was present among studies with known location data.

At the same time, US_ONLY, US_NON_CHINA_MULTI, and overall HAS_US shares were lower in Recent 3Y. The substantially higher UNKNOWN-location share in Recent 3Y limits interpretation of the broader geographic distribution and explains why the direction of the PERMISSIBLE comparison changes when the denominator is restricted to known-location studies.

The most defensible conclusion is therefore narrow: **the registered NEXUS share is modestly higher in the recent period, but the analysis is descriptive, the absolute effect is small, and missing recent location metadata materially affects other category comparisons.**

## Reproducibility Metadata

| Item | Value |
|---|---|
| Full snapshot directory | `runs/run_20260720T074104Z` |
| Summary output directory | `runs/run_20260720T074104Z/out_time_summary` |
| Harvest timestamp | 2026-07-20T09:10:25.562858+00:00 |
| Reference date | 2026-07-20 |
| API | ClinicalTrials.gov API v2 |
| Unique NCT denominator | 594,543 |
| Raw hash verification | PASS |
| Cross-format discrepancies | 0 |
| Reconciliation discrepancies | 0 |
| Offline tests | 37/37 PASS |
