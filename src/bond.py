"""
bond.py — Core bond analytics engine
=====================================
Implements from scratch (no external finance library):
  - Bond price given yield (annual or semi-annual coupon)
  - Yield to Maturity (YTM) via Brent's method
  - Macaulay Duration
  - Modified Duration
  - Convexity
  - DV01 (Dollar Value of 01)
  - Price sensitivity approximation (duration + convexity)

All formulas follow CFA Level 1 Fixed Income curriculum.
"""

import numpy as np
from scipy.optimize import brentq


class Bond:
    """
    Fixed-rate bullet bond with configurable coupon frequency.

    Parameters
    ----------
    face_value : float
        Nominal (par) value — typically 100.
    coupon_rate : float
        Annual coupon rate as a decimal (e.g., 0.05 for 5%).
    years_to_maturity : int or float
        Time to maturity in years.
    market_rate : float
        Annual market yield / discount rate (decimal).
    frequency : int
        Coupon payments per year. 1 = annual, 2 = semi-annual (market standard).
    """

    def __init__(
        self,
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        market_rate: float,
        frequency: int = 2,
    ):
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.years_to_maturity = years_to_maturity
        self.market_rate = market_rate
        self.frequency = frequency

        self.coupon_payment = coupon_rate * face_value / frequency  # per period
        self.n_periods = int(years_to_maturity * frequency)         # total periods

    # ------------------------------------------------------------------
    # 1. BOND PRICE
    # ------------------------------------------------------------------

    def price(self, yield_rate: float = None) -> float:
        """
        Full (dirty) price of the bond.

        For coupon frequency f, period yield y_p = annual_yield / f:
            P = Σ [C_p / (1+y_p)^t]  +  FV / (1+y_p)^n    t=1..n
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        y_p = y / self.frequency
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value

        if y_p == 0:
            pv_coupons = C * n
        else:
            pv_coupons = C * (1 - (1 + y_p) ** (-n)) / y_p

        pv_face = FV / (1 + y_p) ** n
        return pv_coupons + pv_face

    # ------------------------------------------------------------------
    # 2. YIELD TO MATURITY
    # ------------------------------------------------------------------

    def ytm(self) -> float:
        """
        Annual YTM solved via Brent's method.

        Since the user inputs the discount rate directly, YTM == market_rate
        by construction. This method is preserved for architectural clarity
        and future extensibility (e.g., price-input mode).
        """
        market_price = self.price(self.market_rate)

        def objective(y):
            return self.price(y) - market_price

        try:
            result = brentq(objective, 0.0001, 0.50, xtol=1e-8)
        except ValueError:
            result = self.market_rate

        return result

    # ------------------------------------------------------------------
    # 3. MACAULAY DURATION
    # ------------------------------------------------------------------

    def macaulay_duration(self, yield_rate: float = None) -> float:
        """
        Macaulay Duration in years.

        D_mac = (1/f) × Σ [t × PV(CF_t)] / P    (t in periods, result in years)
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        y_p = y / self.frequency
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value
        P = self.price(y)

        if P == 0:
            return 0.0

        weighted_sum = 0.0
        for t in range(1, n + 1):
            cf = C if t < n else C + FV
            pv_cf = cf / (1 + y_p) ** t
            weighted_sum += t * pv_cf

        return (weighted_sum / P) / self.frequency

    # ------------------------------------------------------------------
    # 4. MODIFIED DURATION
    # ------------------------------------------------------------------

    def modified_duration(self, yield_rate: float = None) -> float:
        """
        Modified Duration = Macaulay Duration / (1 + y/f)

        ΔP/P ≈ -ModDur × Δy
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        y_p = y / self.frequency
        return self.macaulay_duration(y) / (1 + y_p)

    # ------------------------------------------------------------------
    # 5. CONVEXITY
    # ------------------------------------------------------------------

    def convexity(self, yield_rate: float = None) -> float:
        """
        Convexity in years².

        C = Σ [t×(t+1) × PV(CF_t)] / [P × (1+y_p)² × f²]
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        y_p = y / self.frequency
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value
        P = self.price(y)

        if P == 0 or y_p == 0:
            return 0.0

        weighted_sum = 0.0
        for t in range(1, n + 1):
            cf = C if t < n else C + FV
            pv_cf = cf / (1 + y_p) ** t
            weighted_sum += t * (t + 1) * pv_cf

        return weighted_sum / (P * (1 + y_p) ** 2 * self.frequency ** 2)

    # ------------------------------------------------------------------
    # 6. DV01
    # ------------------------------------------------------------------

    def dv01(self) -> float:
        """
        DV01 — Dollar Value of 01.

        Price change (in currency units) for a +1bp yield increase.
            DV01 = Modified Duration × Full Price × 0.0001
        """
        return self.modified_duration() * self.price() * 0.0001

    # ------------------------------------------------------------------
    # 7. PRICE SENSITIVITY
    # ------------------------------------------------------------------

    def price_change_estimate(self, delta_y: float) -> dict:
        """
        ΔP/P ≈ -ModDur × Δy  +  ½ × Convexity × (Δy)²
        """
        P0 = self.price(self.market_rate)
        mod_dur = self.modified_duration()
        cvx = self.convexity()

        duration_effect = -mod_dur * delta_y
        convexity_effect = 0.5 * cvx * delta_y ** 2
        total_effect = duration_effect + convexity_effect

        estimated_price = P0 * (1 + total_effect)
        actual_price = self.price(self.market_rate + delta_y)

        return {
            "duration_effect_pct": duration_effect * 100,
            "convexity_effect_pct": convexity_effect * 100,
            "total_effect_pct": total_effect * 100,
            "estimated_price": estimated_price,
            "actual_price": actual_price,
            "approximation_error": abs(estimated_price - actual_price),
        }

    # ------------------------------------------------------------------
    # 8. SUMMARY
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "face_value": self.face_value,
            "coupon_rate_pct": self.coupon_rate * 100,
            "years_to_maturity": self.years_to_maturity,
            "market_rate_pct": self.market_rate * 100,
            "frequency": self.frequency,
            "price": round(self.price(), 4),
            "ytm_pct": round(self.ytm() * 100, 4),
            "macaulay_duration": round(self.macaulay_duration(), 4),
            "modified_duration": round(self.modified_duration(), 4),
            "convexity": round(self.convexity(), 4),
            "dv01": round(self.dv01(), 6),
        }
