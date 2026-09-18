"""
E2E Test Helpers & Fixtures for TrendPulse Investment Portal.
Provides isolated database setups, mock historical data generators,
and path constants for E2E testing.
"""

import os
import sys
import json
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))

# Canonical file path constants
AUTHORITATIVE_DB_PATH = PROJECT_ROOT / "InvestmentPortal" / "backend" / "investment_portal.db"
UNIVERSE_EVALUATED_PATHS = [
    PROJECT_ROOT / "universe_evaluated.json",
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "universe_evaluated.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "universe_evaluated.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "universe_evaluated.json",
]
UNIVERSAL_DEEPDIVE_PATHS = [
    PROJECT_ROOT / "InvestmentPortal" / "backend" / "universal_deepdive_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "public" / "universal_deepdive_data.json",
    PROJECT_ROOT / "InvestmentPortal" / "frontend" / "dist" / "universal_deepdive_data.json",
]
SYNC_CACHE_PATH = PROJECT_ROOT / "sync_cache.json"
SILENT_VBS_PATH = PROJECT_ROOT / "scripts" / "run_sync_silent.vbs"
INSTALL_TASK_BAT_PATH = PROJECT_ROOT / "scripts" / "install_silent_task.bat"
INSTALL_TASK_PS1_PATH = PROJECT_ROOT / "scripts" / "install_silent_task.ps1"
RUN_BAT_PATH = PROJECT_ROOT / "run.bat"
RUN_PS1_PATH = PROJECT_ROOT / "run.ps1"
MAIN_PY_PATH = PROJECT_ROOT / "InvestmentPortal" / "backend" / "main.py"
APP_JSX_PATH = PROJECT_ROOT / "InvestmentPortal" / "frontend" / "src" / "App.jsx"


def create_isolated_test_db(db_path: Path) -> sqlite3.Connection:
    """
    Creates a SQLite database with the exact schema matching InvestmentPortal models.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS industry_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            summary TEXT,
            file_path TEXT,
            tag TEXT DEFAULT '일반'
        );

        CREATE TABLE IF NOT EXISTS value_chain_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            industry_id INTEGER,
            node_name TEXT,
            description TEXT,
            FOREIGN KEY (industry_id) REFERENCES industry_reports(id)
        );

        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            industry_id INTEGER,
            value_chain_node_id INTEGER,
            name TEXT,
            ticker TEXT,
            role_description TEXT,
            future_growth TEXT,
            display_order INTEGER DEFAULT 999,
            portfolio_tier TEXT DEFAULT 'Standard',
            principle_reason TEXT,
            FOREIGN KEY (industry_id) REFERENCES industry_reports(id),
            FOREIGN KEY (value_chain_node_id) REFERENCES value_chain_nodes(id)
        );

        CREATE TABLE IF NOT EXISTS company_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER UNIQUE,
            sector TEXT,
            industry_classification TEXT,
            description TEXT,
            description_ko TEXT,
            ceo TEXT,
            employees INTEGER,
            website TEXT,
            market_cap REAL,
            current_price REAL,
            high_52w REAL,
            mdd_pct REAL,
            buy_signal TEXT,
            dca_stage TEXT,
            moat_score REAL,
            beta REAL,
            pe_ratio REAL,
            pb_ratio REAL,
            ps_ratio REAL,
            ev_ebitda REAL,
            ev_sales REAL,
            dcf_value REAL,
            roe REAL,
            roa REAL,
            roic REAL,
            gross_margin_ttm REAL,
            op_margin_ttm REAL,
            net_margin_ttm REAL,
            ebitda_margin_ttm REAL,
            revenue_growth REAL,
            eps_growth REAL,
            fcf_growth REAL,
            op_income_growth REAL,
            current_ratio REAL,
            debt_to_equity REAL,
            net_debt_to_ebitda REAL,
            interest_coverage REAL,
            dividend_yield REAL,
            payout_ratio REAL,
            asset_turnover REAL,
            receivables_turnover REAL,
            inventory_turnover REAL,
            rsi_14 REAL,
            bollinger_pct_b REAL,
            rebound_score REAL,
            rebound_signal TEXT,
            support_price REAL,
            last_updated TEXT,
            ai_analysis_json TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
    """)
    conn.commit()
    return conn


def populate_sample_companies(conn: sqlite3.Connection):
    """
    Populates sample companies including duplicate tickers to test MIN(id) deduplication.
    """
    cursor = conn.cursor()
    # Insert report
    cursor.execute("INSERT INTO industry_reports (id, title) VALUES (1, 'AI 반도체')")
    cursor.execute("INSERT INTO industry_reports (id, title) VALUES (2, '자율주행')")

    # Insert duplicate NVDA in report 1 (id=1) and report 2 (id=2)
    cursor.execute("""
        INSERT INTO companies (id, industry_id, name, ticker, portfolio_tier, principle_reason)
        VALUES (1, 1, 'NVIDIA Corp', 'NVDA', 'Core', 'AI 가속기 독점')
    """)
    cursor.execute("""
        INSERT INTO companies (id, industry_id, name, ticker, portfolio_tier, principle_reason)
        VALUES (2, 2, 'NVIDIA Corporation', 'NVDA', 'Core', '자율주행 드라이브 플랫폼')
    """)

    # Insert Vertiv (Satellite)
    cursor.execute("""
        INSERT INTO companies (id, industry_id, name, ticker, portfolio_tier, principle_reason)
        VALUES (3, 1, 'Vertiv Holdings', 'VRT', 'Satellite', 'AI 데이터센터 냉각 고성장')
    """)

    # Insert Samsung Electronics (Core Korean)
    cursor.execute("""
        INSERT INTO companies (id, industry_id, name, ticker, portfolio_tier, principle_reason)
        VALUES (4, 1, '삼성전자', '005930.KS', 'Core', '글로벌 메모리 1위')
    """)

    # Insert Standard company
    cursor.execute("""
        INSERT INTO companies (id, industry_id, name, ticker, portfolio_tier, principle_reason)
        VALUES (5, 2, '일반부품사', '999999.KS', 'Standard', '일반 부품 공급사')
    """)

    # Insert Profile for id=1
    cursor.execute("""
        INSERT INTO company_profiles (
            company_id, current_price, high_52w, mdd_pct, buy_signal, dca_stage,
            moat_score, op_margin_ttm, roe, gross_margin_ttm, revenue_growth, debt_to_equity,
            rsi_14, bollinger_pct_b, rebound_score, rebound_signal, support_price, last_updated
        ) VALUES (
            1, 220.0, 240.0, -8.33, 'WAIT (고점 부근 MDD -8.3%)', 'CORE_HOLD',
            92.0, 0.55, 0.65, 0.75, 0.40, 45.0,
            45.0, 0.40, 15.0, 'NEUTRAL', 180.0, '2026-09-18 15:30'
        )
    """)

    # Insert Profile for id=3 (VRT)
    cursor.execute("""
        INSERT INTO company_profiles (
            company_id, current_price, high_52w, mdd_pct, buy_signal, dca_stage,
            moat_score, op_margin_ttm, roe, gross_margin_ttm, revenue_growth, debt_to_equity,
            rsi_14, bollinger_pct_b, rebound_score, rebound_signal, support_price, last_updated
        ) VALUES (
            3, 100.0, 140.0, -28.57, 'BUY_READY (1차 분할매수 MDD -28.6%)', 'SAT_DCA_1',
            68.0, 0.18, 0.22, 0.35, 0.26, 85.0,
            24.0, -0.05, 75.0, 'STRONG_REBOUND', 95.0, '2026-09-18 15:30'
        )
    """)
    conn.commit()


def generate_mock_ohlcv(
    num_days: int = 252,
    base_price: float = 100.0,
    mdd_pct: float = -20.0,
    is_oversold: bool = False
) -> Dict[str, List[float]]:
    """
    Generates deterministic synthetic daily price history for mathematical testing.
    """
    high_52w = base_price / (1.0 + (mdd_pct / 100.0))
    prices = []
    
    for i in range(num_days):
        # Progressively move toward current price
        progress = i / (num_days - 1)
        if is_oversold and i > num_days - 15:
            # Steep plunge in last 14 days to force low RSI (< 25) and Bollinger breakdown
            step_down = (num_days - i) * 1.5
            p = base_price + step_down
        else:
            p = high_52w - (high_52w - base_price) * progress
        prices.append(max(p, 1.0))
        
    prices[-1] = base_price
    highs = [p * 1.02 for p in prices]
    lows = [p * 0.98 for p in prices]
    opens = [p * 0.99 for p in prices]
    closes = prices

    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "high_52w": high_52w,
        "current_price": base_price,
    }
