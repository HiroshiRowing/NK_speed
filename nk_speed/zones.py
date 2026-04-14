"""強度ゾーンの定義と、ゾーン別滞在時間の集計。

ゾーンは list[dict] で表現する:

    [
      {"name": "UT2", "min": 16, "max": 22},
      {"name": "UT1", "min": 22, "max": 26},
      ...
    ]

- `min` は下限(含む)、`max` は上限(含まない)。
- 先頭ゾーンの `min` を省略すると -inf、末尾ゾーンの `max` を省略すると +inf。
- スプリット(split_s)のように "値が小さいほど強度が高い" 指標でも、そのまま
  秒で境界を指定すればよい(例: `{"name":"AT","min":110,"max":120}` は 1:50–2:00)。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

import numpy as np
import pandas as pd
import yaml


PathLike = Union[str, Path]


# 代表的な指標ごとのデフォルトプリセット。
# 初回利用者でもそのまま動かせるよう、漕艇界で広く使われる 5 段階ゾーンに合わせた。
DEFAULT_PRESETS: dict[str, list[dict]] = {
    "spm": [
        {"name": "R (~16)",     "max": 16},
        {"name": "UT2 (16-21)", "min": 16, "max": 22},
        {"name": "UT1 (22-25)", "min": 22, "max": 26},
        {"name": "AT (26-29)",  "min": 26, "max": 30},
        {"name": "TR (30-33)",  "min": 30, "max": 34},
        {"name": "AN (34+)",    "min": 34},
    ],
    "hr": [
        {"name": "Z1 (~130)",    "max": 130},
        {"name": "Z2 (130-149)", "min": 130, "max": 150},
        {"name": "Z3 (150-164)", "min": 150, "max": 165},
        {"name": "Z4 (165-179)", "min": 165, "max": 180},
        {"name": "Z5 (180+)",    "min": 180},
    ],
    # split_s は「秒/500m」。小さいほど速い。
    "split_s": [
        {"name": "UT2 (2:10+)",       "min": 130},
        {"name": "UT1 (2:00-2:09)",   "min": 120, "max": 130},
        {"name": "AT  (1:50-1:59)",   "min": 110, "max": 120},
        {"name": "TR  (1:40-1:49)",   "min": 100, "max": 110},
        {"name": "AN  (~1:39)",       "max": 100},
    ],
    "power": [
        {"name": "Z1 (~150W)",     "max": 150},
        {"name": "Z2 (150-199W)",  "min": 150, "max": 200},
        {"name": "Z3 (200-249W)",  "min": 200, "max": 250},
        {"name": "Z4 (250-299W)",  "min": 250, "max": 300},
        {"name": "Z5 (300W+)",     "min": 300},
    ],
}


def load_zones(path: PathLike) -> tuple[str, list[dict]]:
    """YAML からゾーン設定を読み込む。戻り値は (metric, zones)。

    YAML フォーマット:
        metric: spm
        zones:
          - {name: UT2, min: 16, max: 22}
          - {name: UT1, min: 22, max: 26}
    """
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"{path} のフォーマットが不正です (dict でない)")
    metric = cfg.get("metric")
    zones = cfg.get("zones")
    if not metric or not zones:
        raise ValueError(f"{path} に 'metric' と 'zones' を指定してください")
    return metric, list(zones)


def _in_zone(value: float, zone: dict, is_last: bool) -> bool:
    if pd.isna(value):
        return False
    lo = zone.get("min", -np.inf)
    hi = zone.get("max", np.inf)
    if is_last:
        # 最終ゾーンは上端を含める(デフォルトの +inf ならどのみち同じ)。
        return lo <= value <= hi
    return lo <= value < hi


def classify_zones(series: Iterable[float], zones: list[dict]) -> list[str]:
    """各値をゾーン名に割り当てる。該当なしは "Unknown"。"""
    labels: list[str] = []
    last = zones[-1] if zones else None
    for v in series:
        label = "Unknown"
        for z in zones:
            if _in_zone(v, z, is_last=(z is last)):
                label = z["name"]
                break
        labels.append(label)
    return labels


def time_in_zones(
    df: pd.DataFrame,
    zones: list[dict],
    zone_col: str = "zone",
    dt_col: str = "dt_s",
) -> pd.DataFrame:
    """ゾーン別の滞在時間と割合を集計する。

    `zones` の並び順でソートし、元データに現れないゾーンも 0 秒として残す。
    """
    if dt_col not in df.columns:
        raise KeyError(f"'{dt_col}' 列がありません。prepare() 済みの DataFrame を渡してください")
    if zone_col not in df.columns:
        raise KeyError(f"'{zone_col}' 列がありません。classify_zones の結果を代入してから呼んでください")

    agg = df.groupby(zone_col, dropna=False)[dt_col].sum()
    total = agg.sum()

    ordered_names = [z["name"] for z in zones]
    # "Unknown" があれば末尾に足す。
    if "Unknown" in agg.index and "Unknown" not in ordered_names:
        ordered_names = ordered_names + ["Unknown"]

    rows = []
    for name in ordered_names:
        seconds = float(agg.get(name, 0.0))
        rows.append(
            {
                "zone": name,
                "time_s": seconds,
                "time_min": seconds / 60.0,
                "pct": (seconds / total * 100.0) if total > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)
