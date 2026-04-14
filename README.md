# NK SpeedCoach 強度ゾーン解析

ローイングの **NK SpeedCoach** からエクスポートしたセッション CSV を読み込み、
「選手がどの強度でどれくらいの時間滞在していたか」を一目で把握するためのツールです。

- 指標はストロークレート / 心拍 / 500m スプリット / パワーから選択
- 5 段階ゾーン (R・UT2・UT1・AT・TR・AN など) のプリセットを同梱
- ゾーン境界は YAML で自由に書き換え可能
- 出力は ① 滞在時間の横棒グラフ ② ゾーンで色分けした時系列 ③ CSV サマリ

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

### 1. デフォルト (ストロークレートでゾーン分け)

```bash
python analyze.py path/to/session.csv
```

出力例 (同梱のサンプルセッション):

```
=== Time in zones (spm) ===
Zone                     Time   Minutes       %
------------------------------------------------
R (~16)                  0:47      0.78    3.8%
UT2 (16-21)             12:17     12.29   60.2%
UT1 (22-25)              3:26      3.43   16.8%
AT (26-29)               2:07      2.11   10.4%
TR (30-33)               1:13      1.22    6.0%
AN (34+)                 0:33      0.56    2.7%
------------------------------------------------
Total                   20:24     20.39  100.0%
```

### 2. 指標を変える

```bash
python analyze.py session.csv --metric hr        # 心拍
python analyze.py session.csv --metric split_s   # 500m スプリット (秒)
python analyze.py session.csv --metric power     # パワー (Empower オールロックのみ)
```

### 3. ゾーン境界を自分好みに

`zones_example.yaml` をコピーして書き換え、`--zones` で指定します。

```yaml
metric: spm
zones:
  - { name: "R",   max: 16 }
  - { name: "UT2", min: 16, max: 22 }
  - { name: "UT1", min: 22, max: 26 }
  - { name: "AT",  min: 26, max: 30 }
  - { name: "TR",  min: 30, max: 34 }
  - { name: "AN",  min: 34 }
```

```bash
python analyze.py session.csv --zones zones_example.yaml
```

- `min` は下限(含む)、`max` は上限(含まない)
- 先頭ゾーンの `min` を省略すると -∞、末尾の `max` を省略すると +∞
- スプリット (`split_s`) のように「小さいほど速い」指標でも、そのまま秒で境界を書けば OK

### 4. 出力先

デフォルトでカレント直下の `./nk_output/` に以下を生成します。

- `time_in_zones.csv` — ゾーン別の秒・分・割合
- `time_in_zones.png` — 横棒グラフ
- `timeline.png` — ゾーンで色分けした時系列プロット

`--output-dir ./out/2024-05-01` のように任意のパスを指定可能。
`--no-plots` でグラフ生成をスキップし、集計表のみ出せます。

## 対応する CSV フォーマット

NK SpeedCoach GPS / GPS2 / LiNK エクスポートを想定しています。
CSV の先頭にあるセッション概要(`Total Distance` 等)を読み飛ばし、
以下のキーワードを含む行を自動的にデータヘッダとして検出します。

- `Interval` と `Elapsed Time` を同じ行に含む
- もしくは `Stroke Rate` と `Elapsed` / `Distance` を同じ行に含む

列名には以下が含まれていれば検出されます(機種差を吸収):

| 標準名        | 認識キーワード                                  |
| ------------- | ----------------------------------------------- |
| `elapsed_s`   | `Elapsed` + `Time`                              |
| `split_s`     | `Split` (+ `GPS` 優先)                          |
| `spm`         | `Stroke` + `Rate`                               |
| `hr`          | `Heart` + `Rate`                                |
| `power`       | `Power`                                         |
| `distance_m`  | `Distance` + `GPS` (ただし `Stroke` を含まない) |

サンプル CSV は `sample_data/sample_session.csv` に入っています
(`python tools/make_sample_csv.py` で再生成可能)。

## ライブラリとして使う

```python
from nk_speed import read_nk_csv, prepare, classify_zones, time_in_zones, DEFAULT_PRESETS

raw = read_nk_csv("session.csv")
df = prepare(raw)

zones = DEFAULT_PRESETS["spm"]
df["zone"] = classify_zones(df["spm"].tolist(), zones)
summary = time_in_zones(df, zones)
print(summary)
```

## ディレクトリ構成

```
.
├── analyze.py              # CLI エントリポイント
├── nk_speed/
│   ├── parser.py           # CSV 読み込みと列標準化
│   ├── zones.py            # ゾーン定義と滞在時間集計
│   └── plot.py             # matplotlib 可視化
├── tools/
│   └── make_sample_csv.py  # サンプル CSV 生成
├── sample_data/
│   └── sample_session.csv  # 約 20 分のフェイクセッション
├── zones_example.yaml      # ゾーン設定テンプレート
└── requirements.txt
```
