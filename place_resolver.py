"""place_resolver.py — Phase 1+ adapter shim 模板

委托给 vendored _geoskill_core.aoi。返回 (W, S, E, N) tuple，保留老接口。

本文件是模板，由 build_per_skill_shim.py 注入各 skill 自己的 HARDCODED + PRESETS。
每个 skill 内部独立运行（不依赖运行时跨 skill 共享）。
"""
from __future__ import annotations
import os
import sys
from typing import Tuple

# 优先用 _geoskill_core.aoi
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GEOSKILL_CORE_DIR = os.path.join(_SKILL_DIR, "_geoskill_core")
if os.path.isdir(_GEOSKILL_CORE_DIR) and _GEOSKILL_CORE_DIR not in sys.path:
    sys.path.insert(0, _GEOSKILL_CORE_DIR)
try:
    import aoi as _geoskill_aoi
    _USE_CORE = True
except Exception:  # noqa: BLE001
    _geoskill_aoi = None
    _USE_CORE = False


# ---- PlaceNotFoundError（保留老异常类）----
class PlaceNotFoundError(ValueError):
    """place 解析失败时抛（保留与老实现兼容）"""
    def __init__(self, query, candidates=None):
        msg = f"无法解析地点: {query!r}"
        if candidates:
            msg += f" (candidates: {candidates})"
        super().__init__(msg)
        self.query = query
        self.candidates = candidates or []


# ---- HARDCODED_BBOXES (从 skill 自己的 .legacy 提取)
HARDCODED_BBOXES = {
    '中国': (73.0, 18.0, 135.0, 54.0),
    'china': (73.0, 18.0, 135.0, 54.0),
    'cn': (73.0, 18.0, 135.0, 54.0),
    '长江流域': (90.0, 24.0, 122.0, 36.0),
    '长江': (90.0, 24.0, 122.0, 36.0),
    'yangtze': (90.0, 24.0, 122.0, 36.0),
    'yangtze_river': (90.0, 24.0, 122.0, 36.0),
    '黄河流域': (95.0, 32.0, 119.0, 42.0),
    '黄河': (95.0, 32.0, 119.0, 42.0),
    'yellow_river': (95.0, 32.0, 119.0, 42.0),
    '珠江流域': (97.0, 18.0, 117.0, 27.0),
    '珠江': (97.0, 18.0, 117.0, 27.0),
    '松花江': (119.0, 41.0, 135.0, 51.0),
    '华北': (110.0, 33.0, 125.0, 43.0),
    '东北': (118.0, 38.0, 135.0, 54.0),
    '华东': (113.0, 24.0, 123.0, 38.0),
    '华南': (97.0, 18.0, 125.0, 28.0),
    '华中': (105.0, 25.0, 117.0, 36.0),
    '西南': (97.0, 21.0, 112.0, 35.0),
    '西北': (73.0, 31.0, 110.0, 50.0),
    '北京': (115.7, 39.4, 116.8, 40.3),
    '北京市': (115.7, 39.4, 116.8, 40.3),
    'beijing': (115.7, 39.4, 116.8, 40.3),
    '上海': (120.8, 30.7, 122.2, 31.9),
    '上海市': (120.8, 30.7, 122.2, 31.9),
    'shanghai': (120.8, 30.7, 122.2, 31.9),
    '广州': (112.9, 22.4, 114.0, 23.6),
    '广州市': (112.9, 22.4, 114.0, 23.6),
    'guangzhou': (112.9, 22.4, 114.0, 23.6),
    '深圳': (113.8, 22.4, 114.6, 22.9),
    '深圳市': (113.8, 22.4, 114.6, 22.9),
    'shenzhen': (113.8, 22.4, 114.6, 22.9),
    '成都': (103.7, 30.4, 104.4, 31.0),
    '成都市': (103.7, 30.4, 104.4, 31.0),
    'chengdu': (103.7, 30.4, 104.4, 31.0),
    '武汉': (113.7, 29.9, 115.0, 31.4),
    '武汉市': (113.7, 29.9, 115.0, 31.4),
    'wuhan': (113.7, 29.9, 115.0, 31.4),
    '西安': (108.7, 34.0, 109.5, 34.7),
    '西安市': (108.7, 34.0, 109.5, 34.7),
    'xian': (108.7, 34.0, 109.5, 34.7),
    '南京': (118.3, 31.2, 119.2, 32.6),
    '南京市': (118.3, 31.2, 119.2, 32.6),
    'nanjing': (118.3, 31.2, 119.2, 32.6),
    '杭州': (118.3, 29.8, 120.2, 30.6),
    '杭州市': (118.3, 29.8, 120.2, 30.6),
    'hangzhou': (118.3, 29.8, 120.2, 30.6),
    '重庆': (105.3, 28.2, 107.5, 30.2),
    '重庆市': (105.3, 28.2, 107.5, 30.2),
    'chongqing': (105.3, 28.2, 107.5, 30.2),
    '美国': (-125.0, 24.0, -66.0, 50.0),
    'usa': (-125.0, 24.0, -66.0, 50.0),
    'us': (-125.0, 24.0, -66.0, 50.0),
    '日本': (128.0, 30.0, 146.0, 46.0),
    'japan': (128.0, 30.0, 146.0, 46.0),
    '全球': (-180.0, -90.0, 180.0, 90.0),
    'global': (-180.0, -90.0, 180.0, 90.0),
    'world': (-180.0, -90.0, 180.0, 90.0),
    '亚洲': (25.0, -11.0, 180.0, 81.0),
    'asia': (25.0, -11.0, 180.0, 81.0),
    '欧洲': (-25.0, 34.0, 45.0, 72.0),
    'europe': (-25.0, 34.0, 45.0, 72.0),
    '非洲': (-18.0, -35.0, 52.0, 38.0),
    'africa': (-18.0, -35.0, 52.0, 38.0),
    'beijing_chaoyang': (116.35, 39.83, 116.65, 40.05),
    '朝阳区': (116.35, 39.83, 116.65, 40.05),
    'chaoyang': (116.35, 39.83, 116.65, 40.05),
}


# ---- PRESETS (从 skill 自己的 .legacy 提取)
PRESETS: Dict[str, Dict] = {
    "china-lights": {
        "bbox": (73.0, 18.0, 135.0, 54.0),
        "product": "annual",
        "description": "中国 VIIRS 年度夜间灯光合成（VNL v2）",
    },
    "beijing-lights": {
        "bbox": (115.7, 39.4, 116.8, 40.3),
        "product": "annual",
        "description": "北京 VIIRS 年度夜间灯光",
    },
    "global-lights": {
        "bbox": (-180.0, -90.0, 180.0, 90.0),
        "product": "annual",
        "description": "全球 VIIRS 年度夜间灯光（数据非常大）",
    },
    "us-lights": {
        "bbox": (-125.0, 24.0, -66.0, 50.0),
        "product": "annual",
        "description": "美国 VIIRS 年度夜间灯光",
    },
}


# ---- resolve_place 主入口 ----

def resolve_place(place: str, buffer_deg: float = 0.0, use_nominatim: bool = True, **kwargs) -> Tuple[float, float, float, float]:
    """Resolve a place name to a bbox (W, S, E, N).

    与老 place_resolver.py 接口兼容：
    - buffer_deg: 在 hardcoded bbox 周围扩展（默认 0 — 老实现 hardcoded 命中不加 buffer）
    - use_nominatim: 是否允许在线 fallback（默认 True，向下兼容老 API）
    - 其它 kwargs 忽略

    Returns:
        (W, S, E, N) tuple（精度 round 到 6 位，避免浮点误差）

    Raises:
        PlaceNotFoundError: 解析失败
    """
    if not place or not place.strip():
        raise PlaceNotFoundError(place)
    # 1. 硬编码（命中后按 buffer_deg 扩展，case-insensitive 匹配）
    place_stripped = place.strip()
    if place_stripped in HARDCODED_BBOXES:
        w, s, e, n = HARDCODED_BBOXES[place_stripped]
        bbox = (w - buffer_deg, s - buffer_deg, e + buffer_deg, n + buffer_deg)
        return tuple(round(x, 6) for x in bbox)  # type: ignore[return-value]
    # 1b. case-insensitive 匹配（与老 place_resolver 一致）
    norm = place_stripped.lower().replace(" ", "")
    for key, bbox in HARDCODED_BBOXES.items():
        if key.lower().replace(" ", "") == norm:
            w, s, e, n = bbox
            out = (w - buffer_deg, s - buffer_deg, e + buffer_deg, n + buffer_deg)
            return tuple(round(x, 6) for x in out)  # type: ignore[return-value]
    # 2. 委托 geoskill_core（fallback，含 Nominatim）
    if _USE_CORE and _geoskill_aoi is not None and use_nominatim:
        try:
            m = _geoskill_aoi.resolve_place(place, buffer_deg=buffer_deg, allow_nominatim=True, use_cache=False)
            if m and m.bbox_wgs84 and len(m.bbox_wgs84) == 4:
                return tuple(round(x, 6) for x in m.bbox_wgs84)  # type: ignore[return-value]
        except Exception:
            pass
    # 3. 兜底硬编码
    raise PlaceNotFoundError(place)


def get_preset(name: str) -> dict:
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}")
    return PRESETS[name]


def list_presets() -> str:
    lines = ["Available presets:"]
    for k, v in PRESETS.items():
        desc = v.get("description", "") if isinstance(v, dict) else ""
        lines.append(f"  {k}: {desc}")
    return "\n".join(lines)


def format_bbox(b) -> str:
    if not b or len(b) != 4:
        return str(b)
    return f"{b[0]} {b[1]} {b[2]} {b[3]}"


__all__ = [
    "HARDCODED_BBOXES", "PRESETS",
    "PlaceNotFoundError", "resolve_place",
    "get_preset", "list_presets", "format_bbox",
]
