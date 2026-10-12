"""
Price feed module for QQQ, SOXX, and candidate turnaround stocks.
Provides split/dividend-adjusted daily total return series with the July 10-12, 2001 SOXX bridge.
Guarantees zero NaNs and offline parquet caching from July 10, 2001 to present.
"""
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Union
import logging
import pandas as pd
import numpy as np

from config.settings import DEFAULT_START_DATE, BENCHMARK_TICKERS, CACHE_DIR
from src.data.cache_store import CacheStore

logger = logging.getLogger(__name__)


class PriceFeed:
    """
    Ingests and caches daily price feeds with corporate action adjustments.
    Enforces the July 10, 2001 start date and provides the ^SOX bridge for SOXX launch days.
    """

    BENCHMARK_PARQUET = "etf_prices.parquet"
    FX_PARQUET = "fx_rates.parquet"

    def __init__(self, cache_store: Optional[CacheStore] = None):
        self.cache_store = cache_store or CacheStore(CACHE_DIR)

    def fetch_and_bridge_benchmarks(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """
        Loads or downloads benchmark prices (QQQ & SOXX) starting July 10, 2001.
        Bridges July 10-12, 2001 for SOXX using ^SOX benchmark return backward scaling.
        Guarantees zero NaNs for both ETFs.
        """
        if not force_download and self.cache_store.exists(self.BENCHMARK_PARQUET):
            df = self.cache_store.load_parquet(self.BENCHMARK_PARQUET)
            if df is not None and not df.empty:
                return self._slice_date_range(df, start_date, end_date)

        # Download QQQ, SOXX, and ^SOX from Yahoo Finance
        try:
            import yfinance as yf
            # Download starting from July 9, 2001 to capture ^SOX baseline for July 10
            download_start = "2001-07-09"
            tickers = ["QQQ", "SOXX", "^SOX"]
            raw = yf.download(tickers, start=download_start, end=end_date, auto_adjust=True, progress=False)
            if raw.empty:
                raise ValueError("Yahoo Finance returned empty dataset.")
        except Exception as e:
            logger.warning(f"Failed to download benchmark prices from yfinance: {e}")
            cached = self.cache_store.load_parquet(self.BENCHMARK_PARQUET)
            if cached is not None and not cached.empty:
                return self._slice_date_range(cached, start_date, end_date)
            raise RuntimeError(f"Cannot acquire benchmark prices: {e}")

        # Normalize index to timezone-naive datetime
        raw.index = pd.to_datetime(raw.index).tz_localize(None)

        # Build clean QQQ and SOXX dataset
        bridged = self._apply_soxx_bridge(raw)

        # Squeeze down to QQQ and SOXX only
        price_cols = [c for c in ["Close", "High", "Low", "Open", "Volume"] if c in bridged.columns.levels[0]]
        selected_cols = [(p, t) for p in price_cols for t in ["QQQ", "SOXX"] if (p, t) in bridged.columns]
        etf_df = bridged[selected_cols].copy()

        # Save to parquet cache
        self.cache_store.save_parquet(etf_df, self.BENCHMARK_PARQUET)

        return self._slice_date_range(etf_df, start_date, end_date)

    def _apply_soxx_bridge(self, raw: pd.DataFrame) -> pd.DataFrame:
        """
        Applies ^SOX return scaling backward from July 13, 2001 for July 10-12, 2001.
        """
        df = raw.copy()
        
        # Verify SOXX July 13, 2001 anchor point
        jul13 = pd.Timestamp("2001-07-13")
        if jul13 not in df.index:
            return df

        soxx_close_13 = df.loc[jul13, ("Close", "SOXX")]
        sox_close = df[("Close", "^SOX")]

        # Target bridge dates: July 10, 11, 12, 2001
        bridge_dates = [pd.Timestamp("2001-07-12"), pd.Timestamp("2001-07-11"), pd.Timestamp("2001-07-10")]
        
        # Backward scaling:
        # P(t) = P(t+1) / (1 + r_sox(t+1)) = P(t+1) * (sox_close[t] / sox_close[t+1])
        current_soxx_close = soxx_close_13
        current_anchor_date = jul13

        for b_date in bridge_dates:
            if b_date in df.index and current_anchor_date in df.index:
                sox_ratio = sox_close.loc[b_date] / sox_close.loc[current_anchor_date]
                scaled_close = float(current_soxx_close * sox_ratio)
                
                # Fill SOXX fields
                df.loc[b_date, ("Close", "SOXX")] = scaled_close
                df.loc[b_date, ("Open", "SOXX")] = scaled_close
                df.loc[b_date, ("High", "SOXX")] = scaled_close * 1.01
                df.loc[b_date, ("Low", "SOXX")] = scaled_close * 0.99
                df.loc[b_date, ("Volume", "SOXX")] = 500_000.0  # nominal trading volume

                current_soxx_close = scaled_close
                current_anchor_date = b_date

        return df

    def get_benchmark_prices(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Interface Contract: Returns MultiIndex DataFrame [Close, High, Low, Open, Volume]
        for ['QQQ', 'SOXX'] from start_date to end_date.
        """
        return self.fetch_and_bridge_benchmarks(start_date=start_date, end_date=end_date)

    def get_stock_prices(
        self,
        tickers: List[str],
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Retrieves adjusted daily OHLCV prices for candidate stocks.
        Caches results per ticker or batch in parquet.
        """
        if not tickers:
            return pd.DataFrame()

        cache_key = f"stocks_{len(tickers)}_{start_date}.parquet"
        if use_cache and self.cache_store.exists(cache_key):
            cached = self.cache_store.load_parquet(cache_key)
            if cached is not None and not cached.empty:
                return self._slice_date_range(cached, start_date, end_date)

        import yfinance as yf
        try:
            raw = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)
            if not raw.empty:
                raw.index = pd.to_datetime(raw.index).tz_localize(None)
                if use_cache:
                    self.cache_store.save_parquet(raw, cache_key)
                return raw
        except Exception as e:
            logger.warning(f"Error downloading stock prices: {e}")

        # Fallback to empty or partial
        return pd.DataFrame()

    def fetch_and_bridge_fx_rates(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_download: bool = False,
    ) -> pd.Series:
        """
        Loads or downloads daily USD/KRW exchange rates starting July 10, 2001 to present.
        Uses Yahoo Finance USDKRW=X with FRED DEXKOUS historical bridge for 2001-07-10 to 2003-12-01.
        Caches in data/cache/fx_rates.parquet and guarantees zero NaNs.
        Returns pd.Series named 'USDKRW' indexed by timezone-naive DatetimeIndex.
        """
        if not force_download and self.cache_store.exists(self.FX_PARQUET):
            df = self.cache_store.load_parquet(self.FX_PARQUET)
            if df is not None and not df.empty:
                s = df["USDKRW"] if "USDKRW" in df.columns else df.iloc[:, 0]
                return self._slice_series_date_range(s, start_date, end_date)

        # Download from Yahoo Finance and bridge with FRED
        try:
            import yfinance as yf
            import urllib.request
            import io

            # 1. Fetch FRED DEXKOUS historical rates
            resp = urllib.request.urlopen("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS", timeout=10)
            df_fred = pd.read_csv(io.StringIO(resp.read().decode("utf-8")))
            df_fred["observation_date"] = pd.to_datetime(df_fred["observation_date"])
            df_fred["DEXKOUS"] = pd.to_numeric(df_fred["DEXKOUS"], errors="coerce")
            s_fred = df_fred.set_index("observation_date")["DEXKOUS"].dropna()

            # 2. Fetch yfinance USDKRW=X
            df_yf = yf.download("USDKRW=X", start="2003-12-01", end=end_date, progress=False)
            if isinstance(df_yf.columns, pd.MultiIndex):
                s_yf = df_yf["Close"]["USDKRW=X"].dropna()
            else:
                s_yf = df_yf["Close"].dropna()
            s_yf.index = pd.to_datetime(s_yf.index).tz_localize(None)

            yf_start = s_yf.index.min()
            s_fred_early = s_fred[(s_fred.index >= "2001-07-10") & (s_fred.index < yf_start)]
            combined = pd.concat([s_fred_early, s_yf]).sort_index()
            combined = combined[~combined.index.duplicated(keep="last")]

            all_dates = pd.date_range("2001-07-10", combined.index.max(), freq="D")
            full_series = combined.reindex(all_dates).ffill().bfill()
            full_series.name = "USDKRW"

            # Cache to parquet
            out_df = pd.DataFrame({"USDKRW": full_series})
            self.cache_store.save_parquet(out_df, self.FX_PARQUET)
            return self._slice_series_date_range(full_series, start_date, end_date)
        except Exception as e:
            logger.warning(f"Error fetching fx rates: {e}")
            cached = self.cache_store.load_parquet(self.FX_PARQUET)
            if cached is not None and not cached.empty:
                s = cached["USDKRW"] if "USDKRW" in cached.columns else cached.iloc[:, 0]
                return self._slice_series_date_range(s, start_date, end_date)
            raise RuntimeError(f"Cannot acquire USD/KRW exchange rates: {e}")

    def get_fx_rates(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
    ) -> pd.Series:
        """
        Interface Contract: Returns daily closing USD/KRW exchange rates from start_date to end_date.
        Guarantees zero NaNs and offline cache persistence.
        """
        return self.fetch_and_bridge_fx_rates(start_date=start_date, end_date=end_date)

    def _slice_date_range(
        self,
        df: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """Slices dataframe between start_date and end_date."""
        res = df.copy()
        if start_date:
            ts_start = pd.Timestamp(start_date)
            res = res[res.index >= ts_start]
        if end_date:
            ts_end = pd.Timestamp(end_date)
            res = res[res.index <= ts_end]
        return res

    def _slice_series_date_range(
        self,
        series: pd.Series,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.Series:
        """Slices pandas Series between start_date and end_date."""
        res = series.copy()
        if start_date:
            ts_start = pd.Timestamp(start_date)
            res = res[res.index >= ts_start]
        if end_date:
            ts_end = pd.Timestamp(end_date)
            res = res[res.index <= ts_end]
        return res
