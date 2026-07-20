#!/usr/bin/env python3
"""Analyze an auditable ClinicalTrials.gov harvest snapshot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

BUCKETS = ("NEXUS", "PERMISSIBLE", "US_ONLY", "US_NON_CHINA_MULTI", "UNKNOWN")
TRIAL_FIELDS = ["nct_id", "brief_title", "study_type", "overall_status", "countries_pipe", "country_count",
                "has_location_data", "has_us", "has_china", "bucket", "us_presence_group", "has_hong_kong", "has_macau",
                "has_taiwan", "has_us_territory"]
LOCATION_FIELDS = ["nct_id", "location_number", "facility", "city", "state", "postal_code", "country"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify(countries: Iterable[str], cfg: dict) -> tuple[str, dict]:
    """Apply the version-2 hierarchy: UNKNOWN, PERMISSIBLE, US_ONLY, NEXUS, then US_NON_CHINA_MULTI."""
    values = {c.strip() for c in countries if isinstance(c, str) and c.strip()}
    has_us = bool(values & set(cfg["us_countries"]))
    has_china = bool(values & set(cfg["china_countries"]))
    if not values:
        bucket = "UNKNOWN"
        us_presence_group = "UNKNOWN"
    elif not has_us:
        bucket = "PERMISSIBLE"
        us_presence_group = "NO_US"
    elif values == set(cfg["us_countries"]):
        bucket = "US_ONLY"
        us_presence_group = "HAS_US"
    elif has_china:
        bucket = "NEXUS"
        us_presence_group = "HAS_US"
    else:
        bucket = "US_NON_CHINA_MULTI"
        us_presence_group = "HAS_US"
    tracked = cfg["tracked_separately"]
    return bucket, {
        "has_location_data": bool(values), "has_us": has_us, "has_china": has_china,
        "us_presence_group": us_presence_group,
        "has_hong_kong": bool(values & set(tracked["hong_kong"])),
        "has_macau": bool(values & set(tracked["macau"])),
        "has_taiwan": bool(values & set(tracked["taiwan"])),
        "has_us_territory": bool(values & set(tracked["us_territories"])),
    }


def extract(study: dict, cfg: dict) -> tuple[dict, list[dict]]:
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    design = protocol.get("designModule", {})
    status = protocol.get("statusModule", {})
    contacts = protocol.get("contactsLocationsModule", {})
    nct = ident.get("nctId")
    if not isinstance(nct, str) or not nct.strip():
        raise ValueError("Every retained record must have a non-empty NCT ID")
    locations = []
    countries = set()
    for number, loc in enumerate(contacts.get("locations") or [], 1):
        country = loc.get("country")
        if isinstance(country, str) and country.strip():
            countries.add(country.strip())
        locations.append({"nct_id": nct, "location_number": number, "facility": loc.get("facility", ""),
                          "city": loc.get("city", ""), "state": loc.get("state", ""),
                          "postal_code": loc.get("zip", ""), "country": country or ""})
    bucket, flags = classify(countries, cfg)
    row = {"nct_id": nct, "brief_title": ident.get("briefTitle", ""), "study_type": design.get("studyType", ""),
           "overall_status": status.get("overallStatus", ""), "countries_pipe": "|".join(sorted(countries)),
           "country_count": len(countries), **flags, "bucket": bucket}
    return row, locations


def pct(n: int, d: int) -> float | None:
    return n / d if d else None


def write_csv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare_stream_sheet(ws, headers: list[str], widths: list[int] | None = None):
    """Prepare a write-only worksheet with a styled, frozen, filterable header."""
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
    cells = []
    for value in headers:
        cell = WriteOnlyCell(ws, value=value)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(wrap_text=True)
        cells.append(cell)
    ws.append(cells)
    for index, width in enumerate(widths or [18] * len(headers), 1):
        ws.column_dimensions[get_column_letter(index)].width = width


def append_values(ws, values, percentage_columns=()):
    cells = []
    for index, value in enumerate(values, 1):
        cell = WriteOnlyCell(ws, value=value)
        if index in percentage_columns:
            cell.number_format = "0.00%"
        cells.append(cell)
    ws.append(cells)


def make_workbook(path: Path, summary: dict, trials: list[dict], locations: list[dict], country_rows: list[dict], cfg: dict, manifest: dict, location_rows_per_sheet: int = 500_000):
    if not 1 <= location_rows_per_sheet <= 1_048_575:
        raise ValueError("location_rows_per_sheet must leave room for the Excel header row")
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Executive_Summary")
    prepare_stream_sheet(ws, ["Nexus & Permissible Study Location Analysis — Five-Category Model", "Value"], [58, 95])
    append_values(ws, ["Result status", summary["result_status"]])
    append_values(ws, ["Denominator", "All unique study records accessible through the ClinicalTrials.gov API in this completed snapshot."])
    append_values(ws, ["Snapshot applicability", "Completed all-study snapshot; primary denominator applies." if summary["snapshot_complete"] else "PARTIAL smoke-test snapshot; the target denominator above is not satisfied and these results are not final."])
    append_values(ws, ["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."])
    append_values(ws, ["OVERALL POPULATION", None])
    append_values(ws, ["Total unique studies", summary["total_studies"]])
    append_values(ws, ["Known-location studies", summary["known_location_studies"]])
    append_values(ws, ["Unknown-location studies", summary["buckets"]["UNKNOWN"]["count"]])
    append_values(ws, ["HIGH-LEVEL GEOGRAPHIC SPLIT", None])
    append_values(ws, ["NO_US / PERMISSIBLE count", summary["us_presence_groups"]["NO_US"]["count"]])
    append_values(ws, ["NO_US / PERMISSIBLE % of all studies", summary["us_presence_groups"]["NO_US"]["percentage_total"]], (2,))
    append_values(ws, ["NO_US / PERMISSIBLE % of known-location studies", summary["us_presence_groups"]["NO_US"]["percentage_known_locations"]], (2,))
    append_values(ws, ["HAS_US count", summary["us_presence_groups"]["HAS_US"]["count"]])
    append_values(ws, ["HAS_US % of all studies", summary["us_presence_groups"]["HAS_US"]["percentage_total"]], (2,))
    append_values(ws, ["HAS_US % of known-location studies", summary["us_presence_groups"]["HAS_US"]["percentage_known_locations"]], (2,))
    append_values(ws, ["BREAKDOWN OF HAS_US STUDIES", None])
    for b in ("US_ONLY", "US_NON_CHINA_MULTI", "NEXUS"):
        append_values(ws, [f"{b} count", summary["buckets"][b]["count"]])
        append_values(ws, [f"{b} % of all studies", summary["buckets"][b]["percentage_total"]], (2,))
        append_values(ws, [f"{b} % of known-location studies", summary["buckets"][b]["percentage_known_locations"]], (2,))
        append_values(ws, [f"{b} % of HAS_US studies", summary["buckets"][b]["percentage_has_us"]], (2,))

    cs = wb.create_sheet("Classification_Summary")
    prepare_stream_sheet(cs, ["bucket", "count", "percentage_total", "percentage_known_locations", "percentage_has_us", "denominator_notes"], [24, 14, 20, 27, 22, 55])
    for b in BUCKETS:
        item = summary["buckets"][b]
        append_values(cs, [b, item["count"], item["percentage_total"], item["percentage_known_locations"], item["percentage_has_us"],
                           "Primary: all studies; known-location and HAS_US percentages are secondary diagnostics"], (3, 4, 5))

    detail = wb.create_sheet("Study_Detail")
    prepare_stream_sheet(detail, TRIAL_FIELDS, [16, 45, 18, 20, 45, 14, 18, 12, 14, 24, 20, 18, 14, 14, 20])
    for row in trials:
        append_values(detail, [row.get(f) for f in TRIAL_FIELDS])

    countries = wb.create_sheet("Country_Counts")
    country_fields = ["country", "unique_study_count", "percentage_total", "percentage_known_locations"]
    prepare_stream_sheet(countries, country_fields, [30, 22, 22, 30])
    for row in country_rows:
        append_values(countries, [row.get(f) for f in country_fields], (3, 4))

    location_sheet = None
    location_sheet_number = 0
    rows_in_sheet = 0
    for row in locations:
        if location_sheet is None or rows_in_sheet >= location_rows_per_sheet:
            location_sheet_number += 1
            name = "Locations" if location_sheet_number == 1 else f"Locations_{location_sheet_number:03d}"
            location_sheet = wb.create_sheet(name)
            prepare_stream_sheet(location_sheet, LOCATION_FIELDS, [16, 16, 45, 24, 24, 18, 28])
            rows_in_sheet = 0
        append_values(location_sheet, [row.get(f) for f in LOCATION_FIELDS])
        rows_in_sheet += 1
    if location_sheet is None:
        location_sheet = wb.create_sheet("Locations")
        prepare_stream_sheet(location_sheet, LOCATION_FIELDS, [16, 16, 45, 24, 24, 18, 28])

    defs = wb.create_sheet("Definitions")
    prepare_stream_sheet(defs, ["Item", "Definition"], [28, 100])
    for row in [["Classification model", "Version 2 — five mutually exclusive categories"], ["Unit of analysis", "One unique NCT ID"], ["UNKNOWN", "No usable registered location-country value"], ["PERMISSIBLE", "At least one usable country and no configured US country value"], ["US_ONLY", "The complete unique country set is exactly the configured US set: United States only"], ["US_NON_CHINA_MULTI", "Contains United States, does not contain China, and contains at least one additional non-US country"], ["NEXUS", "Contains at least one United States location and at least one China location; other countries may also be present"], ["NO_US", "High-level group equal to PERMISSIBLE for known-location studies"], ["HAS_US", "High-level group equal to US_ONLY + US_NON_CHINA_MULTI + NEXUS"], ["US values", ", ".join(cfg["us_countries"])], ["China values", ", ".join(cfg["china_countries"])], ["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."]]:
        append_values(defs, row)

    meta = wb.create_sheet("Run_Metadata"); prepare_stream_sheet(meta, ["Key", "Value"], [35, 100])
    for key, value in manifest.items():
        append_values(meta, [key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])
    wb.save(path)


def verify_workbook(path: Path, summary: dict):
    wb = load_workbook(path, data_only=False, read_only=True)
    fixed = ["Executive_Summary", "Classification_Summary", "Study_Detail", "Country_Counts"]
    location_sheets = [name for name in wb.sheetnames if name == "Locations" or name.startswith("Locations_")]
    required_tail = ["Definitions", "Run_Metadata"]
    if wb.sheetnames[:4] != fixed or not location_sheets or wb.sheetnames[-2:] != required_tail:
        raise AssertionError(f"Unexpected workbook sheets: {wb.sheetnames}")
    values = {row[0].value: row[1].value for row in wb["Executive_Summary"].iter_rows(min_row=2) if len(row) >= 2}
    if values["Total unique studies"] != summary["total_studies"]:
        raise AssertionError("Excel total does not match summary.json")
    classification = {row[0].value: row[1].value for row in wb["Classification_Summary"].iter_rows(min_row=2)}
    for bucket in BUCKETS:
        if classification.get(bucket) != summary["buckets"][bucket]["count"]:
            raise AssertionError(f"Excel {bucket} count does not match summary.json")
    if values["HAS_US count"] != summary["us_presence_groups"]["HAS_US"]["count"]:
        raise AssertionError("Excel HAS_US count does not match summary.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--output-name", default="out_v2", help="Versioned output directory name under the selected run")
    args = parser.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    manifest_path = args.run / "manifest.json"
    if not manifest_path.exists():
        parser.error("selected run has no manifest.json (counts-only or failed runs are rejected)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("files") or not isinstance(manifest.get("snapshot_complete"), bool):
        parser.error("manifest is not a verifiable raw snapshot")
    studies_by_id = {}
    duplicate_ids = Counter()
    for entry in manifest["files"]:
        path = args.run / entry["path"]
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise RuntimeError(f"Raw-file hash verification failed: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for study in payload.get("studies", []):
            nct = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
            if not nct: raise ValueError("Every retained record must have an NCT ID")
            if nct in studies_by_id: duplicate_ids[nct] += 1
            else: studies_by_id[nct] = study
    if sum(e["study_count"] for e in manifest["files"]) != manifest["raw_study_count"]:
        raise RuntimeError("Partial-download detection failed: manifest raw count disagrees with page files")
    if len(studies_by_id) != manifest["unique_nct_count"]:
        raise RuntimeError("Unique NCT count disagrees with manifest")
    trials, locations = [], []
    for nct in sorted(studies_by_id):
        row, locs = extract(studies_by_id[nct], cfg); trials.append(row); locations.extend(locs)
    counts = Counter(r["bucket"] for r in trials); total = len(trials); known = total - counts["UNKNOWN"]
    has_us_count = counts["US_ONLY"] + counts["US_NON_CHINA_MULTI"] + counts["NEXUS"]
    if sum(counts[b] for b in BUCKETS) != total: raise AssertionError("Buckets do not sum to denominator")
    for r in trials:
        b = r["bucket"]
        countries = set(filter(None, r["countries_pipe"].split("|")))
        if b == "NEXUS" and not (r["has_us"] and r["has_china"]): raise AssertionError("Invalid NEXUS")
        if b == "US_ONLY" and countries != set(cfg["us_countries"]): raise AssertionError("Invalid US_ONLY")
        if b == "US_NON_CHINA_MULTI" and not (r["has_us"] and not r["has_china"] and len(countries) > 1): raise AssertionError("Invalid US_NON_CHINA_MULTI")
        if b == "PERMISSIBLE" and not (r["has_location_data"] and not r["has_us"]): raise AssertionError("Invalid PERMISSIBLE")
        if b == "UNKNOWN" and r["has_location_data"]: raise AssertionError("Invalid UNKNOWN")
        expected_group = "UNKNOWN" if b == "UNKNOWN" else "NO_US" if b == "PERMISSIBLE" else "HAS_US"
        if r["us_presence_group"] != expected_group: raise AssertionError("Invalid us_presence_group")
    if counts["PERMISSIBLE"] + has_us_count != known: raise AssertionError("NO_US + HAS_US does not equal known-location studies")
    if has_us_count != sum(r["has_us"] for r in trials): raise AssertionError("HAS_US reconciliation failed")
    bucket_items = {}
    for b in BUCKETS:
        bucket_items[b] = {
            "count": counts[b],
            "percentage_total": pct(counts[b], total),
            "percentage_known_locations": pct(counts[b], known) if b != "UNKNOWN" else None,
            "percentage_has_us": pct(counts[b], has_us_count) if b in {"US_ONLY", "US_NON_CHINA_MULTI", "NEXUS"} else None,
        }
    summary = {
        "result_status": "FINAL_COMPLETE_SNAPSHOT" if manifest["snapshot_complete"] else "PARTIAL_NON_FINAL_SMOKE_TEST",
        "snapshot_complete": manifest["snapshot_complete"], "harvest_timestamp_utc": manifest["harvest_timestamp_utc"],
        "classification_model_version": 2,
        "unit_of_analysis": "one unique NCT ID", "total_studies": total, "known_location_studies": known,
        "unknown_location_studies": counts["UNKNOWN"], "buckets": bucket_items,
        "us_presence_groups": {
            "UNKNOWN": {"count": counts["UNKNOWN"], "percentage_total": pct(counts["UNKNOWN"], total), "percentage_known_locations": None},
            "NO_US": {"count": counts["PERMISSIBLE"], "percentage_total": pct(counts["PERMISSIBLE"], total), "percentage_known_locations": pct(counts["PERMISSIBLE"], known)},
            "HAS_US": {"count": has_us_count, "percentage_total": pct(has_us_count, total), "percentage_known_locations": pct(has_us_count, known)},
        },
        "reconciliation_checks": {
            "five_buckets_equal_total": sum(counts[b] for b in BUCKETS) == total,
            "no_us_plus_has_us_equal_known": counts["PERMISSIBLE"] + has_us_count == known,
            "us_subcategories_equal_has_us": counts["US_ONLY"] + counts["US_NON_CHINA_MULTI"] + counts["NEXUS"] == has_us_count,
        },
        "secondary_known_location": {"denominator": known, "nexus_percentage": pct(counts["NEXUS"], known),
                                     "permissible_percentage": pct(counts["PERMISSIBLE"], known)},
        "definitions": {"us_countries": cfg["us_countries"], "china_countries": cfg["china_countries"],
                        "tracked_separately": cfg["tracked_separately"]},
        "duplicate_nct_ids_detected": dict(duplicate_ids),
        "location_proxy_limitation": "ClinicalTrials.gov locations are registered or planned facilities; they do not confirm participant nationality or actual enrollment by country."
    }
    countries_to_ids = defaultdict(set)
    for r in trials:
        for country in filter(None, r["countries_pipe"].split("|")): countries_to_ids[country].add(r["nct_id"])
    country_rows = [{"country": c, "unique_study_count": len(ids), "percentage_total": pct(len(ids), total),
                     "percentage_known_locations": pct(len(ids), known)} for c, ids in sorted(countries_to_ids.items(), key=lambda x: (-len(x[1]), x[0]))]
    out = args.run / args.output_name
    if out.exists() and any(out.iterdir()):
        parser.error(f"output directory already exists and is not empty: {out}")
    out.mkdir(exist_ok=True)
    write_csv(out / "trials.csv", TRIAL_FIELDS, trials)
    write_csv(out / "locations_long.csv", LOCATION_FIELDS, locations)
    write_csv(out / "country_counts.csv", ["country", "unique_study_count", "percentage_total", "percentage_known_locations"], country_rows)
    write_csv(out / "country_vocabulary.csv", ["country"], ({"country": c} for c in sorted(countries_to_ids)))
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    label = "FINAL — COMPLETE SNAPSHOT" if manifest["snapshot_complete"] else "PARTIAL / NON-FINAL SMOKE TEST"
    fmt = lambda v: "N/A" if v is None else f"{v:.2%}"
    lines = [f"# Nexus and Permissible Analysis — Five-Category Model — {label}", "", "## Overall population", "",
             f"- Total studies: **{total:,}**", f"- Known-location studies: **{known:,}**", f"- UNKNOWN: **{counts['UNKNOWN']:,} ({fmt(pct(counts['UNKNOWN'], total))} of all studies)**", "",
             "## High-level geographic split", "", f"- NO_US / PERMISSIBLE: **{counts['PERMISSIBLE']:,} ({fmt(pct(counts['PERMISSIBLE'], total))} of all; {fmt(pct(counts['PERMISSIBLE'], known))} of known-location)**",
             f"- HAS_US: **{has_us_count:,} ({fmt(pct(has_us_count, total))} of all; {fmt(pct(has_us_count, known))} of known-location)**", "",
             "## Breakdown of HAS_US studies", "",
             f"- US_ONLY: **{counts['US_ONLY']:,} ({fmt(pct(counts['US_ONLY'], total))} of all; {fmt(pct(counts['US_ONLY'], known))} of known-location; {fmt(pct(counts['US_ONLY'], has_us_count))} of HAS_US)**",
             f"- US_NON_CHINA_MULTI: **{counts['US_NON_CHINA_MULTI']:,} ({fmt(pct(counts['US_NON_CHINA_MULTI'], total))} of all; {fmt(pct(counts['US_NON_CHINA_MULTI'], known))} of known-location; {fmt(pct(counts['US_NON_CHINA_MULTI'], has_us_count))} of HAS_US)**",
             f"- NEXUS: **{counts['NEXUS']:,} ({fmt(pct(counts['NEXUS'], total))} of all; {fmt(pct(counts['NEXUS'], known))} of known-location; {fmt(pct(counts['NEXUS'], has_us_count))} of HAS_US)**", "",
             "## Reconciliation checks", "", f"- Five buckets equal total: **{sum(counts[b] for b in BUCKETS):,} = {total:,}**",
             f"- PERMISSIBLE + HAS_US = known-location: **{counts['PERMISSIBLE']:,} + {has_us_count:,} = {known:,}**",
             f"- US_ONLY + US_NON_CHINA_MULTI + NEXUS = HAS_US: **{counts['US_ONLY']:,} + {counts['US_NON_CHINA_MULTI']:,} + {counts['NEXUS']:,} = {has_us_count:,}**", "", "## Definitions and limitations", "",
             "- US_ONLY means the complete unique country set is exactly {United States}.",
             "- US_NON_CHINA_MULTI contains United States plus at least one other non-China country.",
             "- NEXUS contains both United States and China and may contain other countries.",
             "- PERMISSIBLE has a known country set with no United States; NEXUS and PERMISSIBLE alone do not partition the registry.",
             f"- US definition: {', '.join(cfg['us_countries'])}", f"- China definition: {', '.join(cfg['china_countries'])}",
             "- Unit of analysis: one unique NCT ID", f"- Harvest timestamp: {manifest['harvest_timestamp_utc']}",
             "- Denominator: all unique accessible API studies only when the snapshot is complete." if manifest["snapshot_complete"] else "- This page-limited snapshot is not the all-study denominator and must not be reported as final.",
             "- Location-proxy limitation: registered or planned facilities do not confirm participant nationality or actual country-level enrollment."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    workbook_path = out / "nexus_permissible_results.xlsx"
    make_workbook(workbook_path, summary, trials, locations, country_rows, cfg, manifest,
                  location_rows_per_sheet=cfg.get("excel_location_rows_per_sheet", 500_000))
    verify_workbook(workbook_path, summary)
    print(out)
    return 0


if __name__ == "__main__": raise SystemExit(main())
