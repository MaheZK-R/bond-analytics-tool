"""
app.py — Bond Analytics Tool — Streamlit Application
======================================================
Entry point. Run with:
    streamlit run app.py

Structure of the UI:
  - Sidebar    : bond parameters + risk-free rate reference (FRED)
  - Tab 1      : Key metrics dashboard
  - Tab 2      : Price / Yield curve (convexity visualization)
  - Tab 3      : Cash flow profile
  - Tab 4      : Sensitivity & stress test
  - Tab 5      : Live US Treasury yield curve
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

# ── Minimal custom CSS for cleaner aesthetics ────────────────────────────────
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


# ── Sidebar — Bond Parameters ────────────────────────────────────────────────
with st.sidebar:
    st.title("Bond Analytics")
    st.caption("Fixed income calculator — CFA L1 concepts")

    st.divider()
    st.subheader("Bond Parameters")

    face_value = st.number_input(
        "Face Value (€ / $)",
        min_value=100.0,
        max_value=1_000_000.0,
        value=1000.0,
        step=100.0,
        help="Par / nominal value of the bond.",
    )

    coupon_rate_pct = st.slider(
        "Annual Coupon Rate (%)",
        min_value=0.0,
        max_value=15.0,
        value=5.0,
        step=0.25,
        help="Annual coupon rate as % of face value.",
    )

    years_to_maturity = st.slider(
        "Years to Maturity",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        help="Remaining life of the bond in years.",
    )

    market_rate_pct = st.slider(
        "Market Yield / Discount Rate (%)",
        min_value=0.1,
        max_value=15.0,
        value=4.5,
        step=0.1,
        help="Current yield used to discount cash flows.",
    )

    st.divider()
    st.subheader("Stress Test")

    shock_bps = st.slider(
        "Yield Shock (basis points)",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="Hypothetical parallel shift in yield for sensitivity analysis.",
    )

    st.divider()

    # ── Load FRED rates ──────────────────────────────────────────────────
    st.subheader("US Treasury Rates (FRED)")
    with st.spinner("Fetching live rates..."):
        treasury_rates = fetch_current_treasury_rates()

    for label, rate in sorted(treasury_rates.items()):
        st.metric(label=label, value=f"{rate:.2f}%")

    st.caption("Source: Federal Reserve Economic Data (FRED)")


# ── Instantiate Bond ─────────────────────────────────────────────────────────
bond = Bond(
    face_value=face_value,
    coupon_rate=coupon_rate_pct / 100,
    years_to_maturity=years_to_maturity,
    market_rate=market_rate_pct / 100,
)

metrics = bond.summary()
current_price = metrics["price"]

# Determine if bond is at premium / discount / par
if abs(current_price - face_value) < 1:
    pricing_label = "At Par"
    pricing_color = "neutral"
elif current_price > face_value:
    pricing_label = "At Premium"
    pricing_color = "positive"
else:
    pricing_label = "At Discount"
    pricing_color = "negative"


# ── Header ───────────────────────────────────────────────────────────────────
st.title("Bond Analytics Tool")
st.markdown(
    "*Fixed income calculator: yield, duration, convexity, and price sensitivity — "
    "built from first principles following CFA L1 curriculum.*  \n"
    "*by [Nieucel Mahe](https://github.com/MaheZK-R)*"
)

# Quick status banner
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("Bond Price", f"{current_price:,.2f}", delta=f"{current_price - face_value:+.2f} vs par")
col_b.metric("YTM", f"{metrics['ytm_pct']:.3f}%")
col_c.metric("Coupon", f"{coupon_rate_pct:.2f}%", delta="vs market rate" if abs(coupon_rate_pct - market_rate_pct) > 0.01 else None)
col_d.metric("Status", pricing_label)


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Key Metrics",
    "Price vs Yield",
    "Cash Flows",
    "Sensitivity",
    "Yield Curve",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — KEY METRICS
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Bond Analytics Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Pricing")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Bond Price</div>
            <div class="metric-value">{current_price:,.4f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Yield to Maturity (YTM)</div>
            <div class="metric-value">{metrics['ytm_pct']:.4f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Premium / discount explanation
        diff = current_price - face_value
        if diff > 1:
            insight = f"Trading at **premium** of {diff:,.2f} — coupon ({coupon_rate_pct:.2f}%) > market rate ({market_rate_pct:.2f}%). YTM < coupon."
        elif diff < -1:
            insight = f"Trading at **discount** of {abs(diff):,.2f} — coupon ({coupon_rate_pct:.2f}%) < market rate ({market_rate_pct:.2f}%). YTM > coupon."
        else:
            insight = f"Trading **at par** — coupon rate ≈ market rate."
        st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("#### Duration & Convexity")
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
        """, unsafe_allow_html=True)

        # Duration intuition
        price_change_1pct = -metrics["modified_duration"] * 0.01 * 100
        st.markdown(
            f'<div class="insight-box">For a +100bps yield increase, '
            f'duration approximation suggests a <strong>{price_change_1pct:.2f}%</strong> price change. '
            f'Convexity softens the actual loss.</div>',
            unsafe_allow_html=True,
        )

    # ── Full metrics table ────────────────────────────────────────────────
    st.divider()
    st.subheader("Complete Metrics Table")

    sensitivity = bond.price_change_estimate(shock_bps / 10000)
    sensitivity_neg = bond.price_change_estimate(-shock_bps / 10000)

    table_data = {
        "Metric": [
            "Face Value", "Coupon Rate", "Years to Maturity", "Market Rate",
            "Bond Price", "YTM",
            "Macaulay Duration", "Modified Duration", "Convexity",
            f"Est. ΔP for +{shock_bps}bps", f"Est. ΔP for -{shock_bps}bps",
        ],
        "Value": [
            f"{face_value:,.2f}", f"{coupon_rate_pct:.4f}%",
            f"{years_to_maturity} years", f"{market_rate_pct:.4f}%",
            f"{current_price:,.4f}", f"{metrics['ytm_pct']:.4f}%",
            f"{metrics['macaulay_duration']:.4f} y",
            f"{metrics['modified_duration']:.4f}",
            f"{metrics['convexity']:.4f}",
            f"{sensitivity['total_effect_pct']:.4f}%",
            f"{sensitivity_neg['total_effect_pct']:.4f}%",
        ],
        "Interpretation": [
            "Par / nominal value", "Annual coupon as % of FV",
            "Remaining life", "Current market discount rate",
            "Theoretical fair value", "Discount rate equating price to cash flows",
            "Weighted avg. timing of cash flows",
            "Price sensitivity to 1% yield change (approx.)",
            "Curvature of price/yield relationship",
            "Price change (duration + convexity approx.)",
            "Price change (duration + convexity approx.)",
        ],
    }

    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        hide_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PRICE vs YIELD CURVE
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Price / Yield Relationship — Convexity Visualization")
    st.markdown(
        "The actual price/yield curve (navy) is **convex** — always above the duration "
        "tangent line (grey dashed). The green area represents the **convexity gain**: "
        "for any yield move, the actual price is always better than the linear approximation predicts."
    )
    st.pyplot(plot_price_yield_curve(bond), use_container_width=True)

    st.markdown(f"""
    <div class="insight-box">
    <strong>Key insight:</strong> The convexity ({metrics['convexity']:.2f}) quantifies how much
    the actual price exceeds the linear (duration-only) estimate.
    Higher convexity → more desirable bond, all else equal. Long-maturity bonds and low-coupon
    bonds have the highest convexity — which is why they outperform in large rate rallies.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — CASH FLOWS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Cash Flow Profile — Present Value by Period")
    st.markdown(
        "Each bar represents the PV of the cash flow received in that period. "
        "The red dashed line marks the **Macaulay Duration** — the weighted average "
        "time at which you effectively receive the bond's total value."
    )
    st.pyplot(plot_cash_flows(bond), use_container_width=True)

    st.markdown(f"""
    <div class="insight-box">
    Macaulay Duration = <strong>{metrics['macaulay_duration']:.2f} years</strong>.
    For a zero-coupon bond, duration equals maturity (all cash flow at T=n).
    For a coupon bond, duration < maturity because intermediate coupons pull the weighted
    average forward. This bond's Macaulay Duration is {(metrics['macaulay_duration']/years_to_maturity*100):.1f}%
    of its total maturity.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — SENSITIVITY & STRESS TEST
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Price Sensitivity — ±{shock_bps}bps Yield Shock")

    col_up, col_down = st.columns(2)

    for col, sign, label in [(col_up, 1, f"+{shock_bps}bps"), (col_down, -1, f"-{shock_bps}bps")]:
        res = bond.price_change_estimate(sign * shock_bps / 10000)
        with col:
            st.markdown(f"#### Yield {label}")
            color = "negative" if sign > 0 else "positive"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Duration Effect</div>
                <div class="metric-value {color}">{res['duration_effect_pct']:.3f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">+ Convexity Adjustment</div>
                <div class="metric-value positive">+{res['convexity_effect_pct']:.4f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Estimated Price</div>
                <div class="metric-value">{res['estimated_price']:,.4f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Actual Price (exact)</div>
                <div class="metric-value">{res['actual_price']:,.4f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Approximation Error</div>
                <div class="metric-value">{res['approximation_error']:.6f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader("Sensitivity Waterfall")
    st.pyplot(plot_sensitivity_decomposition(bond, shock_bps), use_container_width=True)

    # ── Scenario table ────────────────────────────────────────────────────
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
# TAB 5 — LIVE YIELD CURVE
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("US Treasury Yield Curve — Live (FRED)")
    st.markdown(
        "Real-time US Treasury yields fetched from the Federal Reserve Economic Data API (FRED). "
        "An inverted curve (short rates > long rates) has historically preceded recessions."
    )
    st.pyplot(plot_yield_curve(treasury_rates), use_container_width=True)

    # Context against current bond
    nearest_label = min(
        treasury_rates.keys(),
        key=lambda x: abs({"1Y": 1, "2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}.get(x, 99) - years_to_maturity),
    )
    rf_rate = treasury_rates.get(nearest_label, 0)
    spread = market_rate_pct - rf_rate
    st.markdown(f"""
    <div class="insight-box">
    Your bond's market rate ({market_rate_pct:.2f}%) vs. closest Treasury ({nearest_label}: {rf_rate:.2f}%) →
    <strong>spread of {spread:.2f}%</strong>. This spread represents credit risk, liquidity premium,
    and any other risks relative to the risk-free rate.
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
