"""
Adversarial Stress Test Suite for Macro Intelligence FastAPI Endpoints
=======================================================================
Empirical Challenger M2:
1. High-concurrency burst: 12 concurrent workers issuing 60 rapid requests to /summary, /timeline, /indicators.
2. Race condition: Concurrent POST /refresh invalidation while continuous GET reader traffic.
3. DB lock simulation: Fallback to canonical JSON files under sqlite3.OperationalError without 500 errors.
4. Boundary query parameters: limit=0, limit=1000, negative limit, unknown source/sentiment, SQL injection strings.
5. Background vs Synchronous refresh handling.
6. Strict Pydantic schema validation across all responses under adversarial conditions.
"""

import os
import sys
import json
import time
import sqlite3
import unittest
import threading
import concurrent.futures
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
import main
import schemas
import sync_macro


class TestMacroFastAPIAdversarial(unittest.TestCase):
    """Adversarial stress tests for FastAPI Macro Intelligence endpoints."""

    def setUp(self):
        self.client = TestClient(main.app)

    # =========================================================================
    # 1. High Concurrency Burst Testing
    # =========================================================================

    def test_concurrent_api_burst_stress(self):
        """
        Adversarial Test 1:
        12 concurrent worker threads issuing 60 rapid interleaved requests across
        /summary, /timeline, and /indicators.
        Validates:
        - 100% 200 OK responses (zero 500s or thread race exceptions)
        - Thread-safe cache access without data corruption
        - Strict Pydantic schema compliance under concurrent execution
        """
        # Warm cache first to emulate production warm state
        prime_res = self.client.get("/api/v1/macro/summary")
        self.assertEqual(prime_res.status_code, 200)

        endpoints = [
            "/api/v1/macro/summary",
            "/api/macro/summary",
            "/api/v1/macro/timeline",
            "/api/macro/timeline",
            "/api/v1/macro/indicators",
            "/api/macro/indicators",
        ]
        num_workers = 12
        requests_per_worker = 5
        errors = []

        def worker_request(w_id: int):
            try:
                for req_i in range(requests_per_worker):
                    ep = endpoints[(w_id + req_i) % len(endpoints)]
                    res = self.client.get(ep)
                    if res.status_code != 200:
                        errors.append(f"Worker {w_id} got HTTP {res.status_code} for {ep}: {res.text}")
                        continue
                    data = res.json()
                    if data.get("status") != "success":
                        errors.append(f"Worker {w_id} got non-success status: {data}")
                        continue

                    # Validate schemas
                    if "summary" in ep:
                        schemas.MacroSummaryResponse(**data)
                    elif "timeline" in ep:
                        schemas.MacroTimelineResponse(**data)
                    elif "indicators" in ep:
                        schemas.MacroIndicatorsResponse(**data)
            except Exception as e:
                errors.append(f"Worker {w_id} exception: {type(e).__name__}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_request, i) for i in range(num_workers)]
            for f in concurrent.futures.as_completed(futures, timeout=45.0):
                f.result()

        self.assertEqual(len(errors), 0, f"Concurrency burst errors: {errors}")

    # =========================================================================
    # 2. Race Condition: Invalidation & Refresh Under Heavy Read Traffic
    # =========================================================================

    def test_concurrent_refresh_and_readers_race(self):
        """
        Adversarial Test 2:
        Race condition stress: 10 reader threads continuously querying endpoints while
        2 writer threads concurrently trigger POST /api/v1/macro/refresh.
        Validates:
        - Cache invalidation and re-hydration occurs without returning uninitialized/partial data.
        - Zero 500 errors during cache transitions.
        """
        errors = []
        stop_event = threading.Event()

        def reader_loop(r_id: int):
            try:
                while not stop_event.is_set():
                    res = self.client.get("/api/v1/macro/summary")
                    if res.status_code != 200:
                        errors.append(f"Reader {r_id} got {res.status_code}: {res.text}")
                        break
                    val = schemas.MacroSummaryResponse(**res.json())
                    if not val.regime:
                        errors.append(f"Reader {r_id} observed missing regime during cache invalidation")
                        break
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Reader {r_id} exception: {type(e).__name__}: {e}")

        def writer_loop(w_id: int):
            try:
                for _ in range(2):
                    res = self.client.post("/api/v1/macro/refresh", json={"force": False})
                    if res.status_code != 200:
                        errors.append(f"Writer {w_id} got {res.status_code}: {res.text}")
                        break
                    data = res.json()
                    if data.get("status") != "success":
                        errors.append(f"Writer {w_id} got non-success: {data}")
                        break
                    time.sleep(0.05)
            except Exception as e:
                errors.append(f"Writer {w_id} exception: {type(e).__name__}: {e}")

        reader_threads = [threading.Thread(target=reader_loop, args=(i,)) for i in range(10)]
        writer_threads = [threading.Thread(target=writer_loop, args=(j,)) for j in range(2)]

        for t in reader_threads:
            t.start()
        for t in writer_threads:
            t.start()

        for t in writer_threads:
            t.join(timeout=30.0)

        stop_event.set()
        for t in reader_threads:
            t.join(timeout=10.0)

        self.assertEqual(len(errors), 0, f"Race condition errors encountered: {errors}")

    # =========================================================================
    # 3. Database Lock Fallback Resilience
    # =========================================================================

    def test_db_lock_fallback_to_json(self):
        """
        Adversarial Test 3:
        Simulate persistent SQLite database lock (OperationalError: database is locked).
        Validates:
        - In-memory cache invalidation forces DB fetch attempt.
        - DB failure triggers graceful fallback to authoritative JSON files.
        - Endpoints return HTTP 200 OK with valid schema.
        """
        with patch("sync_macro.get_all_macro_data", side_effect=sqlite3.OperationalError("database is locked")):
            main._invalidate_macro_cache()

            # Test /summary fallback
            res_sum = self.client.get("/api/v1/macro/summary")
            self.assertEqual(res_sum.status_code, 200)
            data_sum = res_sum.json()
            self.assertEqual(data_sum.get("status"), "success")
            self.assertIsNotNone(data_sum.get("regime"))
            self.assertIsNotNone(data_sum.get("liquidity_metrics"))
            schemas.MacroSummaryResponse(**data_sum)

            # Test /timeline fallback
            res_tl = self.client.get("/api/v1/macro/timeline")
            self.assertEqual(res_tl.status_code, 200)
            data_tl = res_tl.json()
            self.assertEqual(data_tl.get("status"), "success")
            self.assertGreaterEqual(data_tl.get("total", 0), 10)
            schemas.MacroTimelineResponse(**data_tl)

            # Test /indicators fallback
            res_ind = self.client.get("/api/v1/macro/indicators")
            self.assertEqual(res_ind.status_code, 200)
            data_ind = res_ind.json()
            self.assertEqual(data_ind.get("status"), "success")
            self.assertIsNotNone(data_ind.get("indicators"))
            schemas.MacroIndicatorsResponse(**data_ind)

            # Test /refresh fallback behavior under DB lock
            res_ref = self.client.post("/api/v1/macro/refresh")
            self.assertEqual(res_ref.status_code, 200)
            data_ref = res_ref.json()
            self.assertEqual(data_ref.get("status"), "success")

    # =========================================================================
    # 4. Boundary & Adversarial Query Parameter Handling
    # =========================================================================

    def test_timeline_boundary_query_params(self):
        """
        Adversarial Test 4.1:
        Boundary conditions for /api/v1/macro/timeline query parameters:
        - limit=1000 (very large limit)
        - unknown source / unknown sentiment / unknown category
        - SQL injection strings and special characters
        """
        # Large limit (limit=1000)
        res_large = self.client.get("/api/v1/macro/timeline?limit=1000")
        self.assertEqual(res_large.status_code, 200)
        items_large = res_large.json().get("items", [])
        self.assertEqual(len(items_large), 10)

        # Non-existent source
        res_unk_src = self.client.get("/api/v1/macro/timeline?source=NON_EXISTENT_BANK")
        self.assertEqual(res_unk_src.status_code, 200)
        self.assertEqual(res_unk_src.json().get("total"), 0)
        self.assertEqual(len(res_unk_src.json().get("items")), 0)

        # Non-existent sentiment
        res_unk_sent = self.client.get("/api/v1/macro/timeline?sentiment=EXTREME_EUPHORIA")
        self.assertEqual(res_unk_sent.status_code, 200)
        self.assertEqual(res_unk_sent.json().get("total"), 0)
        self.assertEqual(len(res_unk_sent.json().get("items")), 0)

        # SQL Injection attempt in source query param
        res_sqli = self.client.get("/api/v1/macro/timeline?source=' OR '1'='1")
        self.assertEqual(res_sqli.status_code, 200)
        self.assertEqual(res_sqli.json().get("status"), "success")

        # Special chars and XSS attempts
        res_xss = self.client.get("/api/v1/macro/timeline?category=<script>alert('xss')</script>")
        self.assertEqual(res_xss.status_code, 200)
        self.assertEqual(res_xss.json().get("status"), "success")
        self.assertEqual(res_xss.json().get("total"), 0)

        # Whitespace-only source filter (should match nothing or trimmed)
        res_ws = self.client.get("/api/v1/macro/timeline?source=%20%20%20")
        self.assertEqual(res_ws.status_code, 200)

    def test_timeline_limit_zero_and_negative_behavior(self):
        """
        Adversarial Test 4.2:
        Investigate empirical behavior of limit=0 and negative limits.
        Confirms current non-fatal fallback behavior: limit <= 0 leaves items intact without crashing.
        """
        # When limit=0 is provided
        res_zero = self.client.get("/api/v1/macro/timeline?limit=0")
        self.assertEqual(res_zero.status_code, 200)
        data_zero = res_zero.json()
        self.assertEqual(data_zero.get("status"), "success")
        self.assertIsInstance(data_zero.get("items"), list)

        # When limit=-1 is provided
        res_neg = self.client.get("/api/v1/macro/timeline?limit=-1")
        self.assertEqual(res_neg.status_code, 200)
        data_neg = res_neg.json()
        self.assertEqual(data_neg.get("status"), "success")
        self.assertIsInstance(data_neg.get("items"), list)

    # =========================================================================
    # 5. Refresh Endpoint Method and Body Variations
    # =========================================================================

    def test_refresh_endpoint_robustness(self):
        """
        Adversarial Test 5:
        Test POST and GET /refresh with various payloads:
        - Empty JSON body: {}
        - Missing JSON body (None)
        - background=true
        - background=false, force=true
        """
        # POST with empty dict
        res_empty = self.client.post("/api/v1/macro/refresh", json={})
        self.assertEqual(res_empty.status_code, 200)
        self.assertEqual(res_empty.json().get("status"), "success")

        # POST with null/None body
        res_none = self.client.post("/api/v1/macro/refresh")
        self.assertEqual(res_none.status_code, 200)
        self.assertEqual(res_none.json().get("status"), "success")

        # Background task
        res_bg = self.client.post("/api/v1/macro/refresh", json={"background": True})
        self.assertEqual(res_bg.status_code, 200)
        self.assertEqual(res_bg.json().get("status"), "processing")

        # GET alias with query parameters
        res_get_alias = self.client.get("/api/macro/refresh?force=true")
        self.assertEqual(res_get_alias.status_code, 200)
        self.assertEqual(res_get_alias.json().get("status"), "success")


if __name__ == "__main__":
    unittest.main()
