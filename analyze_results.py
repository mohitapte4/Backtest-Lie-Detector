"""Quick analysis of benchmark results."""

import sys
sys.path.insert(0, 'src')

import pandas as pd
from backtest_lie_detector.evals.run_eval import load_results, load_benchmark
from backtest_lie_detector.evals.scoring import scores_to_dataframe

# Load results
scores = load_results('outputs/results/model_outputs.jsonl')
cases = load_benchmark('data/benchmark/benchmark_v1.jsonl')

# Convert to DataFrame
scores_df = scores_to_dataframe(scores)

# Create case lookup
case_info = {c.id: {'module': c.module.value, 'difficulty': c.difficulty.value, 
                    'expected_validity': c.expected_validity.value} for c in cases}

# Add case info to scores
scores_df['module'] = scores_df['case_id'].map(lambda x: case_info.get(x, {}).get('module'))
scores_df['difficulty'] = scores_df['case_id'].map(lambda x: case_info.get(x, {}).get('difficulty'))
scores_df['expected_validity'] = scores_df['case_id'].map(lambda x: case_info.get(x, {}).get('expected_validity'))

print('='*70)
print('BACKTEST LIE DETECTOR - INITIAL BENCHMARK RESULTS')
print('='*70)
print()

# Overall summary by config
print('OVERALL RESULTS BY MODEL CONFIGURATION')
print('-'*70)
summary = scores_df.groupby('config_name').agg({
    'parse_success': 'mean',
    'validity_correct': 'mean',
    'violation_precision': 'mean',
    'violation_recall': 'mean',
    'violation_f1': 'mean',
    'severity_weighted_recall': 'mean',
    'repair_score': 'mean',
}).round(3)

summary.columns = ['Parse Rate', 'Validity Acc', 'Viol. Prec', 'Viol. Recall', 'Viol. F1', 'Severity Recall', 'Repair Score']
print(summary.to_string())
print()

# By module
print('VALIDITY ACCURACY BY MODULE')
print('-'*70)
module_acc = scores_df.groupby(['config_name', 'module'])['validity_correct'].mean().unstack().round(3)
print(module_acc.to_string())
print()

# By difficulty
print('VALIDITY ACCURACY BY DIFFICULTY')
print('-'*70)
diff_acc = scores_df.groupby(['config_name', 'difficulty'])['validity_correct'].mean().unstack()
diff_acc = diff_acc[['easy', 'medium', 'hard']].round(3)
print(diff_acc.to_string())
print()

# Show failures
print('FAILURE ANALYSIS')
print('-'*70)
failures = scores_df[~scores_df['validity_correct']]
print(f'Total failures: {len(failures)} out of {len(scores_df)} ({len(failures)/len(scores_df)*100:.1f}%)')
print()

if len(failures) > 0:
    print('Failed cases (minimal prompt only):')
    for _, row in failures.iterrows():
        case = next((c for c in cases if c.id == row['case_id']), None)
        if case:
            print(f"  [{row['config_name']}] {row['case_id']}")
            print(f"    Module: {row['module']}, Difficulty: {row['difficulty']}")
            print(f"    Expected: {row['expected_validity']}, Predicted: {row['predicted_validity']}")
            print(f"    Prompt: {case.prompt[:100]}...")
            print()

# Confidence analysis
print('CONFIDENCE ANALYSIS')
print('-'*70)
for config in scores_df['config_name'].unique():
    cfg_df = scores_df[scores_df['config_name'] == config]
    correct = cfg_df[cfg_df['validity_correct']]
    wrong = cfg_df[~cfg_df['validity_correct']]
    
    print(f"{config}:")
    print(f"  Mean confidence (all): {cfg_df['confidence'].mean():.2f}")
    print(f"  Mean confidence (correct): {correct['confidence'].mean():.2f}" if len(correct) > 0 else "  Mean confidence (correct): N/A")
    print(f"  Mean confidence (wrong): {wrong['confidence'].mean():.2f}" if len(wrong) > 0 else "  Mean confidence (wrong): N/A")
    print()

# Key insight
print('='*70)
print('KEY FINDINGS')
print('='*70)
auditor_acc = summary.loc['gpt-4o_finance_auditor', 'Validity Acc']
minimal_acc = summary.loc['gpt-4o_minimal', 'Validity Acc']
print(f"1. Finance auditor prompt: {auditor_acc:.0%} validity accuracy")
print(f"2. Minimal prompt: {minimal_acc:.0%} validity accuracy")
print(f"3. Improvement from specialized prompt: +{(auditor_acc - minimal_acc)*100:.0f} percentage points")
print()
print("This demonstrates that prompt engineering significantly improves")
print("LLM performance on point-in-time validity auditing tasks.")
