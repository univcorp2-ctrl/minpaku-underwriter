# Methodology and confidence boundaries

## 1. Data lineage first

Every metric should retain `source`, `method`, and `confidence`. We distinguish:

1. **Observed** — user-provided rent/area/walk minutes; official government counts; provider-reported metrics.
2. **Estimated** — Inside Airbnb review-model occupancy, provider modelled occupancy, target-property forecast.
3. **Unknown** — exact historic booking ledger, host-blocked vs booked nights in public calendars, unverified legal permission.

A report must never display category 2 as category 1.

## 2. Free historical occupancy proxy

Inside Airbnb detailed review files contain listing ID and review date. For each listing/month:

```text
estimated_bookings = reviews / review_rate
estimated_nights = estimated_bookings * max(default_average_stay, listing_minimum_nights)
occupancy_proxy = min(estimated_nights / days_in_month, occupancy_cap)
```

Defaults follow Inside Airbnb's published conservative model: review rate 50%, fallback stay 3 nights, occupancy cap 70%.

Weaknesses:

- review propensity changes by host/guest/time;
- latest snapshot excludes deleted listings → survivor bias in deep history;
- minimum-night settings can change over time;
- current listing price is not historical realized ADR.

Therefore free historical *occupancy* is usable as a directional proxy, but free historical *revenue* is lower confidence.

## 3. Calendar signal

`calendar.available == false` is called **unavailable rate**, never booked occupancy. It may mean reservation, owner block, regulatory closure, maintenance, or stale calendar. It is useful for future-demand/pacing and cross-sectional ranking only after discounting confidence.

## 4. Comparable-set construction

Initial comp set filters:

- same `room_type` where possible;
- radius 1.5 km by default, expandable if sample is thin;
- bedrooms within ±1 when available;
- accommodates within ±2;
- active/recently reviewed listings preferred.

Weights combine distance, bedroom/accommodates similarity, and recent-review activity. Later versions can learn these weights from paid historical labels.

## 5. Target forecast

Free mode is deliberately empirical, not fake-AI:

- estimate comp monthly occupancy distribution;
- calculate mean, std, p10/p50/p90 and month-of-year seasonality;
- derive target occupancy from weighted comps;
- optionally apply bounded adjustments for walk time and `design_score` when those features are present;
- ADR starts from comp price distribution and is widened when historical ADR is unavailable.

Paid mode should replace weak labels with Airbtics/AirDNA historical occupancy, ADR and revenue, then fit a cross-validated model (e.g. quantile gradient boosting) and hold out geography/time to avoid leakage.

## 6. Legal supply ceiling

Demand occupancy and legal sellable nights are separate variables.

```text
lawful_booked_nights = min(predicted_demand_nights, lawful_sellable_nights)
```

For Housing Accommodation Business Act operation, national ceiling is 180 days/year before local restrictions. Ward rules may reduce this further. Hotel Business Act permits a different operating model and must not inherit the 180-day ceiling.

## 7. Finance

Base output includes p10/p50/p90:

- gross revenue;
- platform/payment fee;
- operating variable cost;
- rent + management + utilities;
- annual cash flow;
- ROI = annual cash flow / initial investment;
- payback months = initial investment / monthly cash flow, when positive.

Cleaning fees are configurable as either pass-through revenue/cost or owner-borne cost.

## 8. Grade

Grade is not only expected profit. Score combines:

- 35% economics (cash flow / ROI / payback)
- 25% demand quality (occupancy + ADR + seasonality)
- 15% comp sample quality
- 15% legal/permission certainty
- 10% supply-growth / operational risk

Hard-stop flags can override score: owner permission absent, incompatible use, management rules prohibition, fire-safety infeasibility, or negative p50 annual cash flow.

## 9. Vision features

Interior photo quality should be a feature, not a hallucinated narrative. Planned/optional pipeline:

- brightness/sharpness/photo-count objective features;
- local CLIP/SigLIP embedding for style similarity to high-performing comps;
- optional vision model to extract structured attributes (`renovated`, `luxury`, `workspace`, `natural_light`, etc.);
- never let a visual score override legal feasibility or hard economics.
