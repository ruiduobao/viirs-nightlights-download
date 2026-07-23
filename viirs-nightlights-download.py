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


def build_annual_url(year: int) -> str:
    """Build URL for annual VNL composite."""
    return (
        f"https://eogdata.mines.edu/products/vnl/v2/"
        f"{year}/annual/"
        f"VNL_v2_npp-j{year}_vcmslcfg_v2_c202303062300.average_masked.dat.tif.gz"
    )


def build_monthly_url(year: int, month: int) -> str:
    """Build URL for monthly VNL composite."""
    return (
        f"https://eogdata.mines.edu/products/vnl/v2/"
        f"{year}/monthly/"
        f"VNL_v2_npp-j{year}{month:02d}_vcmslcfg_v2_c202303062300.average_masked.dat.tif.gz"
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


def cmd_search(args):
    """Handle search command."""
    downloader = ViirsDownloader(output_dir=args.output_dir or ".")
    try:
        results = downloader.search(
            year=args.year,
            product=args.product,
            month=args.month,
        )
        print(json.dumps(results, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        downloader.close()


def cmd_download(args):
    """Handle download command."""
    downloader = ViirsDownloader(
        output_dir=args.output_dir or ".",
        timeout=args.timeout,
    )
    try:
        bbox = None
        if args.bbox:
            bbox = parse_bbox(args.bbox)
            if not validate_bbox(bbox):
                print("Error: Invalid bounding box", file=sys.stderr)
                return 1

        if args.product == "annual":
            path = downloader.download_resource(
                product="annual",
                year=args.year,
                bbox=bbox,
                force=args.force,
            )
            print(f"Downloaded: {path}")
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

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        downloader.close()


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="viirs-nightlights-download",
        description="Download VIIRS nighttime light composite data.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # search subcommand
    search_parser = subparsers.add_parser("search", help="Search available data")
    search_parser.add_argument("--year", type=int, required=True, help=f"Year ({MIN_YEAR}-{MAX_YEAR})")
    search_parser.add_argument("--product", choices=VALID_PRODUCTS, default="annual", help="Product type")
    search_parser.add_argument("--month", type=int, help="Month (1-12, for monthly product)")
    search_parser.add_argument("-o", "--output-dir", help="Output directory")
    search_parser.set_defaults(func=cmd_search)

    # download subcommand
    dl_parser = subparsers.add_parser("download", help="Download data")
    dl_parser.add_argument("--year", type=int, required=True, help=f"Year ({MIN_YEAR}-{MAX_YEAR})")
    dl_parser.add_argument("--product", choices=VALID_PRODUCTS, default="annual", help="Product type")
    dl_parser.add_argument("--month", type=int, help="Month (1-12, for monthly product)")
    dl_parser.add_argument("--bbox", help="Bounding box: west,south,east,north")
    dl_parser.add_argument("-o", "--output-dir", default=".", help="Output directory")
    dl_parser.add_argument("--timeout", type=int, default=120, help="Download timeout in seconds")
    dl_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    dl_parser.set_defaults(func=cmd_download)

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
