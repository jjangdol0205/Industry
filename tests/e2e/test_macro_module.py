"""
Forwarding Shim: Re-exports TestMacroModule from tests.test_macro_module
Allows both `tests/` and `tests/e2e/` test loaders to discover the Macro Module test suite.
"""

from tests.test_macro_module import (
    TestMacroModuleTier1Features,
    TestMacroModuleTier2Boundaries,
    TestMacroModuleTier3Combinations,
    TestMacroModuleTier4Scenarios,
)

__all__ = [
    "TestMacroModuleTier1Features",
    "TestMacroModuleTier2Boundaries",
    "TestMacroModuleTier3Combinations",
    "TestMacroModuleTier4Scenarios",
]
