"""Baseline classifiers for benchmark comparison."""

from backtest_lie_detector.baselines.rule_baseline import (
    RuleBasedClassifier,
    AlwaysInvalidBaseline,
    KeywordSuspicionBaseline,
    run_baseline_evaluation,
)

__all__ = [
    "RuleBasedClassifier",
    "AlwaysInvalidBaseline",
    "KeywordSuspicionBaseline",
    "run_baseline_evaluation",
]
