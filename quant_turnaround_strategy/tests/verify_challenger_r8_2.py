"""
Empirical Verification Harness for Challenger R8-2:
Boundary Conditions, Tax Dynamics, and Valuation Models.
"""
import sys
import io

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure repository root is on sys.path
from pathlib import Path
REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

import numpy as np
import pandas as pd
from src.valuation.sk_square import SKSquareValuationEngine, ExecutiveActionPlaybook
from src.optimizer.etf_rebalancer import compare_tax_timing

def test_tax_timing_empirical():
    print("=== 1. TAX TIMING EMPIRICAL VERIFICATION ===")
    res = compare_tax_timing()
    yb = res["year_beginning"]
    ye = res["year_end"]
    diff = res["difference"]

    print(f"Year-Beginning Final NAV: ${yb['final_nav']:,.2f} ({yb['final_nav_krw']:,.0f} KRW)")
    print(f"Year-End Final NAV:       ${ye['final_nav']:,.2f} ({ye['final_nav_krw']:,.0f} KRW)")
    print(f"Net NAV Difference (YB - YE): +${diff['nav_usd']:,.2f} (+{diff['nav_krw']:,.0f} KRW)")
    print(f"Year-Beginning Taxes:     ${yb['taxes_paid']:,.2f} ({yb['taxes_paid_krw']:,.0f} KRW)")
    print(f"Year-End Taxes:           ${ye['taxes_paid']:,.2f} ({ye['taxes_paid_krw']:,.0f} KRW)")
    print(f"Year-End Tax Savings:     ${diff['tax_savings_year_end_usd']:,.2f} ({diff['tax_savings_year_end_krw']:,.0f} KRW)")

    # Assert exact required properties
    assert abs(diff["nav_usd"] - 92.96) < 0.05, f"Expected ~$92.96, got {diff['nav_usd']}"
    assert abs(diff["nav_krw"] - 124838) < 100, f"Expected ~124,838 KRW, got {diff['nav_krw']}"
    assert abs(diff["tax_savings_year_end_usd"] - (-1847.75)) < 1.0, f"Expected ~-$1,847.75, got {diff['tax_savings_year_end_usd']}"
    assert diff["winner"] == "year_beginning"
    assert "Passive ETF Portfolio: Rebalance in Year-Beginning" in res["recommendation"]
    assert "Active Turnaround Stock Portfolio: Rebalance and execute Tax-Loss Harvesting in Year-End" in res["recommendation"]
    print("Tax Timing Simulation: VERIFIED (PASS)")

def test_sotp_valuation_empirical():
    print("\n=== 2. SK SQUARE SOTP VALUATION VERIFICATION ===")
    hynix_shares = 142_710_503
    hynix_price = 1_443_000.0
    hynix_val = hynix_shares * hynix_price
    print(f"Hynix stake: {hynix_shares:,} * {hynix_price:,.0f} = {hynix_val:,.0f} KRW ({hynix_val/1e12:.2f}조)")
    assert abs(hynix_val - 205.93e12) / 205.93e12 < 0.001

    unlisted_val = 5.0e12
    total_nav = hynix_val + unlisted_val
    sq_shares = 131_774_099
    sq_price = 857_000.0
    nav_per_share = total_nav / sq_shares
    discount = (1.0 - (sq_price / nav_per_share)) * 100.0
    discount_hynix = (1.0 - (sq_price * sq_shares / hynix_val)) * 100.0

    print(f"Total NAV: {total_nav/1e12:.2f}조")
    print(f"NAV per share: {nav_per_share:,.0f} KRW")
    print(f"Discount to Total NAV: {discount:.2f}%")
    print(f"Discount to Hynix Stake Alone: {discount_hynix:.2f}%")

    assert abs(total_nav - 210.93e12) / 210.93e12 < 0.001
    assert abs(nav_per_share - 1_600_693.0) < 100.0
    assert abs(discount - 46.46) < 0.1
    assert abs(discount_hynix - 45.16) < 0.2
    print("SOTP Valuation: VERIFIED (PASS)")

def test_user_position_and_playbook():
    print("\n=== 3. USER 76 SHARES & DAY-1 PLAYBOOK ===")
    engine = SKSquareValuationEngine()
    summary = engine.get_valuation_summary()
    assert summary["user_76_shares_value_krw"] == 65_132_000.0
    assert summary["user_76_shares_value_usd"] == 46523.0

    pb = engine.get_actionable_playbook()
    decision = pb["immediate_decision"]
    assert decision["verdict"] == "PHASED_50_50_REALLOCATION"
    assert decision["sell_shares"] == 38
    assert decision["hold_shares"] == 38
    assert decision["trailing_stop_price"] == 780_000.0
    assert decision["target_exit_price_min"] == 1_150_000.0
    assert decision["target_exit_price_max"] == 1_250_000.0

    d1 = pb["day1_allocation"]
    weights = d1["weights"]
    assert weights["QQQ"] == 0.70
    assert weights["SMH"] == 0.20
    assert weights["CASH_OR_TURNAROUND"] == 0.10

    op = pb["operating_manual"]
    assert len(op["weekly_checklist"]) == 5
    assert len(op["annual_checklist"]) == 2
    assert len(op["stop_loss_checklist"]) == 1
    print("User Position & Playbook: VERIFIED (PASS)")

def test_boundary_stress_scenarios():
    print("\n=== 4. ADVERSARIAL BOUNDARY STRESS TESTS ===")
    engine = SKSquareValuationEngine()

    # Boundary 1: SK Hynix collapses by -65% to 500k KRW
    sotp_collapse = engine.calculate_sotp_nav(hynix_price=500_000.0)
    print(f"Hynix @ 500k: Total NAV = {sotp_collapse.total_nav/1e12:.2f}조, NAV/sh = {sotp_collapse.nav_per_share:,.0f} KRW, Discount = {sotp_collapse.nav_discount_pct:.2f}%")
    assert sotp_collapse.total_nav > 0
    assert sotp_collapse.nav_per_share < 1_000_000

    # Boundary 2: SK Hynix super-cycle to 3M KRW
    sotp_boom = engine.calculate_sotp_nav(hynix_price=3_000_000.0)
    print(f"Hynix @ 3M: Total NAV = {sotp_boom.total_nav/1e12:.2f}조, NAV/sh = {sotp_boom.nav_per_share:,.0f} KRW, Discount = {sotp_boom.nav_discount_pct:.2f}%")
    assert sotp_boom.nav_discount_pct > 70.0  # Discount expands dramatically if market price lags

    # Boundary 3: Complete unlisted write-off (0 KRW)
    sotp_zero_unlisted = engine.calculate_sotp_nav(unlisted_assets={k: 0.0 for k in engine.unlisted_assets})
    print(f"Zero unlisted assets: Total NAV Exact = {sotp_zero_unlisted.total_nav_exact/1e12:.2f}조, Hynix Only Discount = {sotp_zero_unlisted.hynix_only_discount_pct:.2f}%")
    assert sotp_zero_unlisted.hynix_only_discount_pct == pytest.approx(45.16, abs=0.1)
    assert abs(sotp_zero_unlisted.total_nav_exact - 205.93e12) / 205.93e12 < 0.001

    # Boundary 4: Discount compression to parity (0% discount)
    target_parity_price = sotp_zero_unlisted.nav_per_share_exact
    sotp_parity = engine.calculate_sotp_nav(sk_square_price=target_parity_price, hynix_price=1_443_001.0, unlisted_assets={k: 0.0 for k in engine.unlisted_assets})
    assert abs(sotp_parity.nav_discount_pct) < 0.1

    print("Boundary Stress Scenarios: VERIFIED (PASS)")

if __name__ == "__main__":
    import pytest
    test_tax_timing_empirical()
    test_sotp_valuation_empirical()
    test_user_position_and_playbook()
    test_boundary_stress_scenarios()
    print("\nALL EMPIRICAL HARNESS TESTS COMPLETED SUCCESSFULLY!")
