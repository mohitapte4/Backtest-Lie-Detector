"""
Generate V4 benchmark analysis figures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import matplotlib.pyplot as plt

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.analysis.plots import (
    setup_plot_style,
    plot_leaderboard,
    plot_module_breakdown,
    plot_difficulty_breakdown,
    plot_confidence_vs_accuracy,
    plot_calibration_breakdown,
    plot_overcaution_metrics,
    plot_v4_summary,
)


def main():
    # Load data
    print("Loading data...")
    
    scores_df = pd.read_csv("outputs/results/scores_v4.csv")
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    
    # Convert cases to DataFrame
    cases_df = pd.DataFrame([c.model_dump() for c in cases])
    cases_df.rename(columns={"id": "id"}, inplace=True)
    
    # Create output directory
    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter to only working configs (parse success > 50%)
    valid_configs = []
    for config in scores_df["config_name"].unique():
        config_scores = scores_df[scores_df["config_name"] == config]
        if config_scores["parse_success"].mean() > 0.5:
            valid_configs.append(config)
    
    print(f"Valid configs: {valid_configs}")
    
    if valid_configs:
        filtered_scores = scores_df[scores_df["config_name"].isin(valid_configs)]
    else:
        filtered_scores = scores_df
    
    # Generate plots
    print("Generating plots...")
    
    # 1. Leaderboard
    plot_leaderboard(
        filtered_scores, 
        str(output_dir / "v4_leaderboard.png"),
        title="V4 Benchmark Leaderboard"
    )
    plt.close()
    print("  - v4_leaderboard.png")
    
    # 2. Module breakdown
    plot_module_breakdown(
        filtered_scores, 
        cases_df,
        str(output_dir / "v4_module_accuracy.png"),
        title="V4 Accuracy by Module"
    )
    plt.close()
    print("  - v4_module_accuracy.png")
    
    # 3. Difficulty breakdown
    plot_difficulty_breakdown(
        filtered_scores,
        cases_df,
        str(output_dir / "v4_difficulty_breakdown.png"),
        title="V4 Accuracy by Difficulty"
    )
    plt.close()
    print("  - v4_difficulty_breakdown.png")
    
    # 4. Confidence vs accuracy
    if "confidence" in filtered_scores.columns:
        plot_confidence_vs_accuracy(
            filtered_scores,
            str(output_dir / "v4_confidence_calibration.png"),
            title="V4 Confidence Calibration"
        )
        plt.close()
        print("  - v4_confidence_calibration.png")
    
    # 5. Calibration breakdown
    plot_calibration_breakdown(
        filtered_scores,
        cases_df,
        str(output_dir / "v4_calibration_breakdown.png"),
        title="V4 Calibration Analysis"
    )
    plt.close()
    print("  - v4_calibration_breakdown.png")
    
    # 6. Overcaution metrics
    cal_df = pd.read_csv("outputs/results/calibration_scores_v4.csv")
    if not cal_df.empty and "config" in cal_df.columns:
        # Filter to valid configs
        cal_df = cal_df[cal_df["config"].isin([c.replace("gpt-4o-", "") for c in valid_configs] + valid_configs)]
        
        plot_overcaution_metrics(
            cal_df,
            str(output_dir / "v4_overcaution_analysis.png"),
            title="V4 Overcaution Analysis"
        )
        plt.close()
        print("  - v4_overcaution_analysis.png")
    
    # 7. Full summary
    plot_v4_summary(
        filtered_scores,
        cases_df,
        str(output_dir / "v4_summary.png"),
        title="Backtest Lie Detector V4 Results"
    )
    plt.close()
    print("  - v4_summary.png")
    
    print(f"\nAll plots saved to {output_dir}")


if __name__ == "__main__":
    main()
