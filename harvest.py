#!/usr/bin/env python3
"""Harvest the minimum ClinicalTrials.gov API v2 fields into an auditable snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ",".join([
    "NCTId", "BriefTitle", "StudyType", "OverallStatus", "StartDate", "StartDateType",
    "LocationFacility", "LocationCity", "LocationState", "LocationZip", "LocationCountry",
])


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def nct_id(study: dict) -> str | None:
    return study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")


def request_json(url: str, *, user_agent: str, timeout: float, retries: int, base: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            temporary = exc.code == 429 or 500 <= exc.code <= 599
            if not temporary or attempt == retries:
                raise RuntimeError(f"API request failed with HTTP {exc.code}: {url}") from exc
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else base * 2**attempt
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                raise RuntimeError(f"API request failed after {retries + 1} attempts: {exc}") from exc
            delay = base * 2**attempt
        time.sleep(delay + random.uniform(0, min(0.5, delay / 4)))
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=Path("runs"))
    parser.add_argument("--resume-run", type=Path, help="Resume an incomplete run from its last raw page")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--limit-pages", type=int)
    args = parser.parse_args(argv)
    if args.limit_pages is not None and args.limit_pages < 1:
        parser.error("--limit-pages must be at least 1")
    if args.resume_run and args.limit_pages is not None:
        parser.error("--resume-run cannot be combined with --limit-pages")

    cfg = load_config(args.config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_params = {"format": "json", "pageSize": str(cfg.get("page_size", 1000)), "fields": FIELDS}
    files: list[dict] = []
    all_ids: list[str] = []
    next_token_remaining = False
    resumed_from_page = 0

    if args.resume_run:
        run_dir = args.resume_run
        raw_dir = run_dir / "raw"
        if (run_dir / "manifest.json").exists():
            parser.error("completed or manifested runs cannot be resumed")
        page_paths = sorted(raw_dir.glob("page_*.json")) if raw_dir.is_dir() else []
        if not page_paths:
            parser.error("resume run has no raw pages")
        token = None
        for expected_page, page_path in enumerate(page_paths, 1):
            if page_path.name != f"page_{expected_page:06d}.json":
                parser.error("resume run raw pages are not a contiguous sequence")
            payload = json.loads(page_path.read_text(encoding="utf-8"))
            studies = payload.get("studies")
            if not isinstance(studies, list):
                parser.error(f"resume page has no valid studies array: {page_path}")
            files.append({"path": str(page_path.relative_to(run_dir)), "sha256": sha256(page_path), "study_count": len(studies)})
            for study in studies:
                value = nct_id(study)
                if not value:
                    parser.error(f"resume page contains a record without NCT ID: {page_path}")
                all_ids.append(value)
            token = payload.get("nextPageToken")
            if expected_page < len(page_paths) and not token:
                parser.error(f"resume page {expected_page} has no token for the following saved page")
        page = len(page_paths)
        resumed_from_page = page
        failure_marker = run_dir / "HARVEST_FAILED.txt"
        if failure_marker.exists():
            failure_marker.replace(run_dir / f"HARVEST_FAILED_BEFORE_RESUME_{stamp}.txt")
    else:
        run_dir = args.outdir / f"run_{stamp}"
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=False)
        token = None
        page = 0

    try:
        while token or page == 0:
            params = dict(base_params)
            if token:
                params["pageToken"] = token
            url = cfg["api_endpoint"] + "?" + urllib.parse.urlencode(params)
            payload = request_json(
                url, user_agent=cfg["user_agent"], timeout=cfg.get("request_timeout_seconds", 60),
                retries=cfg.get("max_retries", 6), base=cfg.get("retry_base_seconds", 1.0),
            )
            page += 1
            studies = payload.get("studies")
            if not isinstance(studies, list):
                raise RuntimeError(f"Page {page} has no valid studies array")
            page_path = raw_dir / f"page_{page:06d}.json"
            page_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            files.append({"path": str(page_path.relative_to(run_dir)), "sha256": sha256(page_path), "study_count": len(studies)})
            for study in studies:
                value = nct_id(study)
                if not value:
                    raise RuntimeError(f"Page {page} contains a record without NCT ID")
                all_ids.append(value)
            token = payload.get("nextPageToken")
            if args.limit_pages and page >= args.limit_pages:
                next_token_remaining = bool(token)
                break
            if not token:
                break
            print(f"Harvested page {page} ({len(all_ids):,} raw studies)...", file=sys.stderr)
    except Exception as exc:
        (run_dir / "HARVEST_FAILED.txt").write_text(str(exc) + "\n", encoding="utf-8")
        raise

    unique = len(set(all_ids))
    complete = not next_token_remaining and not token
    duplicates = len(all_ids) - unique
    manifest = {
        "schema_version": 1,
        "harvest_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "api_endpoint": cfg["api_endpoint"],
        "request_parameters": base_params,
        "limit_pages": args.limit_pages,
        "page_count": page,
        "raw_study_count": len(all_ids),
        "unique_nct_count": unique,
        "duplicate_nct_count": duplicates,
        "snapshot_complete": complete,
        "partial_reason": None if complete else "page limit reached while a next-page token remained",
        "next_page_token_remaining": next_token_remaining,
        "resumed_from_page": resumed_from_page,
        "files": files,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
