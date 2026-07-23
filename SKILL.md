# VIIRS Nightlights Downloader

Download VIIRS nighttime light composite data from public sources (EOG/NOAA VNL, NASA LAADS).

## Usage

```bash
# Search available data
python viirs-nightlights-download.py search --year 2023 --product annual

# Download global annual composite
python viirs-nightlights-download.py download --year 2023 --product annual -o output/

# Download monthly composite
python viirs-nightlights-download.py download --year 2023 --product monthly --month 6 -o output/

# Download regional subset by bbox
python viirs-nightlights-download.py download --year 2023 --product annual --bbox 100,20,120,40 -o output/
```

## Products
- `annual`: Annual cloud-free composite (VNL v2)
- `monthly`: Monthly composite

## Year Range
2012 - 2024

## Requirements
- Python 3.8+
- requests
- tqdm
