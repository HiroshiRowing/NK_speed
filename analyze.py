"""NK SpeedCoach のセッション CSV を強度ゾーン別に集計・可視化する CLI。

使い方:
    python analyze.py <session.csv>
    python analyze.py <session.csv> --metric hr
    python analyze.py <session.csv> --zones my_zones.yaml --output-dir ./out
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from nk_speed import (
    DEFAULT_PRESETS,
    classify_zones,
    load_zones,
    plot_time_in_zones,
    plot_timeline,
    prepare,
    read_nk_csv,
    time_in_zones,
)


def _format_seconds(s: float) -> str:
    minutes = int(s // 60)
    seconds = int(round(s - minutes * 60))
    return f"{minutes}:{seconds:02d}"


def _print_summary(summary: pd.DataFrame, metric: str) -> None:
    total = summary["time_s"].sum()
    print()
    print(f"=== Time in zones ({metric}) ===")
    print(f"{'Zone':<20} {'Time':>8} {'Minutes':>9} {'%':>7}")
    print("-" * 48)
    for _, row in summary.iterrows():
        print(
            f"{row['zone']:<20} "
            f"{_format_seconds(row['time_s']):>8} "
            f"{row['time_min']:>9.2f} "
            f"{row['pct']:>6.1f}%"
        )
    print("-" * 48)
    print(f"{'Total':<20} {_format_seconds(total):>8} {total/60:>9.2f} {100.0:>6.1f}%")
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="NK SpeedCoach セッションのゾーン別滞在時間を集計")
    p.add_argument("csv", type=Path, help="NK SpeedCoach のセッション CSV")
    p.add_argument(
        "--metric",
        choices=sorted(DEFAULT_PRESETS.keys()),
        default="spm",
        help="ゾーン分けに使う指標 (default: spm)",
    )
    p.add_argument(
        "--zones",
        type=Path,
        default=None,
        help="ゾーン設定を書いた YAML (省略時はプリセット)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./nk_output"),
        help="グラフ・集計 CSV の出力先 (default: ./nk_output)",
    )
    p.add_argument(
        "--no-plots",
        action="store_true",
        help="グラフ生成をスキップしてサマリ表のみ表示",
    )
    args = p.parse_args(argv)

    if not args.csv.exists():
        print(f"ERROR: {args.csv} が見つかりません", file=sys.stderr)
        return 2

    # ゾーン読み込み: --zones があれば metric もそちらを優先する。
    if args.zones:
        metric, zones = load_zones(args.zones)
    else:
        metric = args.metric
        zones = DEFAULT_PRESETS[metric]

    raw, metadata = read_nk_csv(args.csv, return_metadata=True)
    df = prepare(raw)

    if metric not in df.columns:
        print(
            f"ERROR: CSV に '{metric}' に対応する列が見つかりませんでした。\n"
            f"  取り込まれた列: {list(df.columns)}",
            file=sys.stderr,
        )
        return 2

    # セッションヘッダ: シリアル番号・セッション名・総距離・総時間があれば表示。
    header_bits = []
    if metadata.serial:
        header_bits.append(f"Serial: {metadata.serial}")
    if metadata.session_name:
        header_bits.append(f"Session: {metadata.session_name}")
    if metadata.total_distance_m is not None:
        header_bits.append(f"Distance: {metadata.total_distance_m:.0f} m")
    if metadata.total_elapsed_str:
        header_bits.append(f"Elapsed: {metadata.total_elapsed_str}")
    if header_bits:
        print()
        print("  ·  ".join(header_bits))

    df["zone"] = classify_zones(df[metric].tolist(), zones)
    summary = time_in_zones(df, zones)
    _print_summary(summary, metric)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "time_in_zones.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Saved: {summary_path}")

    if not args.no_plots:
        bar_path = args.output_dir / "time_in_zones.png"
        timeline_path = args.output_dir / "timeline.png"
        plot_time_in_zones(summary, metric=metric, output_path=bar_path,
                           title=f"Time in zones ({metric}) — {args.csv.stem}")
        plot_timeline(df, metric=metric, zones=zones, output_path=timeline_path,
                      title=f"{metric} timeline — {args.csv.stem}")
        print(f"Saved: {bar_path}")
        print(f"Saved: {timeline_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
