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


def style_sheet(ws, freeze="A2", filter_range=None):
    ws.sheet_view.showGridLines = False
    if freeze:
        ws.freeze_panes = freeze
    if filter_range:
        ws.auto_filter.ref = filter_range
    fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(wrap_text=True)
    for column in ws.columns:
        values = [len(str(c.value)) for c in column[:200] if c.value is not None]
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(max(values or [8]) + 2, 45)


def make_workbook(path: Path, summary: dict, trials: list[dict], locations: list[dict], country_rows: list[dict], cfg: dict, manifest: dict):
    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Executive_Summary")
    ws.append(["Nexus & Permissible Study Location Analysis", "Value"])
    ws.append(["Result status", summary["result_status"]])
    ws.append(["Denominator", "All unique study records accessible through the ClinicalTrials.gov API in this completed snapshot."])
    ws.append(["Snapshot applicability", "Completed all-study snapshot; primary denominator applies." if summary["snapshot_complete"] else "PARTIAL smoke-test snapshot; the target denominator above is not satisfied and these results are not final."])
    ws.append(["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."])
    ws.append(["Total unique studies", summary["total_studies"]])
    for b in BUCKETS:
        ws.append([f"{b} count", summary["buckets"][b]["count"]])
        ws.append([f"{b} % (primary all-study denominator)", summary["buckets"][b]["percentage"]])
        ws.cell(ws.max_row, 2).number_format = "0.00%"
    ws.append(["Known-location studies", summary["known_location_studies"]])
    ws.append(["Nexus % among known locations (secondary)", summary["secondary_known_location"]["nexus_percentage"]])
    ws.cell(ws.max_row, 2).number_format = "0.00%"
    ws.append(["Permissible % among known locations (secondary)", summary["secondary_known_location"]["permissible_percentage"]])
    ws.cell(ws.max_row, 2).number_format = "0.00%"
    style_sheet(ws, freeze="A2")
    ws.column_dimensions["A"].width = 50; ws.column_dimensions["B"].width = 95
    for row in range(2, ws.max_row + 1): ws.cell(row, 2).alignment = Alignment(wrap_text=True, vertical="top")

    cs = wb.create_sheet("Classification_Summary")
    cs.append(["bucket", "count", "percentage_total", "percentage_known_locations", "denominator_type"])
    for b in BUCKETS:
        known_pct = pct(summary["buckets"][b]["count"], summary["known_location_studies"]) if b != "UNKNOWN" else None
        cs.append([b, summary["buckets"][b]["count"], summary["buckets"][b]["percentage"], known_pct,
                   "primary: all studies; known-location is secondary"])
    for row in cs.iter_rows(min_row=2, min_col=3, max_col=4):
        for cell in row: cell.number_format = "0.00%"
    style_sheet(cs, filter_range=f"A1:E{cs.max_row}")

    for name, fields, rows in [("Study_Detail", TRIAL_FIELDS, trials), ("Country_Counts", list(country_rows[0]) if country_rows else ["country", "unique_study_count", "percentage_total", "percentage_known_locations"], country_rows), ("Locations", LOCATION_FIELDS, locations)]:
        sh = wb.create_sheet(name); sh.append(fields)
        for row in rows: sh.append([row.get(f) for f in fields])
        if name == "Country_Counts":
            for cells in sh.iter_rows(min_row=2, min_col=3, max_col=4):
                for cell in cells: cell.number_format = "0.00%"
        style_sheet(sh, filter_range=f"A1:{get_column_letter(len(fields))}{max(1, sh.max_row)}")

    defs = wb.create_sheet("Definitions")
    defs.append(["Item", "Definition"])
    defs.append(["Unit of analysis", "One unique NCT ID"])
    defs.append(["NEXUS", "At least one registered location in configured US and at least one in configured China"])
    defs.append(["PERMISSIBLE", "No configured US location and at least one usable location country"])
    defs.append(["US_ONLY", "At least one configured US location and no configured China location"])
    defs.append(["UNKNOWN", "No usable location-country metadata"])
    defs.append(["US values", ", ".join(cfg["us_countries"])])
    defs.append(["China values", ", ".join(cfg["china_countries"])])
    defs.append(["Location interpretation", "Registered or planned study facilities, not confirmed participant nationality or actual country-level enrollment."])
    style_sheet(defs); defs.column_dimensions["B"].width = 100

    meta = wb.create_sheet("Run_Metadata"); meta.append(["Key", "Value"])
    for key, value in manifest.items():
        meta.append([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])
    style_sheet(meta); meta.column_dimensions["B"].width = 100
    wb.save(path)


def verify_workbook(path: Path, summary: dict):
    wb = load_workbook(path, data_only=False, read_only=True)
    required = ["Executive_Summary", "Classification_Summary", "Study_Detail", "Country_Counts", "Locations", "Definitions", "Run_Metadata"]
    if wb.sheetnames != required:
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
    make_workbook(workbook_path, summary, trials, locations, country_rows, cfg, manifest)
    verify_workbook(workbook_path, summary)
    print(out)
    return 0


if __name__ == "__main__": raise SystemExit(main())
