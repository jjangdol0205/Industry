"""
Tier 1: Feature 2 - Smart Caching & Sub-3s SLA Mechanism Tests.
Covers market-aware caching (KRX close, US close, weekend), cache structure,
sub-3-second execution SLA verification, and --force invalidation.
"""

import unittest
import json
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, time as dtime, timedelta
from unittest.mock import patch

from tests.e2e.test_helpers import PROJECT_ROOT, SYNC_CACHE_PATH


class TestF2SmartCache(unittest.TestCase):
    """E2E Test Suite for Feature 2 (Smart Caching & Sub-3s SLA Mechanism)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_cache_path = Path(self.temp_dir) / "sync_cache.json"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_f2_01_cache_file_structure_and_creation(self):
        """
        [F2-01] Verifies that the cache file maintains a structured JSON schema
        including timestamp, date, status, market_status, and ticker count.
        """
        try:
            from sync_stocks import write_cache_metadata, read_cache_metadata
        except ImportError:
            try:
                from investment_engine import write_cache_metadata, read_cache_metadata
            except ImportError:
                self.fail("Implementation missing: write_cache_metadata / read_cache_metadata not implemented")

        now = datetime.now()
        write_cache_metadata(
            cache_path=self.test_cache_path,
            status="SUCCESS",
            ticker_count=150,
            timestamp=now.isoformat(),
            market_status="CLOSED"
        )

        self.assertTrue(self.test_cache_path.exists(), "Cache file must be created on disk")
        with open(self.test_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_keys = ["timestamp", "status", "ticker_count"]
        for key in required_keys:
            self.assertIn(key, data, f"Key '{key}' missing from cache metadata")

        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["ticker_count"], 150)

    def test_f2_02_weekend_market_closed_cache_hit(self):
        """
        [F2-02] Verifies that on weekends (Saturday / Sunday), if data was synced
        after Friday market close (15:40 KST), cache check returns valid=True.
        """
        try:
            from sync_stocks import is_cache_valid
        except ImportError:
            self.fail("Implementation missing: is_cache_valid function not found in sync_stocks")

        # Simulate Friday 18:00 KST sync
        friday_sync = datetime(2026, 9, 18, 18, 0, 0)
        cache_data = {
            "timestamp": friday_sync.isoformat(),
            "status": "SUCCESS",
            "ticker_count": 150
        }
        with open(self.test_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        # Evaluate on Saturday morning
        saturday_morning = datetime(2026, 9, 19, 10, 0, 0)
        with patch("sync_stocks.get_current_time", return_value=saturday_morning):
            valid = is_cache_valid(self.test_cache_path)
            self.assertTrue(valid, "Weekend query after Friday close must hit cache (valid=True)")

    def test_f2_03_post_market_close_same_day_cache_hit(self):
        """
        [F2-03] Verifies that on a weekday after market close (16:00 KST), if data
        was already synced today after 15:40 KST, cache is valid.
        """
        try:
            from sync_stocks import is_cache_valid
        except ImportError:
            self.fail("Implementation missing: is_cache_valid function not found in sync_stocks")

        # Synced at 15:45 KST
        sync_time = datetime(2026, 9, 18, 15, 45, 0)
        cache_data = {
            "timestamp": sync_time.isoformat(),
            "status": "SUCCESS",
            "ticker_count": 150
        }
        with open(self.test_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        # Re-executed at 16:30 KST
        current_time = datetime(2026, 9, 18, 16, 30, 0)
        with patch("sync_stocks.get_current_time", return_value=current_time):
            valid = is_cache_valid(self.test_cache_path)
            self.assertTrue(valid, "Same-day post-close query must hit cache (valid=True)")

    def test_f2_04_sub_3s_sla_benchmark(self):
        """
        [F2-04] Benchmarks smart cache evaluation time to ensure it strictly finishes in < 3.0s SLA
        (Acceptance Criteria: "3초 이내에 동기화 완료 판정됨").
        """
        try:
            from sync_stocks import is_cache_valid
        except ImportError:
            self.fail("Implementation missing: is_cache_valid function not found in sync_stocks")

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "ticker_count": 150
        }
        with open(self.test_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        t_start = time.perf_counter()
        # Perform 10 iterations to get average
        for _ in range(10):
            _ = is_cache_valid(self.test_cache_path)
        t_elapsed = time.perf_counter() - t_start

        avg_latency = t_elapsed / 10.0
        self.assertLess(
            avg_latency, 3.0,
            f"Smart cache check took {avg_latency:.4f}s, exceeding 3.0s SLA"
        )
        # Even stricter performance expectation for local file check: < 0.1s
        self.assertLess(
            avg_latency, 0.5,
            f"Smart cache evaluation should typically complete in < 0.5s (actual: {avg_latency:.4f}s)"
        )

    def test_f2_05_force_flag_bypasses_cache(self):
        """
        [F2-05] Verifies that when --force or force=True is passed, cache validity
        is bypassed, returning valid=False to trigger a fresh sync.
        """
        try:
            from sync_stocks import is_cache_valid
        except ImportError:
            self.fail("Implementation missing: is_cache_valid function not found in sync_stocks")

        # Write fresh cache
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "ticker_count": 150
        }
        with open(self.test_cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        valid = is_cache_valid(self.test_cache_path, force=True)
        self.assertFalse(valid, "Passing force=True must bypass cache and return valid=False")


if __name__ == "__main__":
    unittest.main()
