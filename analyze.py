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

BUCKETS = ("NEXUS", "PERMISSIBLE", "US_ONLY", "UNKNOWN")
TRIAL_FIELDS = ["nct_id", "brief_title", "study_type", "overall_status", "countries_pipe", "country_count",
                "has_location_data", "has_us", "has_china", "bucket", "has_hong_kong", "has_macau",
                "has_taiwan", "has_us_territory"]
LOCATION_FIELDS = ["nct_id", "location_number", "facility", "city", "state", "postal_code", "country"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify(countries: Iterable[str], cfg: dict) -> tuple[str, dict]:
    values = {c.strip() for c in countries if isinstance(c, str) and c.strip()}
    has_us = bool(values & set(cfg["us_countries"]))
    has_china = bool(values & set(cfg["china_countries"]))
    if has_us and has_china:
        bucket = "NEXUS"
    elif has_us:
        bucket = "US_ONLY"
    elif values:
        bucket = "PERMISSIBLE"
    else:
        bucket = "UNKNOWN"
    tracked = cfg["tracked_separately"]
    return bucket, {
        "has_location_data": bool(values), "has_us": has_us, "has_china": has_china,
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
    prepare_stream_sheet(ws, ["Nexus & Permissible Study Location Analysis", "Value"], [50, 95])
    append_values(ws, ["Result status", summary["result_status"]])
    append_values(ws, ["Denominator", "All unique study records accessible through the ClinicalTrials.gov API in this completed snapshot."])
    append_values(ws, ["Snapshot applicability", "Completed all-study snapshot; primary denominator applies." if summary["snapshot_complete"] else "PARTIAL smoke-test snapshot; the target denominator above is not satisfied and these results are not final."])
    append_values(ws, ["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."])
    append_values(ws, ["Total unique studies", summary["total_studies"]])
    for b in BUCKETS:
        append_values(ws, [f"{b} count", summary["buckets"][b]["count"]])
        append_values(ws, [f"{b} % (primary all-study denominator)", summary["buckets"][b]["percentage"]], (2,))
    append_values(ws, ["Known-location studies", summary["known_location_studies"]])
    append_values(ws, ["Nexus % among known locations (secondary)", summary["secondary_known_location"]["nexus_percentage"]], (2,))
    append_values(ws, ["Permissible % among known locations (secondary)", summary["secondary_known_location"]["permissible_percentage"]], (2,))

    cs = wb.create_sheet("Classification_Summary")
    prepare_stream_sheet(cs, ["bucket", "count", "percentage_total", "percentage_known_locations", "denominator_type"], [16, 14, 20, 27, 48])
    for b in BUCKETS:
        known_pct = pct(summary["buckets"][b]["count"], summary["known_location_studies"]) if b != "UNKNOWN" else None
        append_values(cs, [b, summary["buckets"][b]["count"], summary["buckets"][b]["percentage"], known_pct,
                           "primary: all studies; known-location is secondary"], (3, 4))

    detail = wb.create_sheet("Study_Detail")
    prepare_stream_sheet(detail, TRIAL_FIELDS, [16, 45, 18, 20, 45, 14, 18, 12, 14, 16, 18, 14, 14, 20])
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
    for row in [["Unit of analysis", "One unique NCT ID"], ["NEXUS", "At least one registered location in configured US and at least one in configured China"], ["PERMISSIBLE", "No configured US location and at least one usable location country"], ["US_ONLY", "At least one configured US location and no configured China location"], ["UNKNOWN", "No usable location-country metadata"], ["US values", ", ".join(cfg["us_countries"])], ["China values", ", ".join(cfg["china_countries"])], ["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."]]:
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
    values = {row[0].value: row[1].value for row in wb["Executive_Summary"].iter_rows(min_row=2)}
    if values["Total unique studies"] != summary["total_studies"]:
        raise AssertionError("Excel total does not match summary.json")
    for bucket in BUCKETS:
        if values[f"{bucket} count"] != summary["buckets"][bucket]["count"]:
            raise AssertionError(f"Excel {bucket} count does not match summary.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
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
    if sum(counts[b] for b in BUCKETS) != total: raise AssertionError("Buckets do not sum to denominator")
    for r in trials:
        b = r["bucket"]
        if b == "NEXUS" and not (r["has_us"] and r["has_china"]): raise AssertionError("Invalid NEXUS")
        if b == "US_ONLY" and not (r["has_us"] and not r["has_china"]): raise AssertionError("Invalid US_ONLY")
        if b == "PERMISSIBLE" and not (r["has_location_data"] and not r["has_us"]): raise AssertionError("Invalid PERMISSIBLE")
        if b == "UNKNOWN" and r["has_location_data"]: raise AssertionError("Invalid UNKNOWN")
    summary = {
        "result_status": "FINAL_COMPLETE_SNAPSHOT" if manifest["snapshot_complete"] else "PARTIAL_NON_FINAL_SMOKE_TEST",
        "snapshot_complete": manifest["snapshot_complete"], "harvest_timestamp_utc": manifest["harvest_timestamp_utc"],
        "unit_of_analysis": "one unique NCT ID", "total_studies": total, "known_location_studies": known,
        "buckets": {b: {"count": counts[b], "percentage": pct(counts[b], total)} for b in BUCKETS},
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
    out = args.run / "out"; out.mkdir(exist_ok=True)
    write_csv(out / "trials.csv", TRIAL_FIELDS, trials)
    write_csv(out / "locations_long.csv", LOCATION_FIELDS, locations)
    write_csv(out / "country_counts.csv", ["country", "unique_study_count", "percentage_total", "percentage_known_locations"], country_rows)
    write_csv(out / "country_vocabulary.csv", ["country"], ({"country": c} for c in sorted(countries_to_ids)))
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    label = "FINAL — COMPLETE SNAPSHOT" if manifest["snapshot_complete"] else "PARTIAL / NON-FINAL SMOKE TEST"
    fmt = lambda v: "N/A" if v is None else f"{v:.2%}"
    lines = [f"# Nexus and Permissible Analysis — {label}", "", f"- Total denominator in this snapshot: **{total:,} unique NCT IDs**",
             f"- NEXUS: **{counts['NEXUS']:,} ({fmt(pct(counts['NEXUS'], total))})**",
             f"- PERMISSIBLE: **{counts['PERMISSIBLE']:,} ({fmt(pct(counts['PERMISSIBLE'], total))})**",
             f"- US_ONLY: **{counts['US_ONLY']:,} ({fmt(pct(counts['US_ONLY'], total))})**",
             f"- UNKNOWN: **{counts['UNKNOWN']:,} ({fmt(pct(counts['UNKNOWN'], total))})**", "",
             "## Secondary metrics: studies with known locations", "", f"- Known-location studies: **{known:,}**",
             f"- Nexus among known locations: **{fmt(pct(counts['NEXUS'], known))}**",
             f"- Permissible among known locations: **{fmt(pct(counts['PERMISSIBLE'], known))}**", "", "## Definitions and limitations", "",
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
