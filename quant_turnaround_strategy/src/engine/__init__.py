"""
Core backtesting engine package.
Exports:
- BacktestEngine, BacktestResult
- Portfolio, Position
- ExecutionEngine, ExecutionResult
- KoreanTaxEngine, AnnualTaxRecord
- RiskManager, ExitSignal
- PerformanceMetrics
"""
from src.engine.portfolio import Portfolio, Position
from src.engine.execution import ExecutionEngine, ExecutionResult
from src.engine.tax import KoreanTaxEngine, AnnualTaxRecord
from src.engine.risk_manager import RiskManager, ExitSignal
from src.engine.metrics import PerformanceMetrics
from src.engine.backtester import BacktestEngine, BacktestResult

__all__ = [
    "Portfolio",
    "Position",
    "ExecutionEngine",
    "ExecutionResult",
    "KoreanTaxEngine",
    "AnnualTaxRecord",
    "RiskManager",
    "ExitSignal",
    "PerformanceMetrics",
    "BacktestEngine",
    "BacktestResult",
]
