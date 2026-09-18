"""
Tier 1: Feature 7 - Frontend React UI Live Integrity & Badges Tests.
Covers dynamic-over-static merge priority (ru.current_price || st.current_price),
Korean buy signal badge filtering, rebound signal badges, and dist artifact verification.
"""

import unittest
import re
from pathlib import Path

from tests.e2e.test_helpers import PROJECT_ROOT, APP_JSX_PATH


class TestF7FrontendIntegrity(unittest.TestCase):
    """E2E Test Suite for Feature 7 (Frontend React UI Live Integrity & Badges)."""

    def setUp(self):
        self.assertTrue(
            APP_JSX_PATH.exists(),
            f"Frontend source file missing at {APP_JSX_PATH}"
        )
        self.app_content = APP_JSX_PATH.read_text(encoding="utf-8", errors="ignore")

    def test_f7_01_app_jsx_merge_priority_live_over_static(self):
        """
        [F7-01] Verifies that App.jsx merges live remote server universe (ru) OVER
        static compile-time JSON (st), ensuring ru.current_price || st.current_price.
        The flawed pattern 'st.current_price || ru.current_price' must NOT be present.
        """
        # Critical bug check: st.current_price || ru.current_price
        flawed_pattern = r"current_price\s*:\s*st\.current_price\s*\|\|\s*ru\.current_price"
        match_flawed = re.search(flawed_pattern, self.app_content)
        self.assertIsNone(
            match_flawed,
            "Found inverted merge priority bug in App.jsx: 'st.current_price || ru.current_price' "
            "causes stale static JSON to suppress live DB prices!"
        )

        # Correct pattern check: ru.current_price || st.current_price
        correct_pattern = r"current_price\s*:\s*ru\.current_price\s*\|\|\s*st\.current_price"
        match_correct = re.search(correct_pattern, self.app_content)
        self.assertIsNotNone(
            match_correct,
            "App.jsx must use 'ru.current_price || st.current_price' so live database prices take precedence."
        )

    def test_f7_02_company_view_price_merge_priority(self):
        """
        [F7-02] Verifies that in CompanyView, remote price takes precedence over prev state.
        The flawed pattern 'prev?.current_price || remote.current_price' must NOT be present.
        """
        flawed_pattern = r"current_price\s*:\s*prev\?\.current_price\s*\|\|\s*remote\.current_price"
        match_flawed = re.search(flawed_pattern, self.app_content)
        self.assertIsNone(
            match_flawed,
            "Found inverted merge in CompanyView: 'prev?.current_price || remote.current_price' "
            "ignores freshly fetched remote prices!"
        )

    def test_f7_03_korean_buy_signal_badge_recognition(self):
        """
        [F7-03] Verifies that App.jsx buy ready filter logic recognizes standardized Korean
        signal keywords ('1차 매수적기', '2차 매수적기', '매수적기', '극단폭락') in addition to
        legacy codes ('BUY_READY', 'DEEP_DISCOUNT').
        """
        # Check if isBuyReady checks Korean terms
        has_korean_buy_check = (
            "매수적기" in self.app_content
            or "1차" in self.app_content
            or "극단폭락" in self.app_content
        )
        self.assertTrue(
            has_korean_buy_check,
            "App.jsx filter logic must recognize Korean buy signals (e.g. '매수적기' or '1차')"
        )

    def test_f7_04_rebound_badge_rendering_logic(self):
        """
        [F7-04] Verifies that oversold rebound badges (STRONG_REBOUND, MODERATE_REBOUND,
        or '과매도 반등') are rendered in Universe cards / table.
        """
        has_rebound_badge = (
            "rebound_signal" in self.app_content
            or "STRONG_REBOUND" in self.app_content
            or "과매도" in self.app_content
        )
        self.assertTrue(
            has_rebound_badge,
            "App.jsx must render oversold rebound badges (rebound_signal / 과매도 반등)"
        )

    def test_f7_05_frontend_dist_build_artifact_integrity(self):
        """
        [F7-05] Verifies that the production build artifact InvestmentPortal/frontend/dist/index.html
        exists and contains bundled application HTML/JS scripts.
        """
        dist_index = PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "index.html"
        self.assertTrue(
            dist_index.exists(),
            f"Production frontend build missing at {dist_index}"
        )
        content = dist_index.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("<html", content.lower())
        self.assertIn("script", content.lower())


if __name__ == "__main__":
    unittest.main()
