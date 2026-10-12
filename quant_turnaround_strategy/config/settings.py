"""
Global configuration and directory paths for the Quantitative Turnaround Strategy System.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_DIR = BASE_DIR / "config"
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
SEED_DIR = DATA_DIR / "seed"
TESTS_DIR = BASE_DIR / "tests"

# Timeline parameters
DEFAULT_START_DATE = "2001-07-10"  # SOXX legal launch date
BENCHMARK_TICKERS = ["QQQ", "SOXX"]

# Screener parameters
DEFAULT_ROLLING_WINDOW = 252  # 1 trading year
DEFAULT_LOW_PROXIMITY_THRESHOLD = 0.05  # Within 5% of 52-week low
DEFAULT_MAX_PORTFOLIO_CAPACITY = 3
DEFAULT_MIN_TRADING_DAYS = 252
DEFAULT_MIN_RSI = 20.0
DEFAULT_MIN_5D_RETURN = -0.05  # -5%
DEFAULT_MIN_DOLLAR_VOLUME = 20_000_000.0  # $20M daily dollar volume

# SEC reporting lag parameters
SEC_LAG_10Q_DAYS = 45
SEC_LAG_10K_DAYS = 90
