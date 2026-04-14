"""NK SpeedCoach GPS 風のサンプル CSV を生成する(テスト・デモ用)。

実デバイスからの正確な形式再現ではなく、パーサとゾーン集計を試すための
最低限のフィクスチャ。ヘッダ・データ形式は NK LiNK で見られる構造に合わせてある。
"""

from __future__ import annotations

import csv
import random
from pathlib import Path


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def _fmt_split(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:04.1f}"


def generate(
    out_path: Path,
    seed: int = 42,
    serial: str = "NK-123456",
    session_name: str = "Morning steady-state",
) -> None:
    rng = random.Random(seed)

    # セッション構成: (区間名, SPM 中心値, 区間ストローク数, 想定スプリット秒, 想定HR)
    segments = [
        ("Warmup",   18, 40, 145, 120),
        ("UT2 1",    20, 90, 135, 135),
        ("UT2 2",    20, 90, 134, 138),
        ("UT1",      24, 80, 125, 152),
        ("AT",       28, 60, 115, 168),
        ("TR",       32, 40, 105, 178),
        ("AN sprint",36, 20,  98, 185),
        ("Cooldown", 16, 30, 155, 130),
    ]

    rows: list[dict] = []
    elapsed = 0.0
    distance = 0.0
    total_strokes = 0

    for _, spm_mid, count, split_mid, hr_mid in segments:
        for _ in range(count):
            spm = max(10, rng.gauss(spm_mid, 0.8))
            split = max(80, rng.gauss(split_mid, 2.0))  # 秒 / 500m
            hr = max(80, rng.gauss(hr_mid, 3.0))
            stroke_time = 60.0 / spm  # この 1 本に掛かった秒
            # 距離 = (500 / split) * stroke_time
            dist_per_stroke = (500.0 / split) * stroke_time
            elapsed += stroke_time
            distance += dist_per_stroke
            total_strokes += 1
            rows.append({
                "Interval": 1,
                "Distance (GPS)": f"{distance:.1f}",
                "Elapsed Time": _fmt_time(elapsed),
                "Split (GPS)": _fmt_split(split),
                "Stroke Rate": f"{spm:.1f}",
                "Total Strokes": total_strokes,
                "Distance/Stroke (GPS)": f"{dist_per_stroke:.2f}",
                "Heart Rate": int(round(hr)),
                "Power": 0,
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        # NK LiNK 風のメタデータヘッダ。Serial Number はデバイスごとに一意で、
        # 艇/クルーの識別に使える。
        f.write("NK SpeedCoach Rowing Session\n")
        f.write("Session Summary:\n")
        f.write(f"Serial Number,{serial}\n")
        f.write(f"Session Name,{session_name}\n")
        f.write(f"Total Distance (GPS),{distance:.0f}\n")
        f.write(f"Total Elapsed Time,{_fmt_time(elapsed)}\n")
        f.write(f"Total Strokes,{total_strokes}\n")
        f.write("\n")
        f.write("Per-Stroke Data:\n")

        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    # 複数艇のデモができるよう、シリアル違いで 3 艇分を生成する。
    sample_dir = here / "sample_data"
    generate(sample_dir / "sample_session.csv",
             seed=42, serial="NK-123456", session_name="Morning steady-state")
    generate(sample_dir / "sample_session_port.csv",
             seed=7,  serial="NK-777888", session_name="Port 8+ morning row")
    generate(sample_dir / "sample_session_stbd.csv",
             seed=21, serial="NK-999111", session_name="Starboard 8+ morning row")
    print("wrote 3 sample CSVs under sample_data/")
