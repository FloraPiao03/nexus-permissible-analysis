#!/usr/bin/env python3
"""Generate long- and recent-period China-involvement trend charts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from china_involvement_charts import (
    aggregate_china_involvement,
    china_involved_studies_chart_svg,
    footprint_chart_svg,
    load_observations,
    write_csv,
)
from country_participation import svg_to_png


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument(
        "--outdir", type=Path,
        default=Path("reports/china_involvement_trends_1991_2025"),
    )
    parser.add_argument("--replace-output", action="store_true")
    args = parser.parse_args(argv)

    stems = (
        "china_involved_study_footprint_1991_2025",
        "china_involved_studies_1991_2025",
        "china_involved_studies_2020_2025",
    )
    owned = [
        *(f"{stem}.{extension}" for stem in stems for extension in ("svg", "png")),
        "china_footprint_by_year_1991_2025.csv",
        "china_involved_studies_by_year_1991_2025.csv",
    ]
    existing = sorted(name for name in owned if (args.outdir / name).exists())
    if existing and not args.replace_output:
        parser.error(f"owned output files already exist; use --replace-output: {existing}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    observations, manifest = load_observations(args.run)
    full_rows, _ = aggregate_china_involvement(observations, 1991, 2025)
    recent_rows = [row for row in full_rows if 2020 <= row["Year"] <= 2025]
    total_rows = [
        {"Year": row["Year"], "China-Involved Studies": row["All China-Involved Studies"]}
        for row in full_rows
    ]
    write_csv(args.outdir / "china_footprint_by_year_1991_2025.csv", full_rows)
    write_csv(args.outdir / "china_involved_studies_by_year_1991_2025.csv", total_rows)

    footprint_path = args.outdir / "china_involved_study_footprint_1991_2025.svg"
    full_path = args.outdir / "china_involved_studies_1991_2025.svg"
    recent_path = args.outdir / "china_involved_studies_2020_2025.svg"
    footprint_chart_svg(full_rows, footprint_path)
    china_involved_studies_chart_svg(full_rows, full_path)
    china_involved_studies_chart_svg(recent_rows, recent_path)
    for svg_path in (footprint_path, full_path, recent_path):
        svg_to_png(svg_path, svg_path.with_suffix(".png"))

    print(json.dumps({
        "outdir": str(args.outdir),
        "snapshot": str(args.run),
        "snapshot_timestamp": manifest["harvest_timestamp_utc"],
        "eligible_observations": len(observations),
        "outputs": owned,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
