"""
Tri-Asset Data Loader & Ingestion Module.
Ingests and aligns daily adjusted total return prices for SPY, QQQ, and SOXX
(including the ^SOX benchmark return bridge for July 10-12, 2001) alongside
daily USDKRW exchange rates from July 10, 2001 to present.
Guarantees zero NaNs, date alignment across all assets, and offline Parquet caching.
"""
from pathlib import Path
from typing import Tuple, Union, Optional
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "2001-07-10"
TRI_ASSET_PARQUET = "tri_asset_prices.parquet"
FX_PARQUET = "fx_rates.parquet"
BENCHMARK_PARQUET = "etf_prices.parquet"


def _resolve_cache_dir(cache_dir: Union[str, Path] = "data/cache") -> Path:
    """Resolves cache directory considering possible current working directories."""
    path = Path(cache_dir)
    if path.is_absolute() and path.exists():
        return path
    
    # Try relative to cwd
    if path.exists():
        return path.resolve()
        
    # Try relative to repo root (quant_turnaround_strategy)
    repo_root = Path(__file__).resolve().parents[2]
    cand = repo_root / path
    if cand.exists():
        return cand.resolve()
        
    # Fallback: create directory under cwd or repo_root
    if (repo_root / "data").exists():
        target = repo_root / path
        target.mkdir(parents=True, exist_ok=True)
        return target.resolve()

    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


class TriAssetDataLoader:
    """
    Manages ingestion, alignment, and persistent caching of the SPY/QQQ/SOXX tri-asset triad
    and USDKRW exchange rates.
    """

    def __init__(self, cache_dir: Union[str, Path] = "data/cache"):
        self.cache_dir = _resolve_cache_dir(cache_dir)
        self.tri_asset_path = self.cache_dir / TRI_ASSET_PARQUET
        self.fx_path = self.cache_dir / FX_PARQUET
        self.benchmark_path = self.cache_dir / BENCHMARK_PARQUET

    def load_data(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads aligned tri-asset prices and FX rates from cache, fetching if absent.
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]:
                - prices_df: pd.DataFrame with columns ['SPY', 'QQQ', 'SOXX'],
                  DatetimeIndex from start_date (2001-07-10) to present, 0 NaNs.
                - fx_df: pd.DataFrame with column ['USDKRW'], aligned on trading days, 0 NaNs.
        """
        prices_df = self.get_tri_asset_prices(
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh,
        )

        fx_df = self.get_fx_rates(
            start_date=start_date,
            end_date=end_date,
            target_index=prices_df.index,
            force_refresh=force_refresh,
        )

        # Enforce exact trading days alignment
        fx_df = fx_df.reindex(prices_df.index)
        if fx_df["USDKRW"].isna().any():
            fx_df["USDKRW"] = fx_df["USDKRW"].ffill().bfill()

        return prices_df, fx_df

    def get_tri_asset_prices(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Retrieves or ingests SPY, QQQ, SOXX daily prices starting July 10, 2001.
        """
        if not force_refresh and self.tri_asset_path.exists() and self.tri_asset_path.stat().st_size > 0:
            try:
                df = pd.read_parquet(self.tri_asset_path)
                if df is not None and not df.empty and set(["SPY", "QQQ", "SOXX"]).issubset(df.columns):
                    return self._slice_df(df, start_date, end_date)
            except Exception as e:
                logger.warning(f"Failed to read cached {self.tri_asset_path}: {e}. Re-ingesting.")

        return self.ingest_tri_asset_prices(start_date=start_date, end_date=end_date)

    def ingest_tri_asset_prices(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Ingests SPY from yfinance and combines with QQQ & SOXX (including ^SOX bridge).
        Caches resulting DataFrame to tri_asset_prices.parquet.
        """
        # 1. Obtain QQQ and SOXX prices
        qqq_series: Optional[pd.Series] = None
        soxx_series: Optional[pd.Series] = None

        if self.benchmark_path.exists() and self.benchmark_path.stat().st_size > 0:
            try:
                etf_raw = pd.read_parquet(self.benchmark_path)
                if isinstance(etf_raw.columns, pd.MultiIndex):
                    if "Close" in etf_raw.columns.levels[0]:
                        close_sub = etf_raw["Close"]
                        if "QQQ" in close_sub.columns and "SOXX" in close_sub.columns:
                            qqq_series = close_sub["QQQ"]
                            soxx_series = close_sub["SOXX"]
                elif "QQQ" in etf_raw.columns and "SOXX" in etf_raw.columns:
                    qqq_series = etf_raw["QQQ"]
                    soxx_series = etf_raw["SOXX"]
            except Exception as e:
                logger.warning(f"Could not read benchmark cache: {e}")

        # If benchmark cache was unavailable or missing columns, fetch via PriceFeed
        if qqq_series is None or soxx_series is None:
            try:
                from src.data.price_feed import PriceFeed
                pf = PriceFeed()
                bench = pf.fetch_and_bridge_benchmarks(start_date="2001-07-09", end_date=end_date)
                if isinstance(bench.columns, pd.MultiIndex):
                    qqq_series = bench["Close"]["QQQ"]
                    soxx_series = bench["Close"]["SOXX"]
                else:
                    qqq_series = bench["QQQ"]
                    soxx_series = bench["SOXX"]
            except Exception as e:
                logger.error(f"Failed to fetch benchmarks via PriceFeed: {e}")
                raise RuntimeError(f"Cannot obtain QQQ and SOXX benchmark prices: {e}")

        # Ensure index is timezone-naive DatetimeIndex
        qqq_series.index = pd.to_datetime(qqq_series.index).tz_localize(None)
        soxx_series.index = pd.to_datetime(soxx_series.index).tz_localize(None)

        # Slice benchmarks starting from July 10, 2001
        mask_bench = qqq_series.index >= pd.Timestamp(DEFAULT_START_DATE)
        qqq_series = qqq_series[mask_bench]
        soxx_series = soxx_series.reindex(qqq_series.index)

        # 2. Ingest SPY from yfinance
        try:
            import yfinance as yf
            logger.info("Downloading SPY historical prices from yfinance...")
            spy_raw = yf.download(
                "SPY",
                start="2001-07-09",
                end=end_date,
                auto_adjust=True,
                progress=False,
            )
            if spy_raw.empty:
                raise ValueError("yfinance returned empty SPY dataset.")

            spy_raw.index = pd.to_datetime(spy_raw.index).tz_localize(None)
            if isinstance(spy_raw.columns, pd.MultiIndex):
                if "Close" in spy_raw.columns.levels[0]:
                    close_df = spy_raw["Close"]
                    spy_series = close_df["SPY"] if "SPY" in close_df.columns else close_df.iloc[:, 0]
                else:
                    spy_series = spy_raw.iloc[:, 0]
            elif "Close" in spy_raw.columns:
                spy_series = spy_raw["Close"]
            else:
                spy_series = spy_raw.iloc[:, 0]
        except Exception as e:
            logger.warning(f"yfinance download for SPY failed: {e}. Checking existing tri-asset cache.")
            if self.tri_asset_path.exists():
                df_cached = pd.read_parquet(self.tri_asset_path)
                if "SPY" in df_cached.columns:
                    spy_series = df_cached["SPY"]
                else:
                    raise RuntimeError(f"Cannot acquire SPY prices and cache is missing SPY: {e}")
            else:
                raise RuntimeError(f"Cannot acquire SPY prices: {e}")

        # Align SPY to benchmark trading days
        spy_aligned = spy_series.reindex(qqq_series.index)
        if spy_aligned.isna().any():
            spy_aligned = spy_aligned.ffill().bfill()

        # Build clean tri-asset DataFrame
        prices_df = pd.DataFrame(
            {
                "SPY": spy_aligned.astype(np.float64),
                "QQQ": qqq_series.astype(np.float64),
                "SOXX": soxx_series.astype(np.float64),
            },
            index=qqq_series.index,
        )
        prices_df.index.name = "Date"

        # Verify zero NaNs
        nan_counts = prices_df.isna().sum().to_dict()
        if any(v > 0 for v in nan_counts.values()):
            logger.warning(f"Filling remaining NaNs in prices_df: {nan_counts}")
            prices_df = prices_df.ffill().bfill()

        # Persist to Parquet
        self.tri_asset_path.parent.mkdir(parents=True, exist_ok=True)
        prices_df.to_parquet(self.tri_asset_path, engine="pyarrow", index=True)
        logger.info(f"Saved tri-asset prices to {self.tri_asset_path} ({len(prices_df)} rows).")

        return self._slice_df(prices_df, start_date, end_date)

    def get_fx_rates(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        target_index: Optional[pd.DatetimeIndex] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Retrieves or ingests unbroken daily USDKRW exchange rates.
        """
        fx_series: Optional[pd.Series] = None

        if not force_refresh and self.fx_path.exists() and self.fx_path.stat().st_size > 0:
            try:
                cached_fx = pd.read_parquet(self.fx_path)
                col = "USDKRW" if "USDKRW" in cached_fx.columns else cached_fx.columns[0]
                fx_series = cached_fx[col]
            except Exception as e:
                logger.warning(f"Failed reading {self.fx_path}: {e}")

        if fx_series is None or force_refresh:
            try:
                from src.data.price_feed import PriceFeed
                pf = PriceFeed()
                s = pf.fetch_and_bridge_fx_rates(start_date="2001-07-10", end_date=end_date, force_download=force_refresh)
                fx_series = s
            except Exception as e:
                logger.error(f"Failed to fetch FX rates: {e}")
                if self.fx_path.exists():
                    cached_fx = pd.read_parquet(self.fx_path)
                    col = "USDKRW" if "USDKRW" in cached_fx.columns else cached_fx.columns[0]
                    fx_series = cached_fx[col]
                else:
                    raise RuntimeError(f"Cannot acquire FX rates: {e}")

        fx_series.index = pd.to_datetime(fx_series.index).tz_localize(None)
        fx_series.name = "USDKRW"

        if target_index is not None:
            aligned_fx = fx_series.reindex(target_index).ffill().bfill()
            fx_df = pd.DataFrame({"USDKRW": aligned_fx.astype(np.float64)}, index=target_index)
        else:
            fx_df = pd.DataFrame({"USDKRW": fx_series.astype(np.float64)}, index=fx_series.index)

        fx_df.index.name = "Date"
        return self._slice_df(fx_df, start_date, end_date)

    def _slice_df(
        self,
        df: pd.DataFrame,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> pd.DataFrame:
        """Slices dataframe between start_date and end_date."""
        res = df.copy()
        if start_date:
            res = res[res.index >= pd.Timestamp(start_date)]
        if end_date:
            res = res[res.index <= pd.Timestamp(end_date)]
        return res


def load_tri_asset_data(
    cache_dir: Union[str, Path] = "data/cache",
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Interface Contract:
    Loads aligned daily prices for SPY, QQQ, and SOXX alongside daily USDKRW FX rates
    from 2001-07-10 to present with 0 NaNs.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            prices_df: DataFrame with columns ['SPY', 'QQQ', 'SOXX']
            fx_df: DataFrame with column ['USDKRW']
    """
    loader = TriAssetDataLoader(cache_dir=cache_dir)
    return loader.load_data(force_refresh=force_refresh)
