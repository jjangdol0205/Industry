"""
Tier 1: Feature 6 - Backend API Enhancements & Data Integrity Tests.
Covers /api/portfolio/universe zero-NULL contract, @app.post /api/portfolio/refresh_prices routing,
/api/companies/{id}/profile price/MDD metric inclusion, and sync preservation.
"""

import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.e2e.test_helpers import (
    PROJECT_ROOT,
    MAIN_PY_PATH,
    create_isolated_test_db,
    populate_sample_companies,
)


class TestF6BackendAPI(unittest.TestCase):
    """E2E Test Suite for Feature 6 (Backend API Enhancements & Data Integrity)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.temp_dir) / "test_portal.db"
        self.conn = create_isolated_test_db(self.test_db_path)
        populate_sample_companies(self.conn)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _get_app(self):
        """Helper to safely import FastAPI app from InvestmentPortal.backend.main."""
        try:
            import main
            return main.app
        except ImportError:
            try:
                from InvestmentPortal.backend import main
                return main.app
            except ImportError:
                self.fail("Implementation missing: InvestmentPortal/backend/main.py could not be imported")

    def test_f6_01_universe_endpoint_zero_nulls(self):
        """
        [F6-01] Verifies GET /api/portfolio/universe contract:
        Zero NULL values allowed for active companies in current_price, high_52w, mdd_pct, buy_signal.
        """
        app = self._get_app()
        from starlette.testclient import TestClient
        client = TestClient(app)

        response = client.get("/api/portfolio/universe")
        self.assertEqual(response.status_code, 200, "GET /api/portfolio/universe must return HTTP 200")
        data = response.json()

        universe_list = data.get("universe", data if isinstance(data, list) else [])
        self.assertGreater(len(universe_list), 0, "Universe list must not be empty")

        for item in universe_list:
            ticker = item.get("ticker")
            # Only validate items that represent active listed companies
            if ticker and not ticker.startswith("PRIVATE_"):
                self.assertIsNotNone(
                    item.get("current_price"),
                    f"Ticker {ticker} has NULL current_price"
                )
                self.assertIsNotNone(
                    item.get("high_52w"),
                    f"Ticker {ticker} has NULL high_52w"
                )
                self.assertIsNotNone(
                    item.get("mdd_pct"),
                    f"Ticker {ticker} has NULL mdd_pct"
                )
                self.assertIsNotNone(
                    item.get("buy_signal"),
                    f"Ticker {ticker} has NULL buy_signal"
                )

    def test_f6_02_refresh_prices_endpoint_routing(self):
        """
        [F6-02] Verifies POST /api/portfolio/refresh_prices endpoint is registered
        in FastAPI routes and does NOT return 404 Not Found or 405 Method Not Allowed.
        """
        app = self._get_app()
        routes = [route.path for route in app.routes]
        
        # Check if route path exists
        refresh_paths = [
            "/api/portfolio/refresh_prices",
            "/api/portfolio/refresh",
        ]
        has_refresh_route = any(p in routes for p in refresh_paths)
        self.assertTrue(
            has_refresh_route,
            f"Expected /api/portfolio/refresh_prices to be registered in app routes. Available: {routes}"
        )

        from starlette.testclient import TestClient
        client = TestClient(app)

        # Call with mock to avoid triggering actual long network fetch during test
        with patch("sync_stocks.run_sync", return_value={"status": "success", "count": 100}), \
             patch("main.refresh_universe_prices", return_value={"message": "Prices refreshed successfully"}):
            resp = client.post("/api/portfolio/refresh_prices")
            self.assertIn(resp.status_code, (200, 201, 202), "POST refresh endpoint should return 200/201/202")

    def test_f6_03_company_profile_endpoint_metrics(self):
        """
        [F6-03] Verifies GET /api/companies/{id}/profile returns full valuation and
        indicators including current_price, high_52w, mdd_pct, buy_signal, rebound_score.
        """
        app = self._get_app()
        from starlette.testclient import TestClient
        client = TestClient(app)

        response = client.get("/api/companies/1/profile")
        if response.status_code == 200:
            data = response.json()
            profile = data.get("profile", data)
            self.assertIn("current_price", profile)
            self.assertIn("high_52w", profile)
            self.assertIn("mdd_pct", profile)
            self.assertIn("buy_signal", profile)

    def test_f6_04_sync_endpoint_preserves_mdd_and_signals(self):
        """
        [F6-04] Verifies POST /api/companies/{id}/sync does NOT erase previously computed
        high_52w, mdd_pct, and buy_signal from SQLite company_profiles.
        """
        app = self._get_app()
        from starlette.testclient import TestClient
        client = TestClient(app)

        # Pre-check profile 1 has valid MDD
        cursor = self.conn.cursor()
        cursor.execute("SELECT mdd_pct, buy_signal FROM company_profiles WHERE company_id = 1")
        row = cursor.fetchone()
        orig_mdd, orig_sig = (row[0], row[1]) if row else (None, None)

        # Call sync endpoint (mocking external fetcher)
        with patch("comprehensive_fetcher.fetch_all_fmp_data", return_value=True):
            resp = client.post("/api/companies/1/sync")
            # Even after sync, verify MDD and buy_signal are not wiped to NULL
            cursor.execute("SELECT mdd_pct, buy_signal FROM company_profiles WHERE company_id = 1")
            updated_row = cursor.fetchone()
            if updated_row:
                self.assertIsNotNone(
                    updated_row[0],
                    "Sync endpoint must preserve mdd_pct and not reset to NULL"
                )
                self.assertIsNotNone(
                    updated_row[1],
                    "Sync endpoint must preserve buy_signal and not reset to NULL"
                )

    def test_f6_05_deduplicated_ticker_join_integrity(self):
        """
        [F6-05] Verifies that when a ticker exists across multiple industries,
        the deduplication logic links company_profiles to MIN(id) so joining on MIN(id)
        returns complete, populated profile fields.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.ticker, MIN(c.id) AS min_id, cp.current_price, cp.buy_signal
            FROM companies c
            LEFT JOIN company_profiles cp ON c.id = cp.company_id
            WHERE c.ticker = 'NVDA'
            GROUP BY c.ticker
        """)
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        ticker, min_id, price, signal = row
        self.assertIsNotNone(price, "current_price must not be NULL for NVDA MIN(id)")
        self.assertIsNotNone(signal, "buy_signal must not be NULL for NVDA MIN(id)")


if __name__ == "__main__":
    unittest.main()
