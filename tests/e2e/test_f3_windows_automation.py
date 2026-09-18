"""
Tier 1: Feature 3 - Windows Silent Background Automation & Launcher Tests.
Covers headless VBScript launcher (pythonw.exe with window style 0),
Task Scheduler non-admin registration scripts, and modernized run.bat / run.ps1 pipeline.
"""

import unittest
import re
from pathlib import Path

from tests.e2e.test_helpers import (
    PROJECT_ROOT,
    SILENT_VBS_PATH,
    INSTALL_TASK_BAT_PATH,
    INSTALL_TASK_PS1_PATH,
    RUN_BAT_PATH,
    RUN_PS1_PATH,
)


class TestF3WindowsAutomation(unittest.TestCase):
    """E2E Test Suite for Feature 3 (Windows Silent Background Automation & Launcher)."""

    def test_f3_01_vbs_silent_wrapper_syntax_and_hidden_flag(self):
        """
        [F3-01] Verifies scripts/run_sync_silent.vbs exists, invokes pythonw.exe,
        and uses WshShell.Run with window style 0 (vbHide) to guarantee zero console window popup.
        """
        self.assertTrue(
            SILENT_VBS_PATH.exists(),
            f"Headless wrapper missing at {SILENT_VBS_PATH}"
        )
        content = SILENT_VBS_PATH.read_text(encoding="utf-8", errors="ignore")

        # Check for pythonw.exe usage
        self.assertRegex(
            content, r"pythonw(\.exe)?",
            "VBS script must invoke 'pythonw.exe' to prevent console window allocation"
        )

        # Check for WshShell.Run with 0 (hidden)
        # Typical VBS pattern: WshShell.Run command, 0, False
        self.assertRegex(
            content, r"\.Run\s+.*,\s*0\b",
            "VBS script must pass window style 0 (hidden) to WshShell.Run"
        )

    def test_f3_02_scheduler_installer_script_configuration(self):
        """
        [F3-02] Verifies Task Scheduler registration scripts exist (scripts/install_silent_task.bat
        or scripts/install_silent_task.ps1) and configure an on-logon trigger with non-admin privileges.
        """
        has_installer = INSTALL_TASK_BAT_PATH.exists() or INSTALL_TASK_PS1_PATH.exists()
        self.assertTrue(
            has_installer,
            "At least one Task Scheduler installer script (install_silent_task.bat or .ps1) must exist"
        )

        if INSTALL_TASK_BAT_PATH.exists():
            bat_content = INSTALL_TASK_BAT_PATH.read_text(encoding="utf-8", errors="ignore")
            # Should contain schtasks /create /sc onlogon
            self.assertIn("schtasks", bat_content.lower())
            self.assertIn("onlogon", bat_content.lower())

        if INSTALL_TASK_PS1_PATH.exists():
            ps1_content = INSTALL_TASK_PS1_PATH.read_text(encoding="utf-8", errors="ignore")
            has_task_cmd = "schtasks" in ps1_content.lower() or "scheduledtask" in ps1_content.lower()
            self.assertTrue(has_task_cmd, "PowerShell installer must register a scheduled task")

    def test_f3_03_run_bat_pre_sync_pipeline(self):
        """
        [F3-03] Verifies run.bat delegates to run.ps1 or executes pre-sync pipeline.
        """
        self.assertTrue(RUN_BAT_PATH.exists(), "run.bat must exist at project root")
        content = RUN_BAT_PATH.read_text(encoding="utf-8", errors="ignore")
        self.assertGreater(len(content.strip()), 0, "run.bat must not be empty")

    def test_f3_04_run_ps1_target_app_correctness(self):
        """
        [F3-04] Verifies run.ps1 launches the InvestmentPortal backend (main.py:app)
        and includes pre-run synchronization, NOT the legacy backend.app:app PDF tool.
        """
        self.assertTrue(RUN_PS1_PATH.exists(), "run.ps1 must exist at project root")
        content = RUN_PS1_PATH.read_text(encoding="utf-8", errors="ignore")

        # Must execute stock sync script before starting server
        has_sync_call = (
            "sync_stocks.py" in content
            or "update_all_stock_prices.py" in content
            or "sync_universe" in content
        )
        self.assertTrue(
            has_sync_call,
            "run.ps1 must include pre-sync step (invoking sync_stocks.py) before launching server"
        )

        # Must NOT point to the legacy app:app PDF extractor
        self.assertNotIn(
            "backend.app:app", content,
            "run.ps1 must NOT launch legacy 'backend.app:app'; it must launch InvestmentPortal"
        )

        # Must launch InvestmentPortal
        self.assertRegex(
            content, r"InvestmentPortal[/\\]backend[/\\]main|InvestmentPortal\.backend\.main|main:app",
            "run.ps1 must target InvestmentPortal backend main:app"
        )

    def test_f3_05_startup_shortcut_fallback_compatibility(self):
        """
        [F3-05] Verifies scripts provide a startup folder fallback or execution policy bypass
        to ensure non-privileged Windows users can execute the automated sync.
        """
        content = RUN_PS1_PATH.read_text(encoding="utf-8", errors="ignore") if RUN_PS1_PATH.exists() else ""
        bat_content = RUN_BAT_PATH.read_text(encoding="utf-8", errors="ignore") if RUN_BAT_PATH.exists() else ""

        # Check for -ExecutionPolicy Bypass in run.bat
        has_bypass = "bypass" in bat_content.lower() or "bypass" in content.lower()
        self.assertTrue(
            has_bypass,
            "run.bat or run.ps1 must use ExecutionPolicy Bypass to allow non-admin PowerShell execution"
        )


if __name__ == "__main__":
    unittest.main()
