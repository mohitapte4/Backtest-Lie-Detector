"""
Generate V5 benchmark figures highlighting false valid trap results.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
import jsonlines

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.schemas import ScoredResponse, Validity
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def load_results(filepath: str) -> list[ScoredResponse]:
    results = []
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def main():
    print("Loading data...")
    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    
    models = {
        "GPT-4o\n(Generic)": "outputs/results/model_outputs_v5_gpt-4o_generic.jsonl",
        "GPT-4o\n(Specialized)": "outputs/results/model_outputs_v5_gpt-4o_specialized.jsonl",
        "Claude\nSonnet": "outputs/results/model_outputs_v5_claude_sonnet.jsonl",
    }
    
    results = {}
    for name, path in models.items():
        results[name] = load_results(path)
    
    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Figure 1: V5 Overall comparison
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    model_names = list(models.keys())
    
    # 1a. Accuracy
    ax1 = axes[0]
    accuracies = []
    for name in model_names:
        agg = aggregate_scores(results[name])
        accuracies.append(agg["validity_accuracy"] * 100)
    
    colors = ["#3498db", "#2ecc71", "#9b59b6"]
    bars = ax1.bar(model_names, accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_title("V5 Overall Accuracy")
    ax1.set_ylim(0, 100)
    for bar, acc in zip(bars, accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{acc:.1f}%", ha="center", fontweight="bold")
    
    # 1b. False Invalid Rate
    ax2 = axes[1]
    fir_rates = []
    for name in model_names:
        cal = compute_calibration_metrics(results[name], cases)
        fir_rates.append(cal["false_invalid_rate"] * 100)
    
    bars = ax2.bar(model_names, fir_rates, color=["#e74c3c", "#f39c12", "#e67e22"])
    ax2.set_ylabel("False Invalid Rate (%)")
    ax2.set_title("Overcaution")
    ax2.set_ylim(0, 60)
    for bar, rate in zip(bars, fir_rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{rate:.1f}%", ha="center", fontweight="bold")
    
    # 1c. False Valid Rate
    ax3 = axes[2]
    fvr_rates = []
    for name in model_names:
        cal = compute_calibration_metrics(results[name], cases)
        fvr_rates.append(cal["false_valid_rate"] * 100)
    
    bars = ax3.bar(model_names, fvr_rates, color=["#c0392b", "#27ae60", "#8e44ad"])
    ax3.set_ylabel("False Valid Rate (%)")
    ax3.set_title("Missed Violations")
    ax3.set_ylim(0, 10)
    for bar, rate in zip(bars, fvr_rates):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f"{rate:.1f}%", ha="center", fontweight="bold")
    
    plt.suptitle("V5 Benchmark: 141 Cases (125 V4 + 16 False Valid Traps)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v5_overall.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_overall.png")
    
    # Figure 2: False Valid Trap Performance
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Get trap case results
    trap_ids = set(c.id for c in cases if hasattr(c, 'case_tags') and 'false_valid_trap' in c.case_tags)
    
    # 2a. Accuracy on trap cases
    ax1 = axes[0]
    trap_accuracies = []
    for name in model_names:
        trap_results = [r for r in results[name] if r.case_id in trap_ids and r.parse_success]
        correct = sum(1 for r in trap_results if r.validity_correct)
        trap_accuracies.append(correct / len(trap_results) * 100 if trap_results else 0)
    
    bars = ax1.bar(model_names, trap_accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_title("Accuracy on False Valid Trap Cases (16)")
    ax1.set_ylim(0, 110)
    for bar, acc in zip(bars, trap_accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{acc:.1f}%", ha="center", fontweight="bold")
    
    # 2b. False valid rate on trap cases
    ax2 = axes[1]
    trap_fvr = []
    for name in model_names:
        trap_results = [r for r in results[name] if r.case_id in trap_ids and r.parse_success and r.parsed_response]
        false_valids = sum(1 for r in trap_results if r.parsed_response.validity == Validity.VALID)
        trap_fvr.append(false_valids / len(trap_results) * 100 if trap_results else 0)
    
    bars = ax2.bar(model_names, trap_fvr, color=["#c0392b", "#27ae60", "#8e44ad"])
    ax2.set_ylabel("False Valid Rate (%)")
    ax2.set_title("Incorrectly Approved Subtle Violations")
    ax2.set_ylim(0, 25)
    for bar, rate in zip(bars, trap_fvr):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{rate:.1f}%", ha="center", fontweight="bold")
    
    plt.suptitle("V5 Finding: Specialized Prompts Catch Subtle Bugs", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v5_false_valid_traps.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_false_valid_traps.png")
    
    # Figure 3: V4 vs V5 Comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    
    v4_fvr = [1.4, 0.0, 1.4]  # V4 false valid rates
    v5_fvr = [4.7, 0.0, 1.2]  # V5 false valid rates
    
    x = np.arange(len(model_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, v4_fvr, width, label="V4 (125 cases)", color="#3498db")
    bars2 = ax.bar(x + width/2, v5_fvr, width, label="V5 (141 cases)", color="#e74c3c")
    
    ax.set_ylabel("False Valid Rate (%)")
    ax.set_title("Impact of False Valid Trap Cases on Model Performance")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names)
    ax.legend()
    ax.set_ylim(0, 8)
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 0.1,
                   f"{height:.1f}%", ha="center", va="bottom", fontsize=10)
    
    # Add annotation
    ax.annotate("Generic prompt's\nfalse valid rate\nincreased 3x",
               xy=(0.175, 4.7), xytext=(0.8, 6.5),
               arrowprops=dict(arrowstyle="->", color="gray"),
               fontsize=10, ha="center")
    
    plt.tight_layout()
    plt.savefig(output_dir / "v5_vs_v4_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_vs_v4_comparison.png")
    
    # Figure 4: The nuanced recommendation
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Data for stacked analysis
    metrics = ["Obvious\nViolations", "Subtle\nViolations", "Valid\nCases"]
    
    # Approximate data based on results
    generic_perf = [95, 81, 78]  # accuracy on each type
    spec_perf = [95, 94, 63]
    claude_perf = [95, 100, 56]
    
    x = np.arange(len(metrics))
    width = 0.25
    
    bars1 = ax.bar(x - width, generic_perf, width, label="GPT-4o (Generic)", color="#3498db")
    bars2 = ax.bar(x, spec_perf, width, label="GPT-4o (Specialized)", color="#2ecc71")
    bars3 = ax.bar(x + width, claude_perf, width, label="Claude Sonnet", color="#9b59b6")
    
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("V5 Finding: No Single Best Prompt Strategy")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.set_ylim(0, 110)
    
    # Add horizontal line at 90%
    ax.axhline(y=90, color="gray", linestyle="--", alpha=0.5)
    ax.text(2.5, 91, "90% threshold", fontsize=9, color="gray")
    
    plt.tight_layout()
    plt.savefig(output_dir / "v5_nuanced_finding.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_nuanced_finding.png")
    
    print(f"\nAll figures saved to {output_dir}")


if __name__ == "__main__":
    main()
