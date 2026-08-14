from __future__ import annotations

import os
from typing import Any

import requests


class AirbticsClient:
    """Thin optional client.

    Airbtics publishes endpoint names and pay-as-you-go prices, while the API docs
    define the current base URL/auth details. We make both configurable rather than
    hard-coding a brittle undocumented assumption.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("AIRBTICS_API_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("AIRBTICS_API_KEY", "")
        if not self.base_url or not self.api_key:
            raise RuntimeError("AIRBTICS_API_BASE_URL and AIRBTICS_API_KEY are required")

    def _get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params=params,
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def report_summary(self, **params: Any) -> dict[str, Any]:
        return self._get("report/summary", **params)

    def report_all(self, **params: Any) -> dict[str, Any]:
        return self._get("report/all", **params)

    def market_history(self, **params: Any) -> dict[str, Any]:
        return self._get("markets/metrics/all", **params)

    def listings_in_bounds(self, **params: Any) -> dict[str, Any]:
        return self._get("listings/search/bounds", **params)

    def listing_history(self, **params: Any) -> dict[str, Any]:
        return self._get("listings/metrics/all", **params)
