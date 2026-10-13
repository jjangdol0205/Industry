"""
Tri-Tech ETF Data Loader & Ingestion Module (SMH, XLK, VGT).
Ingests and aligns daily split/dividend-adjusted total return prices for:
  - SMH (VanEck Semiconductor ETF, launched 2011-12-20)
  - XLK (Technology Select Sector SPDR Fund)
  - VGT (Vanguard Information Technology ETF)
alongside continuous daily USDKRW exchange rates from 2011-12-20 to present.
Guarantees zero NaNs, date alignment across all assets, and offline Parquet caching.
"""
from pathlib import Path
from typing import Tuple, Union, Optional
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_START_DATE = "2011-12-20"
TRI_TECH_PARQUET = "tri_tech_prices.parquet"
FX_PARQUET = "fx_rates.parquet"
TECH_TICKERS = ["SMH", "XLK", "VGT"]


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

    # Fallback: create directory under repo_root or cwd
    if (repo_root / "data").exists():
        target = repo_root / path
        target.mkdir(parents=True, exist_ok=True)
        return target.resolve()

    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


class TriTechDataLoader:
    """
    Manages ingestion, alignment, and persistent caching of the SMH/XLK/VGT tri-tech triad
    and USDKRW exchange rates from December 20, 2011 to present.
    """

    def __init__(self, cache_dir: Union[str, Path] = "data/cache"):
        self.cache_dir = _resolve_cache_dir(cache_dir)
        self.tri_tech_path = self.cache_dir / TRI_TECH_PARQUET
        self.fx_path = self.cache_dir / FX_PARQUET

    def load_data(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Loads aligned tri-tech prices and FX rates from cache, fetching if absent.

        Returns:
            Tuple[pd.DataFrame, pd.Series]:
                - prices_df: pd.DataFrame with columns ['SMH', 'XLK', 'VGT'],
                  DatetimeIndex from start_date (2011-12-20) to present, 0 NaNs.
                - fx_series: pd.Series with name 'USDKRW', aligned on trading days, 0 NaNs.
        """
        prices_df = self.get_tri_tech_prices(
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh,
        )

        fx_series = self.get_fx_rates(
            start_date=start_date,
            end_date=end_date,
            target_index=prices_df.index,
            force_refresh=force_refresh,
        )

        # Enforce exact trading days alignment
        fx_series = fx_series.reindex(prices_df.index)
        if fx_series.isna().any():
            fx_series = fx_series.ffill().bfill()

        return prices_df, fx_series

    def get_tri_tech_prices(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Retrieves or ingests SMH, XLK, VGT daily prices starting December 20, 2011.
        """
        if not force_refresh and self.tri_tech_path.exists() and self.tri_tech_path.stat().st_size > 0:
            try:
                df = pd.read_parquet(self.tri_tech_path)
                if df is not None and not df.empty and set(TECH_TICKERS).issubset(df.columns):
                    sliced = self._slice_df(df[TECH_TICKERS], start_date, end_date)
                    if not sliced.empty:
                        return sliced
            except Exception as e:
                logger.warning(f"Failed to read cached {self.tri_tech_path}: {e}. Re-ingesting.")

        return self.ingest_tri_tech_prices(start_date=start_date, end_date=end_date)

    def ingest_tri_tech_prices(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Ingests SMH, XLK, VGT from yfinance, validates 0 NaNs, and caches to tri_tech_prices.parquet.
        """
        try:
            import yfinance as yf
            logger.info("Downloading SMH, XLK, VGT historical prices from yfinance...")
            raw = yf.download(
                TECH_TICKERS,
                start=DEFAULT_START_DATE,
                end=end_date,
                auto_adjust=True,
                progress=False,
            )
            if raw is None or raw.empty:
                raise ValueError("yfinance returned empty tri-tech dataset.")

            raw.index = pd.to_datetime(raw.index).tz_localize(None)

            if isinstance(raw.columns, pd.MultiIndex):
                if "Close" in raw.columns.levels[0]:
                    close_df = raw["Close"][TECH_TICKERS].copy()
                else:
                    close_df = raw[TECH_TICKERS].copy()
            elif "Close" in raw.columns:
                close_df = raw["Close"][TECH_TICKERS].copy()
            else:
                close_df = raw[TECH_TICKERS].copy()

        except Exception as e:
            logger.warning(f"yfinance download for tri-tech failed: {e}. Checking existing cache fallback.")
            if self.tri_tech_path.exists() and self.tri_tech_path.stat().st_size > 0:
                cached_df = pd.read_parquet(self.tri_tech_path)
                if set(TECH_TICKERS).issubset(cached_df.columns):
                    return self._slice_df(cached_df[TECH_TICKERS], start_date, end_date)
            raise RuntimeError(f"Cannot acquire tri-tech prices from yfinance or cache: {e}")

        # Ensure index name is Date and slice to start_date
        close_df.index.name = "Date"
        close_df = close_df[close_df.index >= pd.Timestamp(DEFAULT_START_DATE)]

        # Guarantee zero NaNs
        if close_df.isna().any().any():
            logger.warning(f"Filling NaNs in tri-tech prices: {close_df.isna().sum().to_dict()}")
            close_df = close_df.ffill().bfill()

        # Enforce float64 type and column order
        prices_df = close_df[TECH_TICKERS].astype(np.float64)

        # Persist to Parquet
        self.tri_tech_path.parent.mkdir(parents=True, exist_ok=True)
        prices_df.to_parquet(self.tri_tech_path, engine="pyarrow", index=True)
        logger.info(f"Saved tri-tech prices to {self.tri_tech_path} ({len(prices_df)} rows).")

        return self._slice_df(prices_df, start_date, end_date)

    def get_fx_rates(
        self,
        start_date: str = DEFAULT_START_DATE,
        end_date: Optional[str] = None,
        target_index: Optional[pd.DatetimeIndex] = None,
        force_refresh: bool = False,
    ) -> pd.Series:
        """
        Retrieves continuous daily USDKRW exchange rates.
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
                s = pf.fetch_and_bridge_fx_rates(
                    start_date="2001-07-10",
                    end_date=end_date,
                    force_download=force_refresh,
                )
                fx_series = s
            except Exception as e:
                logger.error(f"Failed to fetch FX rates via PriceFeed: {e}")
                if self.fx_path.exists():
                    cached_fx = pd.read_parquet(self.fx_path)
                    col = "USDKRW" if "USDKRW" in cached_fx.columns else cached_fx.columns[0]
                    fx_series = cached_fx[col]
                else:
                    raise RuntimeError(f"Cannot acquire FX rates: {e}")

        fx_series.index = pd.to_datetime(fx_series.index).tz_localize(None)
        fx_series.name = "USDKRW"

        if target_index is not None:
            fx_series = fx_series.reindex(target_index).ffill().bfill()

        fx_series = fx_series[fx_series.index >= pd.Timestamp(start_date)]
        if end_date:
            fx_series = fx_series[fx_series.index <= pd.Timestamp(end_date)]

        return fx_series.astype(np.float64)

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


def load_tri_tech_data(
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
    cache_dir: Union[str, Path] = "data/cache",
    refresh: bool = False,
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Interface Contract:
    Loads aligned daily prices for SMH, XLK, and VGT alongside daily USDKRW FX rates
    from December 20, 2011 to present with 0 NaNs.

    Args:
        start_date: Earliest date string (default '2011-12-20').
        end_date: Latest date string (optional).
        cache_dir: Directory containing cache parquet files.
        refresh: Synonym for force_refresh.
        force_refresh: Force re-download from yfinance.

    Returns:
        Tuple[pd.DataFrame, pd.Series]:
            df_prices: DataFrame with columns ['SMH', 'XLK', 'VGT'], DatetimeIndex >= start_date.
            s_fx: Series named 'USDKRW' aligned on trading days, 0 NaNs.
    """
    is_refresh = refresh or force_refresh
    loader = TriTechDataLoader(cache_dir=cache_dir)
    return loader.load_data(start_date=start_date, end_date=end_date, force_refresh=is_refresh)
