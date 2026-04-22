"""
charts.py — Bond analytics visualization module
=================================================
Four publication-quality charts for the bond analytics dashboard.
Titles are intentionally omitted — each chart is headed by st.subheader() in app.py.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bond import Bond

COLORS = {
    "primary":    "#1B3A6B",
    "accent":     "#E8912D",
    "positive":   "#2ECC71",
    "negative":   "#E74C3C",
    "neutral":    "#95A5A6",
    "background": "#F8F9FA",
    "grid":       "#DEE2E6",
    "orange":     "#E8A838",
}

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "axes.facecolor":    COLORS["background"],
    "figure.facecolor":  "white",
    "axes.grid":         True,
    "grid.color":        COLORS["grid"],
    "grid.linewidth":    0.6,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})


def plot_price_yield_curve(bond: "Bond") -> plt.Figure:
    """Price / Yield curve highlighting convexity gain vs duration tangent."""
    fig, ax = plt.subplots(figsize=(9, 5))

    y_current = bond.market_rate
    y_range = np.linspace(max(0.001, y_current - 0.04), y_current + 0.04, 200)
    prices = [bond.price(y) for y in y_range]
    current_price = bond.price(y_current)

    # Actual convex curve
    ax.plot(
        y_range * 100, prices,
        color=COLORS["primary"], linewidth=2.5,
        label="Actual Price (convex)", zorder=3,
    )

    # Duration tangent (linear approximation)
    mod_dur = bond.modified_duration()
    tangent_prices = [current_price * (1 - mod_dur * (y - y_current)) for y in y_range]
    ax.plot(
        y_range * 100, tangent_prices,
        color=COLORS["neutral"], linewidth=1.5, linestyle="--",
        label=f"Duration approx. (ModDur = {mod_dur:.2f})", zorder=2,
    )

    # Convexity gain — filled area with visible green borders
    ax.fill_between(
        y_range * 100, tangent_prices, prices,
        alpha=0.25, color=COLORS["positive"],
        label="Convexity gain (vs linear approx.)",
    )
    ax.plot(y_range * 100, prices,        color=COLORS["positive"], linewidth=0.8, zorder=4, alpha=0.7)
    ax.plot(y_range * 100, tangent_prices, color=COLORS["positive"], linewidth=0.8, zorder=4, alpha=0.7)

    # Current yield marker
    ax.axvline(
        x=y_current * 100,
        color=COLORS["accent"], linewidth=1.8, linestyle=":", alpha=0.9,
        label=f"Current yield: {y_current*100:.2f}%",
    )
    ax.scatter([y_current * 100], [current_price], color=COLORS["accent"], s=80, zorder=5)

    # Par reference
    ax.axhline(
        y=bond.face_value,
        color=COLORS["neutral"], linewidth=1.0, linestyle=":", alpha=0.7,
        label=f"Par ({bond.face_value:,.0f})",
    )

    ax.set_xlabel("Yield (%)", fontsize=11)
    ax.set_ylabel("Bond Price", fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.1f}"))
    fig.suptitle("")
    fig.tight_layout()
    return fig


def plot_cash_flows(bond: "Bond") -> plt.Figure:
    """PV of each cash flow, with Macaulay Duration marker.
    Navy = coupons, orange = principal repayment.
    """
    fig, ax = plt.subplots(figsize=(9, 4.5))

    y_p = bond.market_rate / bond.frequency
    n = bond.n_periods
    C = bond.coupon_payment
    FV = bond.face_value
    freq = bond.frequency

    periods = list(range(1, n + 1))
    years_axis = [t / freq for t in periods]
    bar_width = 0.8 / freq

    pv_coupons = [C / (1 + y_p) ** t for t in periods]
    pv_final_coupon = pv_coupons[-1]
    pv_face = FV / (1 + y_p) ** n

    # Coupon bars (navy)
    ax.bar(
        years_axis[:-1], pv_coupons[:-1],
        color=COLORS["primary"], alpha=0.85,
        label="PV of coupon", width=bar_width,
    )
    # Last period: coupon (navy) + principal (orange) stacked
    ax.bar(years_axis[-1], pv_final_coupon,
           color=COLORS["primary"], alpha=0.85, width=bar_width)
    ax.bar(years_axis[-1], pv_face, bottom=pv_final_coupon,
           color=COLORS["orange"], alpha=0.90,
           label="PV of principal", width=bar_width)

    # Macaulay Duration line
    mac_dur = bond.macaulay_duration()
    ax.axvline(
        x=mac_dur, color=COLORS["negative"], linewidth=2, linestyle="--",
        label=f"Macaulay Duration = {mac_dur:.2f}y",
    )

    # X-axis in years, one tick per year
    tick_years = list(range(1, int(bond.years_to_maturity) + 1))
    ax.set_xticks(tick_years)
    ax.set_xticklabels([f"{y}Y" for y in tick_years], fontsize=9)

    # Y-axis: start at 0, 15% headroom
    max_bar = max(pv_coupons[:-1] + [pv_final_coupon + pv_face]) if len(pv_coupons) > 1 else pv_final_coupon + pv_face
    ax.set_ylim(0, max_bar * 1.15)

    ax.set_xlabel("Years", fontsize=11)
    ax.set_ylabel("Present Value", fontsize=11)
    ax.legend(fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.1f}"))
    fig.suptitle("")
    fig.tight_layout()
    return fig


def plot_sensitivity_decomposition(bond: "Bond", delta_y_bps: int = 100) -> plt.Figure:
    """Waterfall: initial price → duration effect → convexity adjustment → estimated vs actual."""
    delta_y = delta_y_bps / 10000
    result = bond.price_change_estimate(delta_y)
    P0 = bond.price()

    fig, ax = plt.subplots(figsize=(7, 4.5))

    categories = [
        f"Initial Price\n({P0:,.2f})",
        f"Duration Effect\n({result['duration_effect_pct']:.2f}%)",
        f"Convexity Adj.\n(+{result['convexity_effect_pct']:.3f}%)",
        f"Est. Price\n({result['estimated_price']:,.2f})",
        f"Actual Price\n({result['actual_price']:,.2f})",
    ]
    values = [
        P0,
        result["duration_effect_pct"] / 100 * P0,
        result["convexity_effect_pct"] / 100 * P0,
        result["estimated_price"],
        result["actual_price"],
    ]
    bar_colors = [
        COLORS["primary"], COLORS["negative"],
        COLORS["positive"], COLORS["neutral"], COLORS["accent"],
    ]

    ax.bar(
        range(len(categories)),
        [abs(v) if i in (1, 2) else v for i, v in enumerate(values)],
        color=bar_colors, alpha=0.85, width=0.6,
    )
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=8.5)
    ax.set_ylabel("Price", fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.1f}"))
    ax.text(
        0.98, 0.97, f"Approx. error: {result['approximation_error']:.4f}",
        transform=ax.transAxes, fontsize=8, ha="right", va="top",
        color=COLORS["neutral"],
    )
    fig.suptitle("")
    fig.tight_layout()
    return fig


def plot_yield_curve(rates: dict[str, float]) -> plt.Figure:
    """US Treasury yield curve from FRED data."""
    maturities_map = {"1Y": 1, "2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}

    maturities, yields, labels = [], [], []
    for label, y in sorted(rates.items(), key=lambda x: maturities_map.get(x[0], 0)):
        if label in maturities_map:
            maturities.append(maturities_map[label])
            yields.append(y)
            labels.append(label)

    fig, ax = plt.subplots(figsize=(7, 4))

    ax.plot(maturities, yields,
            color=COLORS["primary"], linewidth=2.5, marker="o", markersize=7, zorder=3)
    ax.fill_between(maturities, yields, min(yields) - 0.1,
                    alpha=0.08, color=COLORS["primary"])

    if yields and yields[0] > yields[-1]:
        ax.text(
            0.98, 0.95, "Inverted Curve",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=9, color=COLORS["negative"], fontweight="bold",
        )

    for x, y in zip(maturities, yields):
        ax.annotate(f"{y:.2f}%", (x, y),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8)

    ax.set_xlabel("Maturity (years)", fontsize=11)
    ax.set_ylabel("Yield (%)", fontsize=11)
    ax.set_xticks(maturities)
    ax.set_xticklabels(labels)
    fig.suptitle("")
    fig.tight_layout()
    return fig
