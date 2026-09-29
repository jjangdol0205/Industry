"""
Empirical Challenger 1: Backend Data Integrity & Sync Engine Stress-Test Suite
==============================================================================
Validates:
1. Deduplication Invariance: Idempotent ingestion, SHA-256 hash determinism, SQLite UNIQUE constraints.
2. Reverse-Chronological Ordering: Strict newest-to-oldest date sequence for all 6 stocks.
3. Zero-NULL Contracts: Completeness of 5-dimension deep study fields, prices, MDD, buy signals, and zero '??' encoding corruption.
4. CLI Flexibility: Parsing of comma-separated tickers, selective sync universe retention, and --force execution.
5. Canonical 4-Target Distribution: Integrity and parity across all JSON endpoints.
"""

import os
import sys
import json
import sqlite3
import hashlib
import unittest
from pathlib import Path

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sync_special_watchlist as sw

TARGET_TICKERS = ["UBER", "FLNC", "MBLY", "UPST", "TSLA", "402340.KS", "ENPH", "CELH"]
CANONICAL_JSON_PATHS = [
    PROJECT_ROOT / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "special_watchlist_data.json",
]


class TestChallengerBackendSync(unittest.TestCase):
    """Adversarial stress-test suite for Special Watchlist backend data and sync engine."""

    def setUp(self):
        self.root_json_path = PROJECT_ROOT / "special_watchlist_data.json"
        self.assertTrue(self.root_json_path.exists(), f"Missing canonical JSON at {self.root_json_path}")
        with open(self.root_json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.stocks = self.data.get("stocks", [])
        self.stock_map = {s["ticker"]: s for s in self.stocks if "ticker" in s}

    # ==========================================================================
    # 1. Deduplication Invariance Tests
    # ==========================================================================
    def test_deduplication_hash_determinism(self):
        """Stress-tests compute_news_hash against whitespace, casing, and timestamp variations."""
        h1 = sw.compute_news_hash("uber", "2026-09-24", "Uber and Waymo Expand")
        h2 = sw.compute_news_hash("UBER  ", "2026-09-24T12:00:00Z", "  Uber and Waymo Expand  ")
        h3 = sw.compute_news_hash("UBER", "2026-09-24", "Uber and Waymo Expand")

        self.assertEqual(h1, h2, "Hash must normalize lowercase tickers, trailing whitespace, and ISO dates")
        self.assertEqual(h1, h3, "Hash must be strictly deterministic")
        self.assertEqual(len(h1), 16, "Hash length must be exactly 16 hex characters")

    def test_sqlite_unique_constraint_enforcement(self):
        """Validates that special_watchlist_timeline enforces SQLite UNIQUE constraint on news_id."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = Path(tmp_db.name)

        try:
            # Seed isolated test db
            sw.ensure_tables_and_seed(tmp_db_path)

            conn = sqlite3.connect(str(tmp_db_path))
            cur = conn.cursor()

            # Count rows before duplicate insert attempt
            cur.execute("SELECT COUNT(*) FROM special_watchlist_timeline")
            initial_count = cur.fetchone()[0]
            self.assertGreaterEqual(initial_count, 18, "Seeded timeline must contain at least 18 items")

            # Attempt 1: Re-seed multiple times (idempotency stress test)
            for _ in range(5):
                sw.ensure_tables_and_seed(tmp_db_path)

            cur.execute("SELECT COUNT(*) FROM special_watchlist_timeline")
            after_reseed_count = cur.fetchone()[0]
            self.assertEqual(
                initial_count, after_reseed_count,
                f"Repeated seeding caused duplicate rows! Initial: {initial_count}, After: {after_reseed_count}"
            )

            # Attempt 2: Direct raw SQL duplicate insert should raise IntegrityError
            cur.execute("SELECT news_id, ticker, publish_date, headline, source, summary, sentiment FROM special_watchlist_timeline LIMIT 1")
            sample = cur.fetchone()
            with self.assertRaises(sqlite3.IntegrityError, msg="Direct duplicate news_id insertion must raise IntegrityError"):
                cur.execute("""
                    INSERT INTO special_watchlist_timeline (news_id, ticker, publish_date, headline, source, summary, sentiment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, sample)

            conn.close()
        finally:
            if tmp_db_path.exists():
                try:
                    os.unlink(tmp_db_path)
                except Exception:
                    pass

    def test_canonical_json_zero_duplicate_news(self):
        """Verifies that none of the 6 stocks have duplicate news_ids or identical headlines."""
        total_articles = 0
        all_news_ids = set()

        for s in self.stocks:
            tk = s["ticker"]
            timeline = s.get("timeline", [])
            self.assertGreaterEqual(len(timeline), 2, f"Stock {tk} must have at least 2 timeline events")

            seen_for_stock = set()
            for idx, item in enumerate(timeline):
                nid = item.get("news_id")
                self.assertIsNotNone(nid, f"Stock {tk} item [{idx}] has NULL news_id")
                self.assertNotIn(nid, seen_for_stock, f"Stock {tk} contains duplicate news_id '{nid}'")
                seen_for_stock.add(nid)
                all_news_ids.add(nid)
                total_articles += 1

        self.assertEqual(len(all_news_ids), total_articles, "Globally unique news_ids expected across all stocks")

    # ==========================================================================
    # 2. Reverse-Chronological Ordering Tests
    # ==========================================================================
    def test_reverse_chronological_ordering_all_stocks(self):
        """Verifies every stock's timeline is strictly ordered newest date to oldest."""
        for tk in TARGET_TICKERS:
            self.assertIn(tk, self.stock_map, f"Target ticker {tk} missing")
            stock = self.stock_map[tk]
            timeline = stock.get("timeline", [])

            dates = [t.get("publish_date") for t in timeline]
            self.assertTrue(all(dates), f"Stock {tk} has missing or empty publish_date in timeline")

            # Check format YYYY-MM-DD
            for d in dates:
                self.assertEqual(len(d), 10, f"Stock {tk} date '{d}' not in YYYY-MM-DD format")
                parts = d.split("-")
                self.assertEqual(len(parts), 3, f"Stock {tk} date '{d}' invalid format")

            # Strict reverse chronological check
            expected_dates = sorted(dates, reverse=True)
            self.assertEqual(
                dates, expected_dates,
                f"Stock {tk} timeline is NOT in reverse-chronological order!\nActual:   {dates}\nExpected: {expected_dates}"
            )

    # ==========================================================================
    # 3. Zero-NULL Contracts Tests
    # ==========================================================================
    def test_zero_null_contracts_study_dimensions(self):
        """Verifies that none of the 6 stocks have NULL or missing values in 5 study dimensions."""
        mandatory_study_fields = [
            "business_model",
            "moat_analysis",
            "tam_growth_drivers",
            "financial_margins",
            "key_risks",
        ]

        for tk in TARGET_TICKERS:
            self.assertIn(tk, self.stock_map, f"Ticker {tk} missing from payload")
            stock = self.stock_map[tk]

            for field in mandatory_study_fields:
                # Top-level check
                val = stock.get(field)
                self.assertIsNotNone(val, f"Stock {tk} has NULL top-level '{field}'")
                self.assertIsInstance(val, str, f"Stock {tk} field '{field}' must be str")
                self.assertGreaterEqual(len(val.strip()), 15, f"Stock {tk} field '{field}' is too short: '{val}'")
                self.assertNotIn("??", val, f"Stock {tk} has '??' encoding corruption in '{field}'")

                # Nested study dict check
                nested_study = stock.get("study", {})
                nested_val = nested_study.get(field)
                self.assertIsNotNone(nested_val, f"Stock {tk} has NULL nested study.'{field}'")
                self.assertNotIn("??", nested_val, f"Stock {tk} has '??' in nested study.'{field}'")

            # Dual-contract moat check
            self.assertIsNotNone(stock.get("moat_bottleneck"), f"Stock {tk} missing dual contract 'moat_bottleneck'")
            self.assertEqual(stock.get("moat_bottleneck"), stock.get("moat_analysis"))

    def test_zero_null_contracts_price_and_mdd_metrics(self):
        """Verifies that none of the 6 stocks have NULL or negative prices / invalid MDD metrics."""
        for tk in TARGET_TICKERS:
            stock = self.stock_map[tk]

            price = stock.get("current_price")
            self.assertIsNotNone(price, f"Stock {tk} current_price is NULL")
            self.assertIsInstance(price, (int, float), f"Stock {tk} current_price must be float/int")
            self.assertGreater(price, 0.0, f"Stock {tk} current_price must be positive")

            high_52w = stock.get("high_52w")
            self.assertIsNotNone(high_52w, f"Stock {tk} high_52w is NULL")
            self.assertIsInstance(high_52w, (int, float), f"Stock {tk} high_52w must be float/int")
            self.assertGreaterEqual(high_52w, price, f"Stock {tk} high_52w must be >= current_price")

            mdd_pct = stock.get("mdd_pct")
            self.assertIsNotNone(mdd_pct, f"Stock {tk} mdd_pct is NULL")
            self.assertIsInstance(mdd_pct, (int, float), f"Stock {tk} mdd_pct must be float/int")
            self.assertLessEqual(mdd_pct, 0.0, f"Stock {tk} mdd_pct must be <= 0.0%")

            buy_signal = stock.get("buy_signal")
            self.assertIsNotNone(buy_signal, f"Stock {tk} buy_signal is NULL")
            self.assertIsInstance(buy_signal, str)
            self.assertTrue(any(sig in buy_signal for sig in ["BUY_READY", "WAIT", "DEEP_DISCOUNT"]))

            dca_stage = stock.get("dca_stage")
            self.assertIsNotNone(dca_stage, f"Stock {tk} dca_stage is NULL")

            tier = stock.get("portfolio_tier")
            self.assertIn(tier, ["Core", "Satellite", "Watchlist", "Standard"])

    # ==========================================================================
    # 4. CLI Flexibility & Selective Execution Tests
    # ==========================================================================
    def test_cli_ticker_parsing_and_isolation(self):
        """Tests that run_sync accepts string or list tickers and parses them reliably."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            tmp_db_path = Path(tmp_db.name)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_json:
            tmp_json_path = Path(tmp_json.name)

        try:
            # Run sync on isolated temp files for only UBER and TSLA with force=True
            res = sw.run_sync(
                force=True,
                tickers="UBER, TSLA",
                silent=True,
                source="test_cli",
                db_path=tmp_db_path,
                destinations=[tmp_json_path]
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(set(res["synced_tickers"]), {"UBER", "TSLA"})

            # Verify that output JSON still retains all 6 stocks from database baseline
            self.assertTrue(tmp_json_path.exists())
            with open(tmp_json_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            stocks_saved = saved.get("stocks", [])
            saved_tickers = {s["ticker"] for s in stocks_saved}
            for expected in TARGET_TICKERS:
                self.assertIn(
                    expected, saved_tickers,
                    f"Selective sync wiped out un-targeted ticker {expected}! Full 6-stock persistence required."
                )
        finally:
            for p in [tmp_db_path, tmp_json_path]:
                if p.exists():
                    try:
                        os.unlink(p)
                    except Exception:
                        pass

    # ==========================================================================
    # 5. Canonical Multi-Target Parity Tests
    # ==========================================================================
    def test_multi_target_json_parity(self):
        """Verifies that all 4 canonical distribution paths exist and match in stock count & schema."""
        for p in CANONICAL_JSON_PATHS:
            self.assertTrue(p.exists(), f"Canonical path missing: {p}")
            self.assertGreater(p.stat().st_size, 1000, f"File at {p} unexpectedly small")

            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)

            stocks = data.get("stocks", [])
            self.assertEqual(len(stocks), 8, f"File at {p} must contain exactly 8 stocks, got {len(stocks)}")

            tickers = [s["ticker"] for s in stocks]
            self.assertEqual(tickers, TARGET_TICKERS, f"Ticker order mismatch at {p}: {tickers}")


if __name__ == "__main__":
    unittest.main()
