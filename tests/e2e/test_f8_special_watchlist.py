"""
Tier 1: Feature 8 - Special Watchlist Deep Study & Time-Series News Timeline Tests.
Validates:
- [F8-01]: Data completeness & UTF-8 Korean integrity for all 8 tickers (UBER, FLNC, MBLY, UPST, TSLA, 402340.KS, ENPH, CELH).
  Verifies 5-dimension institutional research (business_model, moat_analysis, tam_growth_drivers,
  financial_margins, key_risks), quantitative metrics (current_price, mdd_pct, buy_signal), and zero '??' encoding corruption.
- [F8-02]: Time-series timeline deduplication & reverse-chronological ordering (latest date first)
  with zero duplicate news_id / headline records.
- [F8-03]: Backend FastAPI endpoint contracts (GET /api/v1/special-watchlist and POST /api/v1/special-watchlist/refresh).
- [F8-04]: Frontend React UI contracts in App.jsx ('special-watchlist' view mode, '특별 관심종목' sidebar item,
  '시계열 외신 최신화', '특별 관심종목 돌려줘').
- [F8-05]: Multi-target atomic JSON distribution across all 4 canonical paths (Root, Backend, Frontend Public, Frontend Dist).
- [F8-06]: CLI runner execution contract (sync_special_watchlist.py exists, defines run_sync).
"""

import os
import sys
import json
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch

from tests.e2e.test_helpers import PROJECT_ROOT, APP_JSX_PATH

TARGET_TICKERS = ["UBER", "FLNC", "MBLY", "UPST", "TSLA", "402340.KS", "ENPH", "CELH"]

CANONICAL_DIST_PATHS = [
    PROJECT_ROOT / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "special_watchlist_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "special_watchlist_data.json",
]


class TestF8SpecialWatchlist(unittest.TestCase):
    """E2E Test Suite for Feature 8 (Special Watchlist 8 Stocks & Timeline Tracking)."""

    def setUp(self):
        self.data_file = PROJECT_ROOT / "special_watchlist_data.json"
        self.dist_paths = CANONICAL_DIST_PATHS

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

    def _load_canonical_data(self):
        """Helper to load and validate root special_watchlist_data.json."""
        self.assertTrue(
            self.data_file.exists(),
            f"Missing canonical file at {self.data_file}. Backend data sync must generate this file."
        )
        with open(self.data_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        stocks = payload.get("stocks", payload) if isinstance(payload, dict) else payload
        self.assertIsInstance(stocks, list, "special_watchlist_data.json must contain a list of stock objects")
        return payload, stocks

    def test_f8_01_six_stocks_data_completeness_and_encoding(self):
        """
        [F8-01] Verifies that all 8 tickers (UBER, FLNC, MBLY, UPST, TSLA, 402340.KS, ENPH, CELH)
        exist in special_watchlist_data.json and have complete 5-dimension study fields
        without question mark ('??') encoding corruption.
        """
        _, stocks = self._load_canonical_data()
        self.assertGreaterEqual(
            len(stocks), 8,
            f"Must contain at least 8 special watchlist stocks, found {len(stocks)}"
        )

        found_map = {}
        for s in stocks:
            tk = s.get("ticker")
            if tk:
                found_map[tk] = s

        # Verify all 6 target tickers are present
        for expected in TARGET_TICKERS:
            self.assertIn(
                expected, found_map,
                f"Target ticker {expected} missing from special watchlist: {list(found_map.keys())}"
            )

        # 5-dimension deep study fields to check
        study_fields = [
            "business_model",
            "moat_analysis",
            "tam_growth_drivers",
            "financial_margins",
            "key_risks",
        ]

        for tk in TARGET_TICKERS:
            stock = found_map[tk]

            # 1. 5-dimension qualitative fields completeness & non-empty
            for field in study_fields:
                val = stock.get(field)
                self.assertIsNotNone(val, f"Stock {tk} missing mandatory field '{field}'")
                self.assertIsInstance(val, str, f"Stock {tk} field '{field}' must be a string")
                self.assertGreaterEqual(
                    len(val.strip()), 10,
                    f"Stock {tk} field '{field}' content too short or empty: '{val}'"
                )
                self.assertNotIn(
                    "??", val,
                    f"Stock {tk} has corrupted question marks ('??') in field '{field}': '{val}'"
                )

            # 2. General string fields UTF-8 Korean integrity (no '??')
            for k, v in stock.items():
                if isinstance(v, str):
                    self.assertNotIn(
                        "??", v,
                        f"Stock {tk} has corrupted question marks ('??') in field '{k}': '{v}'"
                    )

            # 3. Quantitative metrics verification
            current_price = stock.get("current_price")
            self.assertIsNotNone(current_price, f"Stock {tk} has NULL current_price")
            self.assertIsInstance(
                current_price, (int, float),
                f"Stock {tk} current_price must be numeric, got {type(current_price)}"
            )
            self.assertGreater(current_price, 0, f"Stock {tk} current_price must be > 0")

            mdd_pct = stock.get("mdd_pct")
            self.assertIsNotNone(mdd_pct, f"Stock {tk} has NULL mdd_pct")
            self.assertIsInstance(
                mdd_pct, (int, float),
                f"Stock {tk} mdd_pct must be numeric, got {type(mdd_pct)}"
            )

            buy_signal = stock.get("buy_signal")
            self.assertIsNotNone(buy_signal, f"Stock {tk} has NULL buy_signal")
            self.assertTrue(
                isinstance(buy_signal, str) and len(buy_signal.strip()) > 0,
                f"Stock {tk} has invalid or empty buy_signal: '{buy_signal}'"
            )

    def test_f8_02_time_series_timeline_deduplication_and_ordering(self):
        """
        [F8-02] Verifies that timeline entries for all 6 stocks are sorted reverse-chronologically
        (latest date first) and contain zero duplicate news_id / headline records.
        """
        _, stocks = self._load_canonical_data()
        found_map = {s.get("ticker"): s for s in stocks if s.get("ticker")}

        for tk in TARGET_TICKERS:
            self.assertIn(tk, found_map, f"Target ticker {tk} missing from data")
            stock = found_map[tk]
            timeline = stock.get("timeline", [])
            self.assertIsInstance(
                timeline, list,
                f"Stock {tk} timeline must be a list, got {type(timeline)}"
            )
            self.assertGreaterEqual(
                len(timeline), 2,
                f"Stock {tk} must have at least 2 timeline news records, found {len(timeline)}"
            )

            seen_ids = set()
            dates = []
            for idx, item in enumerate(timeline):
                self.assertIsInstance(
                    item, dict,
                    f"Stock {tk} timeline item [{idx}] must be a dict"
                )
                # Deduplication check: news_id or headline must be unique
                nid = item.get("news_id") or item.get("headline")
                self.assertIsNotNone(
                    nid,
                    f"Stock {tk} timeline item [{idx}] missing both news_id and headline"
                )
                self.assertNotIn(
                    nid, seen_ids,
                    f"Duplicate news item detected for {tk}: '{nid}'"
                )
                seen_ids.add(nid)

                # Required timeline item fields
                for req_key in ["publish_date", "headline", "source", "summary"]:
                    self.assertIn(
                        req_key, item,
                        f"Stock {tk} timeline item '{nid}' missing mandatory key '{req_key}'"
                    )
                    self.assertTrue(
                        item[req_key] and len(str(item[req_key]).strip()) > 0,
                        f"Stock {tk} timeline item '{nid}' has empty value for '{req_key}'"
                    )

                # Verify no encoding corruption in timeline
                for k, v in item.items():
                    if isinstance(v, str):
                        self.assertNotIn(
                            "??", v,
                            f"Stock {tk} timeline item '{nid}' has '??' in '{k}': '{v}'"
                        )

                publish_date = str(item.get("publish_date", "")).strip()
                dates.append(publish_date)

            # Check reverse-chronological order (latest date first)
            sorted_dates = sorted(dates, reverse=True)
            self.assertEqual(
                dates, sorted_dates,
                f"Timeline for {tk} is not in reverse-chronological order! Actual: {dates}, Expected: {sorted_dates}"
            )

    def test_f8_03_backend_api_endpoints_contract(self):
        """
        [F8-03] Verifies GET /api/v1/special-watchlist and POST /api/v1/special-watchlist/refresh
        contracts with HTTP 200, valid structure, and registered FastAPI routes.
        """
        app = self._get_app()
        from starlette.testclient import TestClient
        client = TestClient(app)

        # Verify route registration
        registered_routes = [route.path for route in app.routes]
        self.assertIn(
            "/api/v1/special-watchlist",
            registered_routes,
            f"GET /api/v1/special-watchlist route not registered. Available: {registered_routes}"
        )
        self.assertIn(
            "/api/v1/special-watchlist/refresh",
            registered_routes,
            f"POST /api/v1/special-watchlist/refresh route not registered. Available: {registered_routes}"
        )

        # 1. GET /api/v1/special-watchlist
        res_get = client.get("/api/v1/special-watchlist")
        self.assertEqual(
            res_get.status_code, 200,
            f"GET /api/v1/special-watchlist must return HTTP 200, got {res_get.status_code}: {res_get.text}"
        )
        data_get = res_get.json()
        stocks = data_get.get("stocks", data_get) if isinstance(data_get, dict) else data_get
        self.assertIsInstance(stocks, list, "API response must contain 'stocks' list")
        self.assertGreaterEqual(len(stocks), 8, "API must return at least 8 special watchlist stocks")

        returned_tickers = {s.get("ticker") for s in stocks if s.get("ticker")}
        for tk in TARGET_TICKERS:
            self.assertIn(tk, returned_tickers, f"GET endpoint response missing ticker '{tk}'")

        # 2. POST /api/v1/special-watchlist/refresh
        # Avoid long external yfinance network hangs during test by testing endpoint response
        res_post = client.post("/api/v1/special-watchlist/refresh")
        self.assertIn(
            res_post.status_code, (200, 201, 202),
            f"POST /api/v1/special-watchlist/refresh must return 200/201/202, got {res_post.status_code}: {res_post.text}"
        )
        data_post = res_post.json()
        self.assertTrue(
            isinstance(data_post, dict),
            f"POST refresh response must be a JSON object, got {type(data_post)}"
        )

    def test_f8_04_frontend_react_ui_and_trigger_contracts(self):
        """
        [F8-04] Verifies that App.jsx includes 'special-watchlist' view mode,
        navigation button for '특별 관심종목', and trigger string '시계열 외신 최신화 (특별 관심종목 돌려줘)'.
        """
        self.assertTrue(
            APP_JSX_PATH.exists(),
            f"Frontend file missing at {APP_JSX_PATH}"
        )
        content = APP_JSX_PATH.read_text(encoding="utf-8", errors="ignore")

        self.assertIn(
            "special-watchlist", content,
            "App.jsx must declare or handle 'special-watchlist' view mode"
        )
        self.assertIn(
            "특별 관심종목", content,
            "App.jsx must have '특별 관심종목' sidebar navigation item or header"
        )
        self.assertIn(
            "시계열 외신 최신화", content,
            "App.jsx must contain trigger button text '시계열 외신 최신화'"
        )
        self.assertIn(
            "특별 관심종목 돌려줘", content,
            "App.jsx must contain '(특별 관심종목 돌려줘)' trigger subtext or requirement keyword"
        )

    def test_f8_05_atomic_multi_target_json_distribution(self):
        """
        [F8-05] Verifies that special_watchlist_data.json exists across all 4 canonical paths:
        Root, Backend, Frontend Public, and Frontend Dist.
        """
        for p in self.dist_paths:
            self.assertTrue(
                p.exists(),
                f"Multi-target distribution copy missing at canonical path: {p}"
            )
            file_size = p.stat().st_size
            self.assertGreater(
                file_size, 500,
                f"Distribution copy at {p} is too small ({file_size} bytes), must be >= 500 bytes"
            )
            with open(p, "r", encoding="utf-8") as f:
                payload = json.load(f)
            stocks = payload.get("stocks", payload) if isinstance(payload, dict) else payload
            self.assertIsInstance(stocks, list, f"File at {p} must contain a list of stocks")
            self.assertGreaterEqual(
                len(stocks), 8,
                f"File at {p} must contain at least 8 stocks, found {len(stocks)}"
            )

    def test_f8_06_cli_runner_execution_contract(self):
        """
        [F8-06] Verifies that sync_special_watchlist.py exists at project root and defines run_sync.
        """
        cli_file = PROJECT_ROOT / "sync_special_watchlist.py"
        self.assertTrue(
            cli_file.exists(),
            f"CLI runner script missing at {cli_file}. R3 requires sync_special_watchlist.py."
        )

        # Import dynamically to verify syntax and interface contract
        spec = importlib.util.spec_from_file_location("sync_special_watchlist", str(cli_file))
        self.assertIsNotNone(spec, f"Could not create module spec from {cli_file}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            self.fail(f"Failed to import {cli_file}: {e}")

        self.assertTrue(
            hasattr(module, "run_sync"),
            "sync_special_watchlist.py must define 'run_sync' function for programmatic execution"
        )
        self.assertTrue(
            callable(getattr(module, "run_sync")),
            "'run_sync' in sync_special_watchlist.py must be callable"
        )


if __name__ == "__main__":
    unittest.main()
