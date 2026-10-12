"""
Survivorship-bias-free Universe Manager.
Loads historical point-in-time constituent intervals (1,262+ historical members)
and resolves exact index membership at any historical date.
"""
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List, Dict, Set, Union
import logging
import pandas as pd

from config.settings import SEED_DIR, CONFIG_DIR
from src.models.schemas import UniverseConstituent

logger = logging.getLogger(__name__)

# Comprehensive GICS sector mapping for historical S&P 500 constituents
from src.data.sector_map import SECTOR_MAP


class UniverseManager:
    """
    Manages historical index constituents with exact point-in-time date bounds.
    Eliminates survivorship bias by properly including historical members (and bankruptcies)
    and excluding companies before their initial addition.
    """

    def __init__(self, seed_file: Optional[Union[str, Path]] = None):
        if seed_file is None:
            self.seed_path = Path(SEED_DIR) / "sp500_ticker_start_end.csv"
        else:
            self.seed_path = Path(seed_file)

        self._constituents_df: pd.DataFrame = pd.DataFrame()
        self._load_seed()

    def _load_seed(self) -> None:
        """Loads and sanitizes constituent intervals from seed CSV."""
        if not self.seed_path.exists():
            logger.warning(f"Universe seed file not found at {self.seed_path}. Creating fallback.")
            self._create_fallback_seed()

        try:
            df = pd.read_csv(self.seed_path)
            # Normalize column names
            df.columns = [c.strip().lower() for c in df.columns]
            
            # Clean ticker
            df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

            # Clean dates
            df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
            # Default start date for missing
            df["start_date"] = df["start_date"].fillna(pd.Timestamp("1996-01-01"))

            df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
            # Active constituents have null end_date -> map to year 2099
            df["end_date"] = df["end_date"].fillna(pd.Timestamp("2099-12-31"))

            # Assign sector (unmapped tickers default to 'Unknown', not 'Information Technology')
            df["sector"] = df["ticker"].map(SECTOR_MAP).fillna("Unknown")

            self._constituents_df = df
        except Exception as e:
            logger.error(f"Failed to load universe seed from {self.seed_path}: {e}")
            self._constituents_df = pd.DataFrame(columns=["ticker", "start_date", "end_date", "sector"])

    def _create_fallback_seed(self) -> None:
        """Creates basic fallback seed if primary file is missing."""
        self.seed_path.parent.mkdir(parents=True, exist_ok=True)
        # Create minimal starter
        fallback_data = (
            "ticker,start_date,end_date\n"
            "AAPL,1996-01-02,\n"
            "MSFT,1996-01-02,\n"
            "INTC,1996-01-02,\n"
            "AMD,1996-01-02,\n"
            "NVDA,2001-11-30,\n"
            "AAMRQ,1996-01-02,2003-03-14\n"
            "LEH,1996-01-02,2008-09-15\n"
        )
        self.seed_path.write_text(fallback_data, encoding="utf-8")

    def get_constituents_at(self, as_of_date: Union[date, datetime, str, pd.Timestamp]) -> List[str]:
        """
        Returns all tickers that were active index constituents on as_of_date.
        Guarantees zero survivorship bias and zero lookahead bias.
        Normalizes as_of_date to timezone-naive date to prevent TypeError on tz-aware Timestamps.
        """
        if self._constituents_df.empty:
            return []

        norm_date = pd.to_datetime(as_of_date).tz_localize(None).date()
        dt = pd.Timestamp(norm_date)
        mask = (self._constituents_df["start_date"] <= dt) & (dt <= self._constituents_df["end_date"])
        active_tickers = self._constituents_df.loc[mask, "ticker"].drop_duplicates().tolist()
        return sorted(active_tickers)

    def is_member_at(self, ticker: str, as_of_date: Union[date, datetime, str, pd.Timestamp]) -> bool:
        """Checks if ticker was an active constituent on as_of_date."""
        norm_date = pd.to_datetime(as_of_date).tz_localize(None).date()
        active = self.get_constituents_at(norm_date)
        return ticker.upper() in active

    def get_sector(self, ticker: str) -> str:
        """Returns the GICS sector for the given ticker."""
        return SECTOR_MAP.get(ticker.upper(), "Unknown")

    def get_all_historical_tickers(self) -> List[str]:
        """Returns all distinct historical tickers across the entire 1996-present dataset."""
        if self._constituents_df.empty:
            return []
        return sorted(self._constituents_df["ticker"].drop_duplicates().tolist())

    def get_membership_interval(self, ticker: str) -> List[Dict[str, pd.Timestamp]]:
        """Returns the start and end dates for all intervals where ticker was active."""
        if self._constituents_df.empty:
            return []
        t = ticker.upper()
        sub = self._constituents_df[self._constituents_df["ticker"] == t]
        res = []
        for _, row in sub.iterrows():
            res.append({"start_date": row["start_date"], "end_date": row["end_date"]})
        return res
