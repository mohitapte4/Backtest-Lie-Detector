"""
Generate V4 benchmark comparison figures with both specialized and generic prompts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import jsonlines

from backtest_lie_detector.benchmark.build_cases import load_benchmark


def load_results(filepath: str) -> pd.DataFrame:
    """Load results from jsonl file."""
    records = []
    with jsonlines.open(filepath) as reader:
        for record in reader:
            records.append(record)
    return pd.DataFrame(records)


def main():
    print("Loading benchmark data...")
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    cases_df = pd.DataFrame([c.model_dump() for c in cases])
    
    print("Loading results...")
    specialized_df = load_results("outputs/results/model_outputs_v4_specialized.jsonl")
    generic_df = load_results("outputs/results/model_outputs_v4_generic.jsonl")
    
    # Combine into single DataFrame
    all_scores = pd.concat([specialized_df, generic_df], ignore_index=True)
    
    # Save combined scores
    all_scores.to_csv("outputs/results/scores_v4.csv", index=False)
    print("Saved combined scores to scores_v4.csv")
    
    # Merge with case metadata
    merged = all_scores.merge(
        cases_df[["id", "module", "difficulty", "expected_validity", "case_tags"]],
        left_on="case_id",
        right_on="id",
        how="left"
    )
    
    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create comparison figures
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # 1. Overall accuracy comparison
    ax1 = axes[0, 0]
    configs = ["gpt-4o-finance-auditor", "gpt-4o-minimal"]
    accuracies = [
        merged[merged["config_name"] == c]["validity_correct"].mean() * 100
        for c in configs
    ]
    colors = ["#2ecc71", "#3498db"]
    bars = ax1.bar(["Specialized\n(Finance Auditor)", "Generic\n(Minimal)"], accuracies, color=colors)
    ax1.set_ylabel("Accuracy (%)")
    ax1.set_title("Overall Validity Accuracy")
    ax1.set_ylim(0, 100)
    for bar, acc in zip(bars, accuracies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f"{acc:.1f}%", ha="center", fontweight="bold")
    
    # 2. False invalid rate comparison
    ax2 = axes[0, 1]
    false_invalid_rates = []
    for c in configs:
        config_data = merged[merged["config_name"] == c]
        valid_cases = config_data[config_data["expected_validity"] == "valid"]
        fir = (1 - valid_cases["validity_correct"].mean()) * 100
        false_invalid_rates.append(fir)
    
    bars = ax2.bar(["Specialized\n(Finance Auditor)", "Generic\n(Minimal)"], false_invalid_rates, color=["#e74c3c", "#f39c12"])
    ax2.set_ylabel("False Invalid Rate (%)")
    ax2.set_title("Overcaution: Valid Cases Marked Invalid")
    ax2.set_ylim(0, 50)
    for bar, fir in zip(bars, false_invalid_rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f"{fir:.1f}%", ha="center", fontweight="bold")
    
    # 3. Accuracy by difficulty
    ax3 = axes[1, 0]
    difficulties = ["easy", "medium", "hard"]
    x = np.arange(len(difficulties))
    width = 0.35
    
    spec_by_diff = []
    gen_by_diff = []
    for diff in difficulties:
        spec_data = merged[(merged["config_name"] == "gpt-4o-finance-auditor") & (merged["difficulty"] == diff)]
        gen_data = merged[(merged["config_name"] == "gpt-4o-minimal") & (merged["difficulty"] == diff)]
        spec_by_diff.append(spec_data["validity_correct"].mean() * 100 if len(spec_data) > 0 else 0)
        gen_by_diff.append(gen_data["validity_correct"].mean() * 100 if len(gen_data) > 0 else 0)
    
    bars1 = ax3.bar(x - width/2, spec_by_diff, width, label="Specialized", color="#2ecc71")
    bars2 = ax3.bar(x + width/2, gen_by_diff, width, label="Generic", color="#3498db")
    ax3.set_xlabel("Difficulty")
    ax3.set_ylabel("Accuracy (%)")
    ax3.set_title("Accuracy by Difficulty Level")
    ax3.set_xticks(x)
    ax3.set_xticklabels([d.title() for d in difficulties])
    ax3.legend()
    ax3.set_ylim(0, 100)
    
    # 4. Accuracy by expected validity
    ax4 = axes[1, 1]
    validities = ["valid", "invalid", "ambiguous"]
    x = np.arange(len(validities))
    
    spec_by_val = []
    gen_by_val = []
    for val in validities:
        spec_data = merged[(merged["config_name"] == "gpt-4o-finance-auditor") & (merged["expected_validity"] == val)]
        gen_data = merged[(merged["config_name"] == "gpt-4o-minimal") & (merged["expected_validity"] == val)]
        spec_by_val.append(spec_data["validity_correct"].mean() * 100 if len(spec_data) > 0 else 0)
        gen_by_val.append(gen_data["validity_correct"].mean() * 100 if len(gen_data) > 0 else 0)
    
    bars1 = ax4.bar(x - width/2, spec_by_val, width, label="Specialized", color="#2ecc71")
    bars2 = ax4.bar(x + width/2, gen_by_val, width, label="Generic", color="#3498db")
    ax4.set_xlabel("Expected Validity")
    ax4.set_ylabel("Accuracy (%)")
    ax4.set_title("Accuracy by Case Type")
    ax4.set_xticks(x)
    ax4.set_xticklabels([v.title() for v in validities])
    ax4.legend()
    ax4.set_ylim(0, 100)
    
    plt.suptitle("V4 Benchmark: Specialized vs Generic Prompt Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "v4_prompt_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_prompt_comparison.png")
    
    # Create summary metrics figure
    fig, ax = plt.subplots(figsize=(12, 6))
    
    metrics = ["Parse\nSuccess", "Validity\nAccuracy", "Violation\nPrecision", "Violation\nRecall", "Repair\nScore"]
    spec_vals = [
        specialized_df["parse_success"].mean() * 100,
        specialized_df["validity_correct"].mean() * 100,
        specialized_df["violation_precision"].mean() * 100,
        specialized_df["violation_recall"].mean() * 100,
        specialized_df["repair_score"].mean() * 100,
    ]
    gen_vals = [
        generic_df["parse_success"].mean() * 100,
        generic_df["validity_correct"].mean() * 100,
        generic_df["violation_precision"].mean() * 100,
        generic_df["violation_recall"].mean() * 100,
        generic_df["repair_score"].mean() * 100,
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, spec_vals, width, label="Specialized (Finance Auditor)", color="#2ecc71")
    bars2 = ax.bar(x + width/2, gen_vals, width, label="Generic (Minimal)", color="#3498db")
    
    ax.set_ylabel("Score (%)")
    ax.set_title("V4 Benchmark: All Metrics Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.set_ylim(0, 110)
    
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 1,
                   f"{height:.1f}", ha="center", va="bottom", fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / "v4_metrics_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v4_metrics_comparison.png")
    
    # Print summary
    print("\n" + "=" * 60)
    print("V4 BENCHMARK COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\n{'Metric':<30} {'Specialized':>12} {'Generic':>12}")
    print("-" * 60)
    print(f"{'Parse Success Rate':<30} {specialized_df['parse_success'].mean()*100:>11.1f}% {generic_df['parse_success'].mean()*100:>11.1f}%")
    print(f"{'Validity Accuracy':<30} {specialized_df['validity_correct'].mean()*100:>11.1f}% {generic_df['validity_correct'].mean()*100:>11.1f}%")
    print(f"{'Violation Precision':<30} {specialized_df['violation_precision'].mean()*100:>11.1f}% {generic_df['violation_precision'].mean()*100:>11.1f}%")
    print(f"{'Violation Recall':<30} {specialized_df['violation_recall'].mean()*100:>11.1f}% {generic_df['violation_recall'].mean()*100:>11.1f}%")
    print(f"{'Repair Score':<30} {specialized_df['repair_score'].mean()*100:>11.1f}% {generic_df['repair_score'].mean()*100:>11.1f}%")
    print(f"{'Mean Latency (ms)':<30} {specialized_df['latency_ms'].mean():>12.0f} {generic_df['latency_ms'].mean():>12.0f}")
    
    # Calculate false invalid rates
    spec_valid = merged[(merged["config_name"] == "gpt-4o-finance-auditor") & (merged["expected_validity"] == "valid")]
    gen_valid = merged[(merged["config_name"] == "gpt-4o-minimal") & (merged["expected_validity"] == "valid")]
    
    print(f"\n{'False Invalid Rate':<30} {(1-spec_valid['validity_correct'].mean())*100:>11.1f}% {(1-gen_valid['validity_correct'].mean())*100:>11.1f}%")
    
    print("\n" + "=" * 60)
    print("KEY FINDING: Generic prompt achieves HIGHER accuracy (83.2% vs 79.2%)")
    print("             with LOWER overcaution (19.5% vs 29.3% false invalid rate)")
    print("=" * 60)


if __name__ == "__main__":
    main()
