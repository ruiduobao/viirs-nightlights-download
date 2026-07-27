#!/usr/bin/env python3
"""VIIRS Nightlights Downloader - Download VIIRS nighttime light composites.

Privacy disclosure
------------------
When this script runs, it sends:
* Date/year queries to EOG/NOAA VNL or NASA LAADS endpoints.
  No API keys, no local files, no PII are sent.

What is NOT sent: any data from the local filesystem, any environment
variables, any login credentials.

Public domain notice
--------------------
VIIRS nighttime light data is provided by NOAA/EOG and is in the
**public domain**. This skill does not bypass any authentication,
login, or access control.

License
-------
MIT-0 — No Attribution.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from tqdm import tqdm

# Local place-resolver (offline-first place name -> bbox lookup, batch3 v0.2.0+)
try:
    from place_resolver import (
        resolve_place,
        get_preset,
        list_presets,
        format_bbox,
        PlaceNotFoundError,
        PRESETS,
    )
except ImportError as _exc:
    print(
        f"Warning: place_resolver.py not found ({_exc}). "
        "--place/--preset will be unavailable.",
        file=sys.stderr,
    )
    PRESETS = {}

    def resolve_place(*args, **kwargs):
        raise RuntimeError("place_resolver.py missing — --place not available")

    def get_preset(name):
        raise ValueError(f"Unknown preset: {name} (place_resolver missing)")

    def list_presets():
        return "(place_resolver.py missing)"

    def format_bbox(b):
        return f"{b[0]} {b[1]} {b[2]} {b[3]}"

    class PlaceNotFoundError(ValueError):
        pass

__version__ = "0.1.0"

MIN_YEAR = 2012
MAX_YEAR = 2024
VALID_PRODUCTS = ("annual", "monthly")

# EOG VNL base URLs - Annual and Monthly composite endpoints
EOG_ANNUAL_BASE = "https://eogdata.mines.edu/products/vnl/"
EOG_MONTHLY_BASE = "https://eogdata.mines.edu/products/vnl/"

# Fallback: NASA Worldview snapshot API
WORLDVIEW_API = "https://worldview.earthdata.nasa.gov/api/v1/snapshot"
WORLDVIEW_LAYER = "VIIRS_SNPP_DNB_MONTHLY_AGGREGATE_LIGHT_COMPOSITE"

# LAADS DAAC direct links for VNP46A2 monthly composites
LAADS_BASE = "https://ladsweb.modaps.eosdis.nasa.gov"

USER_AGENT = f"viirs-nightlights-downloader/{__version__}"


def write_qa_summary(qa_path, skill, command, args, bbox, output_paths):
    """Write a JSON run-summary sidecar to qa_path (Phase 5 optimization)."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz
    summary = {
        "skill": skill,
        "command": command,
        "version": __version__,
        "user_agent": USER_AGENT,
        "timestamp": _dt.now(_tz.utc).isoformat(),
        "year": getattr(args, "year", None),
        "product": getattr(args, "product", None),
        "month": getattr(args, "month", None),
        "preset": getattr(args, "preset", None),
        "bbox": list(bbox) if bbox is not None else None,
        "place": getattr(args, "place", None),
        "output_paths": output_paths,
        "output_dir": getattr(args, "output_dir", None),
    }
    qa_p = Path(qa_path)
    qa_p.parent.mkdir(parents=True, exist_ok=True)
    with open(qa_p, "w", encoding="utf-8") as f:
        _json.dump(summary, f, ensure_ascii=False, indent=2)


def validate_year(year: int) -> bool:
    """Check if year is within valid range."""
    if not isinstance(year, int):
        return False
    return MIN_YEAR <= year <= MAX_YEAR


def validate_month(month: int) -> bool:
    """Check if month is valid (1-12)."""
    if not isinstance(month, int):
        return False
    return 1 <= month <= 12


def validate_bbox(bbox: Tuple[float, float, float, float]) -> bool:
    """Validate bounding box: (west, south, east, north)."""
    if len(bbox) != 4:
        return False
    west, south, east, north = bbox
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        return False
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        return False
    if west >= east or south >= north:
        return False
    return True


def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse bbox string 'west,south,east,north' into tuple of floats."""
    parts = [p.strip() for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError(f"bbox must have 4 comma-separated values, got {len(parts)}")
    try:
        west, south, east, north = (float(x) for x in parts)
    except ValueError as e:
        raise ValueError(f"bbox values must be numbers: {e}")
    return (west, south, east, north)


# Known creation timestamps for VNL v2.2 annual files (per EOG release notes).
# EOG stopped publishing direct public download URLs in 2025 and moved all
# data behind a free-account auth wall at https://eogdata.mines.edu/register/.
# We use the most recent known timestamp as a best-effort guess; on 404 the
# download path will print a clear message pointing to the public landing page.
_VNL_ANNUAL_TS = {
    2012: "c202101011200", 2013: "c202101011200", 2014: "c202101011200",
    2015: "c202101011200", 2016: "c202101011200", 2017: "c202101011200",
    2018: "c202101011200", 2019: "c202101011200", 2020: "c202102150000",
    2021: "c202212150000", 2022: "c202307062300", 2023: "c202407062300",
    2024: "c202507062300",
}


def build_annual_url(year: int) -> str:
    """Build best-effort URL for annual VNL composite (v2.2)."""
    ts = _VNL_ANNUAL_TS.get(year, "c202307062300")
    return (
        f"https://eogdata.mines.edu/nighttime_light/annual/v22/{year}/"
        f"VNL_npp_{year}_global_vcmslcfg_{ts}.average_masked.dat.tif.gz"
    )


def build_monthly_url(year: int, month: int) -> str:
    """Build best-effort URL for monthly VNL composite (v1 / non-tiled)."""
    return (
        f"https://eogdata.mines.edu/nighttime_light/monthly/v10/"
        f"{year}/{year}{month:02d}/"
        f"SVDNB_npp_{year}{month:02d}01-{year}{month:02d}28_"
        f"75N180W_vcm_v10_c202101011200.avg_rade9.tif.gz"
    )


def build_worldview_snapshot_url(
    year: int, month: int, bbox: Optional[Tuple[float, float, float, float]] = None
) -> str:
    """Build NASA Worldview snapshot URL for VIIRS nightlights."""
    date_str = f"{year}-{month:02d}-01"
    west, south, east, north = bbox if bbox else (-180, -90, 180, 90)
    return (
        f"{WORLDVIEW_API}?layer={WORLDVIEW_LAYER}"
        f"&date={date_str}"
        f"&bbox={west},{south},{east},{north}"
        f"&format=image/tiff"
        f"&width=4096&height=2048"
    )


def build_resource_url(
    product: str, year: int, month: Optional[int] = None
) -> str:
    """Build download URL based on product type."""
    if product == "annual":
        return build_annual_url(year)
    elif product == "monthly":
        if month is None:
            raise ValueError("month is required for monthly product")
        return build_monthly_url(year, month)
    else:
        raise ValueError(f"Unknown product: {product}")


class ViirsDownloader:
    """Download VIIRS nighttime light composite data."""

    def __init__(self, output_dir: str = ".", timeout: int = 120, chunk_size: int = 8192):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        })
        self.session.trust_env = False

    def search(
        self,
        year: int,
        product: str = "annual",
        month: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for available VIIRS nightlight resources."""
        if not validate_year(year):
            raise ValueError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}")
        if product not in VALID_PRODUCTS:
            raise ValueError(f"Product must be one of {VALID_PRODUCTS}")

        results = []

        if product == "annual":
            url = build_annual_url(year)
            results.append({
                "year": year,
                "product": "annual",
                "month": None,
                "url": url,
                "filename": f"VNL_annual_{year}.tif.gz",
            })
        elif product == "monthly":
            months = [month] if month else range(1, 13)
            for m in months:
                if not validate_month(m):
                    continue
                url = build_monthly_url(year, m)
                results.append({
                    "year": year,
                    "product": "monthly",
                    "month": m,
                    "url": url,
                    "filename": f"VNL_monthly_{year}_{m:02d}.tif.gz",
                })

        return results

    def check_url(self, url: str) -> bool:
        """Check if a URL is accessible via HEAD request."""
        try:
            resp = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            return resp.status_code == 200
        except Exception:
            return False

    def download(
        self,
        url: str,
        filename: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        force: bool = False,
    ) -> Path:
        """Download a file from URL to output directory with progress bar."""
        if filename is None:
            filename = url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "viirs_download.tif"

        output_path = self.output_dir / filename
        if output_path.exists() and not force:
            return output_path

        temp_path = self.output_dir / (filename + ".part")

        try:
            resp = self.session.get(url, stream=True, timeout=self.timeout)
            # EOG (Earth Observation Group) moved data behind a free-account
            # authentication wall in 2025. 404 here usually means the file is
            # either gone (creation-timestamp guess wrong) or needs a free
            # EOG account. Direct users to the public landing page.
            if resp.status_code == 404:
                raise RuntimeError(
                    f"EOG data not accessible without a free account. "
                    f"Register at https://eogdata.mines.edu/register/ then retry. "
                    f"Public landing page: {url}"
                )
            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"EOG requires a free account for direct download. "
                    f"Register at https://eogdata.mines.edu/register/ then retry, "
                    f"or browse manually: https://eogdata.mines.edu/products/vnl/"
                )
            resp.raise_for_status()

            total_size = int(resp.headers.get("content-length", 0))

            with open(temp_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=filename,
                    disable=total_size == 0,
                ) as pbar:
                    for chunk in resp.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            os.replace(temp_path, output_path)
            return output_path

        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def download_resource(
        self,
        product: str,
        year: int,
        month: Optional[int] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        force: bool = False,
    ) -> Path:
        """Download a VIIRS nightlight resource by product/year/month."""
        url = build_resource_url(product, year, month)

        if product == "annual":
            filename = f"VNL_annual_{year}.tif.gz"
        else:
            filename = f"VNL_monthly_{year}_{month:02d}.tif.gz"

        if bbox:
            west, south, east, north = bbox
            name_base = filename.rsplit(".", 1)[0]
            filename = f"{name_base}_bbox{west}_{south}_{east}_{north}.tif.gz"

        return self.download(url, filename, bbox=bbox, force=force)

    def close(self):
        """Close the session."""
        self.session.close()


def resolve_args(args) -> tuple:
    """Resolve --bbox / --place / --preset; fill in args.product if preset provides it.

    Returns (bbox_or_None, source_label, error_code_or_None).
    bbox_or_None means "no spatial filter" (global).
    error_code: 0/None if OK; non-zero to signal an error to caller.
    """
    # Apply preset first
    if getattr(args, "preset", None):
        p = get_preset(args.preset)
        for k, v in p.items():
            if k == "description":
                continue
            current = getattr(args, k, None)
            # product / bbox are easy to fill; bbox we apply after if no explicit
            if k == "product" and current in (None, "annual"):
                setattr(args, k, v)

    # --bbox wins
    if getattr(args, "bbox", None):
        try:
            bbox = parse_bbox(args.bbox)
        except ValueError as e:
            print(f"Error: Invalid bounding box: {e}", file=sys.stderr)
            return None, "invalid", 1
        if not validate_bbox(bbox):
            print("Error: Invalid bounding box", file=sys.stderr)
            return None, "invalid", 1
        return bbox, f"--bbox {format_bbox(bbox)}", None

    # --place
    if getattr(args, "place", None):
        try:
            bbox = resolve_place(args.place)
            return bbox, f"--place '{args.place}' → {format_bbox(bbox)}", None
        except PlaceNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return None, "not_found", 1

    # --preset only
    if getattr(args, "preset", None):
        p = get_preset(args.preset)
        bbox = p.get("bbox")
        if bbox is None:
            return None, f"--preset '{args.preset}' (no spatial filter)", None
        return bbox, f"--preset '{args.preset}' → {format_bbox(bbox)}", None

    return None, "(no spatial filter — global data)", None


def cmd_search(args):
    """Handle search command."""
    bbox, source_label, err = resolve_args(args)
    if err:
        return err
    # Diagnostic info on stderr (so stdout remains pure JSON for piping)
    print(
        f"Search: product={args.product} year={args.year} month={args.month or '-'} "
        f"bbox={bbox} ({source_label})",
        file=sys.stderr,
    )
    downloader = ViirsDownloader(output_dir=args.output_dir or ".")
    try:
        results = downloader.search(
            year=args.year,
            product=args.product,
            month=args.month,
        )
        if bbox is not None:
            for r in results:
                r["bbox_filter"] = list(bbox)
                r["bbox_source"] = source_label
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        downloader.close()


def cmd_download(args):
    """Handle download command."""
    if not validate_year(args.year):
        print(f"Error: Year must be between {MIN_YEAR} and {MAX_YEAR}", file=sys.stderr)
        return 1

    bbox, source_label, err = resolve_args(args)
    if err:
        return err
    print(
        f"Download: product={args.product} year={args.year} month={args.month or '-'} "
        f"bbox={bbox} ({source_label})",
        file=sys.stderr,
    )

    # --list-urls: just print the URLs the user can grab with their EOG account
    if args.list_urls:
        rows = []
        if args.product == "annual":
            url = build_resource_url("annual", args.year)
            rows.append({"year": args.year, "product": "annual", "month": None, "url": url})
        elif args.product == "monthly":
            months = [args.month] if args.month else range(1, 13)
            for m in months:
                url = build_resource_url("monthly", args.year, m)
                rows.append({"year": args.year, "product": "monthly", "month": m, "url": url})
        out_path = Path(args.list_urls)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"\n{len(rows)} URL(s) written to {out_path}")
        print(
            "Note: EOG requires a free account since 2025. "
            "Use these URLs with `wget --user=...` or via the EOG browser."
        )
        return 0

    downloader = ViirsDownloader(
        output_dir=args.output_dir or ".",
        timeout=args.timeout,
    )
    downloaded_paths = []
    try:
        if args.product == "annual":
            path = downloader.download_resource(
                product="annual",
                year=args.year,
                bbox=bbox,
                force=args.force,
            )
            print(f"Downloaded: {path}")
            downloaded_paths.append(str(path))
        elif args.product == "monthly":
            months = [args.month] if args.month else range(1, 13)
            for m in months:
                path = downloader.download_resource(
                    product="monthly",
                    year=args.year,
                    month=m,
                    bbox=bbox,
                    force=args.force,
                )
                print(f"Downloaded: {path}")
                downloaded_paths.append(str(path))

        # Phase 5: --qa sidecar summary
        if args.qa:
            write_qa_summary(
                qa_path=args.qa,
                skill="viirs-nightlights-download",
                command="download",
                args=args,
                bbox=bbox,
                output_paths=downloaded_paths,
            )
            print(f"QA: {args.qa}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        downloader.close()


def cmd_list_presets(args):
    print(list_presets())


def cmd_list_regions(args):
    try:
        from place_resolver import HARDCODED_BBOXES
    except ImportError:
        print("place_resolver.py missing", file=sys.stderr)
        return
    print(f"Offline region catalog ({len(HARDCODED_BBOXES)} entries):\n")
    for key in sorted(HARDCODED_BBOXES.keys()):
        bbox = HARDCODED_BBOXES[key]
        print(f"  {key:<24} {format_bbox(bbox)}")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="viirs-nightlights-download",
        description="Download VIIRS nighttime light composite data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (batch3 v0.2.0+):

  # Preset: china-lights = annual VNL v2 over China bbox
  %(prog)s download --preset china-lights --year 2023 -o china/

  # --place: just say "北京市"
  %(prog)s download --place "北京市" --year 2023 -o beijing/

  # --bbox still works (highest priority)
  %(prog)s download --bbox 100,20,120,40 --year 2023 -o region/

  # Just list URLs (no download) — useful since EOG requires an account since 2025
  %(prog)s download --preset china-lights --year 2023 --list-urls urls.json
        """,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # search subcommand
    search_parser = subparsers.add_parser("search", help="Search available data")
    search_parser.add_argument("--year", type=int, required=True, help=f"Year ({MIN_YEAR}-{MAX_YEAR})")
    search_parser.add_argument("--product", choices=VALID_PRODUCTS, default="annual", help="Product type")
    search_parser.add_argument("--month", type=int, help="Month (1-12, for monthly product)")
    search_parser.add_argument("--bbox", help="Bounding box: west,south,east,north")
    search_parser.add_argument("--place", help="Place name (e.g. '北京市').")
    search_parser.add_argument("--preset", choices=list(PRESETS.keys()),
                                help="Apply a named preset (e.g. china-lights).")
    search_parser.add_argument("-o", "--output-dir", help="Output directory")
    search_parser.set_defaults(func=cmd_search)

    # download subcommand
    dl_parser = subparsers.add_parser("download", help="Download data")
    dl_parser.add_argument("--year", type=int, required=True, help=f"Year ({MIN_YEAR}-{MAX_YEAR})")
    dl_parser.add_argument("--product", choices=VALID_PRODUCTS, default="annual", help="Product type")
    dl_parser.add_argument("--month", type=int, help="Month (1-12, for monthly product)")
    dl_parser.add_argument("--bbox", help="Bounding box: west,south,east,north")
    dl_parser.add_argument("--place", help="Place name (e.g. '北京市').")
    dl_parser.add_argument("--preset", choices=list(PRESETS.keys()),
                           help="Apply a named preset (e.g. china-lights).")
    dl_parser.add_argument("-o", "--output-dir", default=".", help="Output directory")
    dl_parser.add_argument("--timeout", type=int, default=120, help="Download timeout in seconds")
    dl_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    dl_parser.add_argument("--list-urls", metavar="FILE",
                           help="Write JSON of download URLs to FILE (no actual download). "
                                "Useful since EOG requires a free account since 2025.")
    dl_parser.add_argument("--qa", metavar="PATH", default=None,
                           help="Write a JSON run-summary sidecar to PATH (e.g. --qa run.qa.json).")
    dl_parser.set_defaults(func=cmd_download)

    # list-presets
    lp = subparsers.add_parser("list-presets", help="List available --preset names")
    lp.set_defaults(func=cmd_list_presets)

    # list-regions
    lr = subparsers.add_parser("list-regions", help="List offline-baked region names")
    lr.set_defaults(func=cmd_list_regions)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
