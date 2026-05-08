"""
Visualization functions for benchmark results.

Generates leaderboards, module breakdowns, confusion matrices,
and other analysis plots.
"""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backtest_lie_detector.schemas import Module, ViolationType


# Color scheme
COLORS = {
    "primary": "#2563eb",
    "secondary": "#7c3aed",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "gray": "#6b7280",
}

MODULE_COLORS = {
    Module.TICKER_TIME_MACHINE.value: "#3b82f6",
    Module.FILING_CLOCK.value: "#8b5cf6",
    Module.ACCOUNTING_AVAILABILITY.value: "#06b6d4",
    Module.SURVIVORSHIP_DELISTING.value: "#f59e0b",
}


def setup_plot_style():
    """Configure matplotlib style for consistent plots."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12


def plot_leaderboard(
    scores_df: pd.DataFrame,
    output_path: Optional[str] = None,
    metric: str = "validity_accuracy",
    title: str = "Model Leaderboard",
) -> plt.Figure:
    """
    Create a horizontal bar chart leaderboard of model performance.
    
    Args:
        scores_df: DataFrame with columns [config_name, validity_correct, ...]
        output_path: Optional path to save the figure.
        metric: Metric to rank by.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    # Aggregate by config
    if "validity_correct" in scores_df.columns:
        agg = scores_df.groupby("config_name").agg({
            "validity_correct": "mean",
            "violation_recall": "mean",
            "violation_precision": "mean",
            "violation_f1": "mean",
            "repair_score": "mean",
        }).reset_index()
        agg.columns = ["config_name", "validity_accuracy", "violation_recall", 
                       "violation_precision", "violation_f1", "repair_score"]
    else:
        agg = scores_df.copy()
    
    # Sort by metric
    agg = agg.sort_values(metric, ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, max(4, len(agg) * 0.6)))
    
    y_pos = np.arange(len(agg))
    bars = ax.barh(y_pos, agg[metric], color=COLORS["primary"], edgecolor="white")
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, agg[metric])):
        ax.text(
            bar.get_width() + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1%}",
            va="center",
            fontsize=10,
        )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(agg["config_name"])
    ax.set_xlabel(metric.replace("_", " ").title())
    ax.set_title(title)
    ax.set_xlim(0, 1.15)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_module_breakdown(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "Accuracy by Module",
) -> plt.Figure:
    """
    Create a grouped bar chart showing accuracy by module for each model.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases (for module info).
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    # Merge to get module info
    if "module" not in scores_df.columns:
        merged = scores_df.merge(
            cases_df[["id", "module"]], 
            left_on="case_id", 
            right_on="id",
            how="left"
        )
    else:
        merged = scores_df.copy()
    
    # Compute accuracy by config and module
    module_acc = merged.groupby(["config_name", "module"])["validity_correct"].mean().unstack()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(module_acc.index))
    width = 0.2
    modules = list(module_acc.columns)
    
    for i, module in enumerate(modules):
        offset = (i - len(modules)/2 + 0.5) * width
        bars = ax.bar(
            x + offset, 
            module_acc[module], 
            width, 
            label=module.replace("_", " ").title(),
            color=MODULE_COLORS.get(module, COLORS["gray"]),
            edgecolor="white",
        )
    
    ax.set_ylabel("Validity Accuracy")
    ax.set_xlabel("Model Configuration")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(module_acc.index, rotation=45, ha="right")
    ax.legend(title="Module", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_ylim(0, 1.05)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_violation_heatmap(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "Violation Detection Recall by Type",
) -> plt.Figure:
    """
    Create a heatmap showing recall for each violation type by model.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    configs = scores_df["config_name"].unique()
    violation_types = [v.value for v in ViolationType]
    
    # Build case lookup
    case_violations = {}
    for _, row in cases_df.iterrows():
        case_violations[row["id"]] = row.get("expected_violations", [])
    
    # Compute recall for each config x violation type
    recall_matrix = np.zeros((len(configs), len(violation_types)))
    
    for i, config in enumerate(configs):
        config_scores = scores_df[scores_df["config_name"] == config]
        
        for j, vtype in enumerate(violation_types):
            # Find cases with this violation
            relevant_cases = []
            for case_id in config_scores["case_id"]:
                violations = case_violations.get(case_id, [])
                if isinstance(violations, str):
                    violations = violations.split(",")
                if vtype in violations:
                    relevant_cases.append(case_id)
            
            if not relevant_cases:
                recall_matrix[i, j] = np.nan
                continue
            
            # Check recall
            detected = 0
            for case_id in relevant_cases:
                score_row = config_scores[config_scores["case_id"] == case_id]
                if len(score_row) > 0:
                    pred_violations = score_row.iloc[0].get("predicted_violations", "")
                    if isinstance(pred_violations, str) and vtype in pred_violations:
                        detected += 1
            
            recall_matrix[i, j] = detected / len(relevant_cases)
    
    fig, ax = plt.subplots(figsize=(14, max(4, len(configs) * 0.8)))
    
    # Create heatmap
    im = ax.imshow(recall_matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    
    # Labels
    ax.set_xticks(np.arange(len(violation_types)))
    ax.set_yticks(np.arange(len(configs)))
    ax.set_xticklabels([v.replace("_", "\n") for v in violation_types], fontsize=9)
    ax.set_yticklabels(configs)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add text annotations
    for i in range(len(configs)):
        for j in range(len(violation_types)):
            val = recall_matrix[i, j]
            if not np.isnan(val):
                text = ax.text(
                    j, i, f"{val:.0%}",
                    ha="center", va="center",
                    color="white" if val > 0.5 else "black",
                    fontsize=8,
                )
    
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Recall", shrink=0.8)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_confidence_vs_accuracy(
    scores_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "Confidence vs Accuracy",
) -> plt.Figure:
    """
    Create a scatter/calibration plot showing confidence vs actual accuracy.
    
    Args:
        scores_df: DataFrame with confidence and validity_correct columns.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    df = scores_df.dropna(subset=["confidence"])
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Scatter by config
    ax1 = axes[0]
    configs = df["config_name"].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(configs)))
    
    for config, color in zip(configs, colors):
        config_df = df[df["config_name"] == config]
        ax1.scatter(
            config_df["confidence"],
            config_df["validity_correct"].astype(float),
            alpha=0.5,
            label=config,
            color=color,
            s=50,
        )
    
    ax1.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect calibration")
    ax1.set_xlabel("Model Confidence")
    ax1.set_ylabel("Actual Correct (0/1)")
    ax1.set_title("Confidence vs Correctness")
    ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax1.set_xlim(-0.05, 1.05)
    ax1.set_ylim(-0.05, 1.05)
    
    # Plot 2: Calibration curve (binned)
    ax2 = axes[1]
    
    bins = np.linspace(0, 1, 11)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    
    for config, color in zip(configs, colors):
        config_df = df[df["config_name"] == config]
        
        bin_accs = []
        bin_counts = []
        for i in range(len(bins) - 1):
            mask = (config_df["confidence"] >= bins[i]) & (config_df["confidence"] < bins[i+1])
            if mask.sum() > 0:
                bin_accs.append(config_df.loc[mask, "validity_correct"].mean())
                bin_counts.append(mask.sum())
            else:
                bin_accs.append(np.nan)
                bin_counts.append(0)
        
        ax2.plot(bin_centers, bin_accs, "o-", label=config, color=color, markersize=8)
    
    ax2.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Perfect calibration")
    ax2.set_xlabel("Confidence Bin")
    ax2.set_ylabel("Actual Accuracy")
    ax2.set_title("Calibration Curve")
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax2.set_xlim(-0.05, 1.05)
    ax2.set_ylim(-0.05, 1.05)
    
    plt.suptitle(title, y=1.02)
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_difficulty_breakdown(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "Accuracy by Difficulty",
) -> plt.Figure:
    """
    Create a bar chart showing accuracy by difficulty level.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    # Merge to get difficulty
    if "difficulty" not in scores_df.columns:
        merged = scores_df.merge(
            cases_df[["id", "difficulty"]], 
            left_on="case_id", 
            right_on="id",
            how="left"
        )
    else:
        merged = scores_df.copy()
    
    # Aggregate
    diff_acc = merged.groupby(["config_name", "difficulty"])["validity_correct"].mean().unstack()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(diff_acc.index))
    width = 0.25
    difficulties = ["easy", "medium", "hard"]
    colors_diff = [COLORS["success"], COLORS["warning"], COLORS["danger"]]
    
    for i, (diff, color) in enumerate(zip(difficulties, colors_diff)):
        if diff in diff_acc.columns:
            offset = (i - 1) * width
            ax.bar(
                x + offset, 
                diff_acc[diff], 
                width, 
                label=diff.title(),
                color=color,
                edgecolor="white",
            )
    
    ax.set_ylabel("Validity Accuracy")
    ax.set_xlabel("Model Configuration")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(diff_acc.index, rotation=45, ha="right")
    ax.legend(title="Difficulty")
    ax.set_ylim(0, 1.05)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def generate_all_plots(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_dir: str,
) -> dict[str, str]:
    """
    Generate all analysis plots and save to output directory.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_dir: Directory to save plots.
    
    Returns:
        Dictionary mapping plot name to file path.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    plots = {}
    
    # Leaderboard
    path = str(Path(output_dir) / "leaderboard.png")
    plot_leaderboard(scores_df, path)
    plots["leaderboard"] = path
    plt.close()
    
    # Module breakdown
    path = str(Path(output_dir) / "module_breakdown.png")
    plot_module_breakdown(scores_df, cases_df, path)
    plots["module_breakdown"] = path
    plt.close()
    
    # Confidence vs accuracy
    if "confidence" in scores_df.columns:
        path = str(Path(output_dir) / "confidence_vs_accuracy.png")
        plot_confidence_vs_accuracy(scores_df, path)
        plots["confidence_vs_accuracy"] = path
        plt.close()
    
    # Difficulty breakdown
    path = str(Path(output_dir) / "difficulty_breakdown.png")
    plot_difficulty_breakdown(scores_df, cases_df, path)
    plots["difficulty_breakdown"] = path
    plt.close()
    
    # Violation heatmap
    path = str(Path(output_dir) / "violation_heatmap.png")
    try:
        plot_violation_heatmap(scores_df, cases_df, path)
        plots["violation_heatmap"] = path
        plt.close()
    except Exception as e:
        print(f"Warning: Could not generate violation heatmap: {e}")
    
    print(f"Generated {len(plots)} plots in {output_dir}")
    return plots
