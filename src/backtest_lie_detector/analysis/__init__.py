"""Analysis and visualization utilities."""

from backtest_lie_detector.analysis.plots import (
    plot_leaderboard,
    plot_module_breakdown,
    plot_violation_heatmap,
    plot_confidence_vs_accuracy,
    generate_all_plots,
)
from backtest_lie_detector.analysis.failure_taxonomy import (
    FailureCategory,
    categorize_failure,
    generate_failure_report,
    sample_failures_by_category,
)

__all__ = [
    "plot_leaderboard",
    "plot_module_breakdown",
    "plot_violation_heatmap",
    "plot_confidence_vs_accuracy",
    "generate_all_plots",
    "FailureCategory",
    "categorize_failure",
    "generate_failure_report",
    "sample_failures_by_category",
]
