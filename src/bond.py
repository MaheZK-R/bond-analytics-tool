"""
bond.py — Core bond analytics engine
=====================================
Implements from scratch (no external finance library) :
  - Bond price given yield
  - Yield to Maturity (YTM) via Newton-Raphson
  - Macaulay Duration
  - Modified Duration
  - Convexity
  - Full price / clean price / accrued interest (simplified annual coupon)
  - Price sensitivity approximation (duration + convexity)

All formulas follow CFA Level 1 Fixed Income curriculum.
"""

import numpy as np
from scipy.optimize import brentq


class Bond:
    """
    Represents a fixed-rate bullet bond with annual coupon payments.

    Parameters
    ----------
    face_value : float
        Nominal (par) value of the bond — typically 1000.
    coupon_rate : float
        Annual coupon rate as a decimal (e.g., 0.05 for 5%).
    years_to_maturity : int or float
        Time to maturity in years.
    market_rate : float
        Current market yield / discount rate (decimal).
    """

    def __init__(
        self,
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        market_rate: float,
    ):
        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.years_to_maturity = years_to_maturity
        self.market_rate = market_rate

        # Derived
        self.coupon_payment = coupon_rate * face_value
        self.n_periods = int(years_to_maturity)  # annual periods

    # ------------------------------------------------------------------
    # 1. BOND PRICE
    # ------------------------------------------------------------------

    def price(self, yield_rate: float = None) -> float:
        """
        Calculate the full (dirty) price of the bond.

        Formula:  P = Σ [C / (1+y)^t]  +  FV / (1+y)^n
                      t=1..n

        Parameters
        ----------
        yield_rate : float, optional
            Yield to use. Defaults to self.market_rate.

        Returns
        -------
        float : Bond price in same currency as face_value.
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value

        # PV of coupon cash flows (annuity)
        if y == 0:
            pv_coupons = C * n
        else:
            pv_coupons = C * (1 - (1 + y) ** (-n)) / y

        # PV of face value at maturity
        pv_face = FV / (1 + y) ** n

        return pv_coupons + pv_face

    # ------------------------------------------------------------------
    # 2. YIELD TO MATURITY (YTM)
    # ------------------------------------------------------------------

    def ytm(self) -> float:
        """
        Solve for YTM numerically using Brent's method.

        YTM is the discount rate y such that:
            Price_market = Σ [C / (1+y)^t]  +  FV / (1+y)^n

        We solve:  f(y) = price(y) - market_price = 0

        Returns
        -------
        float : YTM as a decimal.
        """
        market_price = self.price(self.market_rate)

        def objective(y):
            return self.price(y) - market_price

        # Brent's method: bracket between 0.01% and 50%
        try:
            result = brentq(objective, 0.0001, 0.50, xtol=1e-8)
        except ValueError:
            # Fallback: market_rate is already the YTM
            result = self.market_rate

        return result

    # ------------------------------------------------------------------
    # 3. MACAULAY DURATION
    # ------------------------------------------------------------------

    def macaulay_duration(self, yield_rate: float = None) -> float:
        """
        Macaulay Duration = weighted average time of cash flows.

        Formula:  D_mac = Σ [t * PV(CF_t)] / P
                          t=1..n

        Interpretation : average number of years to recover the
        investment through bond cash flows. A zero-coupon bond's
        Macaulay Duration equals its maturity.

        Returns
        -------
        float : Duration in years.
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value
        P = self.price(y)

        if P == 0:
            return 0.0

        weighted_sum = 0.0
        for t in range(1, n + 1):
            cf = C if t < n else C + FV  # last period includes face value
            pv_cf = cf / (1 + y) ** t
            weighted_sum += t * pv_cf

        return weighted_sum / P

    # ------------------------------------------------------------------
    # 4. MODIFIED DURATION
    # ------------------------------------------------------------------

    def modified_duration(self, yield_rate: float = None) -> float:
        """
        Modified Duration = Macaulay Duration / (1 + y)

        Interpretation : approximates the % price change for a
        1% (100bps) change in yield.

        ΔP/P ≈ -ModDuration × Δy

        Returns
        -------
        float : Modified duration (unit-less, expressed in years).
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        return self.macaulay_duration(y) / (1 + y)

    # ------------------------------------------------------------------
    # 5. CONVEXITY
    # ------------------------------------------------------------------

    def convexity(self, yield_rate: float = None) -> float:
        """
        Convexity captures the curvature of the Price/Yield relationship.

        Formula:  C = Σ [t*(t+1) * PV(CF_t)] / [P * (1+y)^2]
                      t=1..n

        Interpretation : the higher the convexity, the more the bond
        benefits from yield decreases and is protected from yield increases
        (relative to a bond with same duration but lower convexity).

        Returns
        -------
        float : Convexity (years squared).
        """
        y = yield_rate if yield_rate is not None else self.market_rate
        n = self.n_periods
        C = self.coupon_payment
        FV = self.face_value
        P = self.price(y)

        if P == 0 or y == 0:
            return 0.0

        weighted_sum = 0.0
        for t in range(1, n + 1):
            cf = C if t < n else C + FV
            pv_cf = cf / (1 + y) ** t
            weighted_sum += t * (t + 1) * pv_cf

        return weighted_sum / (P * (1 + y) ** 2)

    # ------------------------------------------------------------------
    # 6. PRICE SENSITIVITY (Duration + Convexity approximation)
    # ------------------------------------------------------------------

    def price_change_estimate(self, delta_y: float) -> dict:
        """
        Estimate bond price change for a given yield shift Δy.

        Full approximation:
            ΔP/P ≈ -ModDuration × Δy  +  ½ × Convexity × (Δy)²

        The convexity term is always positive → it adds value (or reduces
        loss) regardless of the direction of the yield move.

        Parameters
        ----------
        delta_y : float
            Yield change in decimal (e.g., 0.01 = +100bps).

        Returns
        -------
        dict with keys: duration_effect, convexity_effect, total_effect,
                        estimated_price, actual_price
        """
        P0 = self.price(self.market_rate)
        mod_dur = self.modified_duration()
        cvx = self.convexity()

        duration_effect = -mod_dur * delta_y
        convexity_effect = 0.5 * cvx * delta_y**2
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
    # 7. FULL ANALYTICS SUMMARY
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Return all key metrics as a dictionary."""
        return {
            "face_value": self.face_value,
            "coupon_rate_pct": self.coupon_rate * 100,
            "years_to_maturity": self.years_to_maturity,
            "market_rate_pct": self.market_rate * 100,
            "price": round(self.price(), 4),
            "ytm_pct": round(self.ytm() * 100, 4),
            "macaulay_duration": round(self.macaulay_duration(), 4),
            "modified_duration": round(self.modified_duration(), 4),
            "convexity": round(self.convexity(), 4),
        }
