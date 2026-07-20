# Nexus / Permissible ClinicalTrials.gov Analysis — Handover

## 1. Purpose

This repository uses the official ClinicalTrials.gov API v2 to calculate the proportions of `NEXUS` and `PERMISSIBLE` studies from registered or planned facility-country metadata.

This is a **location-proxy analysis**, not a participant analysis. A ClinicalTrials.gov location does not establish:

- participant nationality;
- actual enrollment by country;
- whether a planned facility was activated;
- whether recruitment occurred as registered.

## 2. Core business definitions

### 2.1 Unit of analysis

One unique NCT ID is one analytical unit. A study with multiple facilities appears only once in the study denominator.

### 2.2 Primary denominator

The primary denominator is:

> All unique study records accessible through the ClinicalTrials.gov API in the completed snapshot.

No filtering is applied for study type, sponsor, status, phase, date, intervention, or therapeutic area.

### 2.3 Country definitions

- US means the exact string `United States` only.
- China means the exact string `China` only.
- Puerto Rico, Guam, and other US territories are not automatically treated as US.
- Hong Kong, Macau/Macao, and Taiwan are not automatically treated as China.
- Definitions are centralized in `config.json`.

### 2.4 Five mutually exclusive buckets

| Bucket | Definition |
|---|---|
| `UNKNOWN` | No usable location-country value |
| `PERMISSIBLE` | No `United States`, with at least one usable country |
| `US_ONLY` | The complete unique country set is exactly `{United States}` |
| `US_NON_CHINA_MULTI` | Contains `United States`, no `China`, and at least one additional non-US country |
| `NEXUS` | Contains both `United States` and `China`; other countries may also be present |

The buckets must be mutually exclusive and exhaustive:

```text
UNKNOWN + PERMISSIBLE + US_ONLY + US_NON_CHINA_MULTI + NEXUS = total denominator
```

A study with missing country metadata must be `UNKNOWN`, never `PERMISSIBLE`.

```text
All studies
│
├── UNKNOWN
│
└── Known-location studies
    │
    ├── NO_US
    │   └── PERMISSIBLE
    │
    └── HAS_US
        ├── US_ONLY
        ├── US_NON_CHINA_MULTI
        └── NEXUS
```

NEXUS and PERMISSIBLE alone do not partition the registry. Known-location studies satisfy `PERMISSIBLE + HAS_US = known-location`; HAS_US is then divided into three subcategories.

## 3. Repository layout

```text
nexus-permissible-analysis/
├── README.md
├── HANDOVER_ZH.md
├── HANDOVER_EN.md
├── requirements.txt
├── config.json
├── harvest.py
├── analyze.py
├── selftest.py
├── tests/
└── runs/                  # generated data; gitignored by default
```

The intended runtime is Python 3.11 with `openpyxl>=3.1,<4`. The available local interpreter used for execution was Python 3.13.12, but the code uses Python 3.11-compatible syntax.

## 4. Configuration

`config.json` contains:

- API endpoint;
- User-Agent;
- page size;
- timeout and retry settings;
- exact US and China values;
- separately tracked Hong Kong, Macau/Macao, Taiwan, and US territories;
- Excel location-sheet size, defaulting to 500,000 data rows per sheet.

Replace the placeholder User-Agent email with the actual maintainer contact before long-term operation.

## 5. Harvest workflow: `harvest.py`

### 5.1 Requested fields

The API request is deliberately restricted to:

```text
NCTId
BriefTitle
StudyType
OverallStatus
LocationFacility
LocationCity
LocationState
LocationZip
LocationCountry
```

These are trimmed API responses, not complete study records. Participant data, detailed results, adverse events, and full protocols are not downloaded.

### 5.2 Pagination and reliability

The harvester:

1. calls `https://clinicaltrials.gov/api/v2/studies`;
2. requests 1,000 studies per page by default;
3. immediately writes each page to `raw/page_XXXXXX.json`;
4. follows each `nextPageToken`;
5. retries network errors, HTTP 429, and 5xx responses with exponential backoff;
6. uses a timeout and configurable User-Agent;
7. detects missing and duplicate NCT IDs;
8. marks a snapshot complete only when no next-page token remains.

The full dataset is not retained in memory during harvest; pages are downloaded and persisted one at a time.

### 5.3 Manifest

After a successful harvest, `manifest.json` records:

- UTC harvest timestamp;
- endpoint and request parameters;
- page count;
- raw and unique study counts;
- duplicate count;
- `snapshot_complete`;
- whether a next-page token remains;
- SHA-256 and study count for every raw page.

A failed harvest receives `HARVEST_FAILED.txt` and must not be treated as a complete snapshot.

### 5.4 Smoke and full runs

Three-page smoke test:

```bash
.venv/bin/python harvest.py --outdir runs --limit-pages 3
```

This validates API access, pagination, and outputs. It is not a final business result. If a token remains after page three, the manifest is explicitly incomplete.

Full run:

```bash
.venv/bin/python harvest.py --outdir runs
```

Never hard-code an expected study total; ClinicalTrials.gov changes continuously.

## 6. Analysis workflow: `analyze.py`

### 6.1 Input validation

The analyzer requires a valid run manifest and verifies:

- existence of every raw file;
- every SHA-256 hash;
- raw count against the manifest;
- unique NCT count against the manifest;
- nonblank NCT IDs;
- duplicate NCT IDs.

Partial snapshots may produce technical smoke-test reports, but are marked:

```text
PARTIAL_NON_FINAL_SMOKE_TEST
```

Complete snapshots are marked:

```text
FINAL_COMPLETE_SNAPSHOT
```

### 6.2 Normalization and classification

For each unique NCT ID, the analyzer:

1. reads `protocolSection.contactsLocationsModule.locations`;
2. collects each `country` value;
3. trims whitespace and discards blank strings;
4. forms a unique country set;
5. assigns a bucket using configured US/China values;
6. retains separate Hong Kong, Macau, Taiwan, and US-territory flags;
7. retains study type and overall status as metadata without filtering.

### 6.3 Outputs

Revised five-category files are written to `runs/run_<timestamp>/out_v2/` by default, preserving historical four-category `out/` files:

| File | Purpose |
|---|---|
| `summary.md` | Human-readable report |
| `summary.json` | Machine-readable calculations and definitions |
| `trials.csv` | One row per unique NCT ID |
| `locations_long.csv` | One row per NCT ID × registered facility |
| `country_counts.csv` | Study counts and percentages per observed country |
| `country_vocabulary.csv` | Exact country strings observed from the API |
| `nexus_permissible_results.xlsx` | Business-facing workbook |

### 6.4 Large Excel exports

The completed snapshot contains 3,488,092 location rows, above Excel's 1,048,576-row worksheet limit. The implementation was extended to provide:

- `Workbook(write_only=True)` streaming export;
- automatic `Locations`, `Locations_002`, `Locations_003`, etc. sheets;
- 500,000 data rows per location sheet by default;
- configuration through `excel_location_rows_per_sheet`;
- styled headers, filters, and frozen header rows on each sheet.

The revised workbook has seven location sheets: six with 500,000 data rows and the last with 488,092. `locations_long.csv` remains the complete unsplit machine-readable source.

## 7. Tests and hard validation

Run:

```bash
.venv/bin/python selftest.py
.venv/bin/python -m unittest discover -v
```

The current offline suite passes 6/6 tests and covers:

- US + China → NEXUS;
- US only → US_ONLY;
- US + Canada → US_NON_CHINA_MULTI and explicitly not US_ONLY;
- US + Germany + Japan → US_NON_CHINA_MULTI;
- US + China + Canada → NEXUS;
- China only and Germany + France → PERMISSIBLE;
- no location → UNKNOWN;
- Puerto Rico + China → PERMISSIBLE under baseline rules;
- US + Hong Kong → US_NON_CHINA_MULTI;
- Taiwan + Japan → PERMISSIBLE;
- duplicate NCT IDs counted once;
- observational and interventional studies retained;
- manually specified five-bucket totals, US presence groups, and percentages.

Production hard checks additionally enforce five-bucket exhaustiveness, NO_US/HAS_US reconciliations, category invariants, JSON/Excel agreement, and partial-snapshot labeling.

## 8. Completed run and final results

Completed run:

```text
runs/run_20260716T092516Z
```

Verified manifest state:

```text
snapshot_complete: true
next_page_token_remaining: false
page count: 595
raw study count: 594,066
unique NCT IDs: 594,066
duplicate NCT IDs: 0
missing/hash/count errors: 0
```

Revised five-category results (`out_v2/`):

| Bucket | Count | Percentage of all studies |
|---|---:|---:|
| NEXUS | 2,521 | 0.4243636228971192% (reported as 0.42%) |
| PERMISSIBLE | 340,665 | 57.344638474512934% |
| US_ONLY | 167,656 | 28.221780071574535% |
| US_NON_CHINA_MULTI | 23,369 | 3.933738002174843% |
| UNKNOWN | 59,855 | 10.075479828840567% |
| Total | 594,066 | 100% |

There are 534,211 studies with known locations. Nexus among known-location studies is 0.4719109116060882%; Permissible among known-location studies is approximately 63.77%. These are secondary metrics and do not replace the primary denominator.

The old four-category `US_ONLY=191,025` is corrected into true US_ONLY 167,656 and US_NON_CHINA_MULTI 23,369. NEXUS, PERMISSIBLE, and UNKNOWN are unchanged. HAS_US totals 193,546.

## 9. Independent audit

The historical four-category Nexus result was independently audited on 2026-07-17. After the five-category correction, `audit_v2.py` independently read raw JSON without importing the production classifier and reconciled the revised CSV, JSON, Markdown, and Excel outputs.

### 9.1 Raw-snapshot recomputation

The independent script read all 595 raw pages and classified from only NCT ID and `locations[].country`:

```text
unique raw IDs: 594,066
independent NEXUS: 2,521
independent PERMISSIBLE: 340,665
independent US_ONLY: 167,656
independent US_NON_CHINA_MULTI: 23,369
independent UNKNOWN: 59,855
trials.csv row/group mismatches: 0
summary.json discrepancies: 0
summary.md discrepancies: 0
Excel discrepancies: 0
verdict: PASS
```

### 9.2 Historical four-category row-level sample

The following was the pre-correction Nexus audit sample, not a five-category transition sample. Using deterministic seed `20260717`, it sampled:

- 30 NEXUS;
- 20 PERMISSIBLE;
- 20 US_ONLY;
- 20 UNKNOWN.

All 90 expected buckets matched the historical production output. All 30 sampled NEXUS records explicitly contained both raw strings `United States` and `China`. Full row-level zero-discrepancy validation of the five-category model is performed by `audit_v2.py`.

Temporary evidence is located at:

```text
/private/tmp/nexus_raw_audit.py
/private/tmp/nexus_raw_audit_report.json
/private/tmp/nexus_raw_audit_report.samples.csv
/private/tmp/nexus_api_audit.py
/private/tmp/nexus_api_audit_results.json
```

`/private/tmp` is not durable storage. Move these files into a reviewed, version-controlled `audit/` directory if they must be retained permanently.

### 9.3 Independent API query

On 2026-07-17 the live API returned 594,309 total studies and 2,522 US+China studies. Relative to the 2026-07-16 snapshot, these were increases of 243 and 1. This reflects a changing live registry and does not invalidate the frozen snapshot.

The exact-field query was:

```text
(AREA[LocationCountry]EXPANSION[None]COVERAGE[FullMatch]"United States")
AND
(AREA[LocationCountry]EXPANSION[None]COVERAGE[FullMatch]"China")
```

Do not place both countries inside one `SEARCH[Location](...)` expression: that would require one location object's country field to match both values.

The historical live-API verdict was `VALIDATED WITH MINOR DIFFERENCES`, solely because the next day's live registry had one additional Nexus record. The current frozen-snapshot five-category reconciliation verdict is `PASS`.

### 9.4 Country-string audit

Observed strings plausibly related to US/China were limited to:

| Exact value | Unique NCT IDs | Location rows | Conclusion |
|---|---:|---:|---|
| `United States` | 193,546 | 1,486,005 | baseline canonical US value |
| `China` | 52,324 | 166,635 | baseline canonical mainland-China value |
| `United States Minor Outlying Islands` | 2 | 2 | distinct territory; excluded from US |

The snapshot contains none of `US`, `U.S.`, `USA`, `U.S.A.`, `United States of America`, `the US`, `America`, `PRC`, `P.R.C.`, `People's Republic of China`, `People’s Republic of China`, or `Mainland China`. There are no case, punctuation, or whitespace variants of US or China. One unrelated value, `Bonaire, Saint Eustatius and Saba `, has trailing whitespace, so safe `.strip()` remains appropriate. Exact matching on `United States` and `China` is sufficient for this snapshot.

Durable audit outputs:

```text
runs/run_20260716T092516Z/out_v2/country_string_audit.csv
runs/run_20260716T092516Z/out_v2/reclassification_audit.json
```

## 10. Diagnostic denominators

These are explanatory diagnostics only and do not change the primary denominator:

| Denominator | Count | Nexus | Nexus % |
|---|---:|---:|---:|
| All unique studies | 594,066 | 2,521 | 0.4243636228971192% |
| Studies with known locations | 534,211 | 2,521 | 0.4719109116060882% |
| All interventional studies | 453,297 | 2,377 | 0.5243802628298886% |
| Interventional studies with known locations | 411,859 | 2,377 | 0.5771392636800458% |
| Studies with a China location | 52,324 | 2,521 | 4.818056723492088% |
| Studies with a US or China location | 243,349 | 2,521 | 1.0359606984207868% |

Within HAS_US, US_ONLY is 86.62333502113194%, US_NON_CHINA_MULTI is 12.074132247631054%, and NEXUS is 1.3025327312370187%.

## 11. Git and GitHub state

Current branch:

```text
agent/publish-final-results
```

Publication commit:

```text
e94aef8 Publish verified final analysis results
```

Draft PR:

```text
https://github.com/FloraPiao03/nexus-permissible-analysis/pull/1
```

The Excel file exceeds GitHub's normal 100 MB Git file limit and was therefore published as a Release asset:

```text
https://github.com/FloraPiao03/nexus-permissible-analysis/releases/tag/results-20260716
```

Release workbook SHA-256:

```text
890ae0dc8dfe27a37fcae2bedd696a2f640e74912217db5e8aa41ee31e905700
```

`.venv/`, `__pycache__/`, and most of `runs/` are ignored because they are respectively a machine-specific environment, regenerated bytecode, and large generated data. The PR force-includes the final summary and manifest. The workbook is in the Release; raw pages and large CSV files were not uploaded.

## 12. Common commands

Environment and tests:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python selftest.py
```

Full harvest and analysis:

```bash
python harvest.py --outdir runs
python analyze.py --run runs/run_<timestamp> --output-name out_v2
```

Check manifest completeness:

```bash
python -c 'import json; print(json.load(open("runs/run_<timestamp>/manifest.json"))["snapshot_complete"])'
```

Only a run with `snapshot_complete: true` and no remaining next-page token may be reported as final.

## 13. Maintenance recommendations

1. Review the `agent/publish-final-results` diff before merging the PR.
2. Move the temporary audit scripts into a durable `audit/` directory if repeatable audit evidence is required.
3. Always retain the harvest timestamp; do not equate a later live API count with a prior frozen snapshot.
4. Periodically review API v2 fields, search syntax, and country vocabulary changes.
5. Inspect `country_vocabulary.csv` after each run for renamed or historical country strings.
6. Monitor memory and Excel sheet counts as the registry grows; CSV should remain the complete machine-readable source.
7. Never infer location from sponsor, title, organization, or responsible party.
8. External quotations must include the snapshot date, primary denominator, and location-proxy limitation.

Recommended external wording:

> In the completed ClinicalTrials.gov API snapshot harvested on 2026-07-16, 2,521 of 594,066 unique studies had registered facilities in both the United States and China, representing 0.42% of all studies. Location metadata represents registered or planned facilities, not participant nationality or actual country-level enrollment.
