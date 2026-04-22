"""
charts.py — Bond analytics visualization module
=================================================
Generates publication-quality charts for the bond analytics dashboard:

  1. Price vs Yield curve — the central visual showing convexity
  2. Cash flow waterfall — timing and PV of each cash flow
  3. Duration sensitivity bar — decomposition of price sensitivity
  4. Treasury yield curve — live data from FRED
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bond import Bond

# ── Visual style ────────────────────────────────────────────────────────────
# Clean, professional palette suitable for finance presentations
COLORS = {
    "primary": "#1B3A6B",      # Deep navy — serious, financial
    "accent": "#E8912D",       # Amber — highlight / current yield
    "positive": "#2ECC71",     # Green — convexity gain
    "negative": "#E74C3C",     # Red — duration loss
    "neutral": "#95A5A6",      # Grey — reference lines
    "background": "#F8F9FA",   # Off-white — clean background
    "grid": "#DEE2E6",         # Light grey — subtle grid
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.facecolor": COLORS["background"],
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": COLORS["grid"],
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def plot_price_yield_curve(bond: "Bond") -> plt.Figure:
    """
    Plot the Price / Yield curve for a bond.

    Key insight shown:
    - The curve is convex (bowed toward the origin), not linear
    - Duration = slope of tangent at current yield (linear approximation)
    - Convexity = degree of curvature — always benefits the bondholder
    - The gap between the tangent line and the actual curve = convexity adjustment

    Parameters
    ----------
    bond : Bond
        The bond instance to analyze.

    Returns
    -------
    matplotlib.Figure
    """
    fig, ax = plt.subplots(figsize=(9, 5))

    # ── Build yield range ± 400bps around current yield ──────────────────
    y_current = bond.market_rate
    y_range = np.linspace(max(0.001, y_current - 0.04), y_current + 0.04, 200)
    prices = [bond.price(y) for y in y_range]
    current_price = bond.price(y_current)

    # ── Actual price/yield curve (convex) ────────────────────────────────
    ax.plot(
        y_range * 100,
        prices,
        color=COLORS["primary"],
        linewidth=2.5,
        label="Actual Price (convex)",
        zorder=3,
    )

    # ── Duration tangent line (linear approximation) ─────────────────────
    mod_dur = bond.modified_duration()
    # P(y) ≈ P0 * [1 - ModDur * (y - y0)]
    tangent_prices = [current_price * (1 - mod_dur * (y - y_current)) for y in y_range]
    ax.plot(
        y_range * 100,
        tangent_prices,
        color=COLORS["neutral"],
        linewidth=1.5,
        linestyle="--",
        label=f"Duration approx. (ModDur = {mod_dur:.2f}y)",
        zorder=2,
    )

    # ── Convexity gap fill ────────────────────────────────────────────────
    ax.fill_between(
        y_range * 100,
        tangent_prices,
        prices,
        alpha=0.15,
        color=COLORS["positive"],
        label="Convexity gain (vs linear approx.)",
    )

    # ── Current yield marker ─────────────────────────────────────────────
    ax.axvline(
        x=y_current * 100,
        color=COLORS["accent"],
        linewidth=1.8,
        linestyle=":",
        alpha=0.9,
        label=f"Current yield: {y_current*100:.2f}%",
    )
    ax.scatter([y_current * 100], [current_price], color=COLORS["accent"], s=80, zorder=5)

    # ── Par value reference ───────────────────────────────────────────────
    ax.axhline(
        y=bond.face_value,
        color=COLORS["neutral"],
        linewidth=1.0,
        linestyle=":",
        alpha=0.7,
        label=f"Par value ({bond.face_value:,.0f})",
    )

    ax.set_xlabel("Yield (%)", fontsize=11)
    ax.set_ylabel("Bond Price", fontsize=11)
    ax.set_title("Price / Yield Relationship — Convexity Visualization", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=9, loc="upper right")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.1f}"))

    fig.tight_layout()
    return fig


def plot_cash_flows(bond: "Bond") -> plt.Figure:
    """
    Plot the present value of each cash flow over time.

    Shows visually how coupon payments and principal repayment
    contribute to the bond's total value. The weighted average timing
    = Macaulay Duration.
    """
    fig, ax = plt.subplots(figsize=(9, 4.5))

    y = bond.market_rate
    n = bond.n_periods
    C = bond.coupon_payment
    FV = bond.face_value

    periods = list(range(1, n + 1))
    pv_coupons = [C / (1 + y) ** t for t in periods]
    # Last period: coupon + face value
    pv_final_coupon = pv_coupons[-1]
    pv_face = FV / (1 + y) ** n

    # Bars for coupons
    bars = ax.bar(
        periods[:-1],
        pv_coupons[:-1],
        color=COLORS["primary"],
        alpha=0.75,
        label="PV of coupon",
        width=0.5,
    )
    # Final period: stacked bar (coupon + face value)
    ax.bar(n, pv_final_coupon, color=COLORS["primary"], alpha=0.75, width=0.5)
    ax.bar(n, pv_face, bottom=pv_final_coupon, color=COLORS["accent"], alpha=0.85, label="PV of principal", width=0.5)

    # Macaulay Duration marker
    mac_dur = bond.macaulay_duration()
    ax.axvline(
        x=mac_dur,
        color=COLORS["negative"],
        linewidth=2,
        linestyle="--",
        label=f"Macaulay Duration = {mac_dur:.2f}y",
    )

    ax.set_xlabel("Period (years)", fontsize=11)
    ax.set_ylabel("Present Value", fontsize=11)
    ax.set_title("Cash Flow Profile — Present Value by Period", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(periods)
    ax.legend(fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    return fig


def plot_sensitivity_decomposition(bond: "Bond", delta_y_bps: int = 100) -> plt.Figure:
    """
    Waterfall chart decomposing price change into duration effect + convexity effect.

    Parameters
    ----------
    delta_y_bps : int
        Yield shock in basis points (e.g., 100 = +1%).
    """
    delta_y = delta_y_bps / 10000
    result = bond.price_change_estimate(delta_y)
    P0 = bond.price()

    fig, ax = plt.subplots(figsize=(7, 4.5))

    categories = [
        f"Initial Price\n({P0:,.2f})",
        f"Duration Effect\n({result['duration_effect_pct']:.2f}%)",
        f"Convexity Adjustment\n(+{result['convexity_effect_pct']:.3f}%)",
        f"Est. New Price\n({result['estimated_price']:,.2f})",
        f"Actual New Price\n({result['actual_price']:,.2f})",
    ]

    values = [
        P0,
        result["duration_effect_pct"] / 100 * P0,
        result["convexity_effect_pct"] / 100 * P0,
        result["estimated_price"],
        result["actual_price"],
    ]

    bar_colors = [
        COLORS["primary"],
        COLORS["negative"],
        COLORS["positive"],
        COLORS["neutral"],
        COLORS["accent"],
    ]

    bars = ax.bar(
        range(len(categories)),
        [abs(v) if i in (1, 2) else v for i, v in enumerate(values)],
        color=bar_colors,
        alpha=0.85,
        width=0.6,
    )

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=8.5)
    ax.set_ylabel("Price", fontsize=11)
    ax.set_title(
        f"Price Sensitivity to +{delta_y_bps}bps Yield Shock\n"
        f"Duration vs Convexity Decomposition",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.1f}"))

    # Annotation: approximation error
    error = result["approximation_error"]
    ax.text(
        0.98, 0.97,
        f"Approx. error: {error:.4f}",
        transform=ax.transAxes,
        fontsize=8,
        ha="right",
        va="top",
        color=COLORS["neutral"],
    )

    fig.tight_layout()
    return fig


def plot_yield_curve(rates: dict[str, float]) -> plt.Figure:
    """
    Plot the US Treasury yield curve from FRED data.

    Parameters
    ----------
    rates : dict
        { '1Y': 5.10, '2Y': 4.80, ... }
    """
    maturities_map = {"1Y": 1, "2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}

    maturities = []
    yields = []
    for label, y in sorted(rates.items(), key=lambda x: maturities_map.get(x[0], 0)):
        if label in maturities_map:
            maturities.append(maturities_map[label])
            yields.append(y)

    fig, ax = plt.subplots(figsize=(7, 4))

    ax.plot(maturities, yields, color=COLORS["primary"], linewidth=2.5, marker="o", markersize=7, zorder=3)
    ax.fill_between(maturities, yields, min(yields) - 0.1, alpha=0.08, color=COLORS["primary"])

    # Inversion detection
    if yields[0] > yields[-1]:
        ax.text(
            0.98, 0.95,
            "⚠ Inverted Curve",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color=COLORS["negative"],
            fontweight="bold",
        )

    for x, y in zip(maturities, yields):
        ax.annotate(f"{y:.2f}%", (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8)

    ax.set_xlabel("Maturity (years)", fontsize=11)
    ax.set_ylabel("Yield (%)", fontsize=11)
    ax.set_title("US Treasury Yield Curve — Live (FRED)", fontsize=12, fontweight="bold", pad=10)
    ax.set_xticks(maturities)
    ax.set_xticklabels(["1Y", "2Y", "5Y", "10Y", "30Y"])

    fig.tight_layout()
    return fig
