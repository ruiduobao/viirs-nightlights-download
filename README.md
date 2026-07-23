# VIIRS Nightlights Downloader · VIIRS 夜间灯光下载器

> 下载 **VIIRS 夜间灯光**年度/月度合成数据。
> 数据来源为 EOG (Earth Observation Group) 公开数据。
> MIT-0 开源。

[English](#quickstart) | 中文

## 为什么做这个

夜间灯光数据广泛用于城市化进程评估、GDP 空间化、人口估算、
灾害影响评估等研究。NOAA EOG 提供的 VIIRS 夜间灯光数据免费公开，
但下载流程需要手动选择产品、年份、瓦片。本 skill 自动化了整个流程。

## Quickstart / 快速开始

```bash
# 安装依赖
pip install 'requests>=2.28.0'

# 搜索可用的夜间灯光数据
python viirs-nightlights-download.py search \
    --year 2023 \
    --bbox 116.0 39.0 117.0 40.0

# 下载年度合成数据
python viirs-nightlights-download.py download \
    --year 2023 \
    --type annual \
    --bbox 116.0 39.0 117.0 40.0 \
    --output-dir ./nightlights_data

# 下载月度合成数据
python viirs-nightlights-download.py download \
    --year 2023 --month 6 \
    --type monthly \
    --output-dir ./nightlights_data
```

## 数据源 / Data Source

| 来源 | URL | 凭证 |
|---|---|---|
| **EOG**（默认） | `https://eogdata.mines.edu/products/vnl/` | 无 |

> **License** — VIIRS 夜间灯光数据由 NOAA/EOG 发布，**公共领域**。

## 支持的产品 / Supported Products

| 产品 | 说明 | 分辨率 |
|---|---|---|
| **VNL Annual** | 年度平均辐射度合成 | 15 arc-second (~500m) |
| **VNL Monthly** | 月度平均辐射度合成 | 15 arc-second (~500m) |
| **VCMCFG** | 无云、无杂散光版本 | 15 arc-second |

## 参数一览 / Parameters

| 参数 | 说明 | 必填 |
|---|---|---|
| `--year` | 年份（2012-2024） | ✅ |
| `--month` | 月份（1-12，仅月度数据） | ❌ |
| `--type` | `annual` / `monthly`（默认 `annual`） | ❌ |
| `--bbox` | 地理范围 `[minLon minLat maxLon maxLat]` | ❌ |
| `--download` | 触发实际下载 | ❌ |
| `--output-dir` | 下载目录（默认 `./nightlights_data`） | ❌ |

## License

MIT-0（详见 [LICENSE](./LICENSE)）。
VIIRS 夜间灯光数据 © NOAA/EOG，公共领域。
