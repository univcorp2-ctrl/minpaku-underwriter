# Minpaku Underwriter

民泊候補物件を入力すると、周辺類似Airbnbの公開データ、過去レビュー、価格・カレンダー、法規制、賃料・初期投資を統合し、月次稼働率レンジ、ADR、売上、ROI、回収期間、A〜D判定を出すための分析基盤です。

## 重要な設計方針

- **予約実績と公開カレンダーを混同しない。** Airbnb公開カレンダーの unavailable は「予約済み」と「ホストブロック」を区別できません。
- 無料モードは Inside Airbnb のレビュー時系列を主信号にして稼働率を**推定**し、カレンダー unavailable は補助信号として扱います。
- 正確度を上げる場合は Airbtics / AirDNA 等を Provider として差し替えます。特に Airbtics は 36か月の listing-level occupancy / ADR / revenue を従量課金で取得できるため、費用対効果が高い設計です。
- 民泊新法の180日上限と区条例の曜日制限は、需要予測とは別レイヤーで「販売可能泊数」に反映します。
- 出力は `analysis.json` と1枚の `summary.png`。数値ごとに source / confidence を残します。

## セットアップ

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
```

## 3物件サンプル

```bash
minpaku-underwriter analyze examples/tokyo_three_properties.json --out reports
```

住所しかない場合、Photon → Nominatim の順で座標取得を試します。大量処理では公開ジオコーダーを叩かず、座標を入力するか自前ジオコーダーに差し替えてください。

## 有料データを使う場合

Airbtics の API は本リポジトリでは optional provider として扱います。API URL とキーは環境変数のみで渡し、リポジトリには保存しません。

```bash
export AIRBTICS_API_BASE_URL='YOUR_API_BASE_URL'
export AIRBTICS_API_KEY='...'
```

詳細は `docs/DATA_SOURCES.md` と `docs/METHODOLOGY.md` を参照してください。
