---
name: viirs-nightlights-download
description: 'Download VIIRS nighttime light composite data from public sources description: 'Download VIIRS nighttime light composite data from public sources  (EOG/NOAA VNL, NASA LAADS). Supports annual and monthly composites  with regional bbox subsetting.  '
---

# VIIRS Nightlights Downloader

Download VIIRS nighttime light composite data from public sources (EOG/NOAA VNL, NASA LAADS).

## Credentials

EOG (Earth Observation Group, Colorado School of Mines) requires a **free
account** for VNL v2.2 direct download since 2025. The skill does not
authenticate on your behalf; use --list-urls to get the JSON of URLs, then
download manually with wget --user EOG_USER --password '…'.

Optional EOG credentials (for future auto-download):

1. EOG_USERNAME / EOG_PASSWORD env vars
2. ~/.netrc entry for machine eogdata.mines.edu
3. **Default** (geoskill-core credentials.py): empty — register first

Register at https://eogdata.mines.edu/register/ (free, 1-2 days approval).

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

---

## 中文说明

下载 VIIRS 夜间灯光合成数据，支持 EOG/NOAA VNL 和 NASA LAADS 数据源。

### 产品类型

- `annual`：年度云量过滤合成产品（VNL v2）
- `monthly`：月度合成产品

### 年份范围

2012 - 2024

### 使用方法

```bash
# 搜索可用数据
python viirs-nightlights-download.py search --year 2023 --product annual

# 下载全球年度合成
python viirs-nightlights-download.py download --year 2023 --product annual -o output/

# 下载月度合成
python viirs-nightlights-download.py download --year 2023 --product monthly --month 6 -o output/

# 按边界框下载区域子集
python viirs-nightlights-download.py download --year 2023 --product annual --bbox 100,20,120,40 -o output/
```
