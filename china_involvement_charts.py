#!/usr/bin/env python3
"""Create focused China-involvement charts from a complete Phase-enabled snapshot."""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path

from country_participation import eligible_observation, sha256, svg_to_png


REQUIRED_FIELDS = {
    "NCTId", "StudyType", "Phase", "StartDate", "InterventionType",
    "LeadSponsorClass", "LocationCountry",
}
PHASE_ORDER = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4")
PHASE_LABELS = {
    "EARLY_PHASE1": "Early Phase 1",
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
}
FOOTPRINT_ORDER = (
    "China only",
    "China and Other Countries (No US)",
    "China and US",
)
FOOTPRINT_COLORS = {
    "China only": "#d55e00",
    "China and Other Countries (No US)": "#009e73",
    "China and US": "#7b2cbf",
}
CHINA_COLOR = "#d55e00"
NON_CHINA_COLOR = "#8da0ae"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_observations(run: Path) -> tuple[list[dict], dict]:
    manifest_path = run / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"snapshot has no manifest.json: {run}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("snapshot_complete") or manifest.get("next_page_token_remaining") is not False:
        raise ValueError("China-involvement charts require a complete snapshot with no next-page token")
    fields = {
        value.strip()
        for value in manifest.get("request_parameters", {}).get("fields", "").split(",")
        if value.strip()
    }
    missing_fields = sorted(REQUIRED_FIELDS - fields)
    if missing_fields:
        raise ValueError(f"snapshot is missing required fields: {', '.join(missing_fields)}")

    seen: set[str] = set()
    observations = []
    raw_count = 0
    duplicate_count = 0
    for entry in manifest["files"]:
        page_path = run / entry["path"]
        if not page_path.is_file() or sha256(page_path) != entry["sha256"]:
            raise ValueError(f"raw page or SHA-256 validation failed: {page_path}")
        payload = json.loads(page_path.read_text(encoding="utf-8"))
        studies = payload.get("studies")
        if not isinstance(studies, list) or len(studies) != entry["study_count"]:
            raise ValueError(f"raw page study count mismatch: {page_path}")
        raw_count += len(studies)
        for study in studies:
            protocol = study.get("protocolSection") or {}
            nct_id = ((protocol.get("identificationModule") or {}).get("nctId"))
            if not isinstance(nct_id, str) or not nct_id.strip():
                raise ValueError(f"raw study has no usable NCT ID: {page_path}")
            nct_id = nct_id.strip()
            if nct_id in seen:
                duplicate_count += 1
                continue
            seen.add(nct_id)
            observation = eligible_observation(study)
            if observation is None:
                continue
            phases = {
                value.strip()
                for value in ((protocol.get("designModule") or {}).get("phases") or [])
                if isinstance(value, str) and value.strip()
            }
            observation["phases"] = phases
            observations.append(observation)
    if raw_count != manifest["raw_study_count"] or len(seen) != manifest["unique_nct_count"]:
        raise ValueError("snapshot raw or unique study count does not reconcile with manifest")
    if duplicate_count != manifest.get("duplicate_nct_count", duplicate_count):
        raise ValueError("snapshot duplicate count does not reconcile with manifest")
    return observations, manifest


def aggregate_china_involvement(
    observations: list[dict], start_year: int = 2020, end_year: int = 2025,
) -> tuple[list[dict], list[dict]]:
    years = list(range(start_year, end_year + 1))
    footprint_counts = {
        year: {category: 0 for category in FOOTPRINT_ORDER} for year in years
    }
    phase_counts = {
        phase: {"China-Involved": 0, "Non China-Involved": 0}
        for phase in PHASE_ORDER
    }
    for observation in observations:
        year = observation["start_year"]
        if year not in footprint_counts:
            continue
        countries = set(observation["countries"])
        china_involved = "China" in countries
        if china_involved:
            if countries == {"China"}:
                footprint_counts[year]["China only"] += 1
            elif "United States" in countries:
                footprint_counts[year]["China and US"] += 1
            else:
                footprint_counts[year]["China and Other Countries (No US)"] += 1
        for phase in PHASE_ORDER:
            if phase in observation["phases"]:
                category = "China-Involved" if china_involved else "Non China-Involved"
                phase_counts[phase][category] += 1

    footprint_rows = []
    for year in years:
        row = {"Year": year, **footprint_counts[year]}
        row["All China-Involved Studies"] = sum(footprint_counts[year].values())
        footprint_rows.append(row)
    phase_rows = []
    for phase in PHASE_ORDER:
        china_count = phase_counts[phase]["China-Involved"]
        non_china_count = phase_counts[phase]["Non China-Involved"]
        total = china_count + non_china_count
        phase_rows.append({
            "Phase": phase,
            "Phase Label": PHASE_LABELS[phase],
            "China-Involved Studies": china_count,
            "Non China-Involved Studies": non_china_count,
            "Total Studies": total,
            "China-Involved Percentage": china_count / total if total else None,
            "Non China-Involved Percentage": non_china_count / total if total else None,
        })
    return footprint_rows, phase_rows


def nice_integer_axis(maximum: int) -> tuple[int, int]:
    raw_step = max(1, maximum / 6)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude
    factor = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    step = int(factor * magnitude)
    return int(math.ceil(maximum / step) * step), step


def footprint_chart_svg(rows: list[dict], path: Path) -> None:
    width, height = 1600, 1000
    left, right, top, bottom = 140, 70, 115, 140
    plot_w, plot_h = width - left - right, height - top - bottom
    years = [row["Year"] for row in rows]
    maximum = max(row[category] for row in rows for category in FOOTPRINT_ORDER)
    y_max, y_step = nice_integer_axis(maximum)
    x_padding = 85
    inner_width = plot_w - 2 * x_padding
    x = lambda year: left + x_padding + (
        (year - years[0]) / max(1, years[-1] - years[0]) * inner_width
    )
    y = lambda value: top + plot_h - value / y_max * plot_h
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.title{font-size:31px;font-weight:700}.axis{font-size:18px}.tick{font-size:16px}.legend{font-size:13px}</style>',
        '<text x="800" y="55" text-anchor="middle" class="title">China-Involved Study Footprint by Year, 2020-2025</text>',
    ]
    for value in range(0, y_max + 1, y_step):
        yy = y(value)
        parts += [
            f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#d8dde3"/>',
            f'<text x="{left-18}" y="{yy+6:.1f}" text-anchor="end" class="tick">{value:,}</text>',
        ]
    for year in years:
        xx = x(year)
        parts += [
            f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+8}" stroke="#000" stroke-width="2"/>',
            f'<text x="{xx:.1f}" y="{top+plot_h+34}" text-anchor="middle" class="tick">{year}</text>',
        ]
    for category in FOOTPRINT_ORDER:
        color = FOOTPRINT_COLORS[category]
        points = " ".join(
            f"{x(row['Year']):.1f},{y(row[category]):.1f}" for row in rows
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for row in rows:
            parts.append(
                f'<circle cx="{x(row["Year"]):.1f}" cy="{y(row[category]):.1f}" r="8" fill="{color}"/>'
            )
    legend_x, legend_y, legend_w, legend_h = left + 24, top + 8, 365, 88
    parts.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="{legend_w}" height="{legend_h}" fill="#fff" stroke="#9b9b9b"/>'
    )
    for index, category in enumerate(FOOTPRINT_ORDER):
        yy = legend_y + 22 + index * 23
        color = FOOTPRINT_COLORS[category]
        parts += [
            f'<line x1="{legend_x+12}" y1="{yy}" x2="{legend_x+42}" y2="{yy}" stroke="{color}" stroke-width="4"/>',
            f'<circle cx="{legend_x+27}" cy="{yy}" r="4.5" fill="{color}"/>',
            f'<text x="{legend_x+52}" y="{yy+4}" class="legend">{html.escape(category)}</text>',
        ]
    parts += [
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#000" stroke-width="2"/>',
        f'<text x="{left+plot_w/2:.1f}" y="{height-48}" text-anchor="middle" class="axis">Start Year</text>',
        f'<text x="38" y="{top+plot_h/2:.1f}" text-anchor="middle" class="axis" transform="rotate(-90 38 {top+plot_h/2:.1f})">Number of Studies</text>',
        '</svg>',
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def pie_slice_path(cx: float, cy: float, radius: float, start: float, end: float) -> str:
    start_rad = math.radians(start)
    end_rad = math.radians(end)
    x1, y1 = cx + radius * math.cos(start_rad), cy + radius * math.sin(start_rad)
    x2, y2 = cx + radius * math.cos(end_rad), cy + radius * math.sin(end_rad)
    large_arc = 1 if end - start > 180 else 0
    return (
        f"M {cx:.1f},{cy:.1f} L {x1:.1f},{y1:.1f} "
        f"A {radius:.1f},{radius:.1f} 0 {large_arc} 1 {x2:.1f},{y2:.1f} Z"
    )


def phase_pie_chart_svg(row: dict, path: Path) -> None:
    width, height = 1200, 850
    cx, cy, radius = 385, 445, 255
    china_count = row["China-Involved Studies"]
    non_china_count = row["Non China-Involved Studies"]
    total = row["Total Studies"]
    if total <= 0:
        raise ValueError(f"phase pie chart has no observations: {row['Phase']}")
    slices = [
        ("China-Involved", china_count, CHINA_COLOR),
        ("Non China-Involved", non_china_count, NON_CHINA_COLOR),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.title{font-size:27px;font-weight:700}.phase{font-size:23px;font-weight:700}.slice{font-size:18px;font-weight:700;fill:#fff}.legend{font-size:15px}.note{font-size:14px;fill:#4f5965}</style>',
        '<text x="600" y="45" text-anchor="middle" class="title">China-Involved vs. Non China-Involved Studies by Phase</text>',
        f'<text x="600" y="80" text-anchor="middle" class="phase">2020-2025 — {html.escape(row["Phase Label"])}</text>',
        '<rect x="28" y="108" width="1144" height="710" fill="none" stroke="#000" stroke-width="2"/>',
    ]
    start_angle = -90.0
    for label, count, color in slices:
        fraction = count / total
        end_angle = start_angle + fraction * 360
        parts.append(
            f'<path d="{pie_slice_path(cx, cy, radius, start_angle, end_angle)}" fill="{color}" stroke="#fff" stroke-width="3"/>'
        )
        mid_angle = math.radians((start_angle + end_angle) / 2)
        label_x = cx + radius * 0.62 * math.cos(mid_angle)
        label_y = cy + radius * 0.62 * math.sin(mid_angle)
        parts += [
            f'<text x="{label_x:.1f}" y="{label_y-4:.1f}" text-anchor="middle" class="slice">{fraction:.1%}</text>',
            f'<text x="{label_x:.1f}" y="{label_y+20:.1f}" text-anchor="middle" class="slice">n={count:,}</text>',
        ]
        start_angle = end_angle
    legend_x, legend_y = 760, 335
    parts.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="335" height="112" fill="#fff" stroke="#9b9b9b"/>'
    )
    for index, (label, count, color) in enumerate(slices):
        yy = legend_y + 34 + index * 42
        parts += [
            f'<rect x="{legend_x+18}" y="{yy-13}" width="22" height="22" fill="{color}"/>',
            f'<text x="{legend_x+54}" y="{yy+4}" class="legend">{label} (n={count:,})</text>',
        ]
    parts += [
        f'<text x="{legend_x}" y="{legend_y+154}" class="note">Total studies in this registered phase: {total:,}</text>',
        '<text x="52" y="795" class="note">A study registered in multiple phases appears once in each applicable phase chart.</text>',
        '</svg>',
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def combined_phase_pies_svg(rows: list[dict], path: Path) -> None:
    """Render Phase 1–4 as four labeled panels with one compact shared legend."""
    selected = {row["Phase"]: row for row in rows if row["Phase"] in PHASE_ORDER[1:]}
    missing = [phase for phase in PHASE_ORDER[1:] if phase not in selected]
    if missing:
        raise ValueError(f"combined phase chart is missing rows: {', '.join(missing)}")

    width, height = 1600, 1200
    panel_centers = ((570, 385), (1200, 385), (570, 895), (1200, 895))
    radius = 185
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.title{font-size:30px;font-weight:700}.phase{font-size:23px;font-weight:700}.slice{font-size:16px;font-weight:700;fill:#fff}.legend{font-size:14px}.note{font-size:13px;fill:#4f5965}</style>',
        '<text x="800" y="52" text-anchor="middle" class="title">China-Involved vs. Non China-Involved Studies by Phase, 2020-2025</text>',
        '<rect x="28" y="138" width="1544" height="1018" fill="none" stroke="#000" stroke-width="2"/>',
        '<rect x="55" y="160" width="275" height="90" fill="#fff" stroke="#9b9b9b"/>',
        f'<rect x="75" y="176" width="20" height="20" fill="{CHINA_COLOR}"/>',
        '<text x="107" y="192" class="legend">China-Involved</text>',
        f'<rect x="75" y="212" width="20" height="20" fill="{NON_CHINA_COLOR}"/>',
        '<text x="107" y="228" class="legend">Non China-Involved</text>',
    ]
    for phase, (cx, cy) in zip(PHASE_ORDER[1:], panel_centers):
        row = selected[phase]
        china_count = row["China-Involved Studies"]
        non_china_count = row["Non China-Involved Studies"]
        total = row["Total Studies"]
        if total <= 0:
            raise ValueError(f"combined phase chart has no observations: {phase}")
        parts.append(
            f'<text x="{cx}" y="{cy-radius-38}" text-anchor="middle" class="phase">{html.escape(row["Phase Label"])} (n={total:,})</text>'
        )
        start_angle = -90.0
        for count, color in ((china_count, CHINA_COLOR), (non_china_count, NON_CHINA_COLOR)):
            fraction = count / total
            end_angle = start_angle + fraction * 360
            parts.append(
                f'<path d="{pie_slice_path(cx, cy, radius, start_angle, end_angle)}" fill="{color}" stroke="#fff" stroke-width="3"/>'
            )
            mid_angle = math.radians((start_angle + end_angle) / 2)
            label_x = cx + radius * 0.62 * math.cos(mid_angle)
            label_y = cy + radius * 0.62 * math.sin(mid_angle)
            parts += [
                f'<text x="{label_x:.1f}" y="{label_y-3:.1f}" text-anchor="middle" class="slice">{fraction:.1%}</text>',
                f'<text x="{label_x:.1f}" y="{label_y+18:.1f}" text-anchor="middle" class="slice">n={count:,}</text>',
            ]
            start_angle = end_angle
    parts += [
        '<text x="52" y="1132" class="note">Each panel uses all eligible studies in that registered phase; multi-phase studies may appear in more than one panel.</text>',
        '</svg>',
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument(
        "--outdir", type=Path,
        default=Path("reports/annual_percentage_trends_2020_2025"),
    )
    parser.add_argument("--replace-output", action="store_true")
    args = parser.parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    owned_names = {
        "china_footprint_by_year_2020_2025.csv",
        "china_involvement_by_phase_2020_2025.csv",
        "china_involved_study_footprint_2020_2025.svg",
        "china_involved_study_footprint_2020_2025.png",
        "china_involvement_phase1_to_phase4_combined_2020_2025.svg",
        "china_involvement_phase1_to_phase4_combined_2020_2025.png",
        *(f"china_involvement_{phase.lower()}_2020_2025.{extension}"
          for phase in PHASE_ORDER for extension in ("svg", "png")),
    }
    existing_owned = sorted(name for name in owned_names if (args.outdir / name).exists())
    if existing_owned and not args.replace_output:
        parser.error(f"owned output files already exist; use --replace-output: {existing_owned}")

    observations, manifest = load_observations(args.run)
    footprint_rows, phase_rows = aggregate_china_involvement(observations)
    write_csv(args.outdir / "china_footprint_by_year_2020_2025.csv", footprint_rows)
    write_csv(args.outdir / "china_involvement_by_phase_2020_2025.csv", phase_rows)
    footprint_svg = args.outdir / "china_involved_study_footprint_2020_2025.svg"
    footprint_chart_svg(footprint_rows, footprint_svg)
    svg_to_png(footprint_svg, args.outdir / "china_involved_study_footprint_2020_2025.png")
    for row in phase_rows:
        stem = f"china_involvement_{row['Phase'].lower()}_2020_2025"
        svg_path = args.outdir / f"{stem}.svg"
        phase_pie_chart_svg(row, svg_path)
        svg_to_png(svg_path, args.outdir / f"{stem}.png")
    combined_svg = args.outdir / "china_involvement_phase1_to_phase4_combined_2020_2025.svg"
    combined_phase_pies_svg(phase_rows, combined_svg)
    svg_to_png(
        combined_svg,
        args.outdir / "china_involvement_phase1_to_phase4_combined_2020_2025.png",
    )
    print(json.dumps({
        "outdir": str(args.outdir),
        "snapshot": str(args.run),
        "snapshot_timestamp": manifest["harvest_timestamp_utc"],
        "footprint_rows": footprint_rows,
        "phase_rows": phase_rows,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
