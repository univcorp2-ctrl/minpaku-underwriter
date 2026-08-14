from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PropertyInput(BaseModel):
    code: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    nearest_station: str | None = None
    walk_minutes: float | None = None
    monthly_rent_yen: int
    monthly_management_yen: int = 0
    initial_investment_yen: int = 0
    sqm: float | None = None
    layout: str | None = None
    bedrooms: int | None = None
    accommodates: int = 2
    room_type: str = "Entire home/apt"
    build_year: int | None = None
    legal_mode: Literal["housing_act", "hotel_act", "unknown"] = "unknown"
    annual_sellable_nights: int | None = None
    design_score: float | None = Field(default=None, ge=0, le=100)
    platform_fee_rate: float = Field(default=0.15, ge=0, le=0.5)
    variable_cost_rate: float = Field(default=0.08, ge=0, le=0.5)
    monthly_utilities_yen: int = 30_000

    @model_validator(mode="after")
    def set_sellable_default(self) -> "PropertyInput":
        if self.annual_sellable_nights is None and self.legal_mode == "housing_act":
            self.annual_sellable_nights = 180
        return self

    @property
    def monthly_fixed_yen(self) -> int:
        return self.monthly_rent_yen + self.monthly_management_yen + self.monthly_utilities_yen


class ForecastResult(BaseModel):
    code: str
    comp_count: int
    source: str
    confidence: float = Field(ge=0, le=1)
    occupancy_p10: float
    occupancy_p50: float
    occupancy_p90: float
    occupancy_mean: float
    occupancy_std: float
    adr_p10_yen: float
    adr_p50_yen: float
    adr_p90_yen: float
    gross_revenue_p10_yen: float
    gross_revenue_p50_yen: float
    gross_revenue_p90_yen: float
    annual_cashflow_p50_yen: float
    roi_p50: float | None
    payback_months_p50: float | None
    score: float
    grade: str
    hard_stop: bool
    reasons: list[str]
    risks: list[str]
    unknowns: list[str]
