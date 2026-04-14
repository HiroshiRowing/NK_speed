# NK SpeedCoach 強度ゾーン解析

ローイングの **NK SpeedCoach** からエクスポートしたセッション CSV を読み込み、
「選手がどの強度でどれくらいの時間滞在していたか」を一目で把握するためのツールです。

- 指標はストロークレート / 心拍 / 500m スプリット / パワーから選択
- 5〜6 段階ゾーン (R・UT2・UT1・AT・TR・AN など) のプリセットを同梱
- ゾーン境界はブラウザ上で直接編集可能
- 出力は 滞在時間の横棒グラフ / ゾーンで色分けした時系列 / サマリ CSV

---

## 🖱️ 使い方 (インストール不要, おすすめ)

### 方法 1: GitHub Pages の URL にアクセスする

公開 URL(セットアップ後に発行):

> `https://hiroshirowing.github.io/NK_speed/`

このページの真ん中にあるドロップエリアに CSV をドラッグ&ドロップするだけです。
**Python も pip も不要。ブラウザだけで完結します。**

CSV の中身はブラウザ内で処理されるだけで、どこにも送信されません。

### 方法 2: HTML ファイルを直接開く

1. このリポジトリをダウンロード (Code → Download ZIP → 解凍)
2. `docs/index.html` を **ダブルクリック** して Safari / Chrome で開く
3. 中央のドロップエリアに CSV を投げ入れる

ローカルファイルとして動くので、オフラインでも使えます。

---

## 🚀 初回だけ: GitHub Pages を有効化する (オーナー向け)

この PR をマージしたあと、**一度だけ以下の設定**をすれば方法 1 が使えるようになります。

1. リポジトリの **Settings** → 左メニューの **Pages** を開く
2. **Build and deployment** の **Source** を `GitHub Actions` に変更
3. 保存 (自動で次回 push 時にデプロイされます)

設定後、GitHub の **Actions** タブで `Deploy docs to Pages` ワークフローが緑になれば完了。
`https://hiroshirowing.github.io/NK_speed/` にアクセスできるようになります。

---

## 📱 iPad / スマホから使いたい

方法 1 の URL ならそのままスマホのブラウザで開けます。
艇庫の iPad や選手のスマホから、その場で CSV をドロップして解析できます。

---

## 💻 おまけ: Python で CLI / Streamlit から使う

プログラムに詳しい方向け。`requirements.txt` の依存関係(pandas, matplotlib,
streamlit, pyyaml)を入れれば以下のコマンドが使えます。

```bash
# 集計結果を標準出力 + PNG 2 枚 + サマリ CSV で出力
python analyze.py sample_data/sample_session.csv

# Streamlit でローカル Web UI
streamlit run app.py
```

CLI のオプション一覧は `python analyze.py --help` で。

---

## 対応する CSV フォーマット

NK SpeedCoach GPS / GPS2 / LiNK エクスポートを想定しています。
CSV の先頭にあるセッション概要(`Total Distance` 等)を自動で読み飛ばし、
以下のキーワードを含む行をデータヘッダとして検出します。

- `Interval` と `Elapsed Time` を同じ行に含む
- もしくは `Stroke Rate` と `Elapsed` / `Distance` を同じ行に含む

列名の一致は部分マッチ(機種差を吸収):

| 用途        | 認識キーワード                                  |
| ----------- | ----------------------------------------------- |
| 経過時間    | `Elapsed` + `Time`                              |
| スプリット  | `Split` (+ `GPS` 優先)                          |
| ストローク  | `Stroke` + `Rate`                               |
| 心拍        | `Heart` + `Rate`                                |
| パワー      | `Power`                                         |
| 距離        | `Distance` + `GPS` (ただし `Stroke` を含まない) |

サンプル CSV は `sample_data/sample_session.csv` に入っています。
まずはこれで動作確認してからご自分のセッション CSV を試すのがおすすめです。

---

## ディレクトリ構成

```
.
├── docs/
│   └── index.html          # ブラウザ版 (GitHub Pages で公開)
├── .github/workflows/
│   └── pages.yml           # docs/ を自動デプロイするワークフロー
├── app.py                  # Streamlit 版 Web UI (Python 必要)
├── analyze.py              # CLI (Python 必要)
├── nk_speed/
│   ├── parser.py           # CSV 読み込みと列標準化
│   ├── zones.py            # ゾーン定義と滞在時間集計
│   └── plot.py             # matplotlib 可視化
├── tools/
│   └── make_sample_csv.py  # サンプル CSV 生成スクリプト
├── sample_data/
│   └── sample_session.csv  # 約 20 分のフェイクセッション
├── zones_example.yaml      # CLI 用ゾーン設定テンプレート
└── requirements.txt
```
