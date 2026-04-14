"""NK SpeedCoach の CSV をロードして扱いやすい DataFrame に整える。

NK SpeedCoach (GPS / GPS2 / LiNK エクスポート) の CSV は先頭にセッション概要の
メタデータ行が並び、途中の "Per-Stroke Data:" もしくは "Interval,Distance,..."
の行からストローク毎のデータが始まる。機種・ファームによって列名が微妙に
異なるので、ヘッダ行をキーワードで自動検出する。
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd


PathLike = Union[str, Path]


@dataclass
class SessionMetadata:
    """プリアンブルから拾える付随情報。

    シリアル番号は NK SpeedCoach 本体ごとに一意で、艇/クルーの識別に使える。
    """
    serial: str | None = None
    session_name: str | None = None
    total_distance_m: float | None = None
    total_elapsed_str: str | None = None
    raw: dict[str, str] = field(default_factory=dict)


def _find_header_row(lines: list[str]) -> int | None:
    """ストローク毎データのヘッダ行インデックスを探す。見つからなければ None。"""
    for i, line in enumerate(lines):
        low = line.lower()
        # "Interval" と "Elapsed Time" が同じ行にあるのが共通パターン。
        if "interval" in low and "elapsed time" in low:
            return i
        # 新しい LiNK エクスポートでは "Stroke Rate" を含む行がヘッダ。
        if "stroke rate" in low and ("elapsed" in low or "distance" in low):
            return i
    return None


def _extract_metadata(lines: list[str], header_idx: int | None) -> SessionMetadata:
    """プリアンブル(ヘッダ行より上)から「Key,Value」形式の情報を拾う。"""
    scan = lines[: header_idx] if header_idx is not None else lines[:30]
    meta = SessionMetadata()
    for line in scan:
        cells = line.split(",")
        if len(cells) < 2:
            continue
        key = cells[0].strip()
        value = ",".join(cells[1:]).strip()
        if not key or not value:
            continue
        low = key.lower()
        meta.raw[key] = value
        if meta.serial is None and "serial" in low:
            meta.serial = value
        elif meta.session_name is None and "session" in low and "name" in low:
            meta.session_name = value
        elif meta.total_distance_m is None and "total" in low and "distance" in low:
            try:
                meta.total_distance_m = float(value)
            except ValueError:
                pass
        elif meta.total_elapsed_str is None and "total" in low and "elapsed" in low:
            meta.total_elapsed_str = value
    return meta


def read_nk_csv(source, *, return_metadata: bool = False):
    """NK SpeedCoach CSV を読み込み、ストローク毎データを返す。

    `source` はファイルパス(str / Path)でも、read() できる file-like
    (Streamlit の UploadedFile や BytesIO) でも受け付ける。後者は Web UI
    からのアップロードで使う。

    `return_metadata=True` のときは (DataFrame, SessionMetadata) のタプルを返す。
    シリアル番号を使ったクルー分けを行いたい場合に便利。
    """
    # Web UI からのアップロードにも対応するため、まず内容を文字列として吸い上げる。
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
    else:
        with open(Path(source), "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()

    lines = raw.splitlines()
    header_idx = _find_header_row(lines)
    metadata = _extract_metadata(lines, header_idx)

    buf = io.StringIO(raw)
    if header_idx is None:
        # フォールバック: そのまま読む(単純 CSV の場合)。
        df = pd.read_csv(buf)
    else:
        df = pd.read_csv(buf, skiprows=header_idx)

    df.columns = [str(c).strip() for c in df.columns]
    # 空行・完全欠損行を除去。
    df = df.dropna(how="all").reset_index(drop=True)

    if return_metadata:
        return df, metadata
    return df


def _parse_time_to_seconds(value) -> float:
    """HH:MM:SS.s / MM:SS.s / 秒 (数値) を秒(float)に変換。"""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "-"}:
        return np.nan
    try:
        parts = s.split(":")
        seconds = 0.0
        for p in parts:
            seconds = seconds * 60 + float(p)
        return seconds
    except ValueError:
        return np.nan


def _match_column(columns: list[str], *keywords: str) -> str | None:
    """`keywords` の全てを(大文字小文字無視で)含む列名を返す。"""
    for col in columns:
        low = col.lower()
        if all(k.lower() in low for k in keywords):
            return col
    return None


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """解析に使いやすい標準列を持つ DataFrame を作る。

    生成される列:
      elapsed_s   : セッション開始からの経過秒
      dt_s        : 直前サンプルからの経過秒(ゾーン別滞在時間の重みに使う)
      split_s     : 500m スプリット(秒)
      spm         : ストロークレート(本/分)
      hr          : 心拍(bpm)
      power       : パワー(W)
      distance_m  : 累積距離(m)

    元データに存在しない列は自動的に省略される。
    """
    cols = list(df.columns)
    out = pd.DataFrame(index=df.index)

    elapsed_col = _match_column(cols, "elapsed", "time")
    if elapsed_col:
        out["elapsed_s"] = df[elapsed_col].apply(_parse_time_to_seconds)

    split_col = _match_column(cols, "split", "gps") or _match_column(cols, "split")
    if split_col:
        out["split_s"] = df[split_col].apply(_parse_time_to_seconds)

    spm_col = _match_column(cols, "stroke", "rate")
    if spm_col:
        out["spm"] = pd.to_numeric(df[spm_col], errors="coerce")

    hr_col = _match_column(cols, "heart", "rate")
    if hr_col:
        out["hr"] = pd.to_numeric(df[hr_col], errors="coerce")

    power_col = _match_column(cols, "power")
    if power_col:
        out["power"] = pd.to_numeric(df[power_col], errors="coerce")

    distance_col = _match_column(cols, "distance", "gps")
    if distance_col and "stroke" not in distance_col.lower():
        out["distance_m"] = pd.to_numeric(df[distance_col], errors="coerce")

    # dt_s: 直前サンプルからの経過秒。最初の行は 0 とする。
    # NK のログはストローク毎サンプリングなので、サンプル間隔 = そのストロークに
    # 費やした時間 ≒ その強度での滞在時間として扱える。
    if "elapsed_s" in out:
        dt = out["elapsed_s"].diff()
        dt.iloc[0] = 0 if len(dt) else 0
        # 負値(リセット等)や極端に大きな間隔(ポーズ)は 0 扱いで除外。
        dt = dt.where(dt >= 0, 0)
        dt = dt.where(dt <= 30, 0)
        out["dt_s"] = dt.fillna(0)

    return out
