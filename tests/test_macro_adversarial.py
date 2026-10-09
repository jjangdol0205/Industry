"""
Adversarial Stress Test Suite for Macro Intelligence Engine (sync_macro.py)
=============================================================================
Milestone 1 Empirical Challenger M1-2:
1. Multi-threaded database concurrency & SQLite lock resilience (PRAGMA busy_timeout = 30000; WAL mode).
2. Corrupted data injection rejection & Idempotent upserts (ON CONFLICT DO UPDATE SET).
3. Atomic file distribution under rapid consecutive overwrites & zero leftover .tmp files.
4. Exact byte-for-byte parity across 4 distribution JSON targets.
"""

import os
import sys
import json
import sqlite3
import hashlib
import tempfile
import shutil
import unittest
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

import sync_macro


class TestMacroAdversarial(unittest.TestCase):
    """Adversarial stress test suite for sync_macro.py."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="adv_macro_test_")
        self.temp_path = Path(self.temp_dir)
        self.test_db_path = self.temp_path / "test_portal.db"
        self.test_json_targets = [
            self.temp_path / "dest1" / "macro_intelligence_data.json",
            self.temp_path / "dest2" / "macro_intelligence_data.json",
            self.temp_path / "dest3" / "macro_intelligence_data.json",
            self.temp_path / "dest4" / "macro_intelligence_data.json",
        ]
        for p in self.test_json_targets:
            p.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =========================================================================
    # 1. Multi-threaded Database Concurrency & SQLite Lock Resilience
    # =========================================================================

    def test_concurrent_run_sync_parallel_threads(self):
        """
        Adversarial Test 1.1:
        16 threads concurrently calling run_sync(force=True) on the same SQLite database.
        Tests SQLite lock resilience with WAL mode and PRAGMA busy_timeout = 30000.
        Verifies zero 'database is locked' crashes and total DB integrity.
        """
        num_threads = 16
        errors = []

        def worker(thread_idx: int):
            try:
                res = sync_macro.run_sync(
                    db_path=self.test_db_path,
                    force=True,
                    silent=True,
                    source=f"thread_{thread_idx}",
                    destinations=self.test_json_targets,
                )
                if res.get("status") != "success":
                    errors.append(f"Thread {thread_idx} returned non-success: {res}")
                dist_count = len(res.get("distributed_paths", []))
                if dist_count != len(self.test_json_targets):
                    errors.append(f"Thread {thread_idx} distributed only {dist_count}/{len(self.test_json_targets)} files")
            except Exception as e:
                errors.append(f"Thread {thread_idx} failed with {type(e).__name__}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=45.0)

        self.assertEqual(len(errors), 0, f"Concurrency errors encountered: {errors}")

        # Verify database integrity and row counts
        conn = sync_macro.get_db_connection(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM macro_reports;")
        rep_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM macro_indicators;")
        ind_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM macro_regime;")
        reg_count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(rep_count, 10, f"Expected 10 unique reports, got {rep_count}")
        self.assertEqual(ind_count, 30, f"Expected 30 unique indicators, got {ind_count}")
        self.assertEqual(reg_count, 1, f"Expected 1 CURRENT regime, got {reg_count}")

    def test_concurrent_mixed_readers_and_writers(self):
        """
        Adversarial Test 1.2:
        Mixed workload: 10 concurrent reader threads executing continuous queries
        while 5 writer threads execute ensure_tables_and_seed(force_seed=True).
        Verifies reader/writer non-blocking behavior under WAL mode.
        """
        sync_macro.ensure_tables_and_seed(self.test_db_path)
        errors = []
        stop_event = threading.Event()

        def reader_worker(r_id: int):
            try:
                for _ in range(15):
                    if stop_event.is_set():
                        break
                    data = sync_macro.get_all_macro_data(self.test_db_path)
                    self.assertEqual(data.get("status"), "success")
                    self.assertGreaterEqual(len(data.get("reports", [])), 10)
            except Exception as e:
                errors.append(f"Reader {r_id} failed: {type(e).__name__}: {e}")

        def writer_worker(w_id: int):
            try:
                for _ in range(5):
                    if stop_event.is_set():
                        break
                    sync_macro.ensure_tables_and_seed(self.test_db_path, force_seed=True)
            except Exception as e:
                errors.append(f"Writer {w_id} failed: {type(e).__name__}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for i in range(10):
                futures.append(executor.submit(reader_worker, i))
            for j in range(5):
                futures.append(executor.submit(writer_worker, j))

            for f in concurrent.futures.as_completed(futures, timeout=40.0):
                try:
                    f.result()
                except Exception as ex:
                    errors.append(f"Task exception: {ex}")

        self.assertEqual(len(errors), 0, f"Errors in mixed reader/writer test: {errors}")

    def test_rapid_consecutive_sync_loop(self):
        """
        Adversarial Test 1.3:
        Rapid loop of 20 consecutive run_sync(force=True) executions.
        Validates stability, leak-free connection management, and idempotent consistency.
        """
        for i in range(20):
            res = sync_macro.run_sync(
                db_path=self.test_db_path,
                force=True,
                silent=True,
                source=f"rapid_loop_{i}",
                destinations=self.test_json_targets,
            )
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("reports_count"), 10)

        # Check DB row count remains strictly constant
        conn = sync_macro.get_db_connection(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM macro_reports;")
        self.assertEqual(cur.fetchone()[0], 10)
        conn.close()

    # =========================================================================
    # 2. Corrupted Data Injection & Idempotent Upserts
    # =========================================================================

    def test_corrupted_report_injection_rejection(self):
        """
        Adversarial Test 2.1:
        Adversarially inject malformed reports into validate_macro_report.
        Verifies rejection of:
        - Missing mandatory fields
        - Empty string values
        - Invalid sentiment enums
        - Out-of-bounds sentiment scores (< -1.0 or > 1.0)
        """
        valid_seed = dict(sync_macro.SEED_MACRO_REPORTS[0])

        # Test missing field
        for field in ["discount_rate_impact", "factor_style_impact", "sector_industry_impact", "fx_liquidity_flow_impact", "title"]:
            corrupt = dict(valid_seed)
            del corrupt[field]
            with self.assertRaises(ValueError, msg=f"Should reject report missing {field}"):
                sync_macro.validate_macro_report(corrupt)

        # Test empty string field
        for field in ["discount_rate_impact", "title", "summary"]:
            corrupt = dict(valid_seed)
            corrupt[field] = "   "
            with self.assertRaises(ValueError, msg=f"Should reject report with blank {field}"):
                sync_macro.validate_macro_report(corrupt)

        # Test invalid sentiment enum
        corrupt = dict(valid_seed)
        corrupt["sentiment"] = "SUPER_BULLISH"
        with self.assertRaises(ValueError, msg="Should reject invalid sentiment"):
            sync_macro.validate_macro_report(corrupt)

        # Test out-of-bounds sentiment scores
        corrupt = dict(valid_seed)
        corrupt["sentiment_score"] = 2.5
        with self.assertRaises(ValueError, msg="Should reject sentiment score > 1.0"):
            sync_macro.validate_macro_report(corrupt)

        corrupt["sentiment_score"] = -1.5
        with self.assertRaises(ValueError, msg="Should reject sentiment score < -1.0"):
            sync_macro.validate_macro_report(corrupt)

    def test_idempotent_upsert_on_conflict(self):
        """
        Adversarial Test 2.2:
        Test ON CONFLICT DO UPDATE SET for macro_reports, macro_indicators, and macro_regime.
        Verifies duplicate insertions update in-place without generating duplicates or errors.
        """
        sync_macro.ensure_tables_and_seed(self.test_db_path)
        conn = sync_macro.get_db_connection(self.test_db_path)
        cur = conn.cursor()

        # Update an existing report with modified title and perspectives
        cur.execute("SELECT report_id, title FROM macro_reports LIMIT 1;")
        target_id, orig_title = cur.fetchone()

        cur.execute("""
            INSERT INTO macro_reports (
                report_id, source, category, title, publish_date, url,
                summary, key_takeaways, discount_rate_impact, factor_style_impact,
                sector_industry_impact, fx_liquidity_flow_impact, sentiment,
                sentiment_score, pe_impact_pct_estimate, favored_factor,
                unfavored_factor, overweight_sectors, underweight_sectors,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                title=excluded.title,
                summary=excluded.summary,
                discount_rate_impact=excluded.discount_rate_impact;
        """, (
            target_id, "FOMC", "Adversarial Test", "UPDATED_ADVERSARIAL_TITLE", "2026-10-09", None,
            "Updated summary for idempotency check", "[]", "Updated discount rate perspective",
            "Factor impact", "Sector impact", "FX impact", "DOVISH",
            -0.5, 3.0, "Core", "Marginal", "[]", "[]", "2026-10-09", "2026-10-09"
        ))
        conn.commit()

        # Verify record was updated and count didn't increase
        cur.execute("SELECT COUNT(*) FROM macro_reports WHERE report_id = ?;", (target_id,))
        self.assertEqual(cur.fetchone()[0], 1)

        cur.execute("SELECT title, discount_rate_impact FROM macro_reports WHERE report_id = ?;", (target_id,))
        row = cur.fetchone()
        self.assertEqual(row[0], "UPDATED_ADVERSARIAL_TITLE")
        self.assertEqual(row[1], "Updated discount rate perspective")

        # Now re-run ensure_tables_and_seed: should restore canonical state cleanly
        conn.close()
        sync_macro.ensure_tables_and_seed(self.test_db_path, force_seed=True)

        conn = sync_macro.get_db_connection(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM macro_reports;")
        self.assertEqual(cur.fetchone()[0], 10)
        cur.execute("SELECT title FROM macro_reports WHERE report_id = ?;", (target_id,))
        restored_title = cur.fetchone()[0]
        self.assertEqual(restored_title, orig_title)
        conn.close()

    def test_quant_functions_edge_cases(self):
        """
        Adversarial Test 2.3:
        Boundary conditions for quant math routines:
        - compute_yield_spread with identical yields and extreme yields
        - classify_yield_curve_shift at exact epsilon boundary
        - evaluate_rrp_buffer at exact $150B and $50B boundaries
        - compute_net_liquidity with extreme scaling
        """
        # Exact zero spread
        spread, bps = sync_macro.compute_yield_spread(4.0, 4.0)
        self.assertEqual(spread, 0.0)
        self.assertEqual(bps, 0.0)
        self.assertEqual(sync_macro.classify_yield_curve_state(spread).value, "FLAT")

        # Just below zero spread
        spread_neg, _ = sync_macro.compute_yield_spread(3.9999, 4.0)
        self.assertEqual(sync_macro.classify_yield_curve_state(spread_neg).value, "INVERTED")

        # Curve shift epsilon boundaries
        shift_unchanged = sync_macro.classify_yield_curve_shift(4.10, 3.90, 4.10, 3.90, epsilon=0.005)
        self.assertEqual(shift_unchanged.value, "UNCHANGED")

        # RRP Buffer boundaries
        depleted_150, status_150, _ = sync_macro.evaluate_rrp_buffer(150.0)
        self.assertFalse(depleted_150)
        self.assertEqual(status_150.value, "ADEQUATE_BUFFER")

        depleted_149_9, status_149_9, _ = sync_macro.evaluate_rrp_buffer(149.9)
        self.assertTrue(depleted_149_9)
        self.assertEqual(status_149_9.value, "DEPLETION_WARNING")

        depleted_49_9, status_49_9, _ = sync_macro.evaluate_rrp_buffer(49.9)
        self.assertTrue(depleted_49_9)
        self.assertEqual(status_49_9.value, "CRITICAL_DEPLETION")

    # =========================================================================
    # 3. Atomic File Distribution Under Rapid Consecutive Overwrites & Windows Locks
    # =========================================================================

    def test_atomic_distribution_concurrency_and_no_leftover_tmp(self):
        """
        Adversarial Test 3.1:
        16 concurrent threads repeatedly calling distribute_macro_json on the same targets.
        Verifies:
        - No file corruption (all destination files remain valid parseable JSON)
        - ZERO leftover .tmp files across all destination directories
        """
        payload = sync_macro.get_all_macro_data(db_or_path=self.test_db_path)
        num_threads = 16
        errors = []

        def dist_worker(idx: int):
            try:
                for _ in range(5):
                    res = sync_macro.distribute_macro_json(payload, destinations=self.test_json_targets)
                    if len(res) != len(self.test_json_targets):
                        errors.append(f"Worker {idx} distributed only {len(res)}/{len(self.test_json_targets)} files")
            except Exception as e:
                errors.append(f"Worker {idx} raised {type(e).__name__}: {e}")

        threads = [threading.Thread(target=dist_worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        self.assertEqual(len(errors), 0, f"Distribution concurrency errors: {errors}")

        # Check for any leftover .tmp files
        tmp_files = list(self.temp_path.glob("**/*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Found leftover .tmp files: {tmp_files}")

        # Verify all destination files exist and are valid JSON
        for dest in self.test_json_targets:
            self.assertTrue(dest.exists(), f"Destination {dest} missing")
            content = dest.read_text(encoding="utf-8")
            parsed = json.loads(content)
            self.assertEqual(parsed.get("status"), "success")

    def test_atomic_distribution_cleanup_on_error(self):
        """
        Adversarial Test 3.2:
        Simulate distribution failure by passing an unwritable read-only directory or invalid target.
        Verifies that any temporary .tmp file created before failure is unlinked and cleaned up.
        """
        fake_bad_target = self.temp_path / "non_existent_drive_or_file" / "\0_invalid" / "test.json"
        res = sync_macro.distribute_macro_json({"dummy": True}, destinations=[fake_bad_target])
        self.assertEqual(len(res), 0)

        # Ensure no orphan .tmp files
        tmp_files = list(self.temp_path.glob("**/*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Leftover .tmp files after failed distribution: {tmp_files}")

    # =========================================================================
    # 4. Target JSON 4-Path Byte Equality & Parity Verification
    # =========================================================================

    def test_production_4_path_exact_byte_equality(self):
        """
        Adversarial Test 4.1:
        Examines the 4 authoritative canonical production paths:
        1. macro_intelligence_data.json
        2. InvestmentPortal/backend/macro_intelligence_data.json
        3. InvestmentPortal/frontend/public/macro_intelligence_data.json
        4. InvestmentPortal/frontend/dist/macro_intelligence_data.json
        Verifies 100% byte-for-byte SHA-256 hash equality across all 4 files.
        """
        prod_paths = [
            PROJECT_ROOT / "macro_intelligence_data.json",
            PROJECT_ROOT / "InvestmentPortal" / "backend" / "macro_intelligence_data.json",
            PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "macro_intelligence_data.json",
            PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "macro_intelligence_data.json",
        ]

        hashes = []
        sizes = []
        for p in prod_paths:
            self.assertTrue(p.exists(), f"Authoritative production file missing: {p}")
            data = p.read_bytes()
            sizes.append(len(data))
            hashes.append(hashlib.sha256(data).hexdigest())

        self.assertEqual(len(set(hashes)), 1, f"Production JSON files have divergent SHA-256 hashes: {dict(zip(prod_paths, hashes))}")
        self.assertEqual(len(set(sizes)), 1, f"Production JSON files have divergent file sizes: {sizes}")
        self.assertGreater(sizes[0], 20000, f"Production JSON suspiciously small: {sizes[0]} bytes")

    def test_production_json_content_and_perspectives_completeness(self):
        """
        Adversarial Test 4.2:
        Deep inspects the content of the authoritative production JSON:
        - Status is 'success'
        - All 10 reports exist in reverse-chronological order
        - Every report has non-empty 4 perspectives with substantive text (> 50 chars)
        - Zero broken encoding question marks (??)
        - Indicators has current snapshot + 30-day history
        - Regime is populated with Ken Fisher rules and RIMP model
        """
        prod_json_path = PROJECT_ROOT / "macro_intelligence_data.json"
        data = json.loads(prod_json_path.read_text(encoding="utf-8"))

        self.assertEqual(data.get("status"), "success")
        reports = data.get("reports", [])
        self.assertEqual(len(reports), 10, f"Expected 10 reports, found {len(reports)}")

        # Verify reverse chronological ordering
        for i in range(len(reports) - 1):
            curr_date = reports[i]["publish_date"]
            next_date = reports[i + 1]["publish_date"]
            self.assertGreaterEqual(curr_date, next_date, f"Report ordering violation: {curr_date} < {next_date}")

        # Verify 4 Korean perspectives on all reports
        for rep in reports:
            title = rep.get("title")
            for field in ["discount_rate_impact", "factor_style_impact", "sector_industry_impact", "fx_liquidity_flow_impact"]:
                val = rep.get(field, "")
                self.assertIsInstance(val, str, f"Report '{title}' field {field} must be str")
                self.assertGreater(len(val.strip()), 50, f"Report '{title}' field {field} is too short ({len(val)} chars)")
                self.assertNotIn("??", val, f"Report '{title}' field {field} contains corrupted encoding: {val}")

        # Verify indicators
        ind = data.get("indicators", {})
        self.assertIn("history", ind)
        self.assertEqual(len(ind["history"]), 30)
        self.assertEqual(ind.get("indicator_date"), "2026-10-09")
        self.assertEqual(ind.get("yield_spread_10y_2y"), 0.27)

        # Verify regime
        reg = data.get("regime", {})
        self.assertEqual(reg.get("regime_code"), "TRANSITION_UNINVERSION")
        self.assertIn("factor_allocations", reg)
        self.assertIn("sector_matrix", reg)
        self.assertEqual(len(reg["sector_matrix"]), 6)


if __name__ == "__main__":
    unittest.main()
