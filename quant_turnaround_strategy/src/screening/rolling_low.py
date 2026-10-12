"""
52-Week Low Screener with Anti-"Falling Knife" Stabilization Filters.
Computes rolling 252-day low proximity, RSI(14), and 5-day return thresholds.
"""
from datetime import date, datetime
from typing import Optional, Dict, Any, Tuple, Union
import numpy as np
import pandas as pd

from config.settings import (
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_LOW_PROXIMITY_THRESHOLD,
    DEFAULT_MIN_TRADING_DAYS,
    DEFAULT_MIN_RSI,
    DEFAULT_MIN_5D_RETURN,
)
from src.models.schemas import ExclusionReason


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Computes Wilder's Relative Strength Index (RSI) over the specified period.
    """
    if len(series) < period + 1:
        return pd.Series(np.nan, index=series.index)

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Use exponential moving average / Wilder smoothing
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    # Where avg_loss was 0 and avg_gain > 0 (up-only series), RSI is 100.0
    # Where both avg_gain and avg_loss are 0 (completely flat series), return neutral 50.0
    both_zero = (avg_gain == 0.0) & (avg_loss == 0.0)
    loss_zero_only = (avg_gain > 0.0) & (avg_loss == 0.0)

    rsi = rsi.copy()
    rsi[loss_zero_only] = 100.0
    rsi[both_zero] = 50.0
    return rsi


class RollingLowScreener:
    """
    Screens price bars for 52-week low candidate status with stabilization gates.
    """

    def __init__(
        self,
        window: int = DEFAULT_ROLLING_WINDOW,
        proximity_threshold: float = DEFAULT_LOW_PROXIMITY_THRESHOLD,
        min_history_days: int = DEFAULT_MIN_TRADING_DAYS,
        min_rsi: float = DEFAULT_MIN_RSI,
        min_5d_return: float = DEFAULT_MIN_5D_RETURN,
    ):
        self.window = window
        self.proximity_threshold = proximity_threshold
        self.min_history_days = min_history_days
        self.min_rsi = min_rsi
        self.min_5d_return = min_5d_return

    def compute_indicators(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches OHLCV DataFrame with 52-week low, proximity, RSI(14), and 5-day return.
        """
        df = price_df.copy()
        low_col = "Low" if "Low" in df.columns else "Close"
        close_col = "Close"

        # Ensure sorted by date
        df = df.sort_index()

        # Rolling 252-day low
        df["low_52w"] = df[low_col].rolling(window=self.window, min_periods=self.window).min()
        
        # Proximity to 52-week low: (Close - Low_52w) / Low_52w
        df["low_proximity"] = (df[close_col] - df["low_52w"]) / df["low_52w"].replace(0.0, np.nan)

        # Technical indicators
        df["rsi_14"] = calculate_rsi(df[close_col], period=14)
        df["return_5d"] = df[close_col].pct_change(5)
        df["return_30d"] = df[close_col].pct_change(21)

        # 20-day average daily dollar volume: Close * Volume
        vol_col = "Volume" if "Volume" in df.columns else None
        if vol_col:
            df["dollar_volume"] = df[close_col] * df[vol_col]
            df["avg_dollar_volume_20d"] = df["dollar_volume"].rolling(20, min_periods=5).mean()
        else:
            df["avg_dollar_volume_20d"] = 0.0

        return df

    def evaluate_candidate(
        self,
        price_df: pd.DataFrame,
        as_of_date: Union[date, datetime, str],
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates whether a stock qualifies as a stabilized 52-week low candidate on as_of_date.
        Returns (qualifies, metrics_dict).
        """
        if price_df.empty:
            return False, {"reason": "empty_dataframe"}

        ts = pd.to_datetime(as_of_date)
        hist = price_df[price_df.index <= ts]

        if len(hist) < self.min_history_days:
            return False, {
                "reason": ExclusionReason.TRADING_HISTORY_INSUFFICIENT,
                "history_length": len(hist),
                "required": self.min_history_days,
            }

        # Compute indicators on historical data up to as_of_date (strictly zero lookahead)
        indicators = self.compute_indicators(hist)
        last_row = indicators.iloc[-1]

        close_price = float(last_row["Close"])
        low_52w = float(last_row["low_52w"]) if pd.notna(last_row["low_52w"]) else np.nan
        low_proximity = float(last_row["low_proximity"]) if pd.notna(last_row["low_proximity"]) else np.nan
        rsi_14 = float(last_row["rsi_14"]) if pd.notna(last_row["rsi_14"]) else 50.0
        return_5d = float(last_row["return_5d"]) if pd.notna(last_row["return_5d"]) else 0.0
        return_30d = float(last_row["return_30d"]) if pd.notna(last_row["return_30d"]) else 0.0
        avg_dv_20d = float(last_row.get("avg_dollar_volume_20d", 0.0))

        # Check proximity condition: within proximity threshold (e.g. <= 5%)
        is_near_low = (0.0 <= low_proximity <= self.proximity_threshold)

        # Check anti-falling knife stabilization filters:
        # 1. RSI > 20 (not in deep panic freefall)
        # 2. 5-day return >= -5% (not dumping double-digit in recent week)
        is_stabilized = (rsi_14 >= self.min_rsi) and (return_5d >= self.min_5d_return)

        qualifies = is_near_low and is_stabilized

        metrics = {
            "evaluation_date": ts.date() if isinstance(ts, pd.Timestamp) else ts,
            "close_price": close_price,
            "low_52w": low_52w,
            "low_proximity": low_proximity,
            "rsi_14": rsi_14,
            "return_5d": return_5d,
            "return_30d": return_30d,
            "avg_dollar_volume_20d": avg_dv_20d,
            "is_near_low": is_near_low,
            "is_stabilized": is_stabilized,
            "qualifies": qualifies,
        }

        return qualifies, metrics
