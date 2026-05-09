"""
Generate final V4 benchmark comparison figures with all models.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import jsonlines

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.schemas import ScoredResponse
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def load_results(filepath: str) -> list[ScoredResponse]:
    """Load results from jsonl file."""
    results = []
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def main():
    print("Loading data...")
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    
    models = {
        "GPT-4o\n(Generic)": "outputs/results/model_outputs_v4_generic.jsonl",
        "GPT-4o\n(Specialized)": "outputs/results/model_outputs_v4_specialized.jsonl",
        "Claude\nSonnet 4.5": "outputs/results/model_outputs_v4_claude_sonnet.jsonl",
    }
    
    results = {}
    metrics = {}
    calibrations = {}
    
    for name, filepath in models.items():
        r = load_results(filepath)
        results[name] = r
        metrics[name] = aggregate_scores(r)
        calibrations[name] = compute_calibration_metrics(r, cases)
    
    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Figure 1: Multi-model comparison
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    model_names = list(models.keys())
    colors = ["#3498db", "#2ecc71", "#9b59b6"]
    
    # 1. Overall accuracy
    ax1 = axes[0, 0]
    accuracies = [metrics[m]["validity_accuracy"] * 100 for m in model_names]
    bars = ax1.bar(model_names, accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_title("Overall Validity Accuracy")
    ax1.set_ylim(0, 100)
    for bar, acc in zip(bars, accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{acc:.1f}%", ha="center", fontweight="bold")
    
    # 2. False invalid rate
    ax2 = axes[0, 1]
    fir = [calibrations[m]["false_invalid_rate"] * 100 for m in model_names]
    bars = ax2.bar(model_names, fir, color=["#e74c3c", "#f39c12", "#e67e22"])
    ax2.set_ylabel("False Invalid Rate (%)")
    ax2.set_title("Overcaution: Valid Cases Marked Invalid")
    ax2.set_ylim(0, 60)
    for bar, rate in zip(bars, fir):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{rate:.1f}%", ha="center", fontweight="bold")
    
    # 3. Repair quality
    ax3 = axes[1, 0]
    repair_correct = [36.7, 40.0, 66.7]  # From analysis
    repair_partial = [26.7, 36.7, 30.0]
    repair_wrong = [36.7, 23.3, 3.3]
    
    x = np.arange(len(model_names))
    width = 0.25
    
    bars1 = ax3.bar(x - width, repair_correct, width, label="Correct", color="#27ae60")
    bars2 = ax3.bar(x, repair_partial, width, label="Partial", color="#f39c12")
    bars3 = ax3.bar(x + width, repair_wrong, width, label="Wrong", color="#e74c3c")
    
    ax3.set_ylabel("Percentage (%)")
    ax3.set_title("Repair Suggestion Quality")
    ax3.set_xticks(x)
    ax3.set_xticklabels(model_names)
    ax3.legend()
    ax3.set_ylim(0, 80)
    
    # 4. Key metrics comparison
    ax4 = axes[1, 1]
    
    metric_names = ["Accuracy", "Violation F1", "Repair Score"]
    x = np.arange(len(metric_names))
    width = 0.25
    
    gpt_generic = [83.2, 63.7, 60.0]
    gpt_spec = [79.2, 65.5, 60.6]
    claude = [75.2, 60.2, 73.6]
    
    bars1 = ax4.bar(x - width, gpt_generic, width, label="GPT-4o (Generic)", color=colors[0])
    bars2 = ax4.bar(x, gpt_spec, width, label="GPT-4o (Specialized)", color=colors[1])
    bars3 = ax4.bar(x + width, claude, width, label="Claude Sonnet", color=colors[2])
    
    ax4.set_ylabel("Score (%)")
    ax4.set_title("Key Metrics Comparison")
    ax4.set_xticks(x)
    ax4.set_xticklabels(metric_names)
    ax4.legend()
    ax4.set_ylim(0, 100)
    
    plt.suptitle("V4 Benchmark: Multi-Model Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v4_multimodel_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_multimodel_comparison.png")
    
    # Figure 2: LLMs vs Baselines
    fig, ax = plt.subplots(figsize=(12, 6))
    
    all_systems = [
        ("GPT-4o (Generic)", 83.2, 22.0, 1.4),
        ("GPT-4o (Specialized)", 79.2, 36.6, 1.4),
        ("Claude Sonnet", 75.2, 43.9, 1.4),
        ("Always Invalid", 56.0, 100.0, 0.0),
        ("Keyword Suspicion", 40.8, 4.9, 82.9),
        ("Rule-Based", 38.4, 14.6, 81.4),
        ("Always Valid", 32.8, 0.0, 100.0),
    ]
    
    names = [s[0] for s in all_systems]
    accuracies = [s[1] for s in all_systems]
    
    colors = ["#3498db", "#2ecc71", "#9b59b6", "#95a5a6", "#bdc3c7", "#7f8c8d", "#ecf0f1"]
    
    bars = ax.barh(names[::-1], accuracies[::-1], color=colors[::-1])
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("LLMs vs Baselines: Overall Accuracy")
    ax.set_xlim(0, 100)
    
    for bar, acc in zip(bars, accuracies[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
               f"{acc:.1f}%", va="center", fontweight="bold")
    
    # Add vertical line at 50%
    ax.axvline(x=50, color="gray", linestyle="--", alpha=0.5)
    ax.text(51, 6.5, "Random guess", color="gray", fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / "v4_llm_vs_baselines.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_llm_vs_baselines.png")
    
    # Figure 3: Trade-off visualization
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot each system
    for name, acc, fir, fvr in all_systems:
        if "GPT" in name or "Claude" in name:
            marker = "o"
            size = 200
            color = "#3498db" if "Generic" in name else "#2ecc71" if "Specialized" in name else "#9b59b6"
        else:
            marker = "s"
            size = 100
            color = "#7f8c8d"
        
        ax.scatter(fir, fvr, s=size, marker=marker, color=color, label=name, alpha=0.8)
        ax.annotate(name, (fir + 2, fvr + 2), fontsize=9)
    
    ax.set_xlabel("False Invalid Rate (%) - Overcaution")
    ax.set_ylabel("False Valid Rate (%) - Missed Violations")
    ax.set_title("Safety vs Utility Trade-off")
    ax.set_xlim(-5, 110)
    ax.set_ylim(-5, 110)
    
    # Add quadrant labels
    ax.text(80, 80, "Bad at Both", fontsize=12, color="red", alpha=0.5)
    ax.text(5, 80, "Misses Violations", fontsize=12, color="orange", alpha=0.5)
    ax.text(80, 5, "Overcautious", fontsize=12, color="blue", alpha=0.5)
    ax.text(5, 5, "Ideal Zone", fontsize=12, color="green", alpha=0.5)
    
    # Add ideal zone highlight
    ax.axhspan(0, 20, xmin=0, xmax=0.4, alpha=0.1, color="green")
    
    plt.tight_layout()
    plt.savefig(output_dir / "v4_tradeoff_scatter.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_tradeoff_scatter.png")
    
    print(f"\nAll figures saved to {output_dir}")


if __name__ == "__main__":
    main()
