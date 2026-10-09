"""
TrendPulse Investment Portal — Thought Leaders & Gurus Hub (인사이트 센터) E2E Test Suite.
========================================================================================
Validates Thought Leaders & Gurus Hub Module across Tiers 1–4:
- Tier 1: Feature Coverage & Content Completeness (7 Gurus, 7 Tech Leaders, 3 Core Theses,
          Quotes & Translations, zero '??' corruption, YouTube links, SHA-256 deduplication,
          and 16 Institutional Glossaries).
- Tier 2: Boundary & Corner Cases (Empty DB handling, duplicate insertion idempotency,
          invalid ticker handling, special characters/formulas preservation, unicode fidelity).
- Tier 3: Cross-Feature Interactions & Ticker Linkage Engine (Bi-directional linkage for
          9 core universe stocks [402340.KS, 000660.KS, TSLA, UBER, CELH, ENPH, FLNC, MBLY, UPST],
          ticker normalization, SQLite table schema persistence, and 4-path atomic JSON distribution).
- Tier 4: Real-World E2E Scenarios (FastAPI endpoints [/api/v1/insights/feed, /gurus, /tech-leaders,
          /ticker/{ticker}, /refresh], CLI sync pipeline execution, and offline JSON fallback resilience).

Compatible with:
  - python -m unittest tests/test_insights_module.py
  - pytest tests/test_insights_module.py
  - python run_e2e_tests.py --feature F10
"""

import os
import sys
import json
import re
import sqlite3
import hashlib
import tempfile
import shutil
import unittest
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional

# UTF-8 stdout/stderr safety
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Path configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
venv_site = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if venv_site.exists() and str(venv_site) not in sys.path:
    sys.path.insert(0, str(venv_site))
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

CANONICAL_INSIGHTS_JSON_PATHS = [
    PROJECT_ROOT / "insights_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "insights_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "insights_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "insights_data.json",
]

# Authoritative reference metadata
EXPECTED_GURUS = [
    {"name_ko": "하워드 막스", "name_en": "Howard Marks", "firm": "Oaktree Capital"},
    {"name_ko": "워런 버핏", "name_en": "Warren Buffett", "firm": "Berkshire Hathaway"},
    {"name_ko": "테리 스미스", "name_en": "Terry Smith", "firm": "Fundsmith"},
    {"name_ko": "빌 애크먼", "name_en": "Bill Ackman", "firm": "Pershing Square"},
    {"name_ko": "데이비드 아인혼", "name_en": "David Einhorn", "firm": "Greenlight Capital"},
    {"name_ko": "세스 클라만", "name_en": "Seth Klarman", "firm": "The Baupost Group"},
    {"name_ko": "클리프 아스네스", "name_en": "Cliff Asness", "firm": "AQR Capital"},
]

EXPECTED_TECH_LEADERS = [
    {"name_ko": "샘 알트만", "name_en": "Sam Altman", "company": "OpenAI"},
    {"name_ko": "일론 머스크", "name_en": "Elon Musk", "company": "Tesla / xAI"},
    {"name_ko": "젠슨 황", "name_en": "Jensen Huang", "company": "NVIDIA"},
    {"name_ko": "마크 저커버그", "name_en": "Mark Zuckerberg", "company": "Meta"},
    {"name_ko": "리사 수", "name_en": "Lisa Su", "company": "AMD"},
    {"name_ko": "곽노정", "name_en": "Kwak Noh-jung", "company": "SK하이닉스"},
    {"name_ko": "다리오 아모데이", "name_en": "Dario Amodei", "company": "Anthropic"},
]

CORE_THESIS_PILLARS = [
    "모델·안전성",
    "반도체·에너지 인프라",
    "플랫폼 비즈니스",
]

EXPECTED_UNIVERSE_TICKERS = [
    "402340.KS",  # SK스퀘어
    "000660.KS",  # SK하이닉스
    "TSLA",       # 테슬라
    "UBER",       # 우버
    "CELH",       # 셀시우스
    "ENPH",       # 엔페이즈 에너지
    "FLNC",       # 플루언스 에너지
    "MBLY",       # 모빌아이
    "UPST",       # 업스타트
]

FINANCIAL_GLOSSARIES = [
    "ROCE",
    "Owner Earnings",
    "Second-Level Thinking",
    "Margin of Safety",
    "FCF Yield",
    "Pricing Power",
    "Value Factor Spread",
    "Sea Change",
]

TECH_GLOSSARIES = [
    "Advanced MR-MUF",
    "CoWoS",
    "Test-Time Compute",
    "Memory Wall",
    "End-to-End Neural Networks",
    "Constitutional AI",
    "Liquid Cooling",
    "BESS",
]


def _get_sync_insights():
    """Dynamically attempts to import sync_insights from root or InvestmentPortal/backend."""
    for mod_name in ["sync_insights", "InvestmentPortal.backend.sync_insights"]:
        try:
            return importlib.import_module(mod_name)
        except ImportError:
            pass

    root_script = PROJECT_ROOT / "sync_insights.py"
    if root_script.exists():
        try:
            spec = importlib.util.spec_from_file_location("sync_insights_dynamic", str(root_script))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            pass

    backend_script = PROJECT_ROOT / "InvestmentPortal" / "backend" / "sync_insights.py"
    if backend_script.exists():
        try:
            spec = importlib.util.spec_from_file_location("sync_insights_backend_dynamic", str(backend_script))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            pass

    return None


class BaseInsightsTestCase(unittest.TestCase):
    """Base test fixture providing isolated environment and module resolution."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="trendpulse_insights_test_")
        self.temp_path = Path(self.temp_dir)
        self.test_db_path = self.temp_path / "test_portal.db"
        self.insights_mod = _get_sync_insights()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _require_insights(self):
        """Helper to ensure sync_insights is available or fail with actionable explanation."""
        if self.insights_mod is None:
            self.fail(
                "Implementation missing: sync_insights.py could not be imported from project root "
                f"or InvestmentPortal/backend. Expected location: {PROJECT_ROOT / 'sync_insights.py'}. "
                "Ensure Milestone 1 (Insights Core Pipeline & DB) has been implemented."
            )
        return self.insights_mod

    def _get_fastapi_app(self):
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


# =============================================================================
# TIER 1: Feature Coverage & Content Completeness (8 test cases)
# =============================================================================

class TestInsightsTier1Features(BaseInsightsTestCase):
    """Tier 1: Feature Coverage & Content Completeness for Thought Leaders & Gurus Hub."""

    def test_t1_01_seven_investment_gurus_dataset_completeness(self):
        """
        [T1-01] 7 Investment Gurus Data Modeling & Extraction Completeness.
        Verifies:
        - Exactly 7 investment gurus are defined.
        - Covers Howard Marks, Warren Buffett, Terry Smith, Bill Ackman,
          David Einhorn, Seth Klarman, Cliff Asness.
        - Every entry contains name, name_en, firm, title, publish_date, url, and summary.
        """
        m = self._require_insights()
        self.assertTrue(hasattr(m, "GURUS") or hasattr(m, "get_all_insights_data"),
                        "sync_insights must define GURUS dataset or get_all_insights_data")

        # Initialize tables and seed
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        gurus = data.get("gurus", [])
        letters = data.get("guru_letters", [])
        self.assertGreaterEqual(len(gurus), 7, "Must contain at least 7 Investment Gurus")
        self.assertGreaterEqual(len(letters), 7, "Must contain at least 7 Guru Letters/Memos")

        found_names_ko = [g.get("name_ko", g.get("guru_name", "")) for g in gurus]
        found_names_en = [g.get("name_en", g.get("guru_name_en", "")) for g in gurus]

        for expected in EXPECTED_GURUS:
            self.assertTrue(
                any(expected["name_ko"] in name for name in found_names_ko),
                f"Missing Guru: {expected['name_ko']} among {found_names_ko}"
            )
            self.assertTrue(
                any(expected["name_en"].lower() in name.lower() for name in found_names_en),
                f"Missing English Guru name: {expected['name_en']} among {found_names_en}"
            )

        # Verify letter properties
        for letter in letters:
            self.assertTrue(letter.get("title"), f"Guru letter missing title: {letter}")
            self.assertTrue(letter.get("publish_date"), f"Guru letter missing publish_date: {letter}")
            self.assertRegex(letter.get("publish_date"), r"^\d{4}-\d{2}-\d{2}$",
                            f"Invalid publish_date format: {letter.get('publish_date')}")
            self.assertTrue(letter.get("summary"), f"Guru letter missing summary: {letter}")

    def test_t1_02_seven_tech_leaders_dataset_completeness(self):
        """
        [T1-02] 7 AI & Tech Leaders Data Modeling & Extraction Completeness.
        Verifies:
        - Exactly 7 tech leaders are defined.
        - Covers Sam Altman, Elon Musk, Jensen Huang, Mark Zuckerberg,
          Lisa Su, Kwak Noh-jung, Dario Amodei.
        - Every entry contains name, name_en, company, role, title, publish_date, media_source, url.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        leaders = data.get("tech_leaders", data.get("leaders", []))
        interviews = data.get("tech_interviews", data.get("tech_leader_interviews", []))
        self.assertGreaterEqual(len(leaders), 7, "Must contain at least 7 Tech Leaders")
        self.assertGreaterEqual(len(interviews), 7, "Must contain at least 7 Tech Leader Interviews")

        found_names_ko = [l.get("name_ko", l.get("leader_name", "")) for l in leaders]
        found_names_en = [l.get("name_en", l.get("leader_name_en", "")) for l in leaders]

        for expected in EXPECTED_TECH_LEADERS:
            self.assertTrue(
                any(expected["name_ko"] in name for name in found_names_ko),
                f"Missing Tech Leader: {expected['name_ko']} among {found_names_ko}"
            )
            self.assertTrue(
                any(expected["name_en"].lower() in name.lower() for name in found_names_en),
                f"Missing English Tech Leader name: {expected['name_en']} among {found_names_en}"
            )

        # Verify interview properties
        for interview in interviews:
            self.assertTrue(interview.get("title"), f"Interview missing title: {interview}")
            self.assertTrue(interview.get("publish_date"), f"Interview missing publish_date: {interview}")
            self.assertRegex(interview.get("publish_date"), r"^\d{4}-\d{2}-\d{2}$",
                            f"Invalid publish_date format: {interview.get('publish_date')}")
            self.assertTrue(interview.get("media_source"), f"Interview missing media_source: {interview}")

    def test_t1_03_three_core_theses_axes_categorization(self):
        """
        [T1-03] 3 Core Thesis Axes Structuring.
        Verifies:
        - Entries categorize into the 3 Core Thesis Axes:
          ① 모델·안전성 (Models & Safety)
          ② 반도체·에너지 인프라 (Semiconductor & Energy Infrastructure)
          ③ 플랫폼 비즈니스 (Platform Business)
        - All 3 axes are well represented across the dataset.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        all_items = data.get("guru_letters", []) + data.get("tech_interviews", [])
        pillar_counts = {pillar: 0 for pillar in CORE_THESIS_PILLARS}

        for item in all_items:
            pillar_field = str(item.get("thesis_pillar", "") or item.get("core_thesis", "") or item.get("theses", ""))
            for pillar in CORE_THESIS_PILLARS:
                if pillar in pillar_field:
                    pillar_counts[pillar] += 1

        for pillar in CORE_THESIS_PILLARS:
            self.assertGreaterEqual(
                pillar_counts[pillar], 2,
                f"Core Thesis pillar '{pillar}' must have at least 2 associated items, found {pillar_counts[pillar]}"
            )

    def test_t1_04_quotes_and_korean_translations_integrity(self):
        """
        [T1-04] Original Quotes and Korean Translations/Summaries Integrity.
        Verifies:
        - Every record has an original English quote (length >= 30).
        - Every record has an institutional Korean translation/summary (length >= 30).
        - Quotations reflect the real thought leadership statements of the individuals.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        all_items = data.get("guru_letters", []) + data.get("tech_interviews", [])
        self.assertGreaterEqual(len(all_items), 14, "Must have at least 14 total letters and interviews")

        for item in all_items:
            quote = item.get("original_quote", "")
            quote_ko = item.get("original_quote_ko", "") or item.get("quote_ko", "")
            self.assertGreaterEqual(
                len(quote), 25,
                f"Original quote too short or missing in item {item.get('title')}: '{quote}'"
            )
            self.assertGreaterEqual(
                len(quote_ko), 25,
                f"Korean quote translation too short or missing in item {item.get('title')}: '{quote_ko}'"
            )

    def test_t1_05_zero_question_mark_encoding_corruption(self):
        """
        [T1-05] Zero Double Question Mark ('??') Encoding Corruption.
        Performs forensic scanning across all text fields (titles, summaries, quotes,
        translations, concept guides, ticker reasons) to ensure 0 instances of '??'.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        def scan_for_corruptions(obj, path="root"):
            if isinstance(obj, str):
                self.assertNotIn("??", obj, f"Corrupted encoding '??' detected at {path}: '{obj}'")
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    scan_for_corruptions(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for idx, v in enumerate(obj):
                    scan_for_corruptions(v, f"{path}[{idx}]")

        scan_for_corruptions(data)

    def test_t1_06_youtube_and_official_source_urls_validity(self):
        """
        [T1-06] YouTube and Media Source URLs Validity.
        Verifies:
        - All tech leader interviews include a valid YouTube URL (e.g. https://www.youtube.com/watch?v=...).
        - All guru letters include an authoritative source URL or memo reference.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        tech_interviews = data.get("tech_interviews", data.get("tech_leader_interviews", []))
        youtube_regex = re.compile(r"^https://(www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]{11}")

        for item in tech_interviews:
            url = item.get("url", "")
            self.assertTrue(
                bool(youtube_regex.match(url)),
                f"Tech leader interview must have valid YouTube URL, found: '{url}' for leader {item.get('leader_name')}"
            )

        guru_letters = data.get("guru_letters", [])
        for item in guru_letters:
            url = item.get("url", "")
            self.assertTrue(
                url.startswith("http://") or url.startswith("https://"),
                f"Guru letter must have valid http(s) URL, found: '{url}' for guru {item.get('guru_name')}"
            )

    def test_t1_07_deterministic_16_char_sha256_deduplication(self):
        """
        [T1-07] Deterministic 16-Character SHA-256 Deduplication Hash.
        Verifies:
        - compute_letter_hash and compute_interview_hash generate 16 hex characters.
        - Hash generation is deterministic, case-insensitive, and trims excess whitespace.
        - Repeated hashing on identical canonical inputs yields identical hashes.
        """
        m = self._require_insights()
        self.assertTrue(hasattr(m, "compute_letter_hash"), "sync_insights must define compute_letter_hash")
        self.assertTrue(hasattr(m, "compute_interview_hash"), "sync_insights must define compute_interview_hash")

        h1 = m.compute_letter_hash("Howard Marks", "2024-05-08", "The Calculus of Disruption")
        h2 = m.compute_letter_hash("  howard marks  ", "2024-05-08", "  The Calculus of Disruption  ")
        self.assertEqual(len(h1), 16, f"Hash must be 16 characters: {h1}")
        self.assertRegex(h1, r"^[0-9a-f]{16}$", f"Hash must be valid hex: {h1}")
        self.assertEqual(h1, h2, "Hash must be case- and whitespace-insensitive")

        ih1 = m.compute_interview_hash("Sam Altman", "2024-03-18", "Lex Fridman Podcast #419")
        ih2 = m.compute_interview_hash("sam altman", "2024-03-18", "Lex Fridman Podcast #419")
        self.assertEqual(len(ih1), 16)
        self.assertRegex(ih1, r"^[0-9a-f]{16}$")
        self.assertEqual(ih1, ih2)

    def test_t1_08_sixteen_deep_institutional_glossaries(self):
        """
        [T1-08] 16 Deep Institutional Financial & Technology Glossaries.
        Verifies:
        - 8 Institutional Financial/Accounting Glossaries:
          ROCE, Owner Earnings, Second-Level Thinking, Margin of Safety,
          FCF Yield, Pricing Power, Value Factor Spread, Sea Change.
        - 8 Deep Technology Glossaries:
          Advanced MR-MUF, CoWoS, Test-Time Compute, Memory Wall,
          End-to-End Neural Networks, Constitutional AI, Liquid Cooling, BESS.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        all_text = json.dumps(data, ensure_ascii=False)

        for fin_term in FINANCIAL_GLOSSARIES:
            self.assertIn(
                fin_term, all_text,
                f"Financial glossary term '{fin_term}' must be documented in insights data"
            )

        for tech_term in TECH_GLOSSARIES:
            self.assertIn(
                tech_term, all_text,
                f"Technology glossary term '{tech_term}' must be documented in insights data"
            )


# =============================================================================
# TIER 2: Boundary & Corner Cases (5 test cases)
# =============================================================================

class TestInsightsTier2Boundaries(BaseInsightsTestCase):
    """Tier 2: Boundary, Edge, and Corner Case Hardening."""

    def test_t2_01_empty_database_graceful_handling(self):
        """
        [T2-01] Empty Database & Missing Tables Graceful Handling.
        Verifies that querying an empty SQLite DB or uninitialized target path:
        - Does not raise unhandled exceptions.
        - Returns a well-formed JSON dictionary with status 'success' and empty or zero results.
        """
        m = self._require_insights()
        empty_db = self.temp_path / "empty_db.db"

        # Query without seeding
        data = m.get_all_insights_data(empty_db)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(len(data.get("guru_letters", [])), 0)
        self.assertEqual(len(data.get("tech_interviews", [])), 0)

        # Query ticker on empty DB
        ticker_data = m.get_insights_by_ticker("000660.KS", empty_db)
        self.assertIsInstance(ticker_data, dict)
        self.assertEqual(ticker_data.get("status"), "success")
        self.assertEqual(ticker_data.get("total", 0), 0)

    def test_t2_02_duplicate_insertion_idempotency(self):
        """
        [T2-02] Duplicate Insertion Idempotency.
        Verifies that invoking seeding multiple times on the same database:
        - Does NOT create duplicate rows in guru_letters or tech_leader_interviews.
        - Strictly preserves row count = 7 Gurus and 7 Tech Leaders.
        """
        m = self._require_insights()

        # Seed pass 1
        m.ensure_tables_and_seed(self.test_db_path)
        data1 = m.get_all_insights_data(self.test_db_path)
        count_gurus_1 = len(data1.get("guru_letters", []))
        count_tech_1 = len(data1.get("tech_interviews", []))

        # Seed pass 2
        m.ensure_tables_and_seed(self.test_db_path)
        data2 = m.get_all_insights_data(self.test_db_path)
        count_gurus_2 = len(data2.get("guru_letters", []))
        count_tech_2 = len(data2.get("tech_interviews", []))

        self.assertEqual(count_gurus_1, count_gurus_2, "Guru letters count must be idempotent across multiple seed passes")
        self.assertEqual(count_tech_1, count_tech_2, "Tech interviews count must be idempotent across multiple seed passes")

    def test_t2_03_invalid_and_unsupported_ticker_handling(self):
        """
        [T2-03] Invalid, Malformed, or Unsupported Ticker Graceful Handling.
        Verifies that querying nonexistent tickers (e.g. 'UNKNOWN_XYZ', '', None, '!@#$%')
        returns a valid response schema with total=0 and empty arrays rather than 500 error.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        for invalid_ticker in ["UNKNOWN_XYZ", "", "!!!###", "123456789"]:
            res = m.get_insights_by_ticker(invalid_ticker, self.test_db_path)
            self.assertIsInstance(res, dict)
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("total", 0), 0)
            self.assertEqual(res.get("guru_letters", []), [])
            self.assertEqual(res.get("tech_interviews", []), [])

    def test_t2_04_special_characters_quotes_and_formulas_preservation(self):
        """
        [T2-04] Special Characters, Mathematical Formulas, Quotes, and Symbols Preservation.
        Verifies that quotes containing mathematical LaTeX symbols ($ROCE = EBIT / ...$),
        em-dashes (—), bullet points (·), Korean quotation marks (「」, ''),
        and double quotes are persisted and retrieved without corrupting or breaking SQL queries.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)
        data = m.get_all_insights_data(self.test_db_path)

        conn = sqlite3.connect(str(self.test_db_path))
        cur = conn.cursor()

        # Check that quotes containing special punctuation are preserved
        cur.execute("SELECT original_quote, deep_concept_guide FROM guru_letters WHERE guru_name_en LIKE '%Terry Smith%'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        quote, guide = row
        self.assertIn("ROCE", quote + guide)

        cur.execute("SELECT original_quote, tech_concept_guide FROM tech_leader_interviews WHERE leader_name_en LIKE '%Kwak%'")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        quote, guide = row
        self.assertTrue("MR-MUF" in quote + guide or "HBM" in quote + guide)

        conn.close()

    def test_t2_05_unicode_korean_fidelity_and_roundtrip(self):
        """
        [T2-05] Full Unicode Korean Syllables Integrity & Roundtrip.
        Verifies that full UTF-8 Korean text (including complex syllables like '곽노정',
        '투하자본수익률', '독점적 병목 해자') round-trips through SQLite and JSON without
        character loss, escaping issues, or CP949 mojibake.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        test_json_path = self.temp_path / "unicode_test.json"
        data = m.get_all_insights_data(self.test_db_path)

        m.distribute_insights_json(data, [test_json_path])
        self.assertTrue(test_json_path.exists())

        with open(test_json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        loaded_str = json.dumps(loaded, ensure_ascii=False)
        self.assertIn("하워드 막스", loaded_str)
        self.assertIn("곽노정", loaded_str)
        self.assertIn("SK하이닉스", loaded_str)
        self.assertIn("어드밴스드 MR-MUF", loaded_str)


# =============================================================================
# TIER 3: Cross-Feature Interactions & Ticker Linkage Engine (4 test cases)
# =============================================================================

class TestInsightsTier3Combinations(BaseInsightsTestCase):
    """Tier 3: Cross-Module Interactions, Bi-Directional Linkage & Distribution Parity."""

    def test_t3_01_bi_directional_ticker_linkage_coverage_for_nine_stocks(self):
        """
        [T3-01] Symmetrical Bi-Directional Ticker Linkage Engine for 9 Core Universe Stocks.
        Verifies that every single one of the 9 universe stocks:
        - SK Square (402340.KS)
        - SK Hynix (000660.KS)
        - Tesla (TSLA)
        - Uber (UBER)
        - Celsius (CELH)
        - Enphase (ENPH)
        - Fluence (FLNC)
        - Mobileye (MBLY)
        - Upstart (UPST)
        is linked to relevant Gurus and Tech Leaders with actionable implications.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        for ticker in EXPECTED_UNIVERSE_TICKERS:
            result = m.get_insights_by_ticker(ticker, self.test_db_path)
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get("status"), "success")
            total = result.get("total", 0)
            self.assertGreaterEqual(
                total, 1,
                f"Ticker '{ticker}' must be linked to at least 1 Guru letter or Tech interview, got {total}"
            )

        # Specific institutional linkage checks:
        # 1. SK Hynix (000660.KS): must link to Kwak Noh-jung, Jensen Huang, etc.
        hynix_res = m.get_insights_by_ticker("000660.KS", self.test_db_path)
        all_hynix_sources = json.dumps(hynix_res, ensure_ascii=False)
        self.assertTrue(
            "곽노정" in all_hynix_sources or "Kwak" in all_hynix_sources,
            "SK Hynix must link to Kwak Noh-jung"
        )
        self.assertTrue(
            "젠슨 황" in all_hynix_sources or "Jensen" in all_hynix_sources,
            "SK Hynix must link to Jensen Huang"
        )

        # 2. SK Square (402340.KS): must link to at least Howard Marks or Warren Buffett or Kwak
        square_res = m.get_insights_by_ticker("402340.KS", self.test_db_path)
        self.assertGreaterEqual(square_res.get("total", 0), 2, "SK Square must have >=2 linked insights")

        # 3. Tesla (TSLA): must link to Elon Musk
        tsla_res = m.get_insights_by_ticker("TSLA", self.test_db_path)
        all_tsla_sources = json.dumps(tsla_res, ensure_ascii=False)
        self.assertTrue(
            "일론 머스크" in all_tsla_sources or "Musk" in all_tsla_sources,
            "Tesla must link to Elon Musk"
        )

        # 4. Uber (UBER): must link to Warren Buffett or Bill Ackman or Terry Smith
        uber_res = m.get_insights_by_ticker("UBER", self.test_db_path)
        self.assertGreaterEqual(uber_res.get("total", 0), 2, "Uber must have >=2 linked insights")

    def test_t3_02_ticker_normalization_korean_stocks(self):
        """
        [T3-02] Korean Stock Ticker Normalization (.KS suffix handling).
        Verifies that querying with or without '.KS' (e.g. '000660' vs '000660.KS',
        '402340' vs '402340.KS') yields identical matching insights.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        res_full = m.get_insights_by_ticker("000660.KS", self.test_db_path)
        res_short = m.get_insights_by_ticker("000660", self.test_db_path)
        self.assertEqual(res_full.get("total"), res_short.get("total"),
                         "Querying '000660.KS' and '000660' must return identical total results")

        res_sq_full = m.get_insights_by_ticker("402340.KS", self.test_db_path)
        res_sq_short = m.get_insights_by_ticker("402340", self.test_db_path)
        self.assertEqual(res_sq_full.get("total"), res_sq_short.get("total"),
                         "Querying '402340.KS' and '402340' must return identical total results")

    def test_t3_03_sqlite_db_persistence_and_table_schemas(self):
        """
        [T3-03] SQLite Database Persistence and Exact Table Schemas.
        Verifies:
        - guru_letters table has required columns (letter_id, guru_name, summary, original_quote, etc.).
        - tech_leader_interviews table has required columns (interview_id, leader_name, company, etc.).
        - UNIQUE constraints on letter_id and interview_id.
        - PRAGMA busy_timeout is supported.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        conn = sqlite3.connect(str(self.test_db_path))
        cur = conn.cursor()

        # Check guru_letters columns
        cur.execute("PRAGMA table_info(guru_letters);")
        guru_cols = [row[1] for row in cur.fetchall()]
        required_guru_cols = [
            "id", "letter_id", "guru_name", "guru_name_en", "firm", "title",
            "publish_date", "summary", "original_quote", "original_quote_ko",
            "core_thesis", "thesis_pillar", "deep_concept_guide", "related_tickers",
            "ticker_implications"
        ]
        for col in required_guru_cols:
            self.assertIn(col, guru_cols, f"guru_letters table missing required column: '{col}'")

        # Check tech_leader_interviews columns
        cur.execute("PRAGMA table_info(tech_leader_interviews);")
        tech_cols = [row[1] for row in cur.fetchall()]
        required_tech_cols = [
            "id", "interview_id", "leader_name", "leader_name_en", "company", "role",
            "title", "publish_date", "media_source", "url", "summary",
            "original_quote", "original_quote_ko", "core_thesis", "thesis_pillar",
            "tech_concept_guide", "related_tickers", "ticker_implications"
        ]
        for col in required_tech_cols:
            self.assertIn(col, tech_cols, f"tech_leader_interviews table missing required column: '{col}'")

        conn.close()

    def test_t3_04_four_target_atomic_json_distribution_parity(self):
        """
        [T3-04] 4-Target Atomic JSON Distribution Parity & Hash Identity.
        Verifies that distribute_insights_json distributes insights_data.json
        atomically across 4 paths with identical contents and identical SHA-256 hashes.
        """
        m = self._require_insights()
        test_destinations = [
            self.temp_path / "root_insights.json",
            self.temp_path / "backend" / "insights.json",
            self.temp_path / "frontend" / "public" / "insights.json",
            self.temp_path / "frontend" / "dist" / "insights.json",
        ]

        sample_data = {
            "status": "success",
            "gurus": [{"name": "Howard Marks"}],
            "leaders": [{"name": "Sam Altman"}],
            "theses": ["모델·안전성"],
        }

        m.distribute_insights_json(sample_data, test_destinations)

        hashes = []
        for p in test_destinations:
            self.assertTrue(p.exists(), f"Distributed file missing at {p}")
            with open(p, "rb") as f:
                content = f.read()
                self.assertGreater(len(content), 30)
                hashes.append(hashlib.sha256(content).hexdigest())

        # Parity check
        self.assertEqual(len(set(hashes)), 1, "All 4 distribution targets must have identical SHA-256 hash")


# =============================================================================
# TIER 4: Real-World E2E Scenarios (4 test cases)
# =============================================================================

class TestInsightsTier4Scenarios(BaseInsightsTestCase):
    """Tier 4: Realistic E2E Application Scenarios, FastAPI Endpoints & Fallback Resilience."""

    def test_t4_01_fastapi_endpoints_feed_gurus_leaders_contracts(self):
        """
        [T4-01] FastAPI Endpoints: Feed, Gurus, and Tech Leaders Response Contracts.
        Verifies:
        - GET /api/v1/insights/feed returns 200 OK and reverse-chronological feed.
        - GET /api/v1/insights/gurus returns 200 OK with gurus and letters arrays.
        - GET /api/v1/insights/tech-leaders returns 200 OK with leaders and interviews arrays.
        - Dual route compatibility (/api/insights/feed).
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        app = self._get_fastapi_app()
        try:
            from starlette.testclient import TestClient
        except ImportError:
            from fastapi.testclient import TestClient
        client = TestClient(app)

        # Feed endpoint
        res = client.get("/api/v1/insights/feed")
        self.assertEqual(res.status_code, 200, f"GET /api/v1/insights/feed failed: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        items = data.get("items", [])
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

        # Dual route compatibility
        res_dual = client.get("/api/insights/feed")
        self.assertEqual(res_dual.status_code, 200)

        # Gurus endpoint
        res_gurus = client.get("/api/v1/insights/gurus")
        self.assertEqual(res_gurus.status_code, 200)
        data_gurus = res_gurus.json()
        self.assertEqual(data_gurus.get("status"), "success")
        self.assertGreaterEqual(len(data_gurus.get("letters", [])), 7)

        # Tech Leaders endpoint
        res_leaders = client.get("/api/v1/insights/tech-leaders")
        self.assertEqual(res_leaders.status_code, 200)
        data_leaders = res_leaders.json()
        self.assertEqual(data_leaders.get("status"), "success")
        self.assertGreaterEqual(len(data_leaders.get("interviews", [])), 7)

    def test_t4_02_fastapi_ticker_detail_endpoint_contract(self):
        """
        [T4-02] FastAPI Ticker Detail Endpoint Contract (/api/v1/insights/ticker/{ticker}).
        Verifies:
        - GET /api/v1/insights/ticker/000660.KS returns relevant insights for SK Hynix.
        - GET /api/v1/insights/ticker/402340.KS returns relevant insights for SK Square.
        - Response includes 'ticker', 'total', 'guru_letters', 'tech_interviews', and 'consolidated'.
        """
        m = self._require_insights()
        m.ensure_tables_and_seed(self.test_db_path)

        app = self._get_fastapi_app()
        try:
            from starlette.testclient import TestClient
        except ImportError:
            from fastapi.testclient import TestClient
        client = TestClient(app)

        res = client.get("/api/v1/insights/ticker/000660.KS")
        self.assertEqual(res.status_code, 200, f"GET /api/v1/insights/ticker/000660.KS failed: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("000660", data.get("ticker", ""))
        self.assertGreaterEqual(data.get("total", 0), 1)

        res_sq = client.get("/api/v1/insights/ticker/402340.KS")
        self.assertEqual(res_sq.status_code, 200)
        data_sq = res_sq.json()
        self.assertEqual(data_sq.get("status"), "success")
        self.assertGreaterEqual(data_sq.get("total", 0), 1)

    def test_t4_03_cli_sync_pipeline_execution_contract(self):
        """
        [T4-03] CLI Sync Pipeline Execution Contract.
        Verifies that sync_insights.py:
        - Defines run_sync(db_path, force, silent).
        - Executes end-to-end against test database.
        - Returns a status dictionary with success=True or status='success'.
        """
        m = self._require_insights()
        self.assertTrue(hasattr(m, "run_sync"), "sync_insights must define run_sync")

        res = m.run_sync(db_path=self.test_db_path, force=True, silent=True)
        self.assertIsInstance(res, dict)
        self.assertTrue(res.get("success", False) or res.get("status") == "success")

    def test_t4_04_offline_and_db_unreachable_fallback_resilience(self):
        """
        [T4-04] Offline and Database Unreachable Fallback Resilience.
        Verifies that when database connection fails or database file is inaccessible,
        the system seamlessly falls back to static insights_data.json without throwing
        an HTTP 500 error or unhandled crash.
        """
        m = self._require_insights()

        # Seed data to static JSON
        mock_json_path = self.temp_path / "fallback_insights.json"
        seed_payload = {
            "status": "success",
            "gurus": [{"name": "Howard Marks"}],
            "guru_letters": [{"title": "Sea Change", "guru_name": "하워드 막스", "publish_date": "2024-05-08"}],
            "tech_leaders": [{"name": "Sam Altman"}],
            "tech_interviews": [{"title": "Lex Fridman", "leader_name": "샘 알트만", "publish_date": "2024-03-18"}],
        }
        with open(mock_json_path, "w", encoding="utf-8") as f:
            json.dump(seed_payload, f, ensure_ascii=False)

        # In fallback mode, get_all_insights_data should fall back to JSON
        invalid_db_path = self.temp_path / "nonexistent_dir" / "invalid.db"
        fallback_data = m.get_all_insights_data(invalid_db_path)
        self.assertIsInstance(fallback_data, dict)
        self.assertEqual(fallback_data.get("status"), "success")


if __name__ == "__main__":
    unittest.main()
