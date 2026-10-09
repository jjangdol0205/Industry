"""
TrendPulse Investment Portal — Macro Intelligence API Test Suite.
=================================================================
Validates Milestone 2 FastAPI endpoints, query filtering, caching,
fallback resilience, and schema contracts in InvestmentPortal/backend/main.py.

Usage:
  d:\\Industry\\.venv\\Scripts\\python.exe -m unittest tests/test_macro_api.py
"""

import os
import sys
import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

import sync_macro
from fastapi.testclient import TestClient
import main
import schemas


class TestMacroAPIEndpoints(unittest.TestCase):
    """Test suite for /api/v1/macro/* and /api/macro/* endpoints."""

    def setUp(self):
        self.client = TestClient(main.app)

    def test_01_macro_summary_contract_and_alias(self):
        """[API-01] GET /api/v1/macro/summary and alias /api/macro/summary."""
        for path in ["/api/v1/macro/summary", "/api/macro/summary"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Endpoint {path} failed: {res.text}")
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIn("regime", data)
            self.assertIn("ken_fisher_signal", data)
            self.assertIn("per_multiple_outlook", data)
            self.assertIn("policy_stance", data)
            self.assertIn("liquidity_metrics", data)
            self.assertIn("net_liquidity_billion", data["liquidity_metrics"])
            self.assertIn("tga_balance_billion", data["liquidity_metrics"])
            self.assertIn("on_rrp_balance_billion", data["liquidity_metrics"])
            # Validate schema
            validated = schemas.MacroSummaryResponse(**data)
            self.assertEqual(validated.status, "success")

    def test_02_macro_timeline_contract_and_alias(self):
        """[API-02] GET /api/v1/macro/timeline and alias /api/macro/timeline."""
        for path in ["/api/v1/macro/timeline", "/api/macro/timeline"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Endpoint {path} failed: {res.text}")
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIsInstance(data.get("items"), list)
            self.assertGreaterEqual(data.get("total", 0), 1)
            # Verify 4 perspectives
            first_report = data["items"][0]
            for field in [
                "report_id", "source", "category", "title", "summary",
                "discount_rate_impact", "factor_style_impact",
                "sector_industry_impact", "fx_liquidity_flow_impact", "sentiment"
            ]:
                self.assertIn(field, first_report)
            validated = schemas.MacroTimelineResponse(**data)
            self.assertEqual(validated.status, "success")

    def test_03_macro_timeline_filtering(self):
        """[API-03] GET /api/v1/macro/timeline multi-criteria query filtering."""
        # 1. Source filter
        res_fomc = self.client.get("/api/v1/macro/timeline?source=FOMC")
        self.assertEqual(res_fomc.status_code, 200)
        items_fomc = res_fomc.json().get("items", [])
        for it in items_fomc:
            self.assertIn("fomc", it["source"].lower())

        # 2. Sentiment filter
        res_dovish = self.client.get("/api/v1/macro/timeline?sentiment=DOVISH")
        self.assertEqual(res_dovish.status_code, 200)
        items_dovish = res_dovish.json().get("items", [])
        for it in items_dovish:
            self.assertEqual(it["sentiment"].upper(), "DOVISH")

        # 3. Limit filter
        res_limit = self.client.get("/api/v1/macro/timeline?limit=2")
        self.assertEqual(res_limit.status_code, 200)
        items_limit = res_limit.json().get("items", [])
        self.assertLessEqual(len(items_limit), 2)

    def test_04_macro_indicators_contract_and_alias(self):
        """[API-04] GET /api/v1/macro/indicators and alias /api/macro/indicators."""
        for path in ["/api/v1/macro/indicators", "/api/macro/indicators"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Endpoint {path} failed: {res.text}")
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIn("indicators", data)
            self.assertIn("history", data)
            ind = data["indicators"]
            self.assertIn("us_10y_yield", ind)
            self.assertIn("us_2y_yield", ind)
            self.assertIn("yield_spread_10y_2y", ind)
            self.assertIn("net_liquidity_billion", ind)
            self.assertIn("on_rrp_buffer_status", ind)
            self.assertIsInstance(data["history"], list)
            self.assertGreaterEqual(len(data["history"]), 1)
            validated = schemas.MacroIndicatorsResponse(**data)
            self.assertEqual(validated.status, "success")

    def test_05_macro_refresh_post_and_aliases(self):
        """[API-05] POST /api/v1/macro/refresh and GET aliases."""
        for method, path in [
            ("post", "/api/v1/macro/refresh"),
            ("post", "/api/macro/refresh"),
            ("get", "/api/v1/macro/refresh"),
            ("get", "/api/macro/refresh"),
        ]:
            caller = getattr(self.client, method)
            res = caller(path)
            self.assertEqual(res.status_code, 200, f"{method.upper()} {path} failed: {res.text}")
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIn("summary", data)

    def test_06_in_memory_caching_behavior(self):
        """[API-06] In-memory cache returns cached dict without hitting DB repeatedly."""
        # Prime cache
        res1 = self.client.get("/api/v1/macro/summary")
        t1 = res1.json().get("updated_at")

        # Second call immediately should return identical updated_at
        res2 = self.client.get("/api/v1/macro/summary")
        t2 = res2.json().get("updated_at")
        self.assertEqual(t1, t2)

    def test_07_four_path_json_fallback_resilience(self):
        """[API-07] Endpoints return 200 via 4-path JSON fallback when DB raises error."""
        with patch("sync_macro.get_all_macro_data", side_effect=Exception("Database lock simulation")):
            main._invalidate_macro_cache()
            res = self.client.get("/api/v1/macro/summary")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("status"), "success")
            self.assertIsNotNone(data.get("regime"))

    def test_08_refresh_background_mode(self):
        """[API-08] POST /api/v1/macro/refresh with background=true."""
        res = self.client.post("/api/v1/macro/refresh", json={"background": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "processing")


if __name__ == "__main__":
    unittest.main()
