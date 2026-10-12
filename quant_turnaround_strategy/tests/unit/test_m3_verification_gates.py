"""
Unit test suite for M3 Verification Framework (verify_system.py).
Verifies:
- Gate 1: Data Date Bounds & Ingestion Completeness.
- Gate 2: Zero Lookahead Bias Audit.
- Gate 3: Calendar Annual MDD & Calmar Mathematics.
- Gate 4: Strategy Superiority Proof (AR-DM vs Base Strategy).
- Gate 5: Streamlit Application Code & Syntax Validation.
- CLI main() execution and exit codes.
"""
import sys
import subprocess
from pathlib import Path
import pytest

from verify_system import (
    run_gate_1,
    run_gate_2,
    run_gate_3,
    run_gate_4,
    run_gate_5,
    GateResult,
)


class TestVerificationGates:
    """Test suite for programmatic validation gates in verify_system.py."""

    def test_gate_1_data_bounds_and_completeness(self):
        res: GateResult = run_gate_1(verbose=True)
        assert isinstance(res, GateResult)
        assert res.gate_num == 1
        assert res.passed is True
        assert len(res.sub_checks) >= 4
        # Assert each subcheck passes
        for sc in res.sub_checks:
            assert bool(sc.passed) is True, f"SubCheck failed: {sc.name} - {sc.detail}"

    def test_gate_2_zero_lookahead_bias_audit(self):
        res: GateResult = run_gate_2(verbose=True)
        assert isinstance(res, GateResult)
        assert res.gate_num == 2
        assert res.passed is True
        assert len(res.sub_checks) >= 4
        for sc in res.sub_checks:
            assert bool(sc.passed) is True, f"Gate 2 SubCheck failed: {sc.name} - {sc.detail}"

    def test_gate_3_annual_mdd_and_calmar_math(self):
        res: GateResult = run_gate_3(verbose=True)
        assert isinstance(res, GateResult)
        assert res.gate_num == 3
        assert res.passed is True
        assert len(res.sub_checks) >= 4
        for sc in res.sub_checks:
            assert bool(sc.passed) is True, f"Gate 3 SubCheck failed: {sc.name} - {sc.detail}"

    def test_gate_4_strategy_superiority_proof(self):
        res: GateResult = run_gate_4(verbose=True)
        assert isinstance(res, GateResult)
        assert res.gate_num == 4
        assert res.passed is True
        assert len(res.sub_checks) >= 4
        for sc in res.sub_checks:
            assert bool(sc.passed) is True, f"Gate 4 SubCheck failed: {sc.name} - {sc.detail}"

    def test_gate_5_streamlit_ui_validation(self):
        res: GateResult = run_gate_5(verbose=True)
        assert isinstance(res, GateResult)
        assert res.gate_num == 5
        assert res.passed is True
        assert len(res.sub_checks) >= 3
        for sc in res.sub_checks:
            assert bool(sc.passed) is True, f"Gate 5 SubCheck failed: {sc.name} - {sc.detail}"

    def test_cli_execution_returns_exit_code_zero(self):
        repo_dir = Path(__file__).resolve().parent.parent.parent
        verify_script = repo_dir / "verify_system.py"
        python_exe = sys.executable

        result = subprocess.run(
            [python_exe, str(verify_script)],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"verify_system.py returned code {result.returncode}:\n{result.stderr}\n{result.stdout}"
        assert "ALL GATES PASSED (5/5)" in result.stdout
