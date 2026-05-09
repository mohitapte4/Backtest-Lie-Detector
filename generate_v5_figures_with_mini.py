"""
Generate V5 benchmark figures including GPT-4o-mini results.
Updates figures for the CIFEr paper submission.
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
        "GPT-4o-mini": "outputs/results/model_outputs_v5_gpt4o_mini_generic.jsonl",
    }
    
    results = {}
    for name, path in models.items():
        try:
            results[name] = load_results(path)
            print(f"  Loaded {len(results[name])} results for {name}")
        except Exception as e:
            print(f"  Error loading {name}: {e}")
    
    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_names = list(results.keys())
    colors = ["#3498db", "#2ecc71", "#9b59b6", "#e67e22"]
    
    # Figure 1: V5 Overall comparison with GPT-4o-mini
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 1a. Accuracy
    ax1 = axes[0]
    accuracies = []
    for name in model_names:
        agg = aggregate_scores(results[name])
        accuracies.append(agg["validity_accuracy"] * 100)
    
    bars = ax1.bar(model_names, accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)", fontsize=11)
    ax1.set_title("Overall Accuracy", fontsize=12, fontweight="bold")
    ax1.set_ylim(0, 100)
    for bar, acc in zip(bars, accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{acc:.1f}%", ha="center", fontweight="bold", fontsize=10)
    ax1.tick_params(axis='x', labelsize=9)
    
    # 1b. False Invalid Rate
    ax2 = axes[1]
    fir_rates = []
    for name in model_names:
        cal = compute_calibration_metrics(results[name], cases)
        fir_rates.append(cal["false_invalid_rate"] * 100)
    
    bars = ax2.bar(model_names, fir_rates, color=["#e74c3c", "#f39c12", "#e67e22", "#c0392b"])
    ax2.set_ylabel("False Invalid Rate (%)", fontsize=11)
    ax2.set_title("Overcaution", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, 110)
    for bar, rate in zip(bars, fir_rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{rate:.1f}%", ha="center", fontweight="bold", fontsize=10)
    ax2.tick_params(axis='x', labelsize=9)
    
    # 1c. False Valid Rate
    ax3 = axes[2]
    fvr_rates = []
    for name in model_names:
        cal = compute_calibration_metrics(results[name], cases)
        fvr_rates.append(cal["false_valid_rate"] * 100)
    
    bars = ax3.bar(model_names, fvr_rates, color=["#c0392b", "#27ae60", "#8e44ad", "#27ae60"])
    ax3.set_ylabel("False Valid Rate (%)", fontsize=11)
    ax3.set_title("Dangerous Approvals", fontsize=12, fontweight="bold")
    ax3.set_ylim(0, 10)
    for bar, rate in zip(bars, fvr_rates):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f"{rate:.1f}%", ha="center", fontweight="bold", fontsize=10)
    ax3.tick_params(axis='x', labelsize=9)
    
    plt.suptitle("V5 Benchmark Performance (141 Cases)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v5_overall.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_overall.png")
    
    # Figure 2: False Valid Trap Performance with GPT-4o-mini
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    
    trap_ids = set(c.id for c in cases if hasattr(c, 'case_tags') and c.case_tags and 'false_valid_trap' in c.case_tags)
    
    # 2a. Accuracy on trap cases
    ax1 = axes[0]
    trap_accuracies = []
    for name in model_names:
        trap_results = [r for r in results[name] if r.case_id in trap_ids and r.parse_success]
        correct = sum(1 for r in trap_results if r.validity_correct)
        trap_accuracies.append(correct / len(trap_results) * 100 if trap_results else 0)
    
    bars = ax1.bar(model_names, trap_accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)", fontsize=11)
    ax1.set_title("Accuracy on 16 False-Valid Trap Cases", fontsize=12, fontweight="bold")
    ax1.set_ylim(0, 115)
    for bar, acc in zip(bars, trap_accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{acc:.1f}%", ha="center", fontweight="bold", fontsize=10)
    ax1.tick_params(axis='x', labelsize=9)
    
    # 2b. False valid approvals on trap cases
    ax2 = axes[1]
    trap_fv_count = []
    for name in model_names:
        trap_results = [r for r in results[name] if r.case_id in trap_ids and r.parse_success and r.parsed_response]
        false_valids = sum(1 for r in trap_results if r.parsed_response.validity == Validity.VALID)
        trap_fv_count.append(false_valids)
    
    bars = ax2.bar(model_names, trap_fv_count, color=["#c0392b", "#27ae60", "#27ae60", "#27ae60"])
    ax2.set_ylabel("False-Valid Approvals", fontsize=11)
    ax2.set_title("Subtle Invalid Cases Incorrectly Approved", fontsize=12, fontweight="bold")
    ax2.set_ylim(0, 5)
    for bar, count in zip(bars, trap_fv_count):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{count}/16", ha="center", fontweight="bold", fontsize=10)
    ax2.tick_params(axis='x', labelsize=9)
    
    plt.suptitle("False-Valid Trap Analysis: GPT-4o-mini catches all traps via near-universal rejection", 
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v5_false_valid_traps.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v5_false_valid_traps.png")
    
    # Figure 3: Safety-Utility Tradeoff Scatter (updated)
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # LLM data points
    llm_data = []
    for name in model_names:
        agg = aggregate_scores(results[name])
        cal = compute_calibration_metrics(results[name], cases)
        llm_data.append({
            "name": name.replace("\n", " "),
            "accuracy": agg["validity_accuracy"] * 100,
            "fvr": cal["false_valid_rate"] * 100,
            "fir": cal["false_invalid_rate"] * 100,
        })
    
    # Baseline data
    baselines = [
        {"name": "Always Invalid", "accuracy": 56.0, "fvr": 0.0, "fir": 100.0},
        {"name": "Keyword", "accuracy": 40.8, "fvr": 82.9, "fir": 4.9},
        {"name": "Rule-Based", "accuracy": 38.4, "fvr": 81.4, "fir": 14.6},
        {"name": "Always Valid", "accuracy": 32.8, "fvr": 100.0, "fir": 0.0},
    ]
    
    # Plot baselines
    for b in baselines:
        ax.scatter(b["fvr"], b["accuracy"], s=100, marker="s", color="gray", alpha=0.6)
        ax.annotate(b["name"], (b["fvr"], b["accuracy"]), 
                   xytext=(5, 5), textcoords="offset points", fontsize=9, color="gray")
    
    # Plot LLMs
    llm_colors = ["#3498db", "#2ecc71", "#9b59b6", "#e67e22"]
    for i, d in enumerate(llm_data):
        ax.scatter(d["fvr"], d["accuracy"], s=200, marker="o", color=llm_colors[i], 
                  edgecolors="black", linewidth=1.5, zorder=5)
        offset = (8, 5) if d["name"] != "GPT-4o-mini" else (8, -12)
        ax.annotate(d["name"], (d["fvr"], d["accuracy"]), 
                   xytext=offset, textcoords="offset points", fontsize=10, fontweight="bold")
    
    ax.set_xlabel("False Valid Rate (%)", fontsize=12)
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title("Safety-Utility Tradeoff: GPT-4o-mini achieves 0% FVR via near-universal rejection", 
                fontsize=12, fontweight="bold")
    ax.set_xlim(-5, 105)
    ax.set_ylim(25, 90)
    
    # Add annotation for GPT-4o-mini
    ax.annotate("GPT-4o-mini: 0% FVR but\n97.6% FIR (overcautious)",
               xy=(0, 63.8), xytext=(15, 50),
               arrowprops=dict(arrowstyle="->", color="#e67e22", lw=1.5),
               fontsize=10, color="#e67e22", fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e67e22"))
    
    # Add region labels
    ax.axvline(x=5, color="green", linestyle="--", alpha=0.3)
    ax.text(2, 30, "Safe\nRegion", fontsize=10, color="green", alpha=0.7, ha="center")
    ax.text(50, 30, "Dangerous Region", fontsize=10, color="red", alpha=0.7, ha="center")
    
    plt.tight_layout()
    plt.savefig(output_dir / "v4_tradeoff_scatter.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_tradeoff_scatter.png (updated with GPT-4o-mini)")
    
    # Figure 4: LLMs vs Baselines (updated)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Combine all models for comparison
    all_models = ["GPT-4o\n(Generic)", "GPT-4o\n(Spec.)", "Claude\nSonnet", "GPT-4o\n-mini", 
                  "Always\nInvalid", "Keyword", "Rule\nBased", "Always\nValid"]
    all_fvr = [4.7, 0.0, 1.2, 0.0, 0.0, 82.9, 81.4, 100.0]
    all_colors = ["#3498db", "#2ecc71", "#9b59b6", "#e67e22", 
                  "#95a5a6", "#95a5a6", "#95a5a6", "#95a5a6"]
    
    bars = ax.bar(all_models, all_fvr, color=all_colors, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("False Valid Rate (%)", fontsize=12)
    ax.set_title("LLMs vs Rule-Based Baselines: False-Valid Rate Comparison", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 110)
    
    for bar, rate in zip(bars, all_fvr):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f"{rate:.1f}%", ha="center", fontsize=10, fontweight="bold")
    
    # Add dividing line
    ax.axvline(x=3.5, color="black", linestyle="--", alpha=0.3)
    ax.text(1.5, 95, "LLMs", fontsize=11, ha="center", fontweight="bold")
    ax.text(5.5, 95, "Baselines", fontsize=11, ha="center", fontweight="bold", color="gray")
    
    ax.tick_params(axis='x', labelsize=9)
    plt.tight_layout()
    plt.savefig(output_dir / "v4_llm_vs_baselines.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_llm_vs_baselines.png (updated with GPT-4o-mini)")
    
    # Figure 5: Safety-Utility conceptual diagram (updated)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create conceptual scatter
    models_concept = [
        {"name": "GPT-4o Generic", "x": 83, "y": 4.7, "color": "#3498db"},
        {"name": "GPT-4o Specialized", "x": 80.9, "y": 0, "color": "#2ecc71"},
        {"name": "Claude Sonnet", "x": 78, "y": 1.2, "color": "#9b59b6"},
        {"name": "GPT-4o-mini", "x": 63.8, "y": 0, "color": "#e67e22"},
    ]
    
    for m in models_concept:
        ax.scatter(m["x"], m["y"], s=300, color=m["color"], edgecolors="black", linewidth=2, zorder=5)
        offset_y = 0.8 if m["y"] < 1 else -1.2
        ax.annotate(m["name"], (m["x"], m["y"]), 
                   xytext=(0, 15 if m["y"] > 0 else -20), textcoords="offset points",
                   ha="center", fontsize=10, fontweight="bold")
    
    ax.set_xlabel("Accuracy (%)", fontsize=12)
    ax.set_ylabel("False Valid Rate (%)", fontsize=12)
    ax.set_title("Safety-Utility Tradeoff: Higher Accuracy vs. Lower Dangerous Approvals", 
                fontsize=12, fontweight="bold")
    ax.set_xlim(55, 90)
    ax.set_ylim(-1, 7)
    
    # Add quadrant labels
    ax.axhline(y=2.5, color="gray", linestyle="--", alpha=0.3)
    ax.axvline(x=75, color="gray", linestyle="--", alpha=0.3)
    
    ax.text(82, 6, "High Accuracy\nSome Risk", fontsize=9, ha="center", color="gray")
    ax.text(65, 6, "Low Accuracy\nSome Risk", fontsize=9, ha="center", color="gray")
    ax.text(82, 0.5, "High Accuracy\nSafe", fontsize=9, ha="center", color="green")
    ax.text(65, 0.5, "Low Accuracy\nSafe (Overcautious)", fontsize=9, ha="center", color="#e67e22")
    
    plt.tight_layout()
    plt.savefig(output_dir / "safety_utility_tradeoff.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved safety_utility_tradeoff.png (updated with GPT-4o-mini)")
    
    print(f"\nAll figures saved to {output_dir}")
    print("\nFigures updated:")
    print("  1. v5_overall.png - Added GPT-4o-mini bar")
    print("  2. v5_false_valid_traps.png - Added GPT-4o-mini")
    print("  3. v4_tradeoff_scatter.png - Added GPT-4o-mini point with annotation")
    print("  4. v4_llm_vs_baselines.png - Added GPT-4o-mini bar")
    print("  5. safety_utility_tradeoff.png - Added GPT-4o-mini as overcautious region")


if __name__ == "__main__":
    main()
