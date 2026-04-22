"""
fred.py — FRED API client for risk-free rate data
===================================================
Fetches US Treasury yields from the Federal Reserve Economic Data (FRED).
No API key required for basic series access via the public endpoint.

Series used (all public, no authentication):
  - DGS1     : 1-Year Treasury Constant Maturity Rate
  - DGS2     : 2-Year
  - DGS5     : 5-Year
  - DGS10    : 10-Year
  - DGS30    : 30-Year

Docs : https://fred.stlouisfed.org/docs/api/fred/
"""

import requests
import pandas as pd
from datetime import datetime, timedelta


# FRED series IDs → readable labels
TREASURY_SERIES = {
    "DGS1": "1Y",
    "DGS2": "2Y",
    "DGS5": "5Y",
    "DGS10": "10Y",
    "DGS30": "30Y",
}

FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fetch_current_treasury_rates() -> dict[str, float]:
    """
    Fetch the most recent available US Treasury yields from FRED.

    Uses the public CSV endpoint — no API key required.
    Falls back to hardcoded defaults if network is unavailable
    (so the app works offline for demos).

    Returns
    -------
    dict : { '1Y': 5.20, '2Y': 4.95, ... }  (rates in %, not decimal)
    """
    rates = {}

    for series_id, label in TREASURY_SERIES.items():
        try:
            # FRED public CSV endpoint — fetches last 30 days of data
            url = f"{FRED_BASE_URL}?id={series_id}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            # Parse CSV response: DATE, VALUE
            lines = response.text.strip().split("\n")
            # Drop header, iterate from most recent
            for line in reversed(lines[1:]):
                parts = line.strip().split(",")
                if len(parts) == 2 and parts[1] not in (".", ""):
                    try:
                        rates[label] = float(parts[1])
                        break
                    except ValueError:
                        continue

        except Exception:
            # Silent fallback — don't crash the app if FRED is unreachable
            pass

    # Fallback defaults (approximate values — clearly labeled in UI)
    defaults = {"1Y": 5.10, "2Y": 4.80, "5Y": 4.40, "10Y": 4.25, "30Y": 4.50}
    for label, default in defaults.items():
        if label not in rates:
            rates[label] = default

    return rates


def fetch_rate_history(series_id: str = "DGS10", years_back: int = 5) -> pd.DataFrame:
    """
    Fetch historical data for a given FRED series.

    Parameters
    ----------
    series_id : str
        FRED series identifier (e.g., 'DGS10' for 10Y Treasury).
    years_back : int
        Number of years of history to retrieve.

    Returns
    -------
    pd.DataFrame : columns ['date', 'rate'], rate in %.
    """
    observation_start = (datetime.today() - timedelta(days=365 * years_back)).strftime(
        "%Y-%m-%d"
    )

    url = f"{FRED_BASE_URL}?id={series_id}&vintage_date={observation_start}"

    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()

        lines = response.text.strip().split("\n")
        records = []
        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) == 2 and parts[1] not in (".", ""):
                try:
                    records.append(
                        {"date": pd.to_datetime(parts[0]), "rate": float(parts[1])}
                    )
                except ValueError:
                    continue

        df = pd.DataFrame(records)
        return df if not df.empty else _fallback_history()

    except Exception:
        return _fallback_history()


def _fallback_history() -> pd.DataFrame:
    """Return empty DataFrame when FRED is unreachable."""
    return pd.DataFrame(columns=["date", "rate"])
