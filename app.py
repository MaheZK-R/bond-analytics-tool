"""
app.py — Bond Analytics Tool — Streamlit Application
======================================================
Entry point. Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.bond import Bond
from src.fred import fetch_current_treasury_rates
from src.charts import (
    plot_price_yield_curve,
    plot_cash_flows,
    plot_sensitivity_decomposition,
    plot_yield_curve,
)

# ── Page configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bond Analytics Tool",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #F8F9FA;
        border-left: 4px solid #1B3A6B;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    .metric-label { font-size: 0.78rem; color: #6C757D; font-weight: 500; }
    .metric-value { font-size: 1.4rem; color: #1B3A6B; font-weight: 700; }
    .metric-value.positive { color: #2ECC71; }
    .metric-value.negative { color: #E74C3C; }
    .insight-box {
        background: #EBF3FB;
        border: 1px solid #AED6F1;
        border-radius: 6px;
        padding: 12px 16px;
        font-size: 0.88rem;
        margin-top: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Bond Analytics")
    st.caption("Fixed income calculator — CFA L1 concepts")

    st.divider()
    st.subheader("Bond Parameters")

    face_value = st.number_input(
        "Face Value (€ / $)",
        min_value=10.0, max_value=1_000_000.0,
        value=100.0, step=10.0,
        help="Par / nominal value of the bond.",
    )
    coupon_rate_pct = st.slider(
        "Annual Coupon Rate (%)",
        min_value=0.0, max_value=15.0,
        value=5.0, step=0.25,
        help="Annual coupon rate as % of face value.",
    )
    years_to_maturity = st.slider(
        "Years to Maturity",
        min_value=1, max_value=30,
        value=10, step=1,
    )
    market_rate_pct = st.slider(
        "Market Yield / Discount Rate (%)",
        min_value=0.1, max_value=15.0,
        value=4.5, step=0.1,
        help="Current annual yield used to discount cash flows.",
    )
    frequency = st.radio(
        "Coupon Frequency",
        options=[2, 1],
        format_func=lambda x: "Semi-Annual (standard)" if x == 2 else "Annual",
        horizontal=True,
        help="Semi-annual is the market convention for US Treasuries and IG corporates.",
    )

    st.divider()
    st.subheader("Stress Test")
    shock_bps = st.slider(
        "Yield Shock (basis points)",
        min_value=10, max_value=500,
        value=100, step=10,
    )

    st.divider()
    st.subheader("US Treasury Rates")
    treasury_rates_sidebar = fetch_current_treasury_rates()
    for label, rate in sorted(treasury_rates_sidebar.items()):
        st.metric(label=label, value=f"{rate:.2f}%")
    st.caption("Source: FRED · refreshes hourly")


# ── Bond instance ─────────────────────────────────────────────────────────────
bond = Bond(
    face_value=face_value,
    coupon_rate=coupon_rate_pct / 100,
    years_to_maturity=years_to_maturity,
    market_rate=market_rate_pct / 100,
    frequency=frequency,
)
metrics = bond.summary()
current_price = metrics["price"]

if abs(current_price - face_value) < 0.01 * face_value:
    pricing_label = "At Par"
elif current_price > face_value:
    pricing_label = "At Premium"
else:
    pricing_label = "At Discount"


# ── Page header ───────────────────────────────────────────────────────────────
st.title("Bond Analytics Tool")
st.markdown(
    "*Fixed income calculator: yield, duration, convexity, and price sensitivity — "
    "built from first principles following CFA L1 curriculum.*  \n"
    "*by [Nieucel Mahe](https://github.com/MaheZK-R)*"
)


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Key Metrics", "Price vs Yield", "Cash Flows", "Sensitivity", "Yield Curve",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — KEY METRICS
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Bond Analytics Summary")

    # Row 1 — three quick-reference metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Modified Duration", f"{metrics['modified_duration']:.4f}")
    m2.metric("Convexity",          f"{metrics['convexity']:.4f}")
    m3.metric("YTM",                f"{metrics['ytm_pct']:.3f}%")

    # Hero price + status badge
    badge_color = {"At Premium": "#2ECC71", "At Discount": "#E74C3C", "At Par": "#1B3A6B"}[pricing_label]
    st.markdown(f"""
    <div style="margin: 20px 0 4px 0; display: flex; align-items: center; gap: 14px;">
        <span style="font-size: 2.6rem; font-weight: 700; color: #1B3A6B;
                     letter-spacing: -0.5px;">{current_price:,.4f}</span>
        <span style="background: {badge_color}; color: white; font-size: 0.75rem;
                     font-weight: 600; padding: 4px 12px; border-radius: 12px;">
            {pricing_label.upper()}
        </span>
    </div>
    <div style="font-size: 0.77rem; color: #8C9BAB; margin-bottom: 24px;">
        Full price (dirty) — accrued interest not modelled
    </div>
    """, unsafe_allow_html=True)

    # Two columns: Pricing | Risk Metrics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Pricing")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Bond Price</div>
            <div class="metric-value">{current_price:,.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Yield to Maturity (= Market Rate)</div>
            <div class="metric-value">{metrics['ytm_pct']:.4f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### Risk Metrics")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Macaulay Duration</div>
            <div class="metric-value">{metrics['macaulay_duration']:.4f} years</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Modified Duration</div>
            <div class="metric-value">{metrics['modified_duration']:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Convexity</div>
            <div class="metric-value">{metrics['convexity']:.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">DV01 — price change per +1bp yield</div>
            <div class="metric-value">{metrics['dv01']:.4f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Single insight box for Tab 1
    diff = current_price - face_value
    if diff > 0.01 * face_value:
        insight = (f"Trading at <strong>premium</strong> of {diff:,.2f} — "
                   f"coupon ({coupon_rate_pct:.2f}%) &gt; market rate ({market_rate_pct:.2f}%). "
                   f"YTM &lt; coupon rate.")
    elif diff < -0.01 * face_value:
        insight = (f"Trading at <strong>discount</strong> of {abs(diff):,.2f} — "
                   f"coupon ({coupon_rate_pct:.2f}%) &lt; market rate ({market_rate_pct:.2f}%). "
                   f"YTM &gt; coupon rate.")
    else:
        insight = "Trading <strong>at par</strong> — coupon rate equals market rate. YTM = coupon rate."
    st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PRICE vs YIELD CURVE
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Price / Yield Relationship — Convexity Visualization")
    st.markdown(
        "The actual price/yield curve (navy) is **convex** — always above the duration "
        "tangent line (grey dashed). The green shaded area is the **convexity gain**: "
        "for any yield move, the actual price outperforms the linear approximation."
    )
    st.pyplot(plot_price_yield_curve(bond), use_container_width=True)

    st.markdown(f"""
    <div class="insight-box">
    <strong>Key insight:</strong> Convexity = {metrics['convexity']:.2f}.
    The convexity adjustment (<em>½ × C × Δy²</em>) is always positive — it adds value
    for both yield increases and decreases. Higher convexity means the bond outperforms
    the duration approximation the more yields move.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — CASH FLOWS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Cash Flow Profile — Present Value by Period")
    st.markdown(
        "Each bar is the PV of a cash flow. "
        "<strong>Navy</strong> = coupons, <strong>orange</strong> = principal repayment at maturity. "
        "The red dashed line marks the Macaulay Duration.",
        unsafe_allow_html=True,
    )
    st.pyplot(plot_cash_flows(bond), use_container_width=True)

    pct_of_maturity = metrics['macaulay_duration'] / years_to_maturity * 100
    st.markdown(f"""
    <div class="insight-box">
    Macaulay Duration = <strong>{metrics['macaulay_duration']:.2f} years</strong>
    ({pct_of_maturity:.1f}% of total maturity).
    For a zero-coupon bond, duration equals maturity (single cash flow at T=n).
    For coupon bonds, intermediate cash flows pull the weighted average forward.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — SENSITIVITY & STRESS TEST
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Price Sensitivity — ±{shock_bps}bps Yield Shock")
    st.pyplot(plot_sensitivity_decomposition(bond, shock_bps), use_container_width=True)

    st.divider()
    st.subheader("Scenario Analysis — Multiple Yield Shocks")
    scenarios = [-300, -200, -100, -50, 0, 50, 100, 200, 300]
    rows = []
    for bps in scenarios:
        if bps == 0:
            rows.append({
                "Yield Shock": "0 bps (current)",
                "Yield": f"{market_rate_pct:.2f}%",
                "Estimated Price": f"{current_price:,.4f}",
                "Actual Price": f"{current_price:,.4f}",
                "Price Change %": "—",
            })
        else:
            r = bond.price_change_estimate(bps / 10000)
            rows.append({
                "Yield Shock": f"{bps:+d} bps",
                "Yield": f"{market_rate_pct + bps/100:.2f}%",
                "Estimated Price": f"{r['estimated_price']:,.4f}",
                "Actual Price": f"{r['actual_price']:,.4f}",
                "Price Change %": f"{r['total_effect_pct']:+.3f}%",
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — LIVE YIELD CURVE (FRED — cached hourly via @st.cache_data)
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("US Treasury Yield Curve — Live (FRED)")
    st.markdown(
        "Real-time US Treasury yields from the Federal Reserve Economic Data API. "
        "An inverted curve (short > long rates) has historically preceded recessions."
    )

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        if st.button("Refresh"):
            fetch_current_treasury_rates.clear()
            st.rerun()

    treasury_rates = fetch_current_treasury_rates()
    st.pyplot(plot_yield_curve(treasury_rates), use_container_width=True)

    # Credit spread — linear interpolation between bracketing tenors
    tenor_map = {
        k: v for k, v in {"1Y": 1, "2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}.items()
        if k in treasury_rates
    }
    tenors = sorted(tenor_map.items(), key=lambda x: x[1])
    T = years_to_maturity

    if T <= tenors[0][1]:
        rf_rate = treasury_rates[tenors[0][0]]
        interp_note = tenors[0][0]
    elif T >= tenors[-1][1]:
        rf_rate = treasury_rates[tenors[-1][0]]
        interp_note = tenors[-1][0]
    else:
        lower = max((t for t in tenors if t[1] <= T), key=lambda x: x[1])
        upper = min((t for t in tenors if t[1] >= T), key=lambda x: x[1])
        if lower[1] == upper[1]:
            rf_rate = treasury_rates[lower[0]]
            interp_note = lower[0]
        else:
            w = (T - lower[1]) / (upper[1] - lower[1])
            rf_rate = treasury_rates[lower[0]] * (1 - w) + treasury_rates[upper[0]] * w
            interp_note = (
                f"interpolated {lower[0]}–{upper[0]} "
                f"({treasury_rates[lower[0]]:.2f}%–{treasury_rates[upper[0]]:.2f}%)"
            )

    spread = market_rate_pct - rf_rate
    st.markdown(f"""
    <div class="insight-box">
    Bond yield ({market_rate_pct:.2f}%) vs. risk-free rate ({interp_note}: {rf_rate:.2f}%) →
    <strong>credit spread of {spread:.2f}%</strong>.
    This spread reflects credit risk, liquidity premium, and any other risks vs. the risk-free rate.
    </div>
    """, unsafe_allow_html=True)


# ── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "bond-analytics-tool · Built by Nieucel Mahe · "
    "From CFA L1 first principles · "
    "Data: FRED (Federal Reserve) · "
    "Educational purpose only"
)
