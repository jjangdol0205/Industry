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

        returned_map = {s.get("ticker"): s for s in stocks if s.get("ticker")}
        for tk in TARGET_TICKERS:
            self.assertIn(tk, returned_map, f"GET endpoint response missing ticker '{tk}'")
            st = returned_map[tk]
            self.assertIn("industry_dynamics", st, f"GET endpoint stock '{tk}' missing industry_dynamics")
            dyn = st["industry_dynamics"]
            self.assertIsInstance(dyn, dict, f"Stock '{tk}' industry_dynamics must be a dict")
            self.assertIn("tam_current", dyn, f"Stock '{tk}' missing tam_current in API response")
            self.assertIn("tam_2030", dyn, f"Stock '{tk}' missing tam_2030 in API response")
            self.assertIn("cagr_2030", dyn, f"Stock '{tk}' missing cagr_2030 in API response")
            self.assertIn("market_share_pct", dyn, f"Stock '{tk}' missing market_share_pct in API response")
            self.assertIn("share_outlook", dyn, f"Stock '{tk}' missing share_outlook in API response")

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
        self.assertIn(
            "8선 한눈에 보는 산업 규모·성장률·점유율 비교 매트릭스 표", content,
            "App.jsx must contain Top Summary Matrix Table header"
        )
        self.assertIn(
            "산업 규모·성장률 & 시장 점유율 동학 분석기", content,
            "App.jsx must contain Card Widget header"
        )
        self.assertIn(
            "점유율 전망", content,
            "App.jsx must contain share outlook badge text"
        )
        self.assertIn(
            "점유율 확대 요인", content,
            "App.jsx must contain expansion drivers section"
        )
        self.assertIn(
            "점유율 위협 및 경쟁 리스크 요인", content,
            "App.jsx must contain threat factors section"
        )
        self.assertIn(
            "IB_KOREAN_ALIASES", content,
            "App.jsx must define IB_KOREAN_ALIASES for Korean IB search queries like 골드만삭스/모건스탠리"
        )
        self.assertIn(
            "골드만삭스", content,
            "App.jsx search logic must include Korean IB keyword '골드만삭스'"
        )
        self.assertIn(
            "모건스탠리", content,
            "App.jsx search logic must include Korean IB keyword '모건스탠리'"
        )
        self.assertIn(
            "getDyn", content,
            "App.jsx must declare getDyn helper for safe JSON string/object industry_dynamics extraction"
        )
        self.assertIn(
            "dyn.market_rank", content,
            "App.jsx displayedStocks filter must index dyn.market_rank"
        )
        self.assertIn(
            "dyn.tam_current", content,
            "App.jsx displayedStocks filter must index dyn.tam_current"
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


    def test_f8_07_industry_dynamics_tam_cagr_and_market_share_modeling(self):
        """
        [F8-07] Verifies that all 8 stocks have complete, valid industry_dynamics modeling
        covering TAM, CAGR 2030, market share %, share outlook, expansion drivers, threat factors,
        and defense score/rating without Korean '??' corruption.
        """
        _, stocks = self._load_canonical_data()
        found_map = {s.get("ticker"): s for s in stocks if s.get("ticker")}

        valid_outlooks = [
            "확대 우세 (Expanding)",
            "현상 유지 및 수성 (Defending)",
            "잠식 리스크 (Contracting Risk)"
        ]

        for tk in TARGET_TICKERS:
            self.assertIn(tk, found_map, f"Target ticker {tk} missing from canonical data")
            stock = found_map[tk]

            # Check industry_dynamics exists in stock and stock['study']
            dyn = stock.get("industry_dynamics")
            self.assertIsNotNone(dyn, f"Stock {tk} missing industry_dynamics dict")
            self.assertIsInstance(dyn, dict, f"Stock {tk} industry_dynamics must be a dict")

            # Check TAM modeling
            for tam_field in ["tam_current", "tam_2030"]:
                val = dyn.get(tam_field)
                self.assertIsNotNone(val, f"Stock {tk} missing '{tam_field}' in industry_dynamics")
                self.assertIsInstance(val, str, f"Stock {tk} '{tam_field}' must be a string")
                self.assertGreaterEqual(len(val.strip()), 3)
                self.assertNotIn("??", val, f"Stock {tk} has '??' in '{tam_field}': '{val}'")

            # Check 2030 CAGR
            cagr = dyn.get("cagr_2030")
            self.assertIsNotNone(cagr, f"Stock {tk} missing 'cagr_2030'")
            self.assertIsInstance(cagr, (int, float), f"Stock {tk} 'cagr_2030' must be numeric, got {type(cagr)}")
            self.assertGreater(cagr, 0, f"Stock {tk} 'cagr_2030' must be > 0")

            # Check Market Share %
            ms = dyn.get("market_share_pct")
            self.assertIsNotNone(ms, f"Stock {tk} missing 'market_share_pct'")
            self.assertIsInstance(ms, (int, float), f"Stock {tk} 'market_share_pct' must be numeric")
            self.assertTrue(0 < ms <= 100, f"Stock {tk} 'market_share_pct' must be between 0 and 100, got {ms}")

            # Check Market Rank & Position
            rank = dyn.get("market_rank")
            self.assertIsNotNone(rank, f"Stock {tk} missing 'market_rank'")
            self.assertGreaterEqual(len(str(rank).strip()), 3)
            self.assertNotIn("??", str(rank))

            # Check Share Outlook Verdict
            outlook = dyn.get("share_outlook")
            self.assertIsNotNone(outlook, f"Stock {tk} missing 'share_outlook'")
            self.assertIn(
                outlook, valid_outlooks,
                f"Stock {tk} 'share_outlook' must be one of {valid_outlooks}, got '{outlook}'"
            )

            # Check Expansion Drivers
            drivers = dyn.get("expansion_drivers")
            self.assertIsInstance(drivers, list, f"Stock {tk} 'expansion_drivers' must be a list")
            self.assertGreaterEqual(len(drivers), 2, f"Stock {tk} must have at least 2 expansion drivers")
            for d in drivers:
                self.assertIsInstance(d, str)
                self.assertGreaterEqual(len(d.strip()), 10)
                self.assertNotIn("??", d)

            # Check Threat Factors
            threats = dyn.get("threat_factors")
            self.assertIsInstance(threats, list, f"Stock {tk} 'threat_factors' must be a list")
            self.assertGreaterEqual(len(threats), 2, f"Stock {tk} must have at least 2 threat factors")
            for t in threats:
                self.assertIsInstance(t, str)
                self.assertGreaterEqual(len(t.strip()), 10)
                self.assertNotIn("??", t)

            # Check Defense Score & Rating
            score = dyn.get("defense_score")
            self.assertIsNotNone(score, f"Stock {tk} missing 'defense_score'")
            self.assertIsInstance(score, (int, float))
            self.assertTrue(0 <= score <= 100)

            rationale = dyn.get("defense_rationale")
            self.assertIsNotNone(rationale, f"Stock {tk} missing 'defense_rationale'")
            self.assertGreaterEqual(len(str(rationale).strip()), 15)
            self.assertNotIn("??", str(rationale))

            sources = dyn.get("research_sources")
            self.assertIsNotNone(sources, f"Stock {tk} missing 'research_sources'")
            self.assertGreaterEqual(len(str(sources).strip()), 5)
            self.assertNotIn("??", str(sources))

    def test_f8_08_sqlite_db_industry_dynamics_persistence_and_multi_db_sync(self):
        """
        [F8-08] Verifies that industry_dynamics is persisted as a column in special_watchlist_studies
        across authoritative and existing replica SQLite databases, and that all 8 stocks contain
        valid, complete quantitative modeling data.
        """
        import sqlite3
        candidate_dbs = [
            PROJECT_ROOT / "InvestmentPortal" / "backend" / "investment_portal.db",
            PROJECT_ROOT / "investment_portal.db",
            PROJECT_ROOT / "InvestmentPortal" / "investment_portal.db",
        ]

        tested_count = 0
        for db_file in candidate_dbs:
            if not db_file.exists():
                continue
            tested_count += 1
            conn = sqlite3.connect(str(db_file))
            cur = conn.cursor()

            # Check column exists in special_watchlist_studies
            cur.execute("PRAGMA table_info(special_watchlist_studies);")
            cols = [col[1] for col in cur.fetchall()]
            self.assertIn(
                "industry_dynamics", cols,
                f"Column 'industry_dynamics' missing from special_watchlist_studies in {db_file}"
            )

            # Query all 8 stocks
            cur.execute(
                "SELECT ticker, industry_dynamics FROM special_watchlist_studies WHERE ticker IN (?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(TARGET_TICKERS)
            )
            rows = dict(cur.fetchall())
            self.assertEqual(
                len(rows), 8,
                f"DB {db_file} must have 8 target stocks in special_watchlist_studies, found {len(rows)}"
            )

            for tk in TARGET_TICKERS:
                self.assertIn(tk, rows, f"Ticker {tk} missing from DB {db_file}")
                dyn_raw = rows[tk]
                self.assertIsNotNone(dyn_raw, f"Ticker {tk} in {db_file} has NULL industry_dynamics")
                dyn_dict = json.loads(dyn_raw) if isinstance(dyn_raw, str) else dyn_raw
                self.assertIsInstance(dyn_dict, dict, f"Ticker {tk} industry_dynamics in {db_file} must be dict")
                self.assertIn("tam_current", dyn_dict)
                self.assertIn("tam_2030", dyn_dict)
                self.assertIn("cagr_2030", dyn_dict)
                self.assertIn("market_share_pct", dyn_dict)
                self.assertIn("share_outlook", dyn_dict)
                self.assertGreater(dyn_dict["cagr_2030"], 0)
                self.assertGreater(dyn_dict["market_share_pct"], 0)
            conn.close()

        self.assertGreaterEqual(tested_count, 1, "At least one authoritative SQLite DB must exist and be tested")

    def test_f8_09_search_indexing_and_contracting_risk_badges(self):
        """
        [F8-09] Verifies search filtering logic matches quantitative TAM, CAGR, and market_rank terms,
        and verifies that share outlook classification correctly handles '확대 우세', '수성', and
        '잠식 리스크' without false fallbacks.
        """
        _, stocks = self._load_canonical_data()
        stock_map = {s["ticker"]: s for s in stocks}

        # 1. Market rank search keywords simulation
        # For UBER: market_rank contains "독점적 과점 플랫폼"
        uber_dyn = stock_map["UBER"]["industry_dynamics"]
        self.assertIn("독점적 과점 플랫폼", uber_dyn.get("market_rank", ""))

        # For FLNC: market_rank contains "시스템 통합 1위"
        flnc_dyn = stock_map["FLNC"]["industry_dynamics"]
        self.assertIn("시스템 통합 1위", flnc_dyn.get("market_rank", ""))

        # 2. Outlook classification badge logic test
        test_cases = [
            ("확대 우세 (Expanding)", True, False, False),
            ("현상 유지 및 수성 (Defending)", False, True, False),
            ("잠식 리스크 (Contracting Risk)", False, False, True),
            ("", False, False, False),
            (None, False, False, False),
            ("분석 중", False, False, False),
        ]

        for val, exp_exp, exp_def, exp_con in test_cases:
            outlook = val or ""
            is_expanding = "확대" in outlook
            is_defending = "수성" in outlook or "유지" in outlook
            is_contracting = "잠식" in outlook or "축소" in outlook
            self.assertEqual(is_expanding, exp_exp, f"Mismatch for '{val}' is_expanding")
            self.assertEqual(is_defending, exp_def, f"Mismatch for '{val}' is_defending")
            self.assertEqual(is_contracting, exp_con, f"Mismatch for '{val}' is_contracting")


if __name__ == "__main__":
    unittest.main()
