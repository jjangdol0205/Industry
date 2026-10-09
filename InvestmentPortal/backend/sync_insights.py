"""
Thought Leaders & Gurus Hub Synchronization Engine (Backend Mirror)
===================================================================
Mirror of root sync_insights.py for direct import within InvestmentPortal/backend.
Dynamically loads the root sync_insights module to eliminate circular imports
and maintain a single source of truth.
"""

import importlib.util
import sys
from pathlib import Path

_root_script = Path(__file__).resolve().parent.parent.parent / "sync_insights.py"
if not _root_script.exists():
    _candidate = Path("sync_insights.py").resolve()
    if _candidate.exists() and _candidate != Path(__file__).resolve():
        _root_script = _candidate

_spec = importlib.util.spec_from_file_location("_root_sync_insights_mod", str(_root_script))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_root_sync_insights_mod"] = _mod
_spec.loader.exec_module(_mod)

for _k, _v in _mod.__dict__.items():
    if not _k.startswith("__"):
        globals()[_k] = _v

if __name__ in sys.modules:
    sys.modules["sync_insights"] = sys.modules[__name__]
    sys.modules["InvestmentPortal.backend.sync_insights"] = sys.modules[__name__]

if __name__ == "__main__":
    if "main" in globals() and callable(globals()["main"]):
        globals()["main"]()
