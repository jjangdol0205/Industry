"""
Unit tests for UniverseManager: point-in-time constituent queries,
historical additions/removals, and zero survivorship bias.
"""
from datetime import date
import pytest

from src.data.universe import UniverseManager


def test_universe_initialization(universe_manager):
    """Verifies that the historical universe contains over 1,000 distinct historical members."""
    all_tickers = universe_manager.get_all_historical_tickers()
    assert len(all_tickers) >= 1000
    assert "AAPL" in all_tickers
    assert "MSFT" in all_tickers
    assert "NVDA" in all_tickers


def test_survivorship_bias_elimination(universe_manager):
    """
    Verifies that historical bankruptcies and removals (e.g. AAMRQ, LEH)
    are properly returned as active constituents during their index tenure,
    but excluded after their bankruptcy/delisting date.
    """
    # Lehman Brothers (LEH) was active in S&P 500 until bankruptcy in Sept 2008
    assert universe_manager.is_member_at("LEH", "2008-01-01") is True
    assert universe_manager.is_member_at("LEH", "2009-01-01") is False

    # American Airlines pre-merger bankruptcy entity (AAMRQ)
    assert universe_manager.is_member_at("AAMRQ", "2001-07-10") is True
    assert universe_manager.is_member_at("AAMRQ", "2005-01-01") is False


def test_entry_date_discipline_zero_lookahead(universe_manager):
    """
    Verifies that companies are NOT included in the universe before their
    actual point-in-time index addition date (e.g. NVDA was added in Nov 2001).
    """
    # NVDA added 2001-11-30
    assert universe_manager.is_member_at("NVDA", "2001-07-10") is False
    assert universe_manager.is_member_at("NVDA", "2002-01-01") is True


def test_active_count_consistency(universe_manager):
    """Verifies constituent count at historical cross-sections remains close to 500."""
    count_2001 = len(universe_manager.get_constituents_at("2001-07-10"))
    count_2008 = len(universe_manager.get_constituents_at("2008-09-15"))
    count_2024 = len(universe_manager.get_constituents_at("2024-01-01"))

    assert 480 <= count_2001 <= 510
    assert 480 <= count_2008 <= 510
    assert 490 <= count_2024 <= 510


def test_sector_classification(universe_manager):
    """Verifies sector mapping returns valid GICS sectors."""
    assert universe_manager.get_sector("AAPL") == "Information Technology"
    assert universe_manager.get_sector("JPM") == "Financials"
    assert universe_manager.get_sector("XOM") == "Energy"
    assert universe_manager.get_sector("F") == "Consumer Discretionary"
    assert universe_manager.get_sector("VLO") == "Energy"
    assert universe_manager.get_sector("SPG") == "Real Estate"
    assert universe_manager.get_sector("NEE") == "Utilities"
    # Unmapped ticker defaults to 'Unknown', NOT 'Information Technology'
    assert universe_manager.get_sector("TOTALLY_UNMAPPED_XYZ") == "Unknown"


def test_timezone_aware_timestamp_handling(universe_manager):
    """
    Verifies that passing a timezone-aware Timestamp (e.g. from yfinance)
    to is_member_at and get_constituents_at normalizes cleanly without TypeError.
    """
    import pandas as pd
    tz_ts = pd.Timestamp("2020-12-21", tz="America/New_York")
    # TSLA added 2020-12-21
    assert universe_manager.is_member_at("TSLA", tz_ts) is True
    assert "TSLA" in universe_manager.get_constituents_at(tz_ts)

