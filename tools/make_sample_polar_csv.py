"""Polar Flow の CSV エクスポートに似せたサンプルを生成する。

参考にした形式 (ユーザ提供のスクリーンショット):

  Row 1:  Name, Sport, Date, Start time, Duration, Total distance (km),
          Average heart rate (bpm), Average speed (km/h), Max speed (km/h),
          Average pace (min/km)
  Row 2:  <セッション値>
  Row 3:  Sample rate, Time, HR (bpm), Speed (km/h), Pace (min/km),
          Cadence, Altitude (m), Stride length (m), Distances (m), Temperatures (C)
  Row 4+: 1 秒毎のサンプル (Sample rate は最初の行だけ値が入る)

NK SpeedCoach 側のサンプル(sample_session.csv)は 09:12 開始 / 20:27 の長さを
想定しているので、こちらは 09:10:00 開始 / 30 分で作り、2 分ほどのウォームアップを
挟んで NK のセッションとオーバーラップするようにする。
"""

from __future__ import annotations

import csv
import random
from pathlib import Path


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds - h * 3600 - m * 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def generate(out_path: Path, seed: int = 42) -> None:
    rng = random.Random(seed)

    # セッション構成 (HR 推移):
    # 0-120 秒: ウォームアップで HR が 63 → 120 へ緩やかに上昇
    # 120-420 秒: UT2 で HR 130-140 中心
    # 420-720 秒: UT1 で HR 150 中心
    # 720-900 秒: AT で HR 165 中心
    # 900-1020 秒: TR で HR 175
    # 1020-1080 秒: AN sprint で HR 185
    # 1080-1800 秒: クールダウンで HR 150 → 110 へ低下
    def target_hr(t: int) -> float:
        if t < 120:
            return 63 + (120 - 63) * (t / 120)
        elif t < 420:
            return 135
        elif t < 720:
            return 150
        elif t < 900:
            return 165
        elif t < 1020:
            return 175
        elif t < 1080:
            return 185
        elif t < 1800:
            # 1080 秒から徐々に下がる
            return 150 - (150 - 110) * ((t - 1080) / (1800 - 1080))
        return 110

    duration_s = 1800  # 30 分
    samples: list[dict] = []
    for t in range(duration_s + 1):
        hr = max(55, int(round(rng.gauss(target_hr(t), 1.5))))
        # ウォームアップ中(最初の 120 秒)は Speed / Pace / Distance は空
        if t < 120:
            speed = ""
            pace = ""
            dist = ""
        else:
            # 大雑把なローイング速度: HR 帯とだいたいリンク
            speed_kmh = round(max(3.0, (hr - 60) / 12.0) + rng.gauss(0, 0.2), 1)
            speed = f"{speed_kmh}"
            pace = f"{int(60 / speed_kmh):02d}:{int((60 / speed_kmh % 1) * 60):02d}"
            prev_dist = samples[-1].get("_dist", 0) if samples else 0
            dist_next = prev_dist + speed_kmh * (1000 / 3600)  # m per sec
            dist = f"{dist_next:.2f}"

        row = {
            "Sample rate": "1" if t == 0 else "",
            "Time": _fmt_time(t),
            "HR (bpm)": hr,
            "Speed (km/h)": speed,
            "Pace (min/km)": pace,
            "Cadence": "",
            "Altitude (m)": "",
            "Stride length (m)": "",
            "Distances (m)": dist,
            "Temperatures (C)": "13.0",
        }
        # 累積距離を後続の計算に使うため裏で持たせる。
        if dist:
            row["_dist"] = float(dist)
        samples.append(row)

    # メタデータ集計用
    hr_values = [s["HR (bpm)"] for s in samples if isinstance(s["HR (bpm)"], (int, float))]
    avg_hr = int(round(sum(hr_values) / len(hr_values)))
    total_dist_m = samples[-1].get("_dist", 0)

    # 書き出し
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Row 1: summary header
        writer.writerow([
            "Name", "Sport", "Date", "Start time", "Duration",
            "Total distance (km)", "Average heart rate (bpm)",
            "Average speed (km/h)", "Max speed (km/h)", "Average pace (min/km)",
        ])
        # Row 2: summary values
        writer.writerow([
            "sample rower", "ROWING", "2020-01-11", "09:10:00",
            _fmt_time(duration_s),
            f"{total_dist_m / 1000:.2f}",
            avg_hr,
            "3.5", "16.1", "17:21",
        ])
        # Row 3: data header
        writer.writerow([
            "Sample rate", "Time", "HR (bpm)", "Speed (km/h)", "Pace (min/km)",
            "Cadence", "Altitude (m)", "Stride length (m)", "Distances (m)",
            "Temperatures (C)",
        ])
        # Row 4+: per-sample data
        for s in samples:
            writer.writerow([
                s["Sample rate"], s["Time"], s["HR (bpm)"], s["Speed (km/h)"],
                s["Pace (min/km)"], s["Cadence"], s["Altitude (m)"],
                s["Stride length (m)"], s["Distances (m)"], s["Temperatures (C)"],
            ])


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    generate(here / "sample_data" / "sample_polar.csv")
    print("wrote sample_data/sample_polar.csv")
