#!/usr/bin/env python3
"""
E2E Test Runner for TrendPulse Investment Portal.
Executes opaque-box, requirement-driven E2E tests across Tiers 1-4 and Features F1-F7.

Usage:
    python run_e2e_tests.py                   # Run all E2E tests (Tiers 1-4)
    python run_e2e_tests.py --tier 1          # Run Tier 1 Feature Coverage
    python run_e2e_tests.py --tier 2          # Run Tier 2 Boundaries & Corners
    python run_e2e_tests.py --tier 3          # Run Tier 3 Combinations
    python run_e2e_tests.py --tier 4          # Run Tier 4 Real-World Scenarios
    python run_e2e_tests.py --feature F4      # Run Feature 4 (Moat & Margin) tests
    python run_e2e_tests.py --milestone M1    # Run Milestone 1 tests (F4, F5)
    python run_e2e_tests.py --milestone M2    # Run Milestone 2 tests (F1, F6, F7)
    python run_e2e_tests.py --milestone M3    # Run Milestone 3 tests (F2, F3)
"""

import os
import sys
import unittest
import argparse
import time
from pathlib import Path

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

# Ensure project root and backend are on PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "InvestmentPortal" / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

TESTS_DIR = PROJECT_ROOT / "tests" / "e2e"

FEATURE_TEST_MAP = {
    "F1": ["test_f1_sync_engine.py"],
    "F2": ["test_f2_smart_cache.py"],
    "F3": ["test_f3_windows_automation.py"],
    "F4": ["test_f4_moat_engine.py"],
    "F5": ["test_f5_mdd_rebound.py"],
    "F6": ["test_f6_backend_api.py"],
    "F7": ["test_f7_frontend_integrity.py"],
}

TIER_TEST_MAP = {
    1: [
        "test_f1_sync_engine.py",
        "test_f2_smart_cache.py",
        "test_f3_windows_automation.py",
        "test_f4_moat_engine.py",
        "test_f5_mdd_rebound.py",
        "test_f6_backend_api.py",
        "test_f7_frontend_integrity.py",
    ],
    2: ["test_tier2_boundaries.py"],
    3: ["test_tier3_combinations.py"],
    4: ["test_tier4_scenarios.py"],
}

MILESTONE_TEST_MAP = {
    "M1": ["test_f4_moat_engine.py", "test_f5_mdd_rebound.py"],
    "M2": ["test_f1_sync_engine.py", "test_f6_backend_api.py", "test_f7_frontend_integrity.py"],
    "M3": ["test_f2_smart_cache.py", "test_f3_windows_automation.py"],
    "M4": [
        "test_f1_sync_engine.py", "test_f2_smart_cache.py", "test_f3_windows_automation.py",
        "test_f4_moat_engine.py", "test_f5_mdd_rebound.py", "test_f6_backend_api.py",
        "test_f7_frontend_integrity.py", "test_tier2_boundaries.py",
        "test_tier3_combinations.py", "test_tier4_scenarios.py"
    ],
}


def load_selected_tests(tier=None, feature=None, milestone=None):
    """Discovers and filters test files based on user criteria."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    target_files = set()

    if feature:
        feature_upper = feature.upper()
        if feature_upper in FEATURE_TEST_MAP:
            target_files.update(FEATURE_TEST_MAP[feature_upper])
        else:
            print(f"Unknown feature '{feature}'. Supported: {list(FEATURE_TEST_MAP.keys())}")
            sys.exit(1)

    elif tier:
        if tier in TIER_TEST_MAP:
            target_files.update(TIER_TEST_MAP[tier])
        else:
            print(f"Unknown tier '{tier}'. Supported: 1, 2, 3, 4")
            sys.exit(1)

    elif milestone:
        m_upper = milestone.upper()
        if m_upper in MILESTONE_TEST_MAP:
            target_files.update(MILESTONE_TEST_MAP[m_upper])
        else:
            print(f"Unknown milestone '{milestone}'. Supported: M1, M2, M3, M4")
            sys.exit(1)

    else:
        # Load all test files in tests/e2e/
        all_tests = loader.discover(str(TESTS_DIR), pattern="test_*.py")
        return all_tests

    # Load specific files
    for filename in sorted(target_files):
        filepath = TESTS_DIR / filename
        if filepath.exists():
            mod_tests = loader.discover(str(TESTS_DIR), pattern=filename)
            suite.addTests(mod_tests)
        else:
            print(f"Warning: Test file {filename} does not exist yet at {filepath}")

    return suite


def main():
    parser = argparse.ArgumentParser(description="TrendPulse E2E Test Suite Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Execute a specific testing tier")
    parser.add_argument("--feature", type=str, choices=["F1", "F2", "F3", "F4", "F5", "F6", "F7", "f1", "f2", "f3", "f4", "f5", "f6", "f7"], help="Execute a specific feature test suite")
    parser.add_argument("--milestone", type=str, choices=["M1", "M2", "M3", "M4", "m1", "m2", "m3", "m4"], help="Execute tests for a specific implementation milestone")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution output")
    args = parser.parse_args()

    suite = load_selected_tests(tier=args.tier, feature=args.feature, milestone=args.milestone)
    test_count = suite.countTestCases()

    print("=" * 70)
    print(" TrendPulse Investment Portal — E2E Test Suite Runner")
    print("=" * 70)
    print(f"Filter Settings : Tier={args.tier or 'ALL'}, Feature={args.feature or 'ALL'}, Milestone={args.milestone or 'ALL'}")
    print(f"Test Directory  : {TESTS_DIR}")
    print(f"Tests Selected  : {test_count} test cases")
    print("-" * 70)

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    print("-" * 70)
    print(f"Execution Summary:")
    print(f"  Total Run : {result.testsRun}")
    print(f"  Passed    : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures  : {len(result.failures)}")
    print(f"  Errors    : {len(result.errors)}")
    print(f"  Skipped   : {len(result.skipped)}")
    print(f"  Duration  : {duration:.2f} seconds")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
