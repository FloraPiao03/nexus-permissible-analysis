# Nexus and Permissible ClinicalTrials.gov Analysis

This standalone Python 3.11 repository answers a location-based business question: what proportion of unique ClinicalTrials.gov studies are **NEXUS** or **PERMISSIBLE** under configurable jurisdiction definitions?

ClinicalTrials.gov records registered or planned study facilities. Location metadata is a proxy only: it does **not** confirm participant nationality or actual enrollment by country.

## Denominator and classifications

The primary denominator is all unique study records accessible through the official ClinicalTrials.gov API v2 at the time of a **completed** harvest. No study type, sponsor, status, phase, date, intervention, or therapeutic-area filters are applied. One unique NCT ID is the unit of analysis.

- `NEXUS`: at least one configured United States location and at least one configured China location.
- `PERMISSIBLE`: no configured United States location and at least one usable country.
- `US_ONLY`: at least one configured United States location and no configured China location.
- `UNKNOWN`: no usable location-country metadata.

The baseline definitions are exactly `United States` and `China`. Puerto Rico and other US territories are not automatically US; Hong Kong, Macau/Macao, and Taiwan are not automatically China. All definitions live in `config.json`.

The four buckets are mutually exclusive and exhaustive. Missing location data is never Permissible. Percentages among studies with known locations are reported only as secondary metrics.

## Setup and quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python selftest.py

python harvest.py --outdir runs --limit-pages 3
python analyze.py --run runs/run_<smoke-test-timestamp>

python harvest.py --outdir runs
python analyze.py --run runs/run_<full-run-timestamp>
```

Do not cite limited-page output as a final result. It is visibly marked `PARTIAL_NON_FINAL_SMOKE_TEST` throughout the generated reports. A snapshot is complete only when pagination ends with no next-page token; no expected study count is hard-coded.

## Workflow

`harvest.py` requests only the required API v2 fields, uses configurable page size, timeout, User-Agent, exponential-backoff retries for network errors, HTTP 429 and 5xx responses, and follows every next-page token. Raw page JSON files are written to a timestamped directory. The manifest records parameters, counts, completeness, duplicates, and SHA-256 hashes. Failed harvests receive `HARVEST_FAILED.txt` and are not analyzable as valid snapshots.

`analyze.py` verifies the manifest, every raw-file hash, raw and unique counts, and then deduplicates by NCT ID (first observed record wins deterministically). It retains study type and status as metadata without filtering. It writes:

- `summary.md` and `summary.json`
- `trials.csv` (one row per unique NCT ID)
- `locations_long.csv` (one row per registered facility/location)
- `country_counts.csv` and `country_vocabulary.csv`
- `nexus_permissible_results.xlsx` with the seven required worksheets

Outputs are placed in `runs/run_<timestamp>/out/`. The entire `runs/` tree is gitignored, so generated API data and reports are not committed.

## Validation

Hard checks cover NCT IDs, duplicate reporting, raw-file hashes and counts, bucket exhaustiveness, category invariants, correct denominators, and Excel/JSON count agreement. A missing or unverifiable manifest is rejected. Partial snapshots may be analyzed for smoke testing but are explicitly non-final in Markdown, JSON, and Excel.

Run structured offline tests with either:

```bash
python selftest.py
python -m unittest discover -v
```

Synthetic cases manually specify expected results for US+China, US only, China only, European locations, missing locations, Puerto Rico, Hong Kong, Taiwan, duplicate NCT IDs, and both observational and interventional studies.

## Known limitations

- Registry facilities may be planned, incomplete, stale, or missing.
- Country strings are interpreted exactly according to `config.json`; inspect `country_vocabulary.csv` after each run.
- A run is a time-specific API snapshot and may differ from later runs.
- Facility location is not participant nationality and does not prove country-level recruitment or enrollment.
- Deduplication keeps the first byte-verified occurrence of an NCT ID and reports duplicates for review.
