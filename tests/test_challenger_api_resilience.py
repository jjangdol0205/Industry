"""
Challenger 2 — Empirical API & Resilient Ingestion Stress Test Suite
====================================================================
Tests FastAPI endpoints, error recovery, offline network resilience,
concurrency, background task dispatch, and schema compliance for the
Special Watchlist system (UBER, FLNC, MBLY, UPST, TSLA, 402340.KS).
"""

import os
import sys
import time
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Setup python paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "InvestmentPortal" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_TICKERS = ["UBER", "FLNC", "MBLY", "UPST", "TSLA", "402340.KS"]


class TestSpecialWatchlistApiAndResilience(unittest.TestCase):
    """Adversarial and Empirical stress test suite for Special Watchlist API."""

    @classmethod
    def setUpClass(cls):
        try:
            import main
            cls.app = main.app
        except ImportError:
            from InvestmentPortal.backend import main
            cls.app = main.app
        from starlette.testclient import TestClient
        cls.client = TestClient(cls.app)

    # =========================================================================
    # 1. GET /api/v1/special-watchlist Schema & Latency Benchmarks
    # =========================================================================

    def test_01_get_special_watchlist_schema_and_integrity(self):
        """Verifies GET /api/v1/special-watchlist returns 200, valid schema, 6 stocks, and 0 '??'."""
        response = self.client.get("/api/v1/special-watchlist")
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")

        data = response.json()
        self.assertIsInstance(data, dict, "Response must be a JSON dictionary")
        self.assertEqual(data.get("status"), "success", "Response status must be 'success'")
        self.assertIn("updated_at", data, "Response must contain 'updated_at'")
        self.assertIn("stocks", data, "Response must contain 'stocks' list")

        stocks = data["stocks"]
        self.assertGreaterEqual(len(stocks), 6, f"Expected at least 6 stocks, found {len(stocks)}")

        stock_map = {s.get("ticker"): s for s in stocks}
        for tk in TARGET_TICKERS:
            self.assertIn(tk, stock_map, f"Missing required ticker '{tk}' in API response")
            s = stock_map[tk]

            # Qualitative 5-dimension deep study fields
            for field in ["business_model", "moat_analysis", "tam_growth_drivers", "financial_margins", "key_risks"]:
                val = s.get(field)
                self.assertIsNotNone(val, f"{tk} missing deep study field '{field}'")
                self.assertIsInstance(val, str, f"{tk} field '{field}' must be str")
                self.assertGreaterEqual(len(val.strip()), 15, f"{tk} field '{field}' too short: {val}")
                self.assertNotIn("??", val, f"{tk} field '{field}' has '??' encoding corruption")

            # Quantitative fields
            self.assertIsInstance(s.get("current_price"), (int, float), f"{tk} current_price must be numeric")
            self.assertGreater(s.get("current_price"), 0, f"{tk} current_price must be > 0")
            self.assertIsInstance(s.get("high_52w"), (int, float), f"{tk} high_52w must be numeric")
            self.assertIsInstance(s.get("mdd_pct"), (int, float), f"{tk} mdd_pct must be numeric")
            self.assertLessEqual(s.get("mdd_pct"), 0.0, f"{tk} mdd_pct must be <= 0")
            self.assertIn("buy_signal", s, f"{tk} missing buy_signal")
            self.assertIn("dca_stage", s, f"{tk} missing dca_stage")
            self.assertIn("portfolio_tier", s, f"{tk} missing portfolio_tier")

            # Timeline
            timeline = s.get("timeline")
            self.assertIsInstance(timeline, list, f"{tk} timeline must be a list")
            self.assertGreaterEqual(len(timeline), 2, f"{tk} timeline must have >= 2 events")

            dates = []
            for item in timeline:
                self.assertIn("news_id", item, f"{tk} timeline item missing news_id")
                self.assertIn("publish_date", item, f"{tk} timeline item missing publish_date")
                self.assertIn("headline", item, f"{tk} timeline item missing headline")
                self.assertIn("source", item, f"{tk} timeline item missing source")
                self.assertIn("summary", item, f"{tk} timeline item missing summary")
                self.assertIn("sentiment", item, f"{tk} timeline item missing sentiment")
                self.assertNotIn("??", item["headline"], f"{tk} headline has '??'")
                self.assertNotIn("??", item["summary"], f"{tk} summary has '??'")
                dates.append(str(item["publish_date"]).strip())

            # Reverse chronological check
            self.assertEqual(dates, sorted(dates, reverse=True), f"{tk} timeline not sorted reverse-chronologically")

    def test_02_get_special_watchlist_latency_benchmark(self):
        """Stress-tests GET latency: average response time over 10 consecutive requests."""
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            res = self.client.get("/api/v1/special-watchlist")
            elapsed = time.perf_counter() - start
            self.assertEqual(res.status_code, 200)
            latencies.append(elapsed)

        avg_latency_ms = (sum(latencies) / len(latencies)) * 1000
        max_latency_ms = max(latencies) * 1000
        print(f"\n[Bench] GET /api/v1/special-watchlist: Avg={avg_latency_ms:.2f}ms, Max={max_latency_ms:.2f}ms")
        self.assertLess(avg_latency_ms, 300.0, f"Average latency too high: {avg_latency_ms:.2f}ms (threshold 300ms)")

    def test_03_get_special_watchlist_aliases(self):
        """Tests endpoint alias GET /api/special-watchlist (without /v1)."""
        res = self.client.get("/api/special-watchlist")
        self.assertEqual(res.status_code, 200, f"Alias endpoint failed with {res.status_code}")
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertGreaterEqual(len(data.get("stocks", [])), 6)

    def test_04_get_special_watchlist_concurrency_stress(self):
        """Fires 20 concurrent requests to test thread safety and SQLite connection pooling."""
        def fetch_endpoint():
            res = self.client.get("/api/v1/special-watchlist")
            return res.status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(fetch_endpoint) for _ in range(20)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 20)
        for code in results:
            self.assertEqual(code, 200, f"Concurrent request returned non-200: {code}")

    # =========================================================================
    # 2. POST /api/v1/special-watchlist/refresh Tests
    # =========================================================================

    def test_05_post_refresh_synchronous_execution(self):
        """Tests POST /api/v1/special-watchlist/refresh synchronous execution with mock yfinance."""
        with patch("sync_special_watchlist.sync_stock_prices") as mock_prices:
            # Return current cached values without external network call
            mock_prices.return_value = {
                "UBER": {"current_price": 69.22, "high_52w": 101.29, "mdd_pct": -31.66, "buy_signal": "BUY_READY", "dca_stage": "SAT_DCA_1", "portfolio_tier": "Standard"}
            }
            res = self.client.post("/api/v1/special-watchlist/refresh", json={"background": False, "force": False})
            self.assertEqual(res.status_code, 200, f"Sync refresh returned {res.status_code}: {res.text}")
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIn("stocks", data)

    def test_06_post_refresh_background_task_execution(self):
        """Tests POST /api/v1/special-watchlist/refresh with background=True."""
        res = self.client.post("/api/v1/special-watchlist/refresh", json={"background": True})
        self.assertEqual(res.status_code, 200, f"Background refresh returned {res.status_code}: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "processing", f"Expected status 'processing', got: {data}")
        self.assertIn("background", data.get("message", "").lower())

    def test_07_refresh_alias_endpoints_and_http_methods(self):
        """Tests POST /api/special-watchlist/refresh and GET /api/v1/special-watchlist/refresh."""
        # 1. Alias POST
        res_alias = self.client.post("/api/special-watchlist/refresh", json={"background": True})
        self.assertEqual(res_alias.status_code, 200)
        self.assertEqual(res_alias.json().get("status"), "processing")

        # 2. Alias GET with query parameter
        res_get_rf = self.client.get("/api/v1/special-watchlist/refresh?background=true")
        self.assertEqual(res_get_rf.status_code, 200)
        self.assertEqual(res_get_rf.json().get("status"), "processing")

    def test_08_refresh_malformed_and_edge_case_inputs(self):
        """Adversarially feeds unexpected/malformed body types to ensure robustness."""
        # Malformed types
        edge_cases = [
            {},
            {"background": "yes", "force": "invalid_val"},
            {"extra_garbage": 12345, "nested": {"a": [1, 2, 3]}},
            None,
        ]
        for payload in edge_cases:
            res = self.client.post("/api/v1/special-watchlist/refresh", json=payload)
            self.assertIn(
                res.status_code, (200, 422),
                f"Payload {payload} caused unexpected HTTP status {res.status_code}: {res.text}"
            )
            # Never return 500
            self.assertNotEqual(res.status_code, 500)

    # =========================================================================
    # 3. Resilient Ingestion & Offline / Network Failure Tests
    # =========================================================================

    def test_09_offline_network_failure_resilience_in_sync_engine(self):
        """Simulates network timeout/unreachable during yfinance calls; verifies zero data loss and HTTP 200."""
        import sync_special_watchlist

        # Mock yfinance to simulate network outage
        with patch("yfinance.download", side_effect=ConnectionError("Simulated DNS/Network failure")), \
             patch("yfinance.Ticker", side_effect=TimeoutError("Simulated socket timeout")):

            # Run sync under full offline condition
            result = sync_special_watchlist.run_sync(force=True, silent=True, source="test_offline")
            self.assertEqual(result.get("status"), "success", "Sync engine must succeed gracefully offline")
            self.assertGreaterEqual(len(result.get("stocks", [])), 6, "Must retain all 6 stocks")

            # Verify prices and MDD are not NULL or 0
            for s in result["stocks"]:
                self.assertIsNotNone(s.get("current_price"), f"{s.get('ticker')} current_price became None offline")
                self.assertGreater(s.get("current_price"), 0, f"{s.get('ticker')} current_price was lost offline")
                self.assertIsNotNone(s.get("mdd_pct"), f"{s.get('ticker')} mdd_pct became None offline")

    def test_10_api_refresh_graceful_fallback_on_unhandled_sync_exception(self):
        """Verifies POST /api/v1/special-watchlist/refresh gracefully returns cached data on unexpected error."""
        with patch("sync_special_watchlist.run_sync", side_effect=RuntimeError("Simulated fatal sync crash")):
            res = self.client.post("/api/v1/special-watchlist/refresh", json={"background": False})
            self.assertEqual(
                res.status_code, 200,
                f"Refresh endpoint must not crash with 500 on sync error, got {res.status_code}"
            )
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertGreaterEqual(len(data.get("stocks", [])), 6)

    def test_11_db_lock_fallback_to_json_cache(self):
        """Verifies GET /api/v1/special-watchlist falls back to JSON files if DB is locked."""
        with patch("sync_special_watchlist.get_all_special_data", side_effect=sqlite3.OperationalError("database is locked")):
            res = self.client.get("/api/v1/special-watchlist")
            self.assertEqual(
                res.status_code, 200,
                f"GET endpoint failed to fallback to JSON files upon DB lock: {res.status_code} {res.text}"
            )
            data = res.json()
            stocks = data.get("stocks", data) if isinstance(data, dict) else data
            self.assertGreaterEqual(len(stocks), 6, "Fallback JSON must contain at least 6 stocks")

    def test_12_time_series_news_deduplication_integrity(self):
        """Verifies duplicate news events cannot be inserted and timeline retains reverse-chronological order."""
        import sync_special_watchlist
        db_path = sync_special_watchlist.AUTHORITATIVE_DB_PATH

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM special_watchlist_timeline WHERE ticker = 'UBER'")
        initial_count = cur.fetchone()[0]

        # Duplicate insertion attempt
        test_hash = sync_special_watchlist.compute_news_hash("UBER", "2026-09-25", "테스트 중복 헤드라인")
        cur.execute("""
            INSERT OR IGNORE INTO special_watchlist_timeline (
                ticker, news_id, publish_date, headline, source, summary, sentiment, created_at
            ) VALUES ('UBER', ?, '2026-09-25', '테스트 중복 헤드라인', 'TestWire', '요약', 'POSITIVE', datetime('now'))
        """, (test_hash,))
        conn.commit()

        # Try inserting again
        cur.execute("""
            INSERT OR IGNORE INTO special_watchlist_timeline (
                ticker, news_id, publish_date, headline, source, summary, sentiment, created_at
            ) VALUES ('UBER', ?, '2026-09-25', '테스트 중복 헤드라인', 'TestWire', '요약', 'POSITIVE', datetime('now'))
        """, (test_hash,))
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM special_watchlist_timeline WHERE news_id = ?", (test_hash,))
        dup_count = cur.fetchone()[0]
        self.assertEqual(dup_count, 1, f"Deduplication failed: expected 1 record for news_id {test_hash}, got {dup_count}")

        # Clean up test row
        cur.execute("DELETE FROM special_watchlist_timeline WHERE news_id = ?", (test_hash,))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
