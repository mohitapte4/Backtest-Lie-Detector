"""Generate all analysis figures."""

import sys
sys.path.insert(0, 'src')

import pandas as pd
from pathlib import Path

from backtest_lie_detector.evals.run_eval import load_results, load_benchmark
from backtest_lie_detector.evals.scoring import scores_to_dataframe
from backtest_lie_detector.analysis.plots import generate_all_plots

# Load results
scores = load_results('outputs/results/model_outputs.jsonl')
cases = load_benchmark('data/benchmark/benchmark_v1.jsonl')

# Convert to DataFrame
scores_df = scores_to_dataframe(scores)

# Create case DataFrame
cases_df = pd.DataFrame([{
    'id': c.id,
    'module': c.module.value,
    'difficulty': c.difficulty.value,
    'expected_validity': c.expected_validity.value,
    'expected_violations': ','.join(v.value for v in c.expected_violations),
} for c in cases])

# Generate all plots
print("Generating figures...")
plots = generate_all_plots(scores_df, cases_df, 'outputs/figures')

print("\nFigures saved:")
for name, path in plots.items():
    print(f"  - {name}: {path}")

# Also save results summary
print("\nSaving results summary...")
summary = scores_df.groupby('config_name').agg({
    'parse_success': 'mean',
    'validity_correct': 'mean',
    'violation_precision': 'mean',
    'violation_recall': 'mean',
    'violation_f1': 'mean',
    'severity_weighted_recall': 'mean',
    'repair_score': 'mean',
}).round(3)

summary.to_csv('outputs/results/leaderboard.csv')
scores_df.to_csv('outputs/results/scores.csv', index=False)

print("Results saved to outputs/results/")
print("\nDone!")
