"""可視化: 滞在時間の横棒グラフと、ゾーンで色分けしたタイムライン。"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


PathLike = Union[str, Path]


def _zone_colors(zone_names: list[str]) -> dict[str, tuple]:
    """ゾーン名 -> RGBA 色のマップ。tab10 カラーマップを順に当てる。"""
    cmap = plt.get_cmap("tab10")
    colors = {}
    for i, name in enumerate(zone_names):
        if name == "Unknown":
            colors[name] = (0.6, 0.6, 0.6, 1.0)
        else:
            colors[name] = cmap(i % 10)
    return colors


def plot_time_in_zones(
    summary: pd.DataFrame,
    metric: str,
    output_path: PathLike | None = None,
    title: str | None = None,
) -> plt.Figure:
    """ゾーン別滞在時間の横棒グラフを描画する。

    `summary` は `time_in_zones()` の戻り値を想定。
    """
    zone_names = list(summary["zone"])
    colors = _zone_colors(zone_names)

    fig, ax = plt.subplots(figsize=(8, max(3, 0.5 * len(zone_names) + 1.5)))
    y = np.arange(len(zone_names))
    ax.barh(y, summary["time_min"], color=[colors[n] for n in zone_names])
    ax.set_yticks(y)
    ax.set_yticklabels(zone_names)
    ax.invert_yaxis()
    ax.set_xlabel("Time in zone (min)")
    ax.set_title(title or f"Time in zones ({metric})")

    # 各バーの右に「分:秒 (%)」を注記。
    for i, row in summary.reset_index(drop=True).iterrows():
        minutes = int(row["time_s"] // 60)
        seconds = int(round(row["time_s"] - minutes * 60))
        label = f"  {minutes}:{seconds:02d}  ({row['pct']:.1f}%)"
        ax.text(row["time_min"], i, label, va="center", fontsize=9)

    # 注記が切れないよう右端に余白を確保。
    xmax = max(summary["time_min"].max() * 1.25, 1.0)
    ax.set_xlim(0, xmax)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=120)
    return fig


def plot_timeline(
    df: pd.DataFrame,
    metric: str,
    zones: list[dict],
    output_path: PathLike | None = None,
    title: str | None = None,
) -> plt.Figure:
    """時系列の指標値を、ゾーンで色分けした散布で描画する。

    `df` は prepare() + classify_zones() 済みで、
    `elapsed_s`, `<metric>`, `zone` 列を持つ前提。
    """
    if "elapsed_s" not in df.columns or metric not in df.columns:
        raise KeyError(f"必要な列がありません: elapsed_s, {metric}")

    zone_names = [z["name"] for z in zones]
    if "Unknown" in df["zone"].unique():
        zone_names = zone_names + ["Unknown"]
    colors = _zone_colors(zone_names)

    fig, ax = plt.subplots(figsize=(10, 4))
    t_min = df["elapsed_s"] / 60.0
    ax.scatter(
        t_min,
        df[metric],
        c=[colors.get(z, (0.6, 0.6, 0.6, 1.0)) for z in df["zone"]],
        s=6,
    )

    ax.set_xlabel("Elapsed time (min)")
    ax.set_ylabel(metric)
    ax.set_title(title or f"{metric} timeline")

    # split_s は「小さい方が速い」ので Y 軸を反転すると直感的。
    if metric == "split_s":
        ax.invert_yaxis()

    handles = [Patch(color=colors[n], label=n) for n in zone_names]
    ax.legend(handles=handles, loc="upper right", fontsize=8, framealpha=0.9)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=120)
    return fig
