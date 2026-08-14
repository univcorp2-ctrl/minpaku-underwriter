from __future__ import annotations

import json
from pathlib import Path

import typer

from .analysis import forecast_from_history
from .geocode import geocode_address
from .inside_airbnb import InsideAirbnbTokyo
from .models import PropertyInput
from .report import save_report

app = typer.Typer(no_args_is_help=True)


@app.command()
def analyze(
    input_json: Path,
    out: Path = Path("reports"),
    snapshot_date: str | None = None,
    radius_km: float = 1.5,
    months: int = 36,
) -> None:
    """Analyze one property object or an array of properties."""
    raw = json.loads(input_json.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else [raw]
    provider = InsideAirbnbTokyo()
    snapshot = provider.load_snapshot(snapshot_date=snapshot_date, include_calendar=False)
    typer.echo(f"Inside Airbnb Tokyo snapshot: {snapshot.snapshot_date}")

    for item in items:
        target = PropertyInput.model_validate(item)
        if target.latitude is None or target.longitude is None:
            lat, lon = geocode_address(target.address)
            target.latitude, target.longitude = lat, lon
        comps = provider.select_comps(
            snapshot.listings,
            target.latitude,
            target.longitude,
            target.room_type,
            target.bedrooms,
            target.accommodates,
            radius_km=radius_km,
        )
        history = provider.review_occupancy_history(comps, snapshot.reviews, months=months)
        result = forecast_from_history(target, history)
        json_path, png_path = save_report(target, result, out)
        typer.echo(f"{target.code}: grade={result.grade} score={result.score:.1f} comps={result.comp_count}")
        typer.echo(f"  {json_path}\n  {png_path}")


@app.command("discover-snapshots")
def discover_snapshots() -> None:
    for value in InsideAirbnbTokyo().discover_dates():
        typer.echo(value)


if __name__ == "__main__":
    app()
