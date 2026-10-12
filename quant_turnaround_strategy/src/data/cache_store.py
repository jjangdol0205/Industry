"""
Cache store manager for persistent Parquet and SQLite storage.
Ensures instant offline execution and zero network dependency during backtests.
"""
from pathlib import Path
from typing import Optional, Union
import sqlite3
import pandas as pd
import time


class CacheStore:
    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        if cache_dir is None:
            from config.settings import CACHE_DIR
            self.cache_dir = Path(CACHE_DIR)
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_parquet_path(self, filename: str) -> Path:
        if not filename.endswith(".parquet"):
            filename = f"{filename}.parquet"
        return self.cache_dir / filename

    def save_parquet(self, df: pd.DataFrame, filename: str) -> Path:
        """Saves DataFrame to Parquet using PyArrow engine."""
        path = self.get_parquet_path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, engine="pyarrow", index=True)
        return path

    def load_parquet(self, filename: str) -> Optional[pd.DataFrame]:
        """Loads DataFrame from Parquet if file exists, else None."""
        path = self.get_parquet_path(filename)
        if not path.exists():
            return None
        try:
            return pd.read_parquet(path, engine="pyarrow")
        except Exception:
            return None

    def exists(self, filename: str) -> bool:
        """Checks if cache file exists and has non-zero size."""
        path = self.get_parquet_path(filename)
        return path.exists() and path.stat().st_size > 0

    def is_fresh(self, filename: str, max_age_hours: float = 24.0) -> bool:
        """Checks if cached file was modified within max_age_hours."""
        path = self.get_parquet_path(filename)
        if not path.exists():
            return False
        age_seconds = time.time() - path.stat().st_mtime
        return age_seconds <= (max_age_hours * 3600.0)

    def save_sqlite(self, df: pd.DataFrame, table_name: str, db_name: str = "quant_cache.db") -> None:
        """Saves DataFrame into SQLite database table."""
        db_path = self.cache_dir / db_name
        with sqlite3.connect(db_path) as conn:
            df.to_sql(table_name, conn, if_exists="replace", index=True)

    def load_sqlite(self, table_name: str, db_name: str = "quant_cache.db") -> Optional[pd.DataFrame]:
        """Loads DataFrame from SQLite database table."""
        db_path = self.cache_dir / db_name
        if not db_path.exists():
            return None
        try:
            with sqlite3.connect(db_path) as conn:
                return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        except Exception:
            return None
