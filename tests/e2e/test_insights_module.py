"""
Forwarding Shim: Re-exports TestInsightsModule from tests.test_insights_module
Allows both `tests/` and `tests/e2e/` test loaders to discover the Insights Hub test suite.
"""

from tests.test_insights_module import (
    TestInsightsTier1Features,
    TestInsightsTier2Boundaries,
    TestInsightsTier3Combinations,
    TestInsightsTier4Scenarios,
)

__all__ = [
    "TestInsightsTier1Features",
    "TestInsightsTier2Boundaries",
    "TestInsightsTier3Combinations",
    "TestInsightsTier4Scenarios",
]
