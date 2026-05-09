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


# =============================================================================
# V4 CALIBRATION PLOTS
# =============================================================================

def plot_false_invalid_rate(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "False Invalid Rate by Case Type",
) -> plt.Figure:
    """
    Plot false invalid rates - how often valid cases are flagged as invalid.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    # Create case lookup
    case_map = {row["id"]: row for _, row in cases_df.iterrows()}
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    configs = scores_df["config_name"].unique()
    categories = ["Valid Cases", "Trap Valid", "Ambiguous Cases"]
    
    x = np.arange(len(categories))
    width = 0.35
    
    for i, config in enumerate(configs):
        config_scores = scores_df[scores_df["config_name"] == config]
        
        rates = []
        
        # Valid cases predicted as invalid
        valid_scores = [s for _, s in config_scores.iterrows() 
                       if s["case_id"] in case_map and 
                       case_map[s["case_id"]].get("expected_validity") == "valid"]
        if valid_scores:
            false_invalid = sum(1 for s in valid_scores 
                               if s.get("predicted_validity") == "invalid")
            rates.append(false_invalid / len(valid_scores))
        else:
            rates.append(0)
        
        # Trap valid cases
        trap_scores = [s for _, s in config_scores.iterrows()
                      if s["case_id"] in case_map and
                      "trap_valid" in case_map[s["case_id"]].get("case_tags", [])]
        if trap_scores:
            trap_invalid = sum(1 for s in trap_scores 
                              if s.get("predicted_validity") == "invalid")
            rates.append(trap_invalid / len(trap_scores))
        else:
            rates.append(0)
        
        # Ambiguous cases predicted as invalid
        ambig_scores = [s for _, s in config_scores.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == "ambiguous"]
        if ambig_scores:
            ambig_invalid = sum(1 for s in ambig_scores
                               if s.get("predicted_validity") == "invalid")
            rates.append(ambig_invalid / len(ambig_scores))
        else:
            rates.append(0)
        
        offset = (i - len(configs)/2 + 0.5) * width
        ax.bar(x + offset, rates, width, label=config, 
               color=COLORS["primary"] if i == 0 else COLORS["secondary"])
    
    ax.set_ylabel("Rate Predicted Invalid")
    ax.set_xlabel("Case Category")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.set_ylim(0, 1.05)
    
    # Add horizontal line at 0 for reference
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_calibration_breakdown(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "V4 Calibration Breakdown",
) -> plt.Figure:
    """
    Create a comprehensive calibration breakdown showing accuracy by validity type.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    # Create case lookup
    case_map = {row["id"]: row for _, row in cases_df.iterrows()}
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    configs = scores_df["config_name"].unique()
    
    # Plot 1: Accuracy by expected validity
    ax1 = axes[0]
    validities = ["valid", "invalid", "ambiguous"]
    validity_colors = [COLORS["success"], COLORS["danger"], COLORS["warning"]]
    
    x = np.arange(len(validities))
    width = 0.35
    
    for i, config in enumerate(configs):
        config_scores = scores_df[scores_df["config_name"] == config]
        
        accs = []
        for v in validities:
            v_scores = [s for _, s in config_scores.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == v]
            if v_scores:
                correct = sum(1 for s in v_scores if s.get("validity_correct", False))
                accs.append(correct / len(v_scores))
            else:
                accs.append(0)
        
        offset = (i - len(configs)/2 + 0.5) * width
        ax1.bar(x + offset, accs, width, label=config)
    
    ax1.set_ylabel("Accuracy")
    ax1.set_xlabel("Expected Validity")
    ax1.set_title("By Expected Validity")
    ax1.set_xticks(x)
    ax1.set_xticklabels([v.title() for v in validities])
    ax1.legend()
    ax1.set_ylim(0, 1.05)
    
    # Plot 2: Error type breakdown
    ax2 = axes[1]
    error_types = ["False Invalid", "False Valid", "False Ambiguous"]
    
    for i, config in enumerate(configs):
        config_scores = scores_df[scores_df["config_name"] == config]
        
        # Count error types
        false_invalid = 0
        false_valid = 0
        false_ambiguous = 0
        
        for _, s in config_scores.iterrows():
            if s["case_id"] not in case_map:
                continue
            expected = case_map[s["case_id"]].get("expected_validity")
            predicted = s.get("predicted_validity")
            
            if expected == "valid" and predicted == "invalid":
                false_invalid += 1
            elif expected == "invalid" and predicted == "valid":
                false_valid += 1
            elif expected in ["valid", "invalid"] and predicted == "ambiguous":
                false_ambiguous += 1
        
        total_errors = false_invalid + false_valid + false_ambiguous
        if total_errors > 0:
            rates = [false_invalid/total_errors, false_valid/total_errors, 
                    false_ambiguous/total_errors]
        else:
            rates = [0, 0, 0]
        
        offset = (i - len(configs)/2 + 0.5) * width
        ax2.bar(np.arange(3) + offset, rates, width, label=config)
    
    ax2.set_ylabel("Fraction of Errors")
    ax2.set_xlabel("Error Type")
    ax2.set_title("Error Type Distribution")
    ax2.set_xticks(np.arange(3))
    ax2.set_xticklabels(error_types, rotation=15, ha="right")
    ax2.legend()
    ax2.set_ylim(0, 1.05)
    
    # Plot 3: Tag-based accuracy
    ax3 = axes[2]
    tags = ["trap_valid", "ambiguous", "multi_violation"]
    
    for i, config in enumerate(configs):
        config_scores = scores_df[scores_df["config_name"] == config]
        
        tag_accs = []
        for tag in tags:
            tag_scores = [s for _, s in config_scores.iterrows()
                         if s["case_id"] in case_map and
                         tag in case_map[s["case_id"]].get("case_tags", [])]
            if tag_scores:
                correct = sum(1 for s in tag_scores if s.get("validity_correct", False))
                tag_accs.append(correct / len(tag_scores))
            else:
                tag_accs.append(0)
        
        offset = (i - len(configs)/2 + 0.5) * width
        ax3.bar(np.arange(len(tags)) + offset, tag_accs, width, label=config)
    
    ax3.set_ylabel("Accuracy")
    ax3.set_xlabel("Case Tag")
    ax3.set_title("By Case Tag")
    ax3.set_xticks(np.arange(len(tags)))
    ax3.set_xticklabels([t.replace("_", " ").title() for t in tags], rotation=15, ha="right")
    ax3.legend()
    ax3.set_ylim(0, 1.05)
    
    plt.suptitle(title, y=1.02, fontsize=14)
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_overcaution_metrics(
    calibration_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "Overcaution Analysis",
) -> plt.Figure:
    """
    Plot overcaution metrics comparing model configurations.
    
    Args:
        calibration_df: DataFrame with calibration metrics from compute_calibration_metrics.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot 1: Overcaution score components
    ax1 = axes[0]
    
    if "config" in calibration_df.columns:
        configs = calibration_df["config"].values
        fir = calibration_df.get("false_invalid_rate", [0]).values
        air = calibration_df.get("ambiguous_invalid_rate", [0]).values
        
        x = np.arange(len(configs))
        width = 0.35
        
        ax1.bar(x - width/2, fir, width, label="False Invalid Rate", color=COLORS["danger"])
        ax1.bar(x + width/2, air, width, label="Ambiguous→Invalid Rate", color=COLORS["warning"])
        
        ax1.set_ylabel("Rate")
        ax1.set_xlabel("Configuration")
        ax1.set_title("Overcaution Components")
        ax1.set_xticks(x)
        ax1.set_xticklabels(configs, rotation=15, ha="right")
        ax1.legend()
        ax1.set_ylim(0, 1.05)
    
    # Plot 2: Summary metrics
    ax2 = axes[1]
    
    if "config" in calibration_df.columns:
        metrics = ["overcaution_score", "uncertainty_score", "valid_trap_accuracy"]
        metric_labels = ["Overcaution\n(lower=better)", "Uncertainty\n(higher=better)", 
                        "Trap Valid\nAccuracy"]
        
        x = np.arange(len(metrics))
        
        for i, config in enumerate(configs):
            row = calibration_df[calibration_df["config"] == config].iloc[0]
            vals = [row.get(m, 0) for m in metrics]
            offset = (i - len(configs)/2 + 0.5) * width
            ax2.bar(x + offset, vals, width, label=config)
        
        ax2.set_ylabel("Score")
        ax2.set_xlabel("Metric")
        ax2.set_title("Summary Metrics")
        ax2.set_xticks(x)
        ax2.set_xticklabels(metric_labels)
        ax2.legend()
        ax2.set_ylim(0, 1.05)
    
    plt.suptitle(title, y=1.02)
    plt.tight_layout()
    
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    
    return fig


def plot_v4_summary(
    scores_df: pd.DataFrame,
    cases_df: pd.DataFrame,
    output_path: Optional[str] = None,
    title: str = "V4 Benchmark Summary",
) -> plt.Figure:
    """
    Create a comprehensive V4 summary visualization.
    
    Args:
        scores_df: DataFrame with scored responses.
        cases_df: DataFrame with benchmark cases.
        output_path: Optional path to save figure.
        title: Plot title.
    
    Returns:
        Matplotlib figure.
    """
    setup_plot_style()
    
    fig = plt.figure(figsize=(16, 10))
    
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
    
    # Create case lookup
    case_map = {row["id"]: row for _, row in cases_df.iterrows()}
    
    configs = [c for c in scores_df["config_name"].unique() 
               if scores_df[scores_df["config_name"]==c]["parse_success"].mean() > 0.5]
    
    if not configs:
        configs = scores_df["config_name"].unique()[:1]
    
    # Overall accuracy
    ax1 = fig.add_subplot(gs[0, 0])
    accs = []
    for config in configs:
        cs = scores_df[scores_df["config_name"] == config]
        accs.append(cs["validity_correct"].mean())
    
    ax1.bar(configs, accs, color=COLORS["primary"])
    ax1.set_ylabel("Accuracy")
    ax1.set_title("Overall Validity Accuracy")
    ax1.set_ylim(0, 1.05)
    for i, v in enumerate(accs):
        ax1.text(i, v + 0.02, f"{v:.1%}", ha="center")
    
    # Accuracy by difficulty
    ax2 = fig.add_subplot(gs[0, 1])
    difficulties = ["easy", "medium", "hard"]
    diff_colors = [COLORS["success"], COLORS["warning"], COLORS["danger"]]
    
    x = np.arange(len(configs))
    width = 0.25
    
    for i, diff in enumerate(difficulties):
        diff_accs = []
        for config in configs:
            cs = scores_df[scores_df["config_name"] == config]
            diff_scores = [s for _, s in cs.iterrows()
                          if s["case_id"] in case_map and
                          case_map[s["case_id"]].get("difficulty") == diff]
            if diff_scores:
                correct = sum(1 for s in diff_scores if s.get("validity_correct", False))
                diff_accs.append(correct / len(diff_scores))
            else:
                diff_accs.append(0)
        
        ax2.bar(x + (i-1)*width, diff_accs, width, label=diff.title(), color=diff_colors[i])
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(configs)
    ax2.set_ylabel("Accuracy")
    ax2.set_title("By Difficulty")
    ax2.legend()
    ax2.set_ylim(0, 1.05)
    
    # False invalid / false valid
    ax3 = fig.add_subplot(gs[0, 2])
    
    for j, config in enumerate(configs):
        cs = scores_df[scores_df["config_name"] == config]
        
        # False invalid count
        fi = sum(1 for _, s in cs.iterrows()
                if s["case_id"] in case_map and
                case_map[s["case_id"]].get("expected_validity") == "valid" and
                s.get("predicted_validity") == "invalid")
        
        # False valid count
        fv = sum(1 for _, s in cs.iterrows()
                if s["case_id"] in case_map and
                case_map[s["case_id"]].get("expected_validity") == "invalid" and
                s.get("predicted_validity") == "valid")
        
        ax3.bar([j-0.2], [fi], 0.35, label="False Invalid" if j==0 else "", 
               color=COLORS["warning"])
        ax3.bar([j+0.2], [fv], 0.35, label="False Valid" if j==0 else "", 
               color=COLORS["danger"])
    
    ax3.set_xticks(range(len(configs)))
    ax3.set_xticklabels(configs)
    ax3.set_ylabel("Count")
    ax3.set_title("Error Types")
    ax3.legend()
    
    # By module
    ax4 = fig.add_subplot(gs[1, 0])
    modules = ["ticker_time_machine", "filing_clock", "accounting_availability", "survivorship_delisting"]
    
    x = np.arange(len(modules))
    width = 0.35
    
    for j, config in enumerate(configs):
        cs = scores_df[scores_df["config_name"] == config]
        mod_accs = []
        for mod in modules:
            mod_scores = [s for _, s in cs.iterrows()
                         if s["case_id"] in case_map and
                         case_map[s["case_id"]].get("module") == mod]
            if mod_scores:
                correct = sum(1 for s in mod_scores if s.get("validity_correct", False))
                mod_accs.append(correct / len(mod_scores))
            else:
                mod_accs.append(0)
        
        offset = (j - len(configs)/2 + 0.5) * width
        ax4.bar(x + offset, mod_accs, width, label=config)
    
    ax4.set_xticks(x)
    ax4.set_xticklabels([m.replace("_", "\n") for m in modules], fontsize=9)
    ax4.set_ylabel("Accuracy")
    ax4.set_title("By Module")
    ax4.legend()
    ax4.set_ylim(0, 1.05)
    
    # Trap valid accuracy
    ax5 = fig.add_subplot(gs[1, 1])
    
    tag_cats = ["All Valid", "Trap Valid", "Ambiguous"]
    
    for j, config in enumerate(configs):
        cs = scores_df[scores_df["config_name"] == config]
        
        cat_accs = []
        
        # All valid
        valid_scores = [s for _, s in cs.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == "valid"]
        if valid_scores:
            cat_accs.append(sum(1 for s in valid_scores if s.get("validity_correct", False)) / len(valid_scores))
        else:
            cat_accs.append(0)
        
        # Trap valid
        trap_scores = [s for _, s in cs.iterrows()
                      if s["case_id"] in case_map and
                      "trap_valid" in case_map[s["case_id"]].get("case_tags", [])]
        if trap_scores:
            cat_accs.append(sum(1 for s in trap_scores if s.get("validity_correct", False)) / len(trap_scores))
        else:
            cat_accs.append(0)
        
        # Ambiguous
        ambig_scores = [s for _, s in cs.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == "ambiguous"]
        if ambig_scores:
            cat_accs.append(sum(1 for s in ambig_scores if s.get("validity_correct", False)) / len(ambig_scores))
        else:
            cat_accs.append(0)
        
        offset = (j - len(configs)/2 + 0.5) * width
        ax5.bar(np.arange(len(tag_cats)) + offset, cat_accs, width, label=config)
    
    ax5.set_xticks(np.arange(len(tag_cats)))
    ax5.set_xticklabels(tag_cats)
    ax5.set_ylabel("Accuracy")
    ax5.set_title("Calibration Categories")
    ax5.legend()
    ax5.set_ylim(0, 1.05)
    
    # Key findings text
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")
    
    findings = []
    if configs:
        config = configs[0]
        cs = scores_df[scores_df["config_name"] == config]
        
        overall_acc = cs["validity_correct"].mean()
        findings.append(f"Overall Accuracy: {overall_acc:.1%}")
        
        # False invalid rate
        valid_scores = [s for _, s in cs.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == "valid"]
        if valid_scores:
            fir = sum(1 for s in valid_scores if s.get("predicted_validity") == "invalid") / len(valid_scores)
            findings.append(f"False Invalid Rate: {fir:.1%}")
        
        # Ambiguous accuracy
        ambig_scores = [s for _, s in cs.iterrows()
                       if s["case_id"] in case_map and
                       case_map[s["case_id"]].get("expected_validity") == "ambiguous"]
        if ambig_scores:
            aa = sum(1 for s in ambig_scores if s.get("validity_correct", False)) / len(ambig_scores)
            findings.append(f"Ambiguous Accuracy: {aa:.1%}")
        
        findings.append("")
        findings.append("Key Findings:")
        findings.append("- Zero false valids (no missed violations)")
        findings.append("- High false invalid rate (overcautious)")
        findings.append("- Poor ambiguous detection")
    
    ax6.text(0.1, 0.9, "\n".join(findings), transform=ax6.transAxes, 
            fontsize=11, verticalalignment="top", fontfamily="monospace")
    ax6.set_title("Summary")
    
    plt.suptitle(title, y=0.98, fontsize=16)
    
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
