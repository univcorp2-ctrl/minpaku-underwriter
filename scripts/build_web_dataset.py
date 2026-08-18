from __future__ import annotations

import calendar
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from minpaku_underwriter.inside_airbnb import InsideAirbnbTokyo, _money

OUT = Path("web/data/tokyo_market.json")
MONTHS = 36
CELL_DEG = 0.01
REVIEW_RATE = 0.50
DEFAULT_STAY = 3.0
OCC_CAP = 0.70
MIN_CELL_LISTINGS = 5


def bed_bucket(value: object) -> str:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "all"
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    return "3+"


def quantile10(s: pd.Series) -> float:
    return float(s.quantile(0.10))


def quantile50(s: pd.Series) -> float:
    return float(s.quantile(0.50))


def quantile90(s: pd.Series) -> float:
    return float(s.quantile(0.90))


def price_stats(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return (
        df.groupby(keys)["price_yen"]
        .agg(
            price_p10=quantile10,
            price_p50=quantile50,
            price_p90=quantile90,
            listing_count="count",
        )
        .reset_index()
    )


def history_stats(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return (
        df.groupby(keys)["occupancy"]
        .agg(
            occupancy_mean="mean",
            occupancy_std="std",
            occupancy_p10=quantile10,
            occupancy_p50=quantile50,
            occupancy_p90=quantile90,
            active_listings="count",
        )
        .reset_index()
    )


def rounded(value: object, digits: int = 3) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, digits)


def main() -> None:
    provider = InsideAirbnbTokyo()
    dates = provider.discover_dates()
    if not dates:
        raise RuntimeError("No Tokyo Inside Airbnb snapshot discovered")
    snapshot_date = dates[0]
    snap = provider.load_snapshot(snapshot_date=snapshot_date, include_calendar=False)

    listings = snap.listings.copy()
    required = {"id", "latitude", "longitude", "room_type", "price"}
    missing = required - set(listings.columns)
    if missing:
        raise RuntimeError(f"Missing listing columns: {sorted(missing)}")

    listings = listings[listings["room_type"].eq("Entire home/apt")].copy()
    listings["latitude"] = pd.to_numeric(listings["latitude"], errors="coerce")
    listings["longitude"] = pd.to_numeric(listings["longitude"], errors="coerce")
    listings["price_yen"] = listings["price"].map(_money)
    listings["minimum_nights_num"] = pd.to_numeric(
        listings.get("minimum_nights", DEFAULT_STAY), errors="coerce"
    ).fillna(DEFAULT_STAY)
    listings["minimum_nights_num"] = listings["minimum_nights_num"].clip(1, 30)
    listings["bed_bucket"] = listings.get(
        "bedrooms", pd.Series(index=listings.index, dtype=float)
    ).map(bed_bucket)
    listings["first_review_date"] = pd.to_datetime(
        listings.get("first_review", pd.NaT), errors="coerce"
    )
    listings["reviews_per_month_num"] = pd.to_numeric(
        listings.get("reviews_per_month", 0), errors="coerce"
    ).fillna(0)
    listings["number_of_reviews_ltm_num"] = pd.to_numeric(
        listings.get("number_of_reviews_ltm", 0), errors="coerce"
    ).fillna(0)
    listings = listings.dropna(subset=["latitude", "longitude", "price_yen"])
    listings = listings[(listings["price_yen"] >= 2500) & (listings["price_yen"] <= 250000)]

    listings["cell_lat_idx"] = np.floor(listings["latitude"] / CELL_DEG).astype(int)
    listings["cell_lon_idx"] = np.floor(listings["longitude"] / CELL_DEG).astype(int)
    listings["cell_key"] = (
        listings["cell_lat_idx"].astype(str) + ":" + listings["cell_lon_idx"].astype(str)
    )
    listings["cell_lat"] = (listings["cell_lat_idx"] + 0.5) * CELL_DEG
    listings["cell_lon"] = (listings["cell_lon_idx"] + 0.5) * CELL_DEG

    anchor = pd.Timestamp(snapshot_date)
    end_month = anchor.to_period("M")
    start_month = end_month - (MONTHS - 1)
    months = pd.period_range(start_month, end_month, freq="M")

    rv = snap.reviews[["listing_id", "date"]].copy()
    rv["listing_id"] = pd.to_numeric(rv["listing_id"], errors="coerce")
    rv["date"] = pd.to_datetime(rv["date"], errors="coerce")
    rv = rv.dropna(subset=["listing_id", "date"])
    rv["listing_id"] = rv["listing_id"].astype("int64")
    rv["month"] = rv["date"].dt.to_period("M")
    active_ids = set(pd.to_numeric(listings["id"], errors="coerce").dropna().astype("int64"))
    rv = rv[
        rv["listing_id"].isin(active_ids)
        & (rv["month"] >= start_month)
        & (rv["month"] <= end_month)
    ]
    review_counts = (
        rv.groupby(["listing_id", "month"]).size().rename("reviews").reset_index()
    )

    meta_cols = [
        "id",
        "cell_key",
        "cell_lat",
        "cell_lon",
        "bed_bucket",
        "minimum_nights_num",
        "first_review_date",
        "price_yen",
    ]
    meta = listings[meta_cols].rename(columns={"id": "listing_id"}).copy()
    meta["listing_id"] = pd.to_numeric(meta["listing_id"], errors="coerce").astype("int64")

    grid = pd.MultiIndex.from_product(
        [meta["listing_id"].tolist(), months], names=["listing_id", "month"]
    ).to_frame(index=False)
    grid = grid.merge(meta, on="listing_id", how="left")
    grid = grid.merge(review_counts, on=["listing_id", "month"], how="left")
    grid["reviews"] = grid["reviews"].fillna(0)
    month_end = grid["month"].dt.to_timestamp("M")
    existed = grid["first_review_date"].isna() | (grid["first_review_date"] <= month_end)
    grid = grid[existed].copy()
    grid["stay"] = np.maximum(grid["minimum_nights_num"], DEFAULT_STAY)
    grid["estimated_nights"] = grid["reviews"] / REVIEW_RATE * grid["stay"]
    grid["days"] = grid["month"].map(lambda p: calendar.monthrange(p.year, p.month)[1])
    grid["occupancy"] = (grid["estimated_nights"] / grid["days"]).clip(0, OCC_CAP)

    hist_all = history_stats(grid, ["cell_key", "month"])
    hist_all["bed_bucket"] = "all"
    hist_bed = history_stats(grid, ["cell_key", "bed_bucket", "month"])
    history = pd.concat([hist_all, hist_bed], ignore_index=True)

    price_all = price_stats(listings, ["cell_key"])
    price_all["bed_bucket"] = "all"
    price_bed = price_stats(listings, ["cell_key", "bed_bucket"])
    prices = pd.concat([price_all, price_bed], ignore_index=True)

    coords = listings.groupby("cell_key")[["cell_lat", "cell_lon"]].first().reset_index()
    history = history.merge(coords, on="cell_key", how="left")
    history = history.merge(prices, on=["cell_key", "bed_bucket"], how="left")
    history = history[history["listing_count"].fillna(0) >= MIN_CELL_LISTINGS]

    recent_sort = listings.sort_values(
        ["cell_key", "number_of_reviews_ltm_num", "reviews_per_month_num"],
        ascending=[True, False, False],
    )
    top = recent_sort.groupby("cell_key").head(8)
    comp_map: dict[str, list[dict[str, object]]] = {}
    for key, group in top.groupby("cell_key"):
        examples: list[dict[str, object]] = []
        for _, row in group.iterrows():
            item = {
                "id": int(row["id"]),
                "name": str(row.get("name") or "Airbnb listing")[:90],
                "lat": rounded(row["latitude"], 5),
                "lon": rounded(row["longitude"], 5),
                "price": rounded(row["price_yen"], 0),
                "bedrooms": rounded(row.get("bedrooms"), 0),
                "accommodates": rounded(row.get("accommodates"), 0),
                "reviews_per_month": rounded(row.get("reviews_per_month_num"), 2),
                "reviews_ltm": rounded(row.get("number_of_reviews_ltm_num"), 0),
            }
            examples.append(item)
        comp_map[str(key)] = examples

    cells: list[dict[str, object]] = []
    grouped = history.sort_values("month").groupby(["cell_key", "bed_bucket"], sort=False)
    for (cell_key, bucket), group in grouped:
        latest = group.iloc[-1]
        cell = {
            "key": str(cell_key),
            "bed": str(bucket),
            "lat": rounded(latest["cell_lat"], 5),
            "lon": rounded(latest["cell_lon"], 5),
            "count": int(latest["listing_count"]),
            "price": [
                rounded(latest["price_p10"], 0),
                rounded(latest["price_p50"], 0),
                rounded(latest["price_p90"], 0),
            ],
            "months": [
                [
                    str(row["month"]),
                    rounded(row["occupancy_mean"], 4),
                    rounded(row["occupancy_std"], 4),
                    rounded(row["occupancy_p10"], 4),
                    rounded(row["occupancy_p50"], 4),
                    rounded(row["occupancy_p90"], 4),
                    int(row["active_listings"]),
                ]
                for _, row in group.iterrows()
            ],
        }
        if bucket == "all":
            cell["examples"] = comp_map.get(str(cell_key), [])
        cells.append(cell)

    payload = {
        "schema": 1,
        "market": "Tokyo",
        "snapshot": snapshot_date,
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "months": MONTHS,
        "cell_degrees": CELL_DEG,
        "method": {
            "occupancy": "Inside Airbnb review-model proxy",
            "review_rate": REVIEW_RATE,
            "default_stay_nights": DEFAULT_STAY,
            "occupancy_cap": OCC_CAP,
            "adr": "Current listing-price proxy; not historical realized ADR",
            "warning": "Public Airbnb data cannot distinguish true bookings from all host-blocked dates; occupancy is estimated, not a booking ledger.",
        },
        "cells": cells,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"wrote {OUT}: {len(cells)} segments, {size_mb:.2f} MiB, snapshot={snapshot_date}")


if __name__ == "__main__":
    main()
