# Minpaku Underwriter

民泊候補物件のチラシ・住所・賃料・物件スペックを入力し、公開データに基づく周辺類似物件の過去需要、月次稼働率proxy、ADRレンジ、売上、ROI、回収期間、法規制リスクをまとめてA〜D判定する分析基盤です。

## Web版

`web/` はCloudflare Pages向けの静的Webアプリです。`web/data/tokyo_market.json` はGitHub Actionsの `Build market dataset` がInside Airbnbの東京詳細データから生成します。

### 無料データモードで出せるもの

- 住所→座標（Photon / Nominatim）
- 周辺グリッドのComparable件数
- 過去36か月のレビュー時系列から推定した月次稼働率proxy
- 月次平均、標準偏差、P10/P50/P90
- 現在の周辺ADR proxyとレンジ
- 売上、年間CF、ROI、初期投資回収期間
- 民泊新法180日上限と法規制未確認リスクの分離
- A〜D / 100点スコア
- PNG 1枚サマリー
- 物件写真の客観的な明るさ・コントラスト・シャープネス指標
- ブラウザOCRによるチラシ入力補助

### 重要な線引き

Inside Airbnbのレビュー時系列から出す稼働率は**予約台帳の実測値ではなく推定値**です。公開カレンダーの unavailable にはホストブロックが混ざるため、このWeb版では unavailable を予約済みとみなしません。また無料データだけでは過去の実現ADRを完全復元できないため、ADRは現在のComparable価格をproxyとして明示します。

より高精度な36か月のListing-level occupancy / ADR / revenueが必要な場合は `src/minpaku_underwriter/airbtics.py` の有料Providerを利用できます。APIキーは環境変数にのみ置きます。

## ローカル分析

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
minpaku-underwriter analyze examples/tokyo_three_properties.json --out reports
```

## 市場データ生成

```bash
python scripts/build_web_dataset.py
```

生成物: `web/data/tokyo_market.json`

## テスト

```bash
ruff check src tests scripts
pytest -q
```

詳細は `docs/METHODOLOGY.md` と `docs/DATA_SOURCES.md` を参照してください。
