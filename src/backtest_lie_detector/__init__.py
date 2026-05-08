"""
Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research.

This package provides tools to evaluate whether LLMs can detect point-in-time validity
errors in financial research workflows, including look-ahead bias, ticker time-travel,
filing timing mistakes, and survivorship bias.
"""

__version__ = "0.1.0"

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ModelResponse,
    ScoredResponse,
    EvaluationConfig,
    Module,
    Difficulty,
    Validity,
    ViolationType,
)

__all__ = [
    "BenchmarkCase",
    "ModelResponse", 
    "ScoredResponse",
    "EvaluationConfig",
    "Module",
    "Difficulty",
    "Validity",
    "ViolationType",
]
