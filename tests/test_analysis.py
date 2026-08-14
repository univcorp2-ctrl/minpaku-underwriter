import pandas as pd

from minpaku_underwriter.analysis import forecast_from_history
from minpaku_underwriter.models import PropertyInput


def test_housing_act_caps_revenue_nights():
    target = PropertyInput(
        code="T1",
        address="Tokyo",
        monthly_rent_yen=100000,
        monthly_management_yen=10000,
        initial_investment_yen=1000000,
        legal_mode="housing_act",
    )
    hist = pd.DataFrame(
        [
            {
                "month": f"2026-{m:02d}",
                "occupancy_mean": 0.65,
                "occupancy_std": 0.08,
                "occupancy_p10": 0.50,
                "occupancy_p50": 0.65,
                "occupancy_p90": 0.70,
                "adr_proxy_yen": 20000,
                "comp_count": 40,
            }
            for m in range(1, 13)
        ]
    )
    result = forecast_from_history(target, hist)
    assert target.annual_sellable_nights == 180
    assert result.gross_revenue_p50_yen <= 180 * result.adr_p50_yen + 1
    assert 0 <= result.score <= 100


def test_unknown_initial_investment_is_flagged():
    target = PropertyInput(code="T2", address="Tokyo", monthly_rent_yen=90000)
    hist = pd.DataFrame(
        [{
            "month": "2026-01",
            "occupancy_mean": 0.5,
            "occupancy_std": 0.1,
            "occupancy_p10": 0.3,
            "occupancy_p50": 0.5,
            "occupancy_p90": 0.7,
            "adr_proxy_yen": 18000,
            "comp_count": 25,
        }]
    )
    result = forecast_from_history(target, hist)
    assert result.roi_p50 is None
    assert any("Initial investment" in x for x in result.unknowns)
