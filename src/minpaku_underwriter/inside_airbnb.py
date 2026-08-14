from __future__ import annotations

import calendar as month_calendar
import io
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_PAGE = "https://insideairbnb.com/get-the-data/"
TOKYO_PATH = "japan/kant%C5%8D/tokyo"
UA = "minpaku-underwriter/0.1"


def _money(value: object) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    text = re.sub(r"[^0-9.\-]", "", str(value))
    return float(text) if text else float("nan")


def haversine_km(lat1: float, lon1: float, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    p1 = np.radians(lat1)
    p2 = np.radians(lat2.astype(float))
    dp = p2 - p1
    dl = np.radians(lon2.astype(float) - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return pd.Series(6371.0088 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)), index=lat2.index)


@dataclass
class Snapshot:
    snapshot_date: str
    listings: pd.DataFrame
    reviews: pd.DataFrame
    calendar: pd.DataFrame | None = None


class InsideAirbnbTokyo:
    def __init__(self, cache_dir: str | Path = ".cache/inside-airbnb") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def discover_dates(self) -> list[str]:
        html = requests.get(DATA_PAGE, headers={"User-Agent": UA}, timeout=30).text
        pattern = rf"{re.escape(TOKYO_PATH)}/(\d{{4}}-\d{{2}}-\d{{2}})/data/listings\.csv\.gz"
        return sorted(set(re.findall(pattern, html)), reverse=True)

    def _url(self, snapshot_date: str, kind: str) -> str:
        if kind not in {"listings", "reviews", "calendar"}:
            raise ValueError(kind)
        return f"https://data.insideairbnb.com/{TOKYO_PATH}/{snapshot_date}/data/{kind}.csv.gz"

    def _load_csv(self, snapshot_date: str, kind: str) -> pd.DataFrame:
        cached = self.cache_dir / f"tokyo-{snapshot_date}-{kind}.csv.gz"
        if not cached.exists():
            r = requests.get(self._url(snapshot_date, kind), headers={"User-Agent": UA}, timeout=120)
            r.raise_for_status()
            cached.write_bytes(r.content)
        return pd.read_csv(cached, compression="gzip", low_memory=False)

    def load_snapshot(self, snapshot_date: str | None = None, include_calendar: bool = False) -> Snapshot:
        if snapshot_date is None:
            dates = self.discover_dates()
            if not dates:
                raise RuntimeError("Could not discover Tokyo Inside Airbnb snapshot date")
            snapshot_date = dates[0]
        listings = self._load_csv(snapshot_date, "listings")
        reviews = self._load_csv(snapshot_date, "reviews")
        cal = self._load_csv(snapshot_date, "calendar") if include_calendar else None
        return Snapshot(snapshot_date, listings, reviews, cal)

    @staticmethod
    def select_comps(
        listings: pd.DataFrame,
        lat: float,
        lon: float,
        room_type: str,
        bedrooms: int | None,
        accommodates: int,
        radius_km: float = 1.5,
        min_comps: int = 20,
        max_comps: int = 80,
    ) -> pd.DataFrame:
        df = listings.copy()
        df = df.dropna(subset=["latitude", "longitude"])
        df["distance_km"] = haversine_km(lat, lon, df["latitude"], df["longitude"])
        same_type = df["room_type"].eq(room_type) if "room_type" in df else pd.Series(True, index=df.index)
        df = df[same_type & (df["distance_km"] <= radius_km)].copy()
        if len(df) < min_comps:
            df = listings.dropna(subset=["latitude", "longitude"]).copy()
            df["distance_km"] = haversine_km(lat, lon, df["latitude"], df["longitude"])
            df = df[df["distance_km"] <= min(radius_km * 2, 4.0)].copy()
            if "room_type" in df:
                df = df[df["room_type"].eq(room_type)]
        if bedrooms is not None and "bedrooms" in df:
            bed = pd.to_numeric(df["bedrooms"], errors="coerce")
            narrowed = df[(bed.isna()) | ((bed - bedrooms).abs() <= 1)]
            if len(narrowed) >= min(10, min_comps):
                df = narrowed
        if "accommodates" in df:
            acc = pd.to_numeric(df["accommodates"], errors="coerce")
            narrowed = df[(acc - accommodates).abs() <= 2]
            if len(narrowed) >= min(10, min_comps):
                df = narrowed
        if "last_review" in df:
            df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")
            cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=365)
            active = df[df["last_review"].isna() | (df["last_review"] >= cutoff)]
            if len(active) >= min(10, min_comps):
                df = active
        df["comp_weight"] = np.exp(-df["distance_km"] / 0.75)
        return df.nsmallest(max_comps, "distance_km")

    @staticmethod
    def review_occupancy_history(
        comps: pd.DataFrame,
        reviews: pd.DataFrame,
        months: int = 36,
        review_rate: float = 0.50,
        default_stay: float = 3.0,
        cap: float = 0.70,
    ) -> pd.DataFrame:
        if comps.empty:
            raise ValueError("No comparable listings")
        ids = set(pd.to_numeric(comps["id"], errors="coerce").dropna().astype("int64"))
        rv = reviews.copy()
        rv["listing_id"] = pd.to_numeric(rv["listing_id"], errors="coerce")
        rv = rv[rv["listing_id"].isin(ids)].copy()
        rv["date"] = pd.to_datetime(rv["date"], errors="coerce")
        rv = rv.dropna(subset=["date"])
        last_month = pd.Timestamp.today().to_period("M")
        first_month = last_month - (months - 1)
        rv = rv[(rv["date"].dt.to_period("M") >= first_month) & (rv["date"].dt.to_period("M") <= last_month)]
        counts = rv.assign(month=rv["date"].dt.to_period("M")).groupby(["listing_id", "month"]).size().rename("reviews").reset_index()

        meta_cols = [c for c in ["id", "minimum_nights", "first_review", "price", "distance_km", "comp_weight"] if c in comps]
        meta = comps[meta_cols].copy().rename(columns={"id": "listing_id"})
        meta["listing_id"] = pd.to_numeric(meta["listing_id"], errors="coerce")
        meta["minimum_nights"] = pd.to_numeric(meta.get("minimum_nights", default_stay), errors="coerce").fillna(default_stay).clip(upper=30)
        meta["price_yen"] = meta.get("price", pd.Series(index=meta.index, dtype=object)).map(_money)
        if "first_review" in meta:
            meta["first_review"] = pd.to_datetime(meta["first_review"], errors="coerce")

        months_idx = pd.period_range(first_month, last_month, freq="M")
        grid = pd.MultiIndex.from_product([meta["listing_id"].dropna().astype("int64"), months_idx], names=["listing_id", "month"]).to_frame(index=False)
        grid = grid.merge(meta, on="listing_id", how="left").merge(counts, on=["listing_id", "month"], how="left")
        grid["reviews"] = grid["reviews"].fillna(0)
        if "first_review" in grid:
            month_end = grid["month"].dt.to_timestamp("M")
            existed = grid["first_review"].isna() | (grid["first_review"] <= month_end)
            grid = grid[existed]
        grid["stay_nights"] = np.maximum(grid["minimum_nights"], default_stay)
        grid["estimated_nights"] = grid["reviews"] / review_rate * grid["stay_nights"]
        grid["days"] = grid["month"].map(lambda p: month_calendar.monthrange(p.year, p.month)[1])
        grid["occupancy_proxy"] = (grid["estimated_nights"] / grid["days"]).clip(0, cap)
        grid["revenue_proxy_yen"] = grid["estimated_nights"] * grid["price_yen"]

        rows = []
        for period, g in grid.groupby("month"):
            x = g["occupancy_proxy"].to_numpy(dtype=float)
            w = g.get("comp_weight", pd.Series(np.ones(len(g)), index=g.index)).fillna(1).to_numpy(dtype=float)
            w = w / w.sum() if w.sum() else np.ones_like(w) / len(w)
            mean = float(np.sum(x * w))
            rows.append({
                "month": str(period),
                "occupancy_mean": mean,
                "occupancy_std": float(np.nanstd(x, ddof=1)) if len(x) > 1 else 0.0,
                "occupancy_p10": float(np.nanquantile(x, 0.10)),
                "occupancy_p50": float(np.nanquantile(x, 0.50)),
                "occupancy_p90": float(np.nanquantile(x, 0.90)),
                "adr_proxy_yen": float(np.nanmedian(g["price_yen"])) if g["price_yen"].notna().any() else float("nan"),
                "revenue_proxy_yen": float(np.nansum(g["revenue_proxy_yen"] * w)),
                "comp_count": int(len(g)),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def calendar_unavailability(comps: pd.DataFrame, calendar_df: pd.DataFrame) -> pd.DataFrame:
        ids = set(pd.to_numeric(comps["id"], errors="coerce").dropna().astype("int64"))
        cal = calendar_df.copy()
        cal["listing_id"] = pd.to_numeric(cal["listing_id"], errors="coerce")
        cal = cal[cal["listing_id"].isin(ids)].copy()
        cal["date"] = pd.to_datetime(cal["date"], errors="coerce")
        cal["month"] = cal["date"].dt.to_period("M")
        available = cal["available"].astype(str).str.lower().isin({"t", "true", "1"})
        cal["unavailable"] = (~available).astype(int)
        return cal.groupby("month").agg(unavailable_rate=("unavailable", "mean"), comp_calendar_rows=("listing_id", "size")).reset_index().assign(month=lambda d: d["month"].astype(str))
