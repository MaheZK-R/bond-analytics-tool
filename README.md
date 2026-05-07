# Bond Analytics Tool

> **Interactive fixed income calculator — pricing, duration, convexity, and scenario analysis.**

A standalone HTML/JS tool implementing core fixed income analytics from the CFA Level 1 curriculum. No server, no dependencies — open the file in any browser.

---

## What it does

Prices a fixed-rate bullet bond via DCF and computes all standard risk measures in real time as you move the sliders:

| Metric | Description |
|---|---|
| **Bond Price** | DCF: PV of coupons + PV of face value, discounted at all-in yield (risk-free + credit spread) |
| **Macaulay Duration** | Weighted average timing of cash flows (years) |
| **Modified Duration** | Price sensitivity to a 1% yield change: `ΔP/P ≈ −ModDur × Δy` |
| **Convexity** | Second-order curvature of the P/Y relationship |
| **DV01** | Dollar value of a 1 basis point move |
| **Credit Spread** | Explicit separation of risk-free rate and credit premium |

---

## Key features

- **Interactive sliders** — coupon rate, maturity (1–30Y), risk-free rate, credit spread (0–500 bps), yield shock
- **At Par / At Premium / At Discount** badge with pull-to-par insight
- **Scenario analysis table** — ±300 bps shocks, estimated price (duration + convexity) vs. actual full DCF price
- **US Treasury yield curve** — indicative reference curve with your bond positioned on it (hover for tooltips)
- **Credit spread decomposition** — displays risk-free ref, spread, and all-in yield below the chart
- **Methodology accordion** — all 6 formulas displayed inline, editable in the browser
- **Annual / semi-annual coupon frequency** selector
- No install, no server — single `.html` file

---

## Usage

```
open bond-analytics-tool.html
```

Or double-click the file. Works in any modern browser.

---

## Stack

Pure HTML · CSS · Vanilla JavaScript — zero dependencies, zero build step.

---

## Financial concepts

Based on **CFA Level 1 Fixed Income** (Chapters 42–46) and Fabozzi, *Fixed Income Mathematics* (4th ed.).

*Educational purpose only — not financial advice.*
