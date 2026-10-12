"""
Unit tests for ExclusionGates: discretionary risk-reward filters,
liquidity limits, falling-knife limits, and sector concentration limits.
"""
import pytest

from src.screening.exclusion_gates import ExclusionGates
from src.models.schemas import ExclusionReason


def test_gate_rejects_already_held():
    """Verifies that an already held ticker is rejected."""
    gates = ExclusionGates()
    passed, reasons = gates.evaluate_gates(
        ticker="AAPL",
        sector="Information Technology",
        current_holdings=["AAPL", "MSFT"],
        current_holding_sectors=["Information Technology", "Information Technology"],
        metrics={"avg_dollar_volume_20d": 50_000_000.0, "return_5d": 0.01, "return_30d": -0.10, "rsi_14": 40.0},
    )
    assert passed is False
    assert ExclusionReason.ALREADY_HELD in reasons


def test_gate_rejects_illiquid_stocks():
    """Verifies rejection of stocks trading under $20M daily dollar volume."""
    gates = ExclusionGates(min_dollar_volume=20_000_000.0)
    passed, reasons = gates.evaluate_gates(
        ticker="TINY",
        sector="Industrials",
        current_holdings=[],
        current_holding_sectors=[],
        metrics={"avg_dollar_volume_20d": 5_000_000.0, "return_5d": 0.01, "return_30d": -0.10, "rsi_14": 40.0},
    )
    assert passed is False
    assert ExclusionReason.ILLIQUID in reasons


def test_gate_rejects_sector_concentration():
    """Verifies rejection if the candidate sector is already represented in active portfolio."""
    gates = ExclusionGates(max_stocks_per_sector=1)
    passed, reasons = gates.evaluate_gates(
        ticker="NVDA",
        sector="Information Technology",
        current_holdings=["AAPL"],
        current_holding_sectors=["Information Technology"],
        metrics={"avg_dollar_volume_20d": 100_000_000.0, "return_5d": 0.01, "return_30d": -0.10, "rsi_14": 40.0},
    )
    assert passed is False
    assert ExclusionReason.SECTOR_CAPACITY in reasons


def test_gate_passes_healthy_stabilized_candidate():
    """Verifies that a liquid, solvent, non-concentrated candidate passes all gates."""
    gates = ExclusionGates(min_dollar_volume=20_000_000.0)
    passed, reasons = gates.evaluate_gates(
        ticker="AMZN",
        sector="Consumer Discretionary",
        current_holdings=["AAPL"],
        current_holding_sectors=["Information Technology"],
        metrics={
            "avg_dollar_volume_20d": 50_000_000.0,
            "return_5d": 0.02,
            "return_30d": -0.15,
            "rsi_14": 35.0,
            "solvency_score": 0.80,
            "turnaround_score": 0.70,
        },
    )
    assert passed is True
    assert len(reasons) == 0


def test_gate_rejects_zero_volume_and_halted_stocks():
    """Verifies that completely halted or zero-volume stocks ($0.0) are rejected by Gate 1."""
    gates = ExclusionGates(min_dollar_volume=20_000_000.0)
    passed, reasons = gates.evaluate_gates(
        ticker="HALTED",
        sector="Industrials",
        current_holdings=[],
        current_holding_sectors=[],
        metrics={"avg_dollar_volume_20d": 0.0, "solvency_score": 0.8, "turnaround_score": 0.8},
    )
    assert passed is False
    assert ExclusionReason.ILLIQUID in reasons


def test_check_liquidity_method():
    """Verifies check_liquidity helper method contract."""
    gates = ExclusionGates(min_dollar_volume=20_000_000.0)
    assert gates.check_liquidity(0.0) is False
    assert gates.check_liquidity(19_999_999.0) is False
    assert gates.check_liquidity(20_000_000.0) is True
    assert gates.check_liquidity(50_000_000.0) is True


def test_gate_permits_different_sectors():
    """Verifies that holding AAPL (Information Technology) does NOT block Ford (Consumer Discretionary)."""
    gates = ExclusionGates(max_stocks_per_sector=1)
    passed, reasons = gates.evaluate_gates(
        ticker="F",
        sector="Consumer Discretionary",
        current_holdings=["AAPL"],
        current_holding_sectors=["Information Technology"],
        metrics={"avg_dollar_volume_20d": 50_000_000.0, "solvency_score": 0.8, "turnaround_score": 0.8},
    )
    assert passed is True
    assert ExclusionReason.SECTOR_CAPACITY not in reasons

