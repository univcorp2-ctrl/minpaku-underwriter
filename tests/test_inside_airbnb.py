import pandas as pd

from minpaku_underwriter.inside_airbnb import InsideAirbnbTokyo


def test_review_history_is_anchored_to_snapshot_not_today():
    comps = pd.DataFrame(
        [
            {
                "id": 1,
                "minimum_nights": 2,
                "first_review": "2026-01-01",
                "price": "¥20,000",
                "distance_km": 0.3,
                "comp_weight": 1.0,
            }
        ]
    )
    reviews = pd.DataFrame(
        [
            {"listing_id": 1, "date": "2026-05-10"},
            {"listing_id": 1, "date": "2026-06-10"},
        ]
    )
    history = InsideAirbnbTokyo.review_occupancy_history(
        comps,
        reviews,
        months=2,
        as_of="2026-06-30",
    )
    assert history["month"].tolist() == ["2026-05", "2026-06"]
    assert (history["occupancy_mean"] > 0).all()
