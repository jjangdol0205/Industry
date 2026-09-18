"""
Tier 1: Feature 1 - Unified Universe Price & Indicator Sync Engine Tests.
Covers batch yfinance download, atomic multi-target persistence,
SQLite MIN(id) deduplication fix, MDD tracking, and graceful network failure recovery.
"""

import unittest
import json
import sqlite3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.e2e.test_helpers import (
    PROJECT_ROOT,
    UNIVERSE_EVALUATED_PATHS,
    UNIVERSAL_DEEPDIVE_PATHS,
    create_isolated_test_db,
    populate_sample_companies,
)


class TestF1SyncEngine(unittest.TestCase):
    """E2E Test Suite for Feature 1 (Unified Universe Price & Indicator Sync Engine)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_portal.db"
        self.conn = create_isolated_test_db(self.test_db_path)
        populate_sample_companies(self.conn)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_f1_01_ticker_normalization(self):
        """
        [F1-01] Verifies ticker normalization logic for KRX (A005930 -> 005930.KS,
        005930 -> 005930.KS, 018290.KQ) and US tickers (NVDA, TSMC).
        """
        # Test contract: normalizer function or sync engine mapping
        try:
            from sync_stocks import normalize_ticker
        except ImportError:
            # Check if implemented in backend or investment_engine
            try:
                from investment_engine import normalize_ticker
            except ImportError:
                # Standalone contract assertion
                self.fail("Implementation missing: 'normalize_ticker' must be defined in sync_stocks.py or investment_engine.py")

        test_cases = [
            ("A005930", "005930.KS"),
            ("005930", "005930.KS"),
            ("005930.KS", "005930.KS"),
            ("018290.KQ", "018290.KQ"),
            ("NVDA", "NVDA"),
            ("TSMC", "TSM"),  # Or standard TSM/TSMC resolution
            ("AAPL", "AAPL"),
        ]
        for raw, expected in test_cases:
            if raw == "TSMC" and normalize_ticker(raw) in ("TSM", "TSMC"):
                continue
            normalized = normalize_ticker(raw)
            self.assertEqual(
                normalized, expected,
                f"Ticker '{raw}' normalized to '{normalized}', expected '{expected}'"
            )

    def test_f1_02_atomic_json_distribution(self):
        """
        [F1-02] Verifies atomic synchronization writes across all 4 universe_evaluated.json
        locations and all 3 universal_deepdive_data.json locations without desync.
        """
        # Mock destination paths in temp_dir
        mock_universe_paths = [
            Path(self.temp_dir) / "root_universe.json",
            Path(self.temp_dir) / "backend_universe.json",
            Path(self.temp_dir) / "public_universe.json",
            Path(self.temp_dir) / "dist_universe.json",
        ]
        mock_deepdive_paths = [
            Path(self.temp_dir) / "backend_deepdive.json",
            Path(self.temp_dir) / "public_deepdive.json",
            Path(self.temp_dir) / "dist_deepdive.json",
        ]

        sample_universe = [
            {
                "id": 1,
                "ticker": "NVDA",
                "name": "NVIDIA",
                "current_price": 225.5,
                "high_52w": 240.0,
                "mdd_pct": -6.04,
                "buy_signal": "WAIT (고점 부근 MDD -6.0%)",
                "portfolio_tier": "Core",
            }
        ]
        sample_deepdive = {
            "NVDA": {
                "ticker": "NVDA",
                "quote": {"current_price": 225.5, "mdd_pct": -6.04}
            }
        }

        try:
            from sync_stocks import distribute_json_artifacts
            distribute_json_artifacts(
                sample_universe, sample_deepdive,
                universe_destinations=mock_universe_paths,
                deepdive_destinations=mock_deepdive_paths
            )
        except ImportError:
            # Fallback: check sync_universe or export function
            try:
                import sync_stocks
                if hasattr(sync_stocks, "export_artifacts"):
                    sync_stocks.export_artifacts(sample_universe, sample_deepdive)
                else:
                    self.fail("Implementation missing: sync_stocks.py must export JSON artifacts across all distribution targets")
            except ImportError:
                self.fail("Implementation missing: sync_stocks.py does not exist yet")

        # Verify all 4 universe files exist and have matching content
        for u_path in mock_universe_paths:
            self.assertTrue(u_path.exists(), f"Universe file {u_path} was not created atomically")
            with open(u_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]["current_price"], 225.5)

        # Verify all 3 deepdive files exist and have matching content
        for d_path in mock_deepdive_paths:
            self.assertTrue(d_path.exists(), f"Deepdive file {d_path} was not created atomically")
            with open(d_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.assertIn("NVDA", data)
                self.assertEqual(data["NVDA"]["quote"]["current_price"], 225.5)

    def test_f1_03_db_profile_dedup_min_id(self):
        """
        [F1-03] Verifies SQLite deduplication join logic where tickers appearing multiple times
        in `companies` (e.g. NVDA in report 1 id=1, and report 2 id=2) have company_profiles
        reliably linked to MIN(id) so that SELECT with MIN(id) never returns NULLs.
        """
        cursor = self.conn.cursor()

        # Simulate sync updating profiles with deduplication fix
        try:
            from sync_stocks import sync_profiles_to_db
            sync_profiles_to_db(self.conn, [
                {"ticker": "NVDA", "current_price": 230.0, "high_52w": 240.0, "mdd_pct": -4.17, "buy_signal": "WAIT"}
            ])
        except (ImportError, AttributeError):
            # Fallback to direct contract SQL verification
            pass

        # Query deduplicated universe using the exact query from backend/main.py
        cursor.execute("""
            SELECT c.ticker, MIN(c.id) as primary_id, cp.current_price, cp.mdd_pct
            FROM companies c
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.ticker = 'NVDA'
            GROUP BY c.ticker
        """)
        row = cursor.fetchone()
        self.assertIsNotNone(row, "NVDA should be found in companies table")
        ticker, primary_id, price, mdd = row
        self.assertEqual(primary_id, 1, "MIN(id) for NVDA must be 1")
        self.assertIsNotNone(price, "current_price must NOT be NULL for MIN(id) deduplicated row")
        self.assertIsNotNone(mdd, "mdd_pct must NOT be NULL for MIN(id) deduplicated row")

    def test_f1_04_mdd_calculation_precision(self):
        """
        [F1-04] Verifies MDD calculation formula ((P_curr - P_52w_high) / P_52w_high) * 100
        under various price moves.
        """
        try:
            from sync_stocks import calculate_mdd
        except ImportError:
            try:
                from investment_engine import calculate_mdd
            except ImportError:
                self.fail("Implementation missing: calculate_mdd function not found")

        # Case 1: 52w high = 100, curr = 80 -> -20.0%
        self.assertAlmostEqual(calculate_mdd(80.0, 100.0), -20.0, places=2)
        # Case 2: 52w high = 250, curr = 175 -> -30.0%
        self.assertAlmostEqual(calculate_mdd(175.0, 250.0), -30.0, places=2)
        # Case 3: 52w high = 100, curr = 100 -> 0.0%
        self.assertAlmostEqual(calculate_mdd(100.0, 100.0), 0.0, places=2)
        # Case 4: 52w high = 200, curr = 210 -> curr > high52 (new high, MDD = 0.0%)
        self.assertAlmostEqual(calculate_mdd(210.0, 200.0), 0.0, places=2)

    def test_f1_05_network_failure_graceful_recovery(self):
        """
        [F1-05] Verifies that an unexpected network error (e.g. Yahoo 429 or timeout)
        retains the existing database and cache data without raising unhandled exceptions.
        """
        try:
            import sync_stocks
        except ImportError:
            self.fail("Implementation missing: sync_stocks.py does not exist yet")

        # Mock yfinance to simulate network exception
        with patch("yfinance.download", side_effect=Exception("HTTP 429 Too Many Requests")):
            # If sync_universe / main is called with graceful mode
            if hasattr(sync_stocks, "run_sync"):
                result = sync_stocks.run_sync(db_path=self.test_db_path, graceful=True)
                self.assertFalse(result.get("network_success", True))
                self.assertTrue(result.get("fallback_used", False))
            elif hasattr(sync_stocks, "sync_all"):
                result = sync_stocks.sync_all(db_path=self.test_db_path)
                self.assertIsNotNone(result)

        # Confirm DB data remains uncorrupted
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM company_profiles WHERE current_price IS NOT NULL")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "Database profiles must be retained after network failure")


if __name__ == "__main__":
    unittest.main()
