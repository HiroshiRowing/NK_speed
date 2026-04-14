"""ブラウザ上で NK SpeedCoach CSV をドラッグ&ドロップして強度ゾーンを集計する Web UI。

起動:
    streamlit run app.py

ターミナルに `Local URL: http://localhost:8501` と表示されるので、
ブラウザで開くと CSV を置くだけで結果が出る。
同じ LAN の別端末(iPad 等)からは `Network URL` で開ける。
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st
import yaml

from nk_speed import (
    DEFAULT_PRESETS,
    classify_zones,
    plot_time_in_zones,
    plot_timeline,
    prepare,
    read_nk_csv,
    time_in_zones,
)


METRIC_LABELS = {
    "spm": "ストロークレート (SPM)",
    "hr": "心拍 (HR, bpm)",
    "split_s": "500m スプリット (秒)",
    "power": "パワー (W)",
}


def _format_seconds(s: float) -> str:
    minutes = int(s // 60)
    seconds = int(round(s - minutes * 60))
    return f"{minutes}:{seconds:02d}"


st.set_page_config(
    page_title="NK SpeedCoach 強度ゾーン解析",
    page_icon="🚣",
    layout="wide",
)

st.title("🚣 NK SpeedCoach 強度ゾーン解析")
st.caption(
    "NK SpeedCoach のセッション CSV をドラッグ&ドロップすると、"
    "選手がどの強度ゾーンにどれくらい滞在したかを自動集計します。"
)

# --- サイドバー: 指標選択とゾーン編集 -----------------------------------------
with st.sidebar:
    st.header("⚙️ 設定")
    metric = st.selectbox(
        "ゾーン分けに使う指標",
        options=list(METRIC_LABELS.keys()),
        format_func=lambda x: METRIC_LABELS[x],
        help="選んだ指標が CSV に無い場合はエラーになります",
    )

    st.markdown("---")
    st.subheader("ゾーン境界")
    st.caption("デフォルトのプリセットを編集できます。変更は即反映。")

    default_yaml = yaml.safe_dump(
        {"zones": DEFAULT_PRESETS[metric]},
        sort_keys=False,
        allow_unicode=True,
    )
    zones_yaml = st.text_area(
        "ゾーン (YAML)",
        value=default_yaml,
        height=320,
        # metric ごとに別キーにして、指標を変えたらデフォルトが読み直されるように。
        key=f"zones_yaml_{metric}",
        label_visibility="collapsed",
    )

# --- ゾーン設定のパース -------------------------------------------------------
try:
    zones_cfg = yaml.safe_load(zones_yaml) or {}
    zones = zones_cfg.get("zones") or DEFAULT_PRESETS[metric]
    if not isinstance(zones, list) or not all("name" in z for z in zones):
        raise ValueError("`zones` は [{name, min, max}, ...] のリストにしてください")
except Exception as e:  # noqa: BLE001  ユーザ入力の YAML 構文エラーは丸ごと表示したい
    st.sidebar.error(f"ゾーン設定エラー: {e}")
    zones = DEFAULT_PRESETS[metric]

# --- メイン: アップロード & 結果表示 ------------------------------------------
uploaded = st.file_uploader(
    "CSV ファイルをここにドラッグ&ドロップ",
    type=["csv"],
    accept_multiple_files=False,
    help="NK SpeedCoach GPS / GPS2 / LiNK からエクスポートしたセッション CSV",
)

if uploaded is None:
    st.info(
        "👆 上のエリアに CSV をドロップすると解析が始まります。\n\n"
        "まずは `sample_data/sample_session.csv` で試すのがおすすめ。"
    )
    st.stop()


@st.cache_data(show_spinner="CSV を読み込み中…")
def _load(name: str, content: bytes) -> pd.DataFrame:
    """同じファイルを再アップロードしても再パースしないようにキャッシュ。"""
    # `name` を引数に含めることでファイル単位のキーになる。
    return prepare(read_nk_csv(io.BytesIO(content)))


df = _load(uploaded.name, uploaded.getvalue())

if metric not in df.columns:
    st.error(
        f"この CSV には指標 **{METRIC_LABELS[metric]}** に対応する列が見つかりませんでした。\n\n"
        f"取り込まれた列: `{list(df.columns)}`\n\n"
        "サイドバーで別の指標を選んでください。"
    )
    st.stop()

df = df.copy()
df["zone"] = classify_zones(df[metric].tolist(), zones)
summary = time_in_zones(df, zones)
total_s = float(summary["time_s"].sum())

# サマリメトリクス
col_a, col_b, col_c = st.columns(3)
col_a.metric("総セッション時間", _format_seconds(total_s))
col_b.metric("ゾーン分け指標", METRIC_LABELS[metric])
col_c.metric("ファイル", uploaded.name)

# ゾーン別滞在時間 (表 + 横棒グラフ)
st.markdown("## ゾーン別滞在時間")
col1, col2 = st.columns([2, 3])

with col1:
    display = summary.copy()
    display["滞在時間"] = display["time_s"].apply(_format_seconds)
    display["分"] = display["time_min"].round(2)
    display["%"] = display["pct"].round(1)
    display = display[["zone", "滞在時間", "分", "%"]]
    display.columns = ["ゾーン", "滞在時間", "分", "%"]
    st.dataframe(display, hide_index=True, use_container_width=True)

    buf = io.StringIO()
    summary.to_csv(buf, index=False)
    st.download_button(
        "📥 サマリ CSV をダウンロード",
        buf.getvalue(),
        file_name=f"time_in_zones_{metric}.csv",
        mime="text/csv",
    )

with col2:
    fig_bar = plot_time_in_zones(summary, metric=metric, title=f"Time in zones ({metric})")
    st.pyplot(fig_bar)

# タイムライン
st.markdown("## タイムライン")
st.caption("各ストロークを時系列でプロットし、ゾーンで色分けしています。")
fig_timeline = plot_timeline(df, metric=metric, zones=zones,
                             title=f"{metric} timeline — {uploaded.name}")
st.pyplot(fig_timeline)

# 生データを確認したいときのため
with st.expander("取り込んだストローク毎データを表示"):
    st.dataframe(df, use_container_width=True)
