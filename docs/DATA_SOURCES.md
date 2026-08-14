# Data sources / cost map

最終確認: 2026-08-14。価格は変更され得るため、実行時に provider の公式ページを再確認する前提です。

| Source | Cost | What we use it for | Main limitation |
|---|---:|---|---|
| Inside Airbnb | Free | detailed listings, calendar, reviews, geo; Tokyo quarterly snapshots for last 12 months | calendar unavailable ≠ booked; listing coordinates are anonymized; older archives need request/own cache |
| OpenBnB `mcp-server-airbnb` | Free / MIT | current live Airbnb search and listing details | unofficial scraping; no reliable historical occupancy; breakage/ToS/robots risk |
| e-Stat / Statistics Dashboard API | Free | macro demand, accommodation/tourism time series | not property-level STR data |
| MLIT Minpaku Portal | Free |届出件数、都道府県別宿泊実績、制度情報 | 2か月集計中心、物件別実績ではない |
| MLIT National Land Numerical Information | Free | railway/station geometry | walking route itself is not provided |
| Airbtics API | Pay as you go | 36-month listing/market occupancy, ADR, revenue; bounds search; revenue report | proprietary estimates; API key required |
| AirDNA | Subscription / enterprise API | mature STR comps, historical and future demand | API pricing is quote-based; dashboard subscription cost |
| PriceLabs Market Dashboard | from $9.99/mo | market/comp dashboard and revenue estimation | not a raw historical listing API replacement |
| Bright Data Airbnb Scraper | 5,000 records/mo free then $1.5/1k records | live listing/availability collection at scale | scraping-derived; booking vs block still needs inference |
| Apify community actors | actor-specific | low-cost experimental live scraping | quality, maintenance and pricing vary by actor |

## Current paid prices verified on 2026-08-14

### Airbtics API

Official public endpoint pricing:

- `report/all`: **$0.50** / request — full property revenue report + nearby comps + historical performance
- `report/summary`: **$0.10** / request
- `markets/metrics/all`: **$0.50** / request — up to 36 months monthly occupancy/ADR/revenue/active listings
- `listings/search/bounds`: **$0.05** / request
- `listings/metrics/all`: **$0.10** / listing — up to 36 months
- `markets/metrics/future/pacing`: **$0.20** / request
- enterprise: **$500/month minimum commitment**

For this project, the first paid upgrade should normally be `report/all` before buying dozens of per-listing histories. If more granular model training is needed, add `listings/search/bounds` + `listings/metrics/all` for a selected comp set.

### AirDNA

Public dashboard pricing shows Research at **$125 monthly**, or **$34/month billed $400 annually**. AirDNA's API is offered to businesses, but API pricing is not publicly fixed on the API page, so treat it as quote-based rather than inventing a per-call cost.

### PriceLabs

Ready-to-View Market Dashboards start at **$9.99/month**. Useful as a low-cost cross-check, but this project should not depend on UI scraping.

### Bright Data

Airbnb Scraper API currently advertises **5,000 records/month free**, then **$1.50 per 1,000 records** pay-as-you-go. Scale tier is advertised at $499/month with 384k records included.

## Why the official Airbnb API is not the core source

Airbnb has an API program for approved organizations/software partners, but access is program/scope based and requires contractual/security requirements. It is not a general public market-data API for arbitrary competitor occupancy research. Therefore the repository never assumes a public Airbnb API key exists.

## Sources

- Inside Airbnb: https://insideairbnb.com/get-the-data/
- Inside Airbnb assumptions: https://insideairbnb.com/data-assumptions/
- OpenBnB MCP: https://github.com/openbnb-org/mcp-server-airbnb
- Airbnb API terms: https://www.airbnb.com/help/article/3418
- e-Stat API: https://www.e-stat.go.jp/en/developer
- MLIT railway data: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html
- MLIT minpaku status: https://www.mlit.go.jp/kankocho/minpaku/business/host/construction_situation.html
- Airbtics API: https://airbtics.com/airbnb-api
- AirDNA pricing: https://www.airdna.co/pricing
- PriceLabs market dashboard: https://hello.pricelabs.co/ready-to-view-market-dashboard/
- Bright Data Airbnb scraper: https://brightdata.com/products/web-scraper/airbnb
