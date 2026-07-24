---
description: 'Download VIIRS nighttime light composite data from public sources

  (EOG/NOAA VNL, NASA LAADS). Supports annual and monthly composites

  with regional bbox subsetting.

  '
name: viirs-nightlights-download
---

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
