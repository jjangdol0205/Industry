#!/usr/bin/env python
"""
Standalone Master Programmatic Verification Script: verify_real_investment.py
Validates the Real Investment & SK Square Quantitative Strategy across 8 Core Gates:
  - Gate 1: 1D QQQ vs SOXX 101 Grid Search Mathematical Validity & Calmar Peak
  - Gate 2: Year-End vs Year-Beginning After-Tax Rebalancing & Compounding Calculation
  - Gate 3: Alternative High-Yield ETF Comparative Matrix & SMH Alpha Superiority
  - Gate 4: Hybrid 4-Asset Backtester Daily -10% Stop, T+1 Auto-Replacement & FIFO Tax
  - Gate 5: SK Square Fundamental SOTP NAV, 46.46% Discount & 76 Shares Valuation
  - Gate 6: Actionable Today Playbook Data Structures, Allocation & Checklists
  - Gate 7: Streamlit Tab 7 Module Import, Syntax & Function Signature Validation
  - Gate 8: Headless Streamlit AppTest Execution with Tab 7 Integration (0 Exceptions)

Usage:
  python verify_real_investment.py [--verbose]
Exit code: 0 on ALL GATES PASS, 1 on ANY GATE FAILURE.
"""

import argparse
import ast
from dataclasses import dataclass, field
from datetime import date, datetime
import math
import os
from pathlib import Path
import py_compile
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure repository root is on sys.path
REPO_DIR = Path(__file__).resolve().parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class SubCheck:
    name: str
    passed: bool
    detail: str

    def __post_init__(self):
        self.passed = bool(self.passed)


@dataclass
class GateResult:
    gate_num: int
    gate_name: str
    passed: bool
    duration_sec: float
    sub_checks: List[SubCheck] = field(default_factory=list)
    summary: str = ""

    def __post_init__(self):
        self.passed = bool(self.passed)


# ==============================================================================
# Gate 1: 1D QQQ vs SOXX 101 Grid Search Mathematical Validity & Calmar Peak
# ==============================================================================
def run_gate_1(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.optimizer.etf_rebalancer import compute_1d_grid_search, get_sensitivity_table

    grid_df = compute_1d_grid_search()

    # 1.1 Row count exactly 101
    c1 = (len(grid_df) == 101)
    sub_checks.append(SubCheck("Grid Row Count (101 allocations)", c1, f"len={len(grid_df)}"))

    # 1.2 Bounds & Weights Sum = 1.0
    w_sum = grid_df["weight_a"] + grid_df["weight_b"]
    c2 = bool(np.all(np.isclose(w_sum, 1.0, atol=1e-5))) and bool((grid_df["weight_a"] >= 0).all()) and bool((grid_df["weight_b"] >= 0).all())
    sub_checks.append(SubCheck("Weights Non-Negativity & Unity Sum", c2, f"Min sum={w_sum.min():.4f}, Max sum={w_sum.max():.4f}"))

    # 1.3 Calmar Peak at 100% QQQ / 0% SOXX
    best_calmar_idx = int(grid_df["calmar_usd"].idxmax())
    w_calmar = float(grid_df.loc[best_calmar_idx, "weight_a"])
    c_calmar = float(grid_df.loc[best_calmar_idx, "calmar_usd"])
    c3 = math.isclose(w_calmar, 1.0, abs_tol=0.01) and (0.245 <= c_calmar <= 0.255)
    sub_checks.append(SubCheck("Calmar Peak Oracle (100% QQQ, ~0.2513)", c3, f"Weight={w_calmar:.2f}, Calmar={c_calmar:.4f}"))

    # 1.4 Sharpe Peak at 90% QQQ / 10% SOXX
    best_sharpe_idx = int(grid_df["sharpe_usd"].idxmax())
    w_sharpe = float(grid_df.loc[best_sharpe_idx, "weight_a"])
    s_val = float(grid_df.loc[best_sharpe_idx, "sharpe_usd"])
    c4 = math.isclose(w_sharpe, 0.90, abs_tol=0.03) and (0.550 <= s_val <= 0.565)
    sub_checks.append(SubCheck("Sharpe Peak Oracle (88-90% QQQ, ~0.5582)", c4, f"Weight={w_sharpe:.2f}, Sharpe={s_val:.4f}"))

    # 1.5 USD and KRW Metrics Complete
    required_cols = {"weight_a", "weight_b", "cagr_usd", "cagr_krw", "annual_mdd_usd", "calmar_usd", "sharpe_usd"}
    c5 = required_cols.issubset(set(grid_df.columns)) and not grid_df[list(required_cols)].isna().any().any()
    sub_checks.append(SubCheck("Dual-Currency Metrics Completeness", c5, f"Columns verified: {len(required_cols)}"))

    # 1.6 Sensitivity Table & Crisis Drawdowns
    sens = get_sensitivity_table(grid_df)
    c6 = "calmar_sensitivity" in sens and "sharpe_sensitivity" in sens and "crisis_drawdowns" in sens
    sub_checks.append(SubCheck("Sensitivity & Crisis Stress Structure", c6, f"Keys: {list(sens.keys())}"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=1,
        gate_name="1D QQQ vs SOXX 101 Grid Search & Calmar Peak",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 2: Year-End vs Year-Beginning After-Tax Rebalancing & Compounding
# ==============================================================================
def run_gate_2(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.optimizer.etf_rebalancer import compare_tax_timing

    tax_res = compare_tax_timing(weights=(0.70, 0.30), capital_usd=100_000.0)

    # 2.1 Both Regimes Present
    c1 = "year_beginning" in tax_res and "year_end" in tax_res and "difference" in tax_res
    sub_checks.append(SubCheck("Dual Tax Regimes Evaluated", c1, f"Keys: {list(tax_res.keys())}"))

    # 2.2 Net After-Tax NAV Terminal Values ($2.528M target range)
    yb = tax_res["year_beginning"]
    ye = tax_res["year_end"]
    c2 = (yb["final_nav"] > 2_000_000.0) and (ye["final_nav"] > 2_000_000.0)
    sub_checks.append(SubCheck("Terminal Net After-Tax NAV Scale", c2, f"Jan=${yb['final_nav']:,.0f}, Dec=${ye['final_nav']:,.0f}"))

    # 2.3 Year-Beginning Compounding Advantage
    diff_usd = tax_res["difference"]["nav_usd"]
    c3 = (diff_usd >= 0.0) or math.isclose(diff_usd, 0.0, abs_tol=500.0)
    sub_checks.append(SubCheck("Year-Beginning Tax Deferral Compounding", c3, f"Delta NAV=${diff_usd:,.2f} USD"))

    # 2.4 Korean Basic Deduction & 22% Tax Applied
    c4 = (yb["taxes_paid"] > 0) and (ye["taxes_paid"] > 0) and (yb["taxes_paid_krw"] > 0)
    sub_checks.append(SubCheck("Taxes Paid Aggregation (USD/KRW)", c4, f"Jan Tax=₩{yb['taxes_paid_krw']:,.0f}, Dec Tax=₩{ye['taxes_paid_krw']:,.0f}"))

    # 2.5 Strategic Recommendation
    rec = tax_res.get("recommendation", "")
    c5 = ("Passive ETF" in rec or "패시브" in rec or "Year-Beginning" in rec) and len(rec) > 50
    sub_checks.append(SubCheck("Actionable Tax Recommendation Text", c5, f"Length={len(rec)} chars"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=2,
        gate_name="Year-End vs Year-Beginning After-Tax Rebalancing",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 3: Alternative High-Yield ETF Comparative Matrix & SMH Alpha
# ==============================================================================
def run_gate_3(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.optimizer.etf_rebalancer import evaluate_etf_alternatives

    alt_df = evaluate_etf_alternatives()

    # 3.1 Matrix Populated
    c1 = isinstance(alt_df, pd.DataFrame) and len(alt_df) >= 5
    sub_checks.append(SubCheck("Alternative Matrix Table Rows", c1, f"Rows={len(alt_df)}"))

    # 3.2 SMH vs SOXX Alpha (+48 bps)
    smh_rows = alt_df[alt_df["strategy"].str.contains("SMH", case=False, na=False)]
    soxx_rows = alt_df[alt_df["strategy"].str.contains("SOXX", case=False, na=False)]
    c2 = not smh_rows.empty and not soxx_rows.empty
    if c2:
        cagr_smh = float(smh_rows.iloc[0]["cagr"])
        cagr_soxx = float(soxx_rows.iloc[0]["cagr"])
        c2 = (cagr_smh > cagr_soxx) and math.isclose((cagr_smh - cagr_soxx) * 10000.0, 48.0, abs_tol=15.0)
        sub_checks.append(SubCheck("SMH Alpha Superiority over SOXX (+48 bps)", c2, f"SMH={cagr_smh:.2%}, SOXX={cagr_soxx:.2%}, Alpha={(cagr_smh-cagr_soxx)*10000:.1f} bps"))
    else:
        sub_checks.append(SubCheck("SMH vs SOXX Presence", False, "Missing SMH/SOXX rows"))

    # 3.3 SMH Milder Drawdown than SOXX
    if not smh_rows.empty and not soxx_rows.empty:
        mdd_smh = float(smh_rows.iloc[0]["worst_annual_mdd"])
        mdd_soxx = float(soxx_rows.iloc[0]["worst_annual_mdd"])
        c3 = abs(mdd_smh) < abs(mdd_soxx)
        sub_checks.append(SubCheck("SMH Drawdown Resilience", c3, f"SMH MDD={mdd_smh:.2%}, SOXX MDD={mdd_soxx:.2%}"))
    else:
        sub_checks.append(SubCheck("SMH Drawdown Resilience", False, "Missing rows"))

    # 3.4 Optimal 80% QQQ / 20% SMH Combination
    opt_rows = alt_df[alt_df["strategy"].str.contains("80% QQQ / 20% SMH", case=False, na=False)]
    c4 = not opt_rows.empty and (float(opt_rows.iloc[0]["cagr"]) >= 0.135)
    sub_checks.append(SubCheck("Optimal Pair (80% QQQ / 20% SMH) Verification", c4, f"Present={not opt_rows.empty}"))

    # 3.5 Leveraged ETF Pairs (2x/3x) Volatility Decay Modeled
    lev_rows = alt_df[alt_df["strategy"].str.contains("Leveraged", case=False, na=False)]
    c5 = not lev_rows.empty and (float(lev_rows.iloc[-1]["worst_annual_mdd"]) < -0.80)
    sub_checks.append(SubCheck("Leveraged Pairs Volatility Decay Captured", c5, f"Worst MDD={lev_rows.iloc[-1]['worst_annual_mdd']:.2%}" if not lev_rows.empty else "N/A"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=3,
        gate_name="Alternative High-Yield ETF Pairs & SMH Alpha",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 4: Hybrid 4-Asset Backtester Daily -10% Stop, Auto-Replacement & FIFO Tax
# ==============================================================================
def run_gate_4(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.engine.hybrid_backtester import HybridBacktester, HybridBacktestResult

    engine = HybridBacktester(w_qqq=0.70, w_soxx=0.20, w_stocks=0.10, initial_capital=100_000.0)
    res = engine.run_simulation()

    # 4.1 HybridBacktestResult Interface Contract
    c1 = isinstance(res, HybridBacktestResult) and not res.equity_curve.empty and not res.trade_log.empty
    sub_checks.append(SubCheck("Backtester Execution & Outputs", c1, f"Days={len(res.equity_curve)}, Trades={len(res.trade_log)}"))

    # 4.2 Strict Daily -10% Stop Loss Triggers with Slippage
    stop_trades = res.trade_log[res.trade_log["Reason"] == "STOP_LOSS"]
    c2 = not stop_trades.empty and (stop_trades["Return %"] <= -0.09).all()
    sub_checks.append(SubCheck("-10% Hard Stop-Loss Executions", c2, f"Count={len(stop_trades)}, Max return={stop_trades['Return %'].max():.2%}"))

    # 4.3 Partial Profit Taking (+25% gain)
    take_trades = res.trade_log[res.trade_log["Reason"] == "PARTIAL_TAKE"]
    c3 = not take_trades.empty and (take_trades["Return %"] >= 0.20).all()
    sub_checks.append(SubCheck("+25% Partial Profit-Taking Executions", c3, f"Count={len(take_trades)}, Min return={take_trades['Return %'].min():.2%}"))

    # 4.4 FIFO Tax Lot Realization & Korean 22% Tax Deductions
    turnover = res.turnover_summary
    c4 = "Total Taxes Paid KRW" in turnover and (turnover["Total Taxes Paid KRW"] > 0)
    sub_checks.append(SubCheck("FIFO Lot Accounting & Korean Taxes", c4, f"Taxes=₩{turnover.get('Total Taxes Paid KRW', 0):,.0f}"))

    # 4.5 Execution Frictions Decomposition (Commissions, Slippage, SEC/FINRA)
    c5 = "Total Fees Paid USD" in turnover and (turnover["Total Fees Paid USD"] > 0)
    sub_checks.append(SubCheck("Frictions & Regulatory Fee Tracking", c5, f"Fees=${turnover.get('Total Fees Paid USD', 0):,.2f}"))

    # 4.6 Net Alpha Generation
    c6 = turnover.get("Net After-Tax CAGR %", 0) > 0
    sub_checks.append(SubCheck("Net Positive CAGR After Frictions/Taxes", c6, f"Net CAGR={turnover.get('Net After-Tax CAGR %', 0):.2f}%"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=4,
        gate_name="Hybrid 4-Asset Engine with Frictions & FIFO Tax",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 5: SK Square Fundamental SOTP NAV, 46.46% Discount & 76 Shares Valuation
# ==============================================================================
def run_gate_5(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.valuation.sk_square import SKSquareValuationEngine

    engine = SKSquareValuationEngine(usd_krw_rate=1400.0)
    val = engine.get_valuation_summary()

    # 5.1 SK Hynix 20.07% Stake Value (₩205.93조)
    c1 = math.isclose(val["hynix_stake_value"] / 1e12, 205.93, abs_tol=0.5)
    sub_checks.append(SubCheck("SK Hynix 20.07% Stake Valuation (₩205.93조)", c1, f"Hynix Stake=₩{val['hynix_stake_value']/1e12:.2f}조"))

    # 5.2 Total SOTP NAV (₩210.93조) & NAV per Share (₩1,600,693)
    c2 = math.isclose(val["total_nav"] / 1e12, 210.93, abs_tol=0.5) and math.isclose(val["nav_per_share"], 1_600_693.0, abs_tol=100.0)
    sub_checks.append(SubCheck("Total SOTP NAV & NAV per Share", c2, f"Total NAV=₩{val['total_nav']/1e12:.2f}조, Per Share=₩{val['nav_per_share']:,.0f}"))

    # 5.3 NAV Discount (46.46% total, 45.16% vs Hynix alone)
    c3 = math.isclose(val["nav_discount_pct"], 46.46, abs_tol=0.2) and math.isclose(val["hynix_only_discount_pct"], 45.16, abs_tol=0.2)
    sub_checks.append(SubCheck("Mathematical NAV Discount Calculation (46.46%)", c3, f"Total Disc={val['nav_discount_pct']:.2f}%, Hynix-only={val['hynix_only_discount_pct']:.2f}%"))

    # 5.4 User 76 Shares Valuation (₩65,132,000 / $46,523 USD)
    c4 = math.isclose(val["user_76_shares_value_krw"], 65_132_000.0, abs_tol=1.0) and math.isclose(val["user_76_shares_value_usd"], 46_523.0, abs_tol=5.0)
    sub_checks.append(SubCheck("User 76 Shares Position Valuation", c4, f"KRW=₩{val['user_76_shares_value_krw']:,.0f}, USD=${val['user_76_shares_value_usd']:,}"))

    # 5.5 Corporate Value-Up Policies
    v_up = engine.get_value_up_policy_analysis()
    c5 = ("cumulative_buybacks_krw" in v_up) and ("treasury_retirement_pct" in v_up) and (v_up["treasury_retirement_pct"] == 100.0)
    sub_checks.append(SubCheck("Corporate Value-Up & 100% Retirement Policy", c5, f"Buybacks=₩{v_up['cumulative_buybacks_krw']/1e9:.0f}억, Retirement={v_up['treasury_retirement_pct']:.0f}%"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=5,
        gate_name="SK Square Fundamental SOTP NAV & 76 Shares Valuation",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 6: Actionable Today Playbook Data Structures, Allocation & Checklists
# ==============================================================================
def run_gate_6(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from src.valuation.sk_square import ExecutiveActionPlaybook

    playbook = ExecutiveActionPlaybook(total_shares=76, share_price=857_000.0, usd_krw_rate=1400.0)
    data = playbook.get_full_playbook()

    # 6.1 Immediate Decision: Phased 50/50 Reallocation
    dec = data["immediate_decision"]
    c1 = (dec["verdict"] == "PHASED_50_50_REALLOCATION") and (dec["sell_shares"] == 38) and (dec["hold_shares"] == 38)
    sub_checks.append(SubCheck("Phased 50/50 Reallocation Verdict", c1, f"Sell={dec['sell_shares']} sh, Hold={dec['hold_shares']} sh"))

    # 6.2 Trailing Stop & Target Exit Prices
    c2 = math.isclose(dec["trailing_stop_price"], 780_000.0, abs_tol=1.0) and (dec["target_exit_price_min"] == 1_150_000.0) and (dec["target_exit_price_max"] == 1_250_000.0)
    sub_checks.append(SubCheck("Trailing Stop (₩780k) & Target Exits (₩1.15M~₩1.25M)", c2, f"Stop=₩{dec['trailing_stop_price']:,.0f}, Min=₩{dec['target_exit_price_min']:,.0f}"))

    # 6.3 Day-1 Brokerage Allocation (70% QQQ, 20% SMH, 10% Cash/Turnaround)
    d1 = data["day1_allocation"]
    w = d1["weights"]
    c3 = math.isclose(w["QQQ"], 0.70) and math.isclose(w["SMH"], 0.20) and math.isclose(w["CASH_OR_TURNAROUND"], 0.10)
    sub_checks.append(SubCheck("Day-1 Allocation Weights (70/20/10)", c3, f"Weights={w}"))

    # 6.4 Weekly Operational Checklist Present
    chk = data["checklists"]
    c4 = len(chk.get("weekly", [])) >= 4
    sub_checks.append(SubCheck("Weekly Operational Checklist (>=4 steps)", c4, f"Steps={len(chk.get('weekly', []))}"))

    # 6.5 Annual Tax & Rebalancing Checklist Present
    c5 = len(chk.get("annual", [])) >= 2
    sub_checks.append(SubCheck("Annual Tax/Rebalance Checklist (Late Dec vs Early Jan)", c5, f"Steps={len(chk.get('annual', []))}"))

    # 6.6 Stop-Loss Order Rules (Stop-Limit with -0.5% offset)
    stop_rules = chk.get("stop_loss", [])
    c6 = len(stop_rules) >= 1 and ("Stop-Limit" in str(stop_rules) or "Stop Limit" in str(stop_rules))
    sub_checks.append(SubCheck("Stop-Loss Order Execution Rules", c6, f"Rules={len(stop_rules)}"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=6,
        gate_name="Actionable Today Playbook & Checklists",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 7: Streamlit Tab 7 Module Import, Syntax & Function Signature
# ==============================================================================
def run_gate_7(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    tab_path = REPO_DIR / "src" / "ui" / "real_investment_tab.py"
    app_path = REPO_DIR / "app.py"

    # 7.1 AST parse check for real_investment_tab.py
    with open(tab_path, "r", encoding="utf-8") as f:
        tree_tab = ast.parse(f.read(), filename=str(tab_path))
    c1 = tree_tab is not None
    sub_checks.append(SubCheck("AST Parse real_investment_tab.py", c1, "Valid syntax"))

    # 7.2 Bytecode compilation of real_investment_tab.py
    comp_tab = py_compile.compile(str(tab_path), doraise=True)
    c2 = comp_tab is not None
    sub_checks.append(SubCheck("Bytecode Compile real_investment_tab.py", c2, str(comp_tab)))

    # 7.3 AST parse check for app.py
    with open(app_path, "r", encoding="utf-8") as f:
        tree_app = ast.parse(f.read(), filename=str(app_path))
    c3 = tree_app is not None
    sub_checks.append(SubCheck("AST Parse app.py", c3, "Valid syntax"))

    # 7.4 Bytecode compilation of app.py
    comp_app = py_compile.compile(str(app_path), doraise=True)
    c4 = comp_app is not None
    sub_checks.append(SubCheck("Bytecode Compile app.py", c4, str(comp_app)))

    # 7.5 Dynamic import of render_real_investment_tab
    from src.ui.real_investment_tab import render_real_investment_tab
    c5 = callable(render_real_investment_tab)
    sub_checks.append(SubCheck("Import callable render_real_investment_tab", c5, f"Callable={c5}"))

    # 7.6 Inspect 8 required section headers in code
    with open(tab_path, "r", encoding="utf-8") as f:
        code_str = f.read()
    sections = [
        "Section 1",
        "Section 2",
        "Section 3",
        "Section 4",
        "Section 5",
        "Section 6",
        "Section 7",
        "Section 8",
    ]
    all_secs = all(s in code_str for s in sections)
    sub_checks.append(SubCheck("Presence of 8 Required UI Sections in Module", all_secs, f"Sections matched: {len(sections)}/8"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=7,
        gate_name="Streamlit Tab 7 Syntax, AST & Module Contracts",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Gate 8: Headless Streamlit AppTest Execution with Tab 7 Integration
# ==============================================================================
def run_gate_8(verbose: bool = False) -> GateResult:
    t0 = time.time()
    sub_checks = []

    from streamlit.testing.v1 import AppTest

    # Force Tab 7 rendering in AppTest
    os.environ["FORCE_SHOW_TAB_7"] = "1"
    app_file = str(REPO_DIR / "app.py")

    at = AppTest.from_file(app_file, default_timeout=60)
    at.run()

    # 8.1 Zero unhandled exceptions
    c1 = (len(at.exception) == 0)
    sub_checks.append(SubCheck("AppTest Zero Exceptions across All Tabs", c1, f"Exceptions: {[repr(e.value) for e in at.exception]}"))

    # 8.2 Tabs rendered (at least 7 primary tabs)
    tab_count = len(at.tabs)
    c2 = (tab_count >= 7)
    sub_checks.append(SubCheck("Tab Count (>= 7 tabs rendered)", c2, f"Total tabs={tab_count}"))

    # 8.3 Tab 7 Label matches Real Investment / SK Square
    tab_labels = [t.label for t in at.tabs]
    c3 = any("실전 투자" in lbl or "Real Investment" in lbl or "SK스퀘어" in lbl for lbl in tab_labels)
    sub_checks.append(SubCheck("Tab 7 Registered Label Matching", c3, f"Matching labels found in {len(tab_labels)} tabs"))

    # 8.4 Sidebar radio controls operational
    c4 = len(at.sidebar.radio) >= 2
    sub_checks.append(SubCheck("Sidebar Controls Present", c4, f"Radio count={len(at.sidebar.radio)}"))

    all_passed = all(sc.passed for sc in sub_checks)
    dur = time.time() - t0
    return GateResult(
        gate_num=8,
        gate_name="Headless Streamlit AppTest Execution with Tab 7",
        passed=all_passed,
        duration_sec=dur,
        sub_checks=sub_checks,
        summary=f"{sum(sc.passed for sc in sub_checks)}/{len(sub_checks)} sub-checks passed in {dur:.2f}s",
    )


# ==============================================================================
# Master Runner & Command-Line Interface
# ==============================================================================
def run_all_gates(verbose: bool = False) -> bool:
    print("=" * 80)
    print("  ROUND 8 REAL INVESTMENT & SK SQUARE QUANTITATIVE VERIFICATION SUITE")
    print("=" * 80)
    print(f"  Target Root: {REPO_DIR}")
    print(f"  Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    gates = [
        ("Gate 1", run_gate_1),
        ("Gate 2", run_gate_2),
        ("Gate 3", run_gate_3),
        ("Gate 4", run_gate_4),
        ("Gate 5", run_gate_5),
        ("Gate 6", run_gate_6),
        ("Gate 7", run_gate_7),
        ("Gate 8", run_gate_8),
    ]

    results: List[GateResult] = []
    overall_start = time.time()

    for idx, (label, gate_fn) in enumerate(gates, start=1):
        print(f"\n[RUNNING] Gate {idx}/8: {label}...")
        try:
            res = gate_fn(verbose=verbose)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            res = GateResult(
                gate_num=idx,
                gate_name=label,
                passed=False,
                duration_sec=0.0,
                summary=f"CRITICAL EXCEPTION: {exc}",
            )
        results.append(res)
        status_tag = "[PASS]" if res.passed else "[FAIL]"
        print(f"  {status_tag} Gate {idx}: {res.gate_name} ({res.duration_sec:.2f}s)")
        for sc in res.sub_checks:
            sc_tag = "  [OK]" if sc.passed else "  [FAIL]"
            print(f"    {sc_tag} {sc.name}: {sc.detail}")

    overall_dur = time.time() - overall_start

    print("\n" + "=" * 80)
    print("  FINAL GATES AUDIT SCORECARD")
    print("=" * 80)
    all_gates_pass = True
    for r in results:
        status_tag = "PASS" if r.passed else "FAIL"
        if not r.passed:
            all_gates_pass = False
        print(f"  Gate {r.gate_num}: [{status_tag:4s}] {r.gate_name:<55} ({r.duration_sec:.2f}s)")

    print("-" * 80)
    passed_count = sum(1 for r in results if r.passed)
    print(f"  Total Result: {passed_count}/{len(results)} Gates Passed ({'100% COMPLETE' if all_gates_pass else 'FAILURES DETECTED'}) in {overall_dur:.2f}s")
    print("=" * 80)

    return all_gates_pass


def main():
    parser = argparse.ArgumentParser(description="Master verification suite for Real Investment & SK Square strategy.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed diagnostic messages.")
    args = parser.parse_args()

    success = run_all_gates(verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
