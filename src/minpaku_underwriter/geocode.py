from __future__ import annotations

import time
from typing import Any

import requests

UA = "minpaku-underwriter/0.1 (research; respectful public geocoding usage)"


def _photon(address: str, timeout: int = 20) -> tuple[float, float] | None:
    r = requests.get(
        "https://photon.komoot.io/api/",
        params={"q": address, "limit": 1},
        headers={"User-Agent": UA},
        timeout=timeout,
    )
    r.raise_for_status()
    features: list[dict[str, Any]] = r.json().get("features", [])
    if not features:
        return None
    lon, lat = features[0]["geometry"]["coordinates"]
    return float(lat), float(lon)


def _nominatim(address: str, timeout: int = 20) -> tuple[float, float] | None:
    time.sleep(1.05)
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": UA},
        timeout=timeout,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return None
    return float(rows[0]["lat"]), float(rows[0]["lon"])


def geocode_address(address: str) -> tuple[float, float]:
    for fn in (_photon, _nominatim):
        try:
            result = fn(address)
            if result:
                return result
        except requests.RequestException:
            continue
    raise RuntimeError(f"Could not geocode address: {address}")
