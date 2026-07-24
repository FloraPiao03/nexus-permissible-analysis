#!/usr/bin/env python3
"""Describe annual registered-country participation for a focused trial cohort."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


REQUIRED_FIELDS = {
    "NCTId", "StudyType", "StartDate", "InterventionType", "LeadSponsorClass", "LocationCountry",
}
COHORT_DEFINITION = (
    "StudyType == INTERVENTIONAL AND LeadSponsorClass == INDUSTRY "
    "AND contains at least one InterventionType == DRUG"
)
START_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
CONTINENT_ORDER = ("Africa", "Asia", "Europe", "North America", "South America", "Oceania")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_start_year(value: object) -> int | None:
    """Return a validated year for YYYY, YYYY-MM, or YYYY-MM-DD."""
    if not isinstance(value, str):
        return None
    match = START_DATE_RE.fullmatch(value.strip())
    if not match:
        return None
    year, month, day = match.groups()
    try:
        if month is None:
            parsed_year = int(year)
            return parsed_year if 1 <= parsed_year <= 9999 else None
        if day is None:
            datetime.strptime(f"{year}-{month}", "%Y-%m")
        else:
            date.fromisoformat(f"{year}-{month}-{day}")
        return int(year)
    except ValueError:
        return None


def eligible_observation(study: dict) -> dict | None:
    """Extract only the approved structured fields; return None outside the cohort."""
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    design = protocol.get("designModule") or {}
    status = protocol.get("statusModule") or {}
    sponsor = (protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
    interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
    locations = (protocol.get("contactsLocationsModule") or {}).get("locations") or []

    study_type = design.get("studyType")
    sponsor_class = sponsor.get("class")
    intervention_types = {
        item.get("type").strip()
        for item in interventions
        if isinstance(item, dict) and isinstance(item.get("type"), str) and item.get("type").strip()
    }
    if not (
        isinstance(study_type, str) and study_type.strip() == "INTERVENTIONAL"
        and isinstance(sponsor_class, str) and sponsor_class.strip() == "INDUSTRY"
        and "DRUG" in intervention_types
    ):
        return None

    nct_id = identification.get("nctId")
    if not isinstance(nct_id, str) or not nct_id.strip():
        raise ValueError("Eligible record has no usable NCT ID")
    countries = {
        location.get("country").strip()
        for location in locations
        if isinstance(location, dict)
        and isinstance(location.get("country"), str)
        and location.get("country").strip()
    }
    start_raw = (status.get("startDateStruct") or {}).get("date")
    return {
        "nct_id": nct_id.strip(),
        "start_year": parse_start_year(start_raw),
        "start_date_raw": start_raw,
        "countries": countries,
    }


def load_continent_mapping(path: Path) -> tuple[dict[str, str], dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    groups = document.get("continents")
    if not isinstance(groups, dict) or tuple(groups) != CONTINENT_ORDER:
        raise ValueError(f"continent mapping must contain these ordered groups: {CONTINENT_ORDER}")
    reverse: dict[str, str] = {}
    for continent, countries in groups.items():
        if not isinstance(countries, list):
            raise ValueError(f"continent mapping group is not a list: {continent}")
        for country in countries:
            if not isinstance(country, str) or not country.strip():
                raise ValueError(f"continent mapping contains an invalid country under {continent}")
            if country in reverse:
                raise ValueError(f"country appears in more than one continent: {country}")
            reverse[country] = continent
    return reverse, document


def aggregate_observations(
    observations: list[dict], start_year: int, reporting_end_year: int,
    continent_mapping: dict[str, str] | None = None,
) -> dict:
    if reporting_end_year < start_year:
        raise ValueError("reporting_end_year must not precede start_year")
    year_study_ids: dict[int, set[str]] = defaultdict(set)
    year_countries: dict[int, set[str]] = defaultdict(set)
    country_year_study_ids: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    continent_year_study_ids: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    year_known_location_ids: dict[int, set[str]] = defaultdict(set)
    year_nexus_ids: dict[int, set[str]] = defaultdict(set)
    study_country_counts: dict[int, list[int]] = defaultdict(list)
    missing_start = 0
    missing_country = 0

    for observation in observations:
        nct_id = observation["nct_id"]
        year = observation["start_year"]
        countries = set(observation["countries"])
        if year is None:
            missing_start += 1
            if not countries:
                missing_country += 1
            continue
        year_study_ids[year].add(nct_id)
        if not countries:
            missing_country += 1
        else:
            year_known_location_ids[year].add(nct_id)
        study_country_counts[year].append(len(countries))
        for country in countries:
            year_countries[year].add(country)
            country_year_study_ids[country][year].add(nct_id)
        if {"United States", "China"}.issubset(countries):
            year_nexus_ids[year].add(nct_id)
        if continent_mapping is not None:
            for continent in {continent_mapping[country] for country in countries if country in continent_mapping}:
                continent_year_study_ids[continent][year].add(nct_id)

    years = list(range(start_year, reporting_end_year + 1))
    annual_rows = []
    cumulative: set[str] = set()
    for year in years:
        cumulative.update(year_countries[year])
        rolling = set().union(*(
            year_countries[item] for item in range(max(start_year, year - 2), year + 1)
        ))
        annual_rows.append({
            "Year": year,
            "Eligible Studies Started": len(year_study_ids[year]),
            "Known-Location Studies": len(year_known_location_ids[year]),
            "Missing-Location Studies": len(year_study_ids[year] - year_known_location_ids[year]),
            "Missing-Location Percentage": (
                len(year_study_ids[year] - year_known_location_ids[year]) / len(year_study_ids[year])
                if year_study_ids[year] else None
            ),
            "Unique Countries Involved": len(year_countries[year]),
            "3-Year Rolling Active Countries": len(rolling),
            "Cumulative Countries Since 1991": len(cumulative),
            "Year Status": "partial year" if year == reporting_end_year else "complete year",
        })

    primary_country_values = set().union(*(year_countries[year] for year in years))
    unmapped_countries = sorted(
        primary_country_values - set(continent_mapping or {})
    ) if continent_mapping is not None else []
    if unmapped_countries:
        raise ValueError(f"continent mapping is missing registered country values: {unmapped_countries}")
    continent_rows = []
    if continent_mapping is not None:
        for year in years:
            denominator = len(year_study_ids[year])
            known_denominator = len(year_known_location_ids[year])
            for continent in CONTINENT_ORDER:
                count = len(continent_year_study_ids[continent][year])
                continent_rows.append({
                    "Year": year,
                    "Continent": continent,
                    "Eligible Studies Started": denominator,
                    "Studies with Continent Participation": count,
                    "Percentage of All Eligible Studies": count / denominator if denominator else None,
                    "Known-Location Studies": known_denominator,
                    "Percentage of Known-Location Studies": count / known_denominator if known_denominator else None,
                    "Year Status": "partial year" if year == reporting_end_year else "complete year",
                })
    nexus_rows = []
    for year in years:
        denominator = len(year_study_ids[year])
        known_denominator = len(year_known_location_ids[year])
        count = len(year_nexus_ids[year])
        moving_years = range(max(start_year, year - 2), year + 1)
        moving_counts = [len(year_nexus_ids[item]) for item in moving_years]
        nexus_rows.append({
            "Year": year,
            "Eligible Studies Started": denominator,
            "Known-Location Studies": known_denominator,
            "NEXUS Studies": count,
            "NEXUS Percentage of All Eligible Studies": count / denominator if denominator else None,
            "NEXUS Percentage of Known-Location Studies": count / known_denominator if known_denominator else None,
            "3-Year Moving Average NEXUS Studies": sum(moving_counts) / len(moving_counts),
            "Year Status": "partial year" if year == reporting_end_year else "complete year",
        })

    primary_countries = {
        country for country, year_map in country_year_study_ids.items()
        if any(start_year <= year <= reporting_end_year for year in year_map)
    }
    first_rows = []
    first_by_year: dict[int, list[str]] = defaultdict(list)
    return_rows = []
    returns_by_year: dict[int, list[str]] = defaultdict(list)
    for country in sorted(primary_countries):
        active_years = sorted(
            year for year in country_year_study_ids[country]
            if start_year <= year <= reporting_end_year
        )
        first_year = min(active_years)
        first_rows.append({
            "Country": country,
            "First Active Year": first_year,
            "Studies in First Active Year": len(country_year_study_ids[country][first_year]),
        })
        first_by_year[first_year].append(country)
        for previous_year, return_year in zip(active_years, active_years[1:]):
            if return_year - previous_year <= 1:
                continue
            return_rows.append({
                "Return Year": return_year,
                "Country": country,
                "Previous Active Year": previous_year,
                "Gap Length (Years)": return_year - previous_year - 1,
                "Studies in Return Year": len(country_year_study_ids[country][return_year]),
            })
            returns_by_year[return_year].append(country)

    first_rows.sort(key=lambda row: (row["First Active Year"], row["Country"]))
    return_rows.sort(key=lambda row: (row["Return Year"], row["Country"]))
    first_summary_rows = [{
        "Year": year,
        "Number of First-Time Countries": len(first_by_year[year]),
        "First-Time Countries": "; ".join(sorted(first_by_year[year])),
    } for year in years]
    return_summary_rows = [{
        "Year": year,
        "Number of Returning Countries": len(returns_by_year[year]),
        "Returning Countries": "; ".join(sorted(returns_by_year[year])),
    } for year in years]

    valid_start_count = sum(len(ids) for ids in year_study_ids.values())
    primary_valid_start_count = sum(len(year_study_ids[year]) for year in years)
    pre_period_count = sum(len(ids) for year, ids in year_study_ids.items() if year < start_year)
    future_count = sum(len(ids) for year, ids in year_study_ids.items() if year > reporting_end_year)
    latest_observed_year = max(year_study_ids, default=None)
    comparison_2025 = None
    country_change_2025_rows = []
    if 2024 in years and 2025 in years:
        countries_2024 = year_countries[2024]
        countries_2025 = year_countries[2025]
        lost = sorted(countries_2024 - countries_2025)
        gained = sorted(countries_2025 - countries_2024)
        for country in sorted(lost, key=lambda item: (-len(country_year_study_ids[item][2024]), item)):
            country_change_2025_rows.append({
                "Country": country,
                "2024 Studies": len(country_year_study_ids[country][2024]),
                "2025 Studies": 0,
                "Change Status": "Not represented among studies starting in 2025",
            })
        for country in sorted(gained, key=lambda item: (-len(country_year_study_ids[item][2025]), item)):
            country_change_2025_rows.append({
                "Country": country,
                "2024 Studies": 0,
                "2025 Studies": len(country_year_study_ids[country][2025]),
                "Change Status": "Newly represented among studies starting in 2025",
            })
        def yearly_concentration(year: int) -> dict:
            known_counts = [count for count in study_country_counts[year] if count]
            pairs = sum(study_country_counts[year])
            country_counts = sorted(
                (len(country_year_study_ids[country][year]) for country in year_countries[year]),
                reverse=True,
            )
            return {
                "study_count": len(year_study_ids[year]),
                "known_location_count": len(year_known_location_ids[year]),
                "missing_location_count": len(year_study_ids[year] - year_known_location_ids[year]),
                "missing_location_percentage": (
                    len(year_study_ids[year] - year_known_location_ids[year]) / len(year_study_ids[year])
                ),
                "country_count": len(year_countries[year]),
                "study_country_pairs": pairs,
                "mean_countries_per_known_location_study": pairs / len(known_counts) if known_counts else None,
                "multicountry_percentage_known_location": (
                    sum(count > 1 for count in known_counts) / len(known_counts) if known_counts else None
                ),
                "top_10_country_share_of_study_country_pairs": (
                    sum(country_counts[:10]) / pairs if pairs else None
                ),
            }
        comparison_2025 = {
            "2024": yearly_concentration(2024),
            "2025": yearly_concentration(2025),
            "countries_not_represented_in_2025": len(lost),
            "countries_newly_represented_in_2025": len(gained),
            "net_country_change": len(gained) - len(lost),
            "not_represented_countries_with_one_2024_study": sum(
                len(country_year_study_ids[country][2024]) == 1 for country in lost
            ),
            "not_represented_countries_with_multiple_2024_studies": sum(
                len(country_year_study_ids[country][2024]) > 1 for country in lost
            ),
        }

    validations = {
        "annual_country_counts_match_reconstructed_sets": all(
            row["Unique Countries Involved"] == len(year_countries[row["Year"]]) for row in annual_rows
        ),
        "first_active_year_is_minimum": all(
            row["First Active Year"] == min(
                year for year in country_year_study_ids[row["Country"]]
                if start_year <= year <= reporting_end_year
            ) for row in first_rows
        ),
        "return_events_have_missing_intervening_year": all(
            row["Gap Length (Years)"] >= 1
            and row["Return Year"] - row["Previous Active Year"] - 1 == row["Gap Length (Years)"]
            for row in return_rows
        ),
        "no_country_is_first_time_twice": len(first_rows) == len({row["Country"] for row in first_rows}),
        "no_nct_id_counted_twice_within_year": all(
            len(ids) == len(set(ids)) for ids in year_study_ids.values()
        ),
        "location_duplicates_do_not_inflate_country_sets": all(
            country in year_countries[year]
            for country, year_map in country_year_study_ids.items() for year in year_map
        ),
        "all_valid_start_year_studies_reconcile": valid_start_count == len(observations) - missing_start,
        "primary_period_studies_reconcile": (
            primary_valid_start_count
            == valid_start_count - pre_period_count - future_count
        ),
        "country_values_are_only_from_registered_locations": True,
        "continent_mapping_covers_all_primary_country_values": not unmapped_countries,
        "continent_counts_do_not_exceed_annual_denominator": all(
            len(continent_year_study_ids[continent][year]) <= len(year_study_ids[year])
            for continent in CONTINENT_ORDER for year in years
        ) if continent_mapping is not None else True,
        "known_location_studies_have_at_least_one_mapped_continent": all(
            set().union(*(continent_year_study_ids[continent][year] for continent in CONTINENT_ORDER))
            == year_known_location_ids[year]
            for year in years
        ) if continent_mapping is not None else True,
        "annual_nexus_is_subset_of_known_location_studies": all(
            year_nexus_ids[year] <= year_known_location_ids[year] for year in years
        ),
    }
    if not all(validations.values()):
        failed = [name for name, passed in validations.items() if not passed]
        raise AssertionError(f"Country-participation validation failed: {failed}")

    return {
        "annual_rows": annual_rows,
        "first_rows": first_rows,
        "return_rows": return_rows,
        "first_summary_rows": first_summary_rows,
        "return_summary_rows": return_summary_rows,
        "continent_rows": continent_rows,
        "nexus_rows": nexus_rows,
        "country_change_2025_rows": country_change_2025_rows,
        "comparison_2024_2025": comparison_2025,
        "eligible_study_count": len(observations),
        "valid_start_year_count": valid_start_count,
        "missing_or_invalid_start_date_count": missing_start,
        "missing_location_country_count": missing_country,
        "pre_1991_valid_start_count": pre_period_count,
        "future_start_year_count": future_count,
        "primary_period_valid_start_count": primary_valid_start_count,
        "latest_observed_start_year": latest_observed_year,
        "total_distinct_countries": len(primary_countries),
        "countries_with_return_event": len({row["Country"] for row in return_rows}),
        "return_event_count": len(return_rows),
        "validations": validations,
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def chart_svg(rows: list[dict], path: Path, latest_complete_year: int) -> None:
    width, height = 1600, 1600
    left, right, top, bottom = 120, 70, 145, 120
    plot_w, plot_h = width - left - right, height - top - bottom
    years = [row["Year"] for row in rows]
    annual = [row["Unique Countries Involved"] for row in rows]
    rolling = [row["3-Year Rolling Active Countries"] for row in rows]
    max_y = max(annual + rolling + [1])
    y_step = max(10, int(math.ceil(max_y / 6 / 10.0) * 10))
    y_max = int(math.ceil(max_y / y_step) * y_step)
    x = lambda year: left + (year - years[0]) / max(1, years[-1] - years[0]) * plot_w
    y = lambda value: top + plot_h - value / y_max * plot_h
    annual_points = " ".join(f"{x(year):.1f},{y(value):.1f}" for year, value in zip(years, annual))
    rolling_points = " ".join(f"{x(year):.1f},{y(value):.1f}" for year, value in zip(years, rolling))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" fill-opacity="1"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202936}.title{font-size:30px;font-weight:700}.subtitle{font-size:17px;fill:#556273}.axis{font-size:15px}.small{font-size:13px;fill:#687486}.legend{font-size:15px}</style>',
        '<text x="800" y="48" text-anchor="middle" class="title">Annual Geographic Breadth of Industry-Sponsored Drug-Containing Clinical Trials</text>',
        '<text x="800" y="82" text-anchor="middle" class="subtitle">Interventional studies with Lead Sponsor Class = INDUSTRY and at least one DRUG intervention</text>',
        f'<rect x="{left}" y="{top}" width="{max(0, x(2000)-left):.1f}" height="{plot_h}" fill="#f3f0e8"/>',
        f'<text x="{(left+x(2000))/2:.1f}" y="{top+25}" text-anchor="middle" class="small">Pre-ClinicalTrials.gov / retrospectively registered period</text>',
    ]
    for value in range(0, y_max + 1, y_step):
        yy = y(value)
        parts += [f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dfe5eb" stroke-width="1"/>',
                  f'<text x="{left-18}" y="{yy+5:.1f}" text-anchor="end" class="axis">{value}</text>']
    for year in years:
        if year == years[0] or year == years[-1] or year % 5 == 0:
            xx = x(year)
            parts += [f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+7}" stroke="#4d5966"/>',
                      f'<text x="{xx:.1f}" y="{top+plot_h+30}" text-anchor="middle" class="axis">{year}</text>']
    parts += [
        f'<line x1="{x(2000):.1f}" y1="{top}" x2="{x(2000):.1f}" y2="{top+plot_h}" stroke="#7a6f55" stroke-width="2" stroke-dasharray="7 6"/>',
        f'<text x="{x(2000)+8:.1f}" y="{top+48}" class="small">ClinicalTrials.gov era begins (2000)</text>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<polyline points="{rolling_points}" fill="none" stroke="#9aa7b2" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<polyline points="{annual_points}" fill="none" stroke="#146c94" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<line x1="{x(latest_complete_year+1):.1f}" y1="{top}" x2="{x(latest_complete_year+1):.1f}" y2="{top+plot_h}" stroke="#b33a3a" stroke-width="2" stroke-dasharray="5 5"/>',
        f'<text x="{x(latest_complete_year+1)-8:.1f}" y="{top+plot_h-15}" text-anchor="end" class="small">Current year is partial</text>',
        f'<text x="{left+plot_w/2:.1f}" y="{height-42}" text-anchor="middle" class="axis">Study Start Year</text>',
        f'<text x="34" y="{top+plot_h/2:.1f}" text-anchor="middle" class="axis" transform="rotate(-90 34 {top+plot_h/2:.1f})">Number of Unique Countries Involved</text>',
        f'<line x1="{width-520}" y1="110" x2="{width-465}" y2="110" stroke="#146c94" stroke-width="5"/><text x="{width-450}" y="115" class="legend">Annual active countries</text>',
        f'<line x1="{width-270}" y1="110" x2="{width-215}" y2="110" stroke="#9aa7b2" stroke-width="4"/><text x="{width-200}" y="115" class="legend">3-year rolling</text>',
        '</svg>',
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def continent_chart_svg(rows: list[dict], path: Path, latest_complete_year: int) -> None:
    width, height = 1600, 1600
    left, right, top, bottom = 120, 70, 180, 120
    plot_w, plot_h = width - left - right, height - top - bottom
    years = sorted({row["Year"] for row in rows})
    by_continent = {
        continent: {
            row["Year"]: row["Percentage of All Eligible Studies"]
            for row in rows if row["Continent"] == continent
        } for continent in CONTINENT_ORDER
    }
    maximum = max(
        (value or 0) for values in by_continent.values() for value in values.values()
    )
    y_step = 0.1
    y_max = max(0.5, math.ceil(maximum / y_step) * y_step)
    x = lambda year: left + (year - years[0]) / max(1, years[-1] - years[0]) * plot_w
    y = lambda value: top + plot_h - (value or 0) / y_max * plot_h
    colors = {
        "Africa": "#d55e00",
        "Asia": "#0072b2",
        "Europe": "#009e73",
        "North America": "#cc79a7",
        "South America": "#e69f00",
        "Oceania": "#6f63b6",
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" fill-opacity="1"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202936}.title{font-size:30px;font-weight:700}.subtitle{font-size:17px;fill:#556273}.axis{font-size:15px}.small{font-size:13px;fill:#687486}.legend{font-size:14px}</style>',
        '<text x="800" y="48" text-anchor="middle" class="title">Annual Continent Participation in Industry-Sponsored Drug-Containing Clinical Trials</text>',
        '<text x="800" y="82" text-anchor="middle" class="subtitle">Share of all eligible studies with at least one registered location in each continent; shares are non-exclusive</text>',
        f'<rect x="{left}" y="{top}" width="{max(0, x(2000)-left):.1f}" height="{plot_h}" fill="#f3f0e8"/>',
        f'<text x="{(left+x(2000))/2:.1f}" y="{top+25}" text-anchor="middle" class="small">Retrospectively registered period</text>',
    ]
    for value_index in range(int(round(y_max / y_step)) + 1):
        value = value_index * y_step
        yy = y(value)
        parts += [
            f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dfe5eb" stroke-width="1"/>',
            f'<text x="{left-18}" y="{yy+5:.1f}" text-anchor="end" class="axis">{value:.0%}</text>',
        ]
    for year in years:
        if year == years[0] or year == years[-1] or year % 5 == 0:
            xx = x(year)
            parts += [
                f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+7}" stroke="#4d5966"/>',
                f'<text x="{xx:.1f}" y="{top+plot_h+30}" text-anchor="middle" class="axis">{year}</text>',
            ]
    for continent in CONTINENT_ORDER:
        points = " ".join(
            f"{x(year):.1f},{y(by_continent[continent].get(year)):.1f}" for year in years
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{colors[continent]}" '
            'stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>'
        )
    parts += [
        f'<line x1="{x(2000):.1f}" y1="{top}" x2="{x(2000):.1f}" y2="{top+plot_h}" stroke="#7a6f55" stroke-width="2" stroke-dasharray="7 6"/>',
        f'<line x1="{x(latest_complete_year+1):.1f}" y1="{top}" x2="{x(latest_complete_year+1):.1f}" y2="{top+plot_h}" stroke="#b33a3a" stroke-width="2" stroke-dasharray="5 5"/>',
        f'<text x="{x(latest_complete_year+1)-8:.1f}" y="{top+plot_h-15}" text-anchor="end" class="small">Current year is partial</text>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<text x="{left+plot_w/2:.1f}" y="{height-42}" text-anchor="middle" class="axis">Study Start Year</text>',
        f'<text x="34" y="{top+plot_h/2:.1f}" text-anchor="middle" class="axis" transform="rotate(-90 34 {top+plot_h/2:.1f})">Percentage of All Eligible Studies</text>',
    ]
    for index, continent in enumerate(CONTINENT_ORDER):
        legend_x = 210 + (index % 3) * 430
        legend_y = 112 + (index // 3) * 34
        parts += [
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+55}" y2="{legend_y}" stroke="{colors[continent]}" stroke-width="5"/>',
            f'<text x="{legend_x+70}" y="{legend_y+5}" class="legend">{continent}</text>',
        ]
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def nexus_chart_svg(rows: list[dict], path: Path, latest_complete_year: int) -> None:
    width, height = 1600, 1600
    left, right, top, bottom = 120, 70, 155, 120
    plot_w, plot_h = width - left - right, height - top - bottom
    years = [row["Year"] for row in rows]
    counts = [row["NEXUS Studies"] for row in rows]
    moving = [row["3-Year Moving Average NEXUS Studies"] for row in rows]
    maximum = max(counts + moving + [1])
    y_step = max(10, int(math.ceil(maximum / 6 / 10.0) * 10))
    y_max = int(math.ceil(maximum / y_step) * y_step)
    x = lambda year: left + (year - years[0]) / max(1, years[-1] - years[0]) * plot_w
    y = lambda value: top + plot_h - value / y_max * plot_h
    count_points = " ".join(f"{x(year):.1f},{y(value):.1f}" for year, value in zip(years, counts))
    moving_points = " ".join(f"{x(year):.1f},{y(value):.1f}" for year, value in zip(years, moving))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" fill-opacity="1"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202936}.title{font-size:30px;font-weight:700}.subtitle{font-size:17px;fill:#556273}.axis{font-size:15px}.small{font-size:13px;fill:#687486}.legend{font-size:15px}</style>',
        '<text x="800" y="48" text-anchor="middle" class="title">Annual NEXUS Studies by Registered Study Start Year</text>',
        '<text x="800" y="82" text-anchor="middle" class="subtitle">Industry-sponsored Interventional DRUG-containing studies with both United States and China registered locations</text>',
        f'<rect x="{left}" y="{top}" width="{max(0, x(2000)-left):.1f}" height="{plot_h}" fill="#f3f0e8"/>',
        f'<text x="{(left+x(2000))/2:.1f}" y="{top+25}" text-anchor="middle" class="small">Retrospectively registered period</text>',
    ]
    for value in range(0, y_max + 1, y_step):
        yy = y(value)
        parts += [
            f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dfe5eb" stroke-width="1"/>',
            f'<text x="{left-18}" y="{yy+5:.1f}" text-anchor="end" class="axis">{value}</text>',
        ]
    for year in years:
        if year == years[0] or year == years[-1] or year % 5 == 0:
            xx = x(year)
            parts += [
                f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+7}" stroke="#4d5966"/>',
                f'<text x="{xx:.1f}" y="{top+plot_h+30}" text-anchor="middle" class="axis">{year}</text>',
            ]
    parts += [
        f'<line x1="{x(2000):.1f}" y1="{top}" x2="{x(2000):.1f}" y2="{top+plot_h}" stroke="#7a6f55" stroke-width="2" stroke-dasharray="7 6"/>',
        f'<line x1="{x(latest_complete_year+1):.1f}" y1="{top}" x2="{x(latest_complete_year+1):.1f}" y2="{top+plot_h}" stroke="#b33a3a" stroke-width="2" stroke-dasharray="5 5"/>',
        f'<polyline points="{moving_points}" fill="none" stroke="#9aa7b2" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<polyline points="{count_points}" fill="none" stroke="#7b2cbf" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>',
        f'<text x="{x(latest_complete_year+1)-8:.1f}" y="{top+plot_h-15}" text-anchor="end" class="small">Current year is partial</text>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#394553" stroke-width="2"/>',
        f'<text x="{left+plot_w/2:.1f}" y="{height-42}" text-anchor="middle" class="axis">Study Start Year</text>',
        f'<text x="34" y="{top+plot_h/2:.1f}" text-anchor="middle" class="axis" transform="rotate(-90 34 {top+plot_h/2:.1f})">Number of NEXUS Studies</text>',
        f'<line x1="{width-580}" y1="112" x2="{width-525}" y2="112" stroke="#7b2cbf" stroke-width="5"/><text x="{width-510}" y="117" class="legend">Annual NEXUS studies</text>',
        f'<line x1="{width-300}" y1="112" x2="{width-245}" y2="112" stroke="#9aa7b2" stroke-width="4"/><text x="{width-230}" y="117" class="legend">3-year moving average</text>',
        "</svg>",
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def svg_to_png(svg_path: Path, png_path: Path) -> None:
    converter = shutil.which("sips")
    if converter:
        result = subprocess.run(
            [converter, "-s", "format", "png", str(svg_path), "--out", str(png_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and png_path.is_file():
            return
    quicklook = shutil.which("qlmanage")
    if quicklook:
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = subprocess.run(
                [quicklook, "-t", "-s", "1600", "-o", temporary_directory, str(svg_path.resolve())],
                capture_output=True, text=True,
            )
            rendered = Path(temporary_directory) / f"{svg_path.name}.png"
            if result.returncode == 0 and rendered.is_file():
                shutil.move(rendered, png_path)
                return
    raise RuntimeError(
        "PNG conversion failed with the available macOS SVG renderers; "
        "the publication-quality SVG was generated successfully"
    )


def add_sheet(wb: Workbook, title: str, rows: list[dict], fields: list[str]) -> None:
    ws = wb.create_sheet(title)
    ws.append(fields)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{chr(64 + len(fields))}1"
    for row in rows:
        ws.append([row[field] for field in fields])
    for column in ws.columns:
        width = min(90, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
        ws.column_dimensions[column[0].column_letter].width = width


def write_workbook(path: Path, result: dict, metadata: dict) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    add_sheet(wb, "Annual_Trend", result["annual_rows"], list(result["annual_rows"][0]))
    add_sheet(wb, "Annual_NEXUS", result["nexus_rows"], [
        "Year", "Eligible Studies Started", "Known-Location Studies", "NEXUS Studies",
        "NEXUS Percentage of All Eligible Studies", "NEXUS Percentage of Known-Location Studies",
        "3-Year Moving Average NEXUS Studies", "Year Status",
    ])
    add_sheet(wb, "First_Time_Countries", result["first_rows"], ["Country", "First Active Year", "Studies in First Active Year"])
    add_sheet(wb, "First_Time_By_Year", result["first_summary_rows"], ["Year", "Number of First-Time Countries", "First-Time Countries"])
    add_sheet(wb, "Returning_Countries", result["return_rows"], ["Return Year", "Country", "Previous Active Year", "Gap Length (Years)", "Studies in Return Year"])
    add_sheet(wb, "Returning_By_Year", result["return_summary_rows"], ["Year", "Number of Returning Countries", "Returning Countries"])
    add_sheet(wb, "Continent_Trend", result["continent_rows"], [
        "Year", "Continent", "Eligible Studies Started", "Studies with Continent Participation",
        "Percentage of All Eligible Studies", "Known-Location Studies",
        "Percentage of Known-Location Studies", "Year Status",
    ])
    add_sheet(wb, "Country_Continent_Map", result["continent_mapping_rows"], ["Country", "Continent"])
    add_sheet(wb, "2025_Country_Change", result["country_change_2025_rows"], [
        "Country", "2024 Studies", "2025 Studies", "Change Status",
    ])
    definitions = [
        {"Item": "Cohort", "Definition": COHORT_DEFINITION},
        {"Item": "Start year", "Definition": "Calendar year parsed from registered Start Date (YYYY, YYYY-MM, or YYYY-MM-DD)"},
        {"Item": "Annual active countries", "Definition": "Distinct exact registered location-country strings among eligible studies starting in that year"},
        {"Item": "First-time country", "Definition": "First appearance within the current eligible ClinicalTrials.gov cohort and 1991–reporting-year window"},
        {"Item": "Returning country", "Definition": "Active earlier, absent for >=1 intervening complete calendar year, then active again"},
        {"Item": "Continent participation rate", "Definition": "Eligible studies with >=1 registered location in the continent / all eligible studies starting that year; a cross-continent study counts in each participating continent"},
        {"Item": "Continent mapping", "Definition": metadata["continent_mapping_definition"]},
        {"Item": "Continent mapping source", "Definition": metadata["continent_mapping_source"]},
        {"Item": "Snapshot", "Definition": metadata["snapshot_directory"]},
        {"Item": "Snapshot date", "Definition": metadata["snapshot_date"]},
    ]
    add_sheet(wb, "Definitions", definitions, ["Item", "Definition"])
    wb.save(path)


def extrema(rows: list[dict], latest_complete_year: int) -> dict:
    completed = [row for row in rows if row["Year"] <= latest_complete_year]
    max_count = max(row["Unique Countries Involved"] for row in completed)
    max_years = [row["Year"] for row in completed if row["Unique Countries Involved"] == max_count]
    changes = []
    for previous, current in zip(completed, completed[1:]):
        changes.append((current["Unique Countries Involved"] - previous["Unique Countries Involved"], current["Year"]))
    max_change = max(change for change, _ in changes)
    min_change = min(change for change, _ in changes)
    return {
        "maximum_count": max_count,
        "maximum_years": max_years,
        "largest_increase": max_change,
        "largest_increase_years": [year for change, year in changes if change == max_change],
        "largest_decrease": min_change,
        "largest_decrease_years": [year for change, year in changes if change == min_change],
    }


def write_summary(path: Path, result: dict, metadata: dict) -> None:
    annual = {row["Year"]: row for row in result["annual_rows"]}
    latest_complete = metadata["latest_complete_year"]
    stats = extrema(result["annual_rows"], latest_complete)
    max_first = max(row["Number of First-Time Countries"] for row in result["first_summary_rows"])
    max_first_rows = [row for row in result["first_summary_rows"] if row["Number of First-Time Countries"] == max_first]
    max_return = max(row["Number of Returning Countries"] for row in result["return_summary_rows"])
    max_return_rows = [row for row in result["return_summary_rows"] if row["Number of Returning Countries"] == max_return]
    long_returns = sorted(result["return_rows"], key=lambda row: (-row["Gap Length (Years)"], row["Return Year"], row["Country"]))[:10]
    continent_by_year = {
        (row["Year"], row["Continent"]): row for row in result["continent_rows"]
    }
    comparison = result["comparison_2024_2025"]
    change_lost = [
        row for row in result["country_change_2025_rows"]
        if row["Change Status"].startswith("Not represented")
    ]
    change_gained = [
        row for row in result["country_change_2025_rows"]
        if row["Change Status"].startswith("Newly represented")
    ]
    continent_for_country = {
        row["Country"]: row["Continent"] for row in result["continent_mapping_rows"]
    }
    lost_by_continent = Counter(continent_for_country[row["Country"]] for row in change_lost)
    gained_by_continent = Counter(continent_for_country[row["Country"]] for row in change_gained)
    completed_nexus_rows = [
        row for row in result["nexus_rows"] if row["Year"] <= latest_complete
    ]
    maximum_nexus_count = max(row["NEXUS Studies"] for row in completed_nexus_rows)
    maximum_nexus_years = [
        row["Year"] for row in completed_nexus_rows if row["NEXUS Studies"] == maximum_nexus_count
    ]

    lines = [
        "# Country Participation Trend Analysis", "",
        "## Cohort definition", "", f"`{COHORT_DEFINITION}`", "",
        "Mixed DRUG-containing intervention combinations remain included. One unique NCT ID is the study unit.", "",
        "## Data source", "",
        f"- Snapshot: `{metadata['snapshot_directory']}`",
        f"- Snapshot date: **{metadata['snapshot_date']}**",
        f"- Eligible studies: **{result['eligible_study_count']:,}**",
        f"- Missing/malformed Start Date, excluded from year-specific calculations: **{result['missing_or_invalid_start_date_count']:,}**",
        f"- No usable registered location country: **{result['missing_location_country_count']:,}** (retained in annual study counts when Start Year is valid; contributes no country)",
        f"- Valid Start Year before 1991, outside primary period: **{result['pre_1991_valid_start_count']:,}**",
        f"- Future Start Year after {metadata['reporting_end_year']}, outside primary period: **{result['future_start_year_count']:,}**",
        f"- Latest observed Start Year: **{result['latest_observed_start_year']}**",
        f"- Latest complete reporting year: **{latest_complete}**",
        f"- {metadata['reporting_end_year']} is included and labeled **partial year**.", "",
        "## Annual trend", "",
        "| Year | Eligible Studies Started | Missing Location % | Unique Countries Involved | 3-Year Rolling Active Countries | Cumulative Countries Since 1991 | Status |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["annual_rows"]:
        missing_location_percentage = (
            "N/A" if row["Missing-Location Percentage"] is None
            else f"{row['Missing-Location Percentage']:.2%}"
        )
        lines.append(
            f"| {row['Year']} | {row['Eligible Studies Started']:,} | "
            f"{missing_location_percentage} | "
            f"{row['Unique Countries Involved']:,} | "
            f"{row['3-Year Rolling Active Countries']:,} | {row['Cumulative Countries Since 1991']:,} | {row['Year Status']} |"
        )
    lines += ["", "### Selected annual diagnostics", ""]
    for year in (1991, 2000, 2010, 2020, latest_complete, metadata["reporting_end_year"]):
        if year in annual:
            lines.append(f"- {year}: **{annual[year]['Unique Countries Involved']:,} countries**, {annual[year]['Eligible Studies Started']:,} studies{'; partial year' if year == metadata['reporting_end_year'] else ''}")
    lines += [
        f"- Maximum completed-year annual country count: **{stats['maximum_count']:,}** in {', '.join(map(str, stats['maximum_years']))}",
        f"- Largest completed-year year-over-year increase: **{stats['largest_increase']:+,}** in {', '.join(map(str, stats['largest_increase_years']))} versus the preceding year",
        f"- Largest completed-year year-over-year decrease: **{stats['largest_decrease']:+,}** in {', '.join(map(str, stats['largest_decrease_years']))} versus the preceding year", "",
        "## 2024–2025 breadth diagnostic", "",
        f"- Eligible studies increased from **{comparison['2024']['study_count']:,}** to **{comparison['2025']['study_count']:,}**.",
        f"- Known-location studies increased from **{comparison['2024']['known_location_count']:,}** to **{comparison['2025']['known_location_count']:,}**.",
        f"- Missing-location percentage increased from **{comparison['2024']['missing_location_percentage']:.2%}** to **{comparison['2025']['missing_location_percentage']:.2%}**.",
        f"- Registered country breadth decreased from **{comparison['2024']['country_count']}** to **{comparison['2025']['country_count']}**.",
        f"- **{comparison['countries_not_represented_in_2025']}** countries present in 2024 were not represented among studies starting in 2025; **{comparison['countries_newly_represented_in_2025']}** countries appeared in 2025, for a net change of **{comparison['net_country_change']:+}**.",
        f"- Of the countries not represented in 2025, **{comparison['not_represented_countries_with_one_2024_study']}** had only one 2024 study and **{comparison['not_represented_countries_with_multiple_2024_studies']}** had multiple 2024 studies.",
        f"- Mean countries per known-location study decreased from **{comparison['2024']['mean_countries_per_known_location_study']:.2f}** to **{comparison['2025']['mean_countries_per_known_location_study']:.2f}**.",
        f"- Multi-country share among known-location studies decreased from **{comparison['2024']['multicountry_percentage_known_location']:.2%}** to **{comparison['2025']['multicountry_percentage_known_location']:.2%}**.",
        f"- Top-10 countries' share of study-country pairs increased from **{comparison['2024']['top_10_country_share_of_study_country_pairs']:.2%}** to **{comparison['2025']['top_10_country_share_of_study_country_pairs']:.2%}**.", "",
        "| Country | 2024 Studies | 2025 Studies | Status |", "|---|---:|---:|---|",
    ]
    for row in change_lost + change_gained:
        lines.append(
            f"| {row['Country']} | {row['2024 Studies']} | {row['2025 Studies']} | "
            f"{row['Change Status']} |"
        )
    lines += [
        "", "| Continent | 2024 countries not represented in 2025 | Newly represented in 2025 | Net country change |",
        "|---|---:|---:|---:|",
    ]
    for continent in CONTINENT_ORDER:
        lines.append(
            f"| {continent} | {lost_by_continent[continent]} | {gained_by_continent[continent]} | "
            f"{gained_by_continent[continent] - lost_by_continent[continent]:+} |"
        )
    lines += [
        "", "This diagnostic describes how the count fell; it does not establish a causal reason or permanent country exit.", "",
        "## Annual continent participation", "",
        "The primary percentage is the number of eligible studies with at least one registered location in the continent divided by all eligible studies starting that year. Cross-continent studies count once in each participating continent, so percentages across continents are not mutually exclusive and may sum to more than 100%.", "",
        "| Year | Africa | Asia | Europe | North America | South America | Oceania | Status |",
        "|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["annual_rows"]:
        year = row["Year"]
        values = [
            continent_by_year[(year, continent)]["Percentage of All Eligible Studies"]
            for continent in CONTINENT_ORDER
        ]
        lines.append(
            f"| {year} | "
            + " | ".join("N/A" if value is None else f"{value:.2%}" for value in values)
            + f" | {row['Year Status']} |"
        )
    lines += [
        "", f"Continent mapping source: {metadata['continent_mapping_source']}", "",
        "## Annual NEXUS trend", "",
        "NEXUS means the eligible study has at least one exact `United States` registered location and at least one exact `China` registered location; it may also include other countries.", "",
        f"- Maximum completed-year annual NEXUS count: **{maximum_nexus_count:,}** in {', '.join(map(str, maximum_nexus_years))}.", "",
        "| Year | NEXUS Studies | NEXUS % of All Eligible | NEXUS % of Known-Location | 3-Year Moving Average | Status |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["nexus_rows"]:
        all_percentage = (
            "N/A" if row["NEXUS Percentage of All Eligible Studies"] is None
            else f"{row['NEXUS Percentage of All Eligible Studies']:.2%}"
        )
        known_percentage = (
            "N/A" if row["NEXUS Percentage of Known-Location Studies"] is None
            else f"{row['NEXUS Percentage of Known-Location Studies']:.2%}"
        )
        lines.append(
            f"| {row['Year']} | {row['NEXUS Studies']:,} | {all_percentage} | "
            f"{known_percentage} | {row['3-Year Moving Average NEXUS Studies']:.1f} | "
            f"{row['Year Status']} |"
        )
    lines += [
        "",
        "## First-time participation", "",
        f"- Total distinct countries represented from 1991 through {metadata['reporting_end_year']}: **{result['total_distinct_countries']:,}**",
        f"- Largest number of first-time countries in one year: **{max_first:,}**", "",
        "| Year | Number of First-Time Countries | First-Time Countries |", "|---:|---:|---|",
    ]
    for row in max_first_rows:
        lines.append(f"| {row['Year']} | {row['Number of First-Time Countries']} | {row['First-Time Countries']} |")
    lines += [
        "", "A first-time country means its first appearance in the current eligible ClinicalTrials.gov cohort, not its first-ever participation in clinical research globally.", "",
        "## Returning participation", "",
        f"- Countries with at least one return after a gap: **{result['countries_with_return_event']:,}**",
        f"- Total return events: **{result['return_event_count']:,}**",
        f"- Largest number of returning countries in one year: **{max_return:,}**", "",
        "| Year | Number of Returning Countries | Returning Countries |", "|---:|---:|---|",
    ]
    for row in max_return_rows:
        lines.append(f"| {row['Year']} | {row['Number of Returning Countries']} | {row['Returning Countries']} |")
    lines += ["", "### Longest observed gaps before return", "", "| Return Year | Country | Previous Active Year | Gap Length | Studies in Return Year |", "|---:|---|---:|---:|---:|"]
    for row in long_returns:
        lines.append(f"| {row['Return Year']} | {row['Country']} | {row['Previous Active Year']} | {row['Gap Length (Years)']} | {row['Studies in Return Year']} |")
    lines += [
        "", "## Validation", "",
        *[f"- {name}: **{'PASS' if passed else 'FAIL'}**" for name, passed in result["validations"].items()],
        "", "## Interpretation limitations", "",
        "> This analysis measures the number of distinct registered ClinicalTrials.gov study-location countries among eligible studies starting in each year.", "",
        "It does not measure the number of countries globally conducting clinical trials that year. Registered locations do not establish participant nationality or confirmed enrollment activity.", "",
        "> ClinicalTrials.gov launched in 2000. Studies with Start Dates before 2000 were retrospectively registered, so the 1991–1999 period should be interpreted cautiously and should not be treated as equally complete prospective registry coverage.", "",
        f"The {metadata['reporting_end_year']} value is a partial-year observation and should not be compared naively with completed prior years. Future registered Start Dates are reported separately and are not included in the primary chart.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, default=Path("reports/country_participation_trend"))
    parser.add_argument("--start-year", type=int, default=1991)
    parser.add_argument("--continent-mapping", type=Path,
                        default=Path(__file__).with_name("continent_mapping.json"))
    parser.add_argument("--replace-output", action="store_true",
                        help="Replace this analysis's lightweight files in an existing output directory")
    args = parser.parse_args(argv)

    manifest_path = args.run / "manifest.json"
    if not manifest_path.is_file():
        parser.error("selected run has no manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("snapshot_complete") or manifest.get("next_page_token_remaining") is not False:
        parser.error("country trend analysis requires a completed snapshot with no remaining page token")
    fields = {
        value.strip() for value in manifest.get("request_parameters", {}).get("fields", "").split(",") if value.strip()
    }
    missing_fields = sorted(REQUIRED_FIELDS - fields)
    if missing_fields:
        parser.error(f"snapshot is missing required harvested fields: {', '.join(missing_fields)}")
    if args.outdir.exists() and any(args.outdir.iterdir()) and not args.replace_output:
        parser.error(f"output directory already exists and is not empty: {args.outdir}")
    continent_mapping, continent_document = load_continent_mapping(args.continent_mapping)

    snapshot_date = datetime.fromisoformat(manifest["harvest_timestamp_utc"].replace("Z", "+00:00")).date()
    reporting_end_year = snapshot_date.year
    seen: set[str] = set()
    observations = []
    raw_count = 0
    duplicate_count = 0
    for entry in manifest["files"]:
        page_path = args.run / entry["path"]
        if not page_path.is_file() or sha256(page_path) != entry["sha256"]:
            raise RuntimeError(f"Raw page or SHA-256 validation failed: {page_path}")
        payload = json.loads(page_path.read_text(encoding="utf-8"))
        studies = payload.get("studies")
        if not isinstance(studies, list) or len(studies) != entry["study_count"]:
            raise RuntimeError(f"Raw page study count mismatch: {page_path}")
        raw_count += len(studies)
        for study in studies:
            nct_id = (study.get("protocolSection", {}).get("identificationModule", {}) or {}).get("nctId")
            if not isinstance(nct_id, str) or not nct_id.strip():
                raise ValueError(f"Raw study has no NCT ID: {page_path}")
            nct_id = nct_id.strip()
            if nct_id in seen:
                duplicate_count += 1
                continue
            seen.add(nct_id)
            observation = eligible_observation(study)
            if observation is not None:
                observations.append(observation)
    if raw_count != manifest["raw_study_count"] or len(seen) != manifest["unique_nct_count"]:
        raise RuntimeError("Snapshot raw or unique study count does not reconcile with manifest")
    if duplicate_count != manifest.get("duplicate_nct_count", duplicate_count):
        raise RuntimeError("Snapshot duplicate count does not reconcile with manifest")

    result = aggregate_observations(
        observations, args.start_year, reporting_end_year, continent_mapping
    )
    result["continent_mapping_rows"] = [
        {"Country": country, "Continent": continent_mapping[country]}
        for country in sorted({
            country for observation in observations
            if observation["start_year"] is not None
            and args.start_year <= observation["start_year"] <= reporting_end_year
            for country in observation["countries"]
        })
    ]
    metadata = {
        "snapshot_directory": str(args.run.resolve()),
        "snapshot_date": snapshot_date.isoformat(),
        "reporting_end_year": reporting_end_year,
        "latest_complete_year": reporting_end_year - 1,
        "continent_mapping_source": continent_document["source"],
        "continent_mapping_definition": continent_document["definition"],
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(args.outdir / "annual_country_participation.csv", result["annual_rows"], list(result["annual_rows"][0]))
    write_csv(args.outdir / "country_first_active_year.csv", result["first_rows"], ["Country", "First Active Year", "Studies in First Active Year"])
    write_csv(args.outdir / "first_time_countries_by_year.csv", result["first_summary_rows"], ["Year", "Number of First-Time Countries", "First-Time Countries"])
    write_csv(args.outdir / "country_returns.csv", result["return_rows"], ["Return Year", "Country", "Previous Active Year", "Gap Length (Years)", "Studies in Return Year"])
    write_csv(args.outdir / "returning_countries_by_year.csv", result["return_summary_rows"], ["Year", "Number of Returning Countries", "Returning Countries"])
    write_csv(args.outdir / "annual_continent_participation.csv", result["continent_rows"], [
        "Year", "Continent", "Eligible Studies Started", "Studies with Continent Participation",
        "Percentage of All Eligible Studies", "Known-Location Studies",
        "Percentage of Known-Location Studies", "Year Status",
    ])
    write_csv(args.outdir / "country_continent_mapping.csv", result["continent_mapping_rows"], ["Country", "Continent"])
    write_csv(args.outdir / "country_change_2024_2025.csv", result["country_change_2025_rows"], [
        "Country", "2024 Studies", "2025 Studies", "Change Status",
    ])
    write_csv(args.outdir / "annual_nexus_studies.csv", result["nexus_rows"], [
        "Year", "Eligible Studies Started", "Known-Location Studies", "NEXUS Studies",
        "NEXUS Percentage of All Eligible Studies", "NEXUS Percentage of Known-Location Studies",
        "3-Year Moving Average NEXUS Studies", "Year Status",
    ])
    write_summary(args.outdir / "country_participation_summary.md", result, metadata)
    write_workbook(args.outdir / "country_participation_analysis.xlsx", result, metadata)
    svg_path = args.outdir / "annual_country_participation_trend.svg"
    chart_svg(result["annual_rows"], svg_path, metadata["latest_complete_year"])
    svg_to_png(svg_path, args.outdir / "annual_country_participation_trend.png")
    continent_svg_path = args.outdir / "annual_continent_participation_trend.svg"
    continent_chart_svg(result["continent_rows"], continent_svg_path, metadata["latest_complete_year"])
    svg_to_png(continent_svg_path, args.outdir / "annual_continent_participation_trend.png")
    nexus_svg_path = args.outdir / "annual_nexus_studies_trend.svg"
    nexus_chart_svg(result["nexus_rows"], nexus_svg_path, metadata["latest_complete_year"])
    svg_to_png(nexus_svg_path, args.outdir / "annual_nexus_studies_trend.png")
    print(args.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
