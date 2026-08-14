from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .models import ForecastResult, PropertyInput


def _bounded_adjustment(base: float, target: PropertyInput) -> float:
    factor = 1.0
    if target.walk_minutes is not None:
        # Small bounded heuristic until learned coefficients are available.
        factor *= float(np.clip(1.04 - 0.008 * max(target.walk_minutes - 3, 0), 0.88, 1.04))
    if target.design_score is not None:
        factor *= float(np.clip(0.90 + 0.002 * target.design_score, 0.90, 1.10))
    return float(np.clip(base * factor, 0.02, 0.95))


def _annual_gross(occupancy: float, adr: float, target: PropertyInput) -> float:
    demand_nights = occupancy * 365
    if target.annual_sellable_nights is not None:
        booked = min(demand_nights, float(target.annual_sellable_nights))
    else:
        booked = demand_nights
    return booked * adr


def _cashflow(gross: float, target: PropertyInput) -> float:
    net_after_variable = gross * (1 - target.platform_fee_rate - target.variable_cost_rate)
    return net_after_variable - target.monthly_fixed_yen * 12


def _grade(score: float, hard_stop: bool) -> str:
    if hard_stop:
        return "D"
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    return "D"


def forecast_from_history(target: PropertyInput, history: pd.DataFrame) -> ForecastResult:
    if history.empty:
        raise ValueError("history is empty")
    recent = history.tail(min(24, len(history))).copy()
    occ_mean_raw = float(recent["occupancy_mean"].mean())
    occ_std = float(np.sqrt(np.nanmean(np.square(recent["occupancy_std"].fillna(0))) + np.nanvar(recent["occupancy_mean"])))
    occ_p50_raw = float(recent["occupancy_p50"].median())
    occ_p10_raw = float(recent["occupancy_p10"].median())
    occ_p90_raw = float(recent["occupancy_p90"].median())

    occ_mean = _bounded_adjustment(occ_mean_raw, target)
    occ_p50 = _bounded_adjustment(occ_p50_raw, target)
    occ_p10 = float(np.clip(_bounded_adjustment(occ_p10_raw, target), 0, occ_p50))
    occ_p90 = float(np.clip(_bounded_adjustment(occ_p90_raw, target), occ_p50, 0.95))

    adr_series = pd.to_numeric(recent["adr_proxy_yen"], errors="coerce").dropna()
    if adr_series.empty:
        raise ValueError("No ADR proxy available")
    adr_p50 = float(adr_series.median())
    # Free mode has no realized historical ADR, so deliberately widen the interval.
    adr_p10 = float(max(1000, adr_p50 * 0.72))
    adr_p90 = float(adr_p50 * 1.28)

    gross10 = _annual_gross(occ_p10, adr_p10, target)
    gross50 = _annual_gross(occ_p50, adr_p50, target)
    gross90 = _annual_gross(occ_p90, adr_p90, target)
    cash50 = _cashflow(gross50, target)
    roi = cash50 / target.initial_investment_yen if target.initial_investment_yen > 0 else None
    monthly_cash = cash50 / 12
    payback = target.initial_investment_yen / monthly_cash if target.initial_investment_yen > 0 and monthly_cash > 0 else None

    comp_count = int(recent["comp_count"].median())
    sample_score = min(100.0, comp_count / 50 * 100)
    econ_margin = cash50 / max(target.monthly_fixed_yen * 12, 1)
    econ_score = float(np.clip(50 + econ_margin * 70, 0, 100))
    demand_score = float(np.clip((occ_p50 / 0.70) * 70 + min(adr_p50 / 30000, 1) * 30, 0, 100))
    legal_score = 70 if target.legal_mode != "unknown" else 35
    confidence = float(np.clip(0.30 + min(comp_count, 50) / 100 + min(len(recent), 24) / 120, 0, 0.78))
    score = 0.35 * econ_score + 0.25 * demand_score + 0.15 * sample_score + 0.15 * legal_score + 0.10 * 50

    hard_stop = cash50 < 0
    reasons = [
        f"Comparable sample median count: {comp_count}",
        f"Review-model occupancy p50: {occ_p50:.1%}",
        f"Free-mode ADR proxy p50: ¥{adr_p50:,.0f}",
    ]
    risks = [
        "Inside Airbnb unavailable dates cannot distinguish bookings from owner blocks.",
        "Free-mode historical revenue uses price snapshots, not realized transaction ADR.",
        "Deleted historical listings are absent from the latest snapshot, creating survivor bias.",
    ]
    unknowns = []
    if target.legal_mode == "unknown":
        unknowns.append("Operating permit route is not verified (Housing Accommodation Business Act vs Hotel Business Act).")
    if target.annual_sellable_nights is None:
        unknowns.append("Lawful annual sellable nights are not fixed in the input.")
    if target.initial_investment_yen <= 0:
        unknowns.append("Initial investment is zero/unknown, so ROI/payback is not calculated.")

    return ForecastResult(
        code=target.code,
        comp_count=comp_count,
        source="inside_airbnb_review_model",
        confidence=confidence,
        occupancy_p10=occ_p10,
        occupancy_p50=occ_p50,
        occupancy_p90=occ_p90,
        occupancy_mean=occ_mean,
        occupancy_std=occ_std,
        adr_p10_yen=adr_p10,
        adr_p50_yen=adr_p50,
        adr_p90_yen=adr_p90,
        gross_revenue_p10_yen=gross10,
        gross_revenue_p50_yen=gross50,
        gross_revenue_p90_yen=gross90,
        annual_cashflow_p50_yen=cash50,
        roi_p50=roi,
        payback_months_p50=payback,
        score=float(np.clip(score, 0, 100)),
        grade=_grade(score, hard_stop),
        hard_stop=hard_stop,
        reasons=reasons,
        risks=risks,
        unknowns=unknowns,
    )
