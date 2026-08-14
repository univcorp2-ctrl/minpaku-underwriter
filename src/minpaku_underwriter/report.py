from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from .models import ForecastResult, PropertyInput


def _yen(v: float) -> str:
    return f"¥{v:,.0f}"


def save_report(target: PropertyInput, result: ForecastResult, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir) / target.code
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "analysis.json"
    json_path.write_text(
        json.dumps({"property": target.model_dump(), "result": result.model_dump()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    png_path = out / "summary.png"
    fig = plt.figure(figsize=(12, 7), facecolor="#f7f7f5")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    grade_color = {"A": "#0b8f55", "B": "#3d7edb", "C": "#d99000", "D": "#c83f49"}[result.grade]
    fig.text(0.05, 0.91, f"MINPAKU UNDERWRITING  {target.code}", fontsize=23, weight="bold", color="#171717")
    fig.text(0.05, 0.865, target.address, fontsize=12, color="#555")
    fig.text(0.83, 0.87, result.grade, fontsize=58, weight="bold", color=grade_color, ha="center")
    fig.text(0.83, 0.82, f"Score {result.score:.0f}/100", fontsize=14, ha="center", color="#333")

    blocks = [
        ("Occupancy p10 / p50 / p90", f"{result.occupancy_p10:.0%}  /  {result.occupancy_p50:.0%}  /  {result.occupancy_p90:.0%}"),
        ("ADR p10 / p50 / p90", f"{_yen(result.adr_p10_yen)}  /  {_yen(result.adr_p50_yen)}  /  {_yen(result.adr_p90_yen)}"),
        ("Gross revenue p50", _yen(result.gross_revenue_p50_yen)),
        ("Annual cash flow p50", _yen(result.annual_cashflow_p50_yen)),
        ("Comparable listings", str(result.comp_count)),
        ("Evidence confidence", f"{result.confidence:.0%}"),
    ]
    y = 0.72
    for label, value in blocks:
        fig.text(0.06, y, label, fontsize=11, color="#777")
        fig.text(0.32, y, value, fontsize=16, weight="bold", color="#111")
        y -= 0.085

    risk_text = "\n".join(f"• {x}" for x in (result.risks + result.unknowns)[:5])
    fig.text(0.60, 0.70, "Risk / Unknown", fontsize=14, weight="bold", color="#222")
    fig.text(0.60, 0.65, risk_text, fontsize=10.5, color="#444", va="top", wrap=True)
    fig.text(0.05, 0.06, f"Source: {result.source}  |  estimated metrics are explicitly labelled; not a booking ledger", fontsize=9, color="#777")
    fig.savefig(png_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return json_path, png_path
