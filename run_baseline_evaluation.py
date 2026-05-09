"""
Evaluate rule-based baselines on V4 benchmark.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.baselines.rule_baseline import (
    AlwaysInvalidBaseline,
    AlwaysValidBaseline,
    KeywordSuspicionBaseline,
    RuleBasedClassifier,
    run_baseline_evaluation,
)
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def main():
    print("=" * 70)
    print("BASELINE EVALUATION ON V4 BENCHMARK")
    print("=" * 70)
    
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    print(f"\nLoaded {len(cases)} cases")
    
    baselines = [
        AlwaysInvalidBaseline(),
        AlwaysValidBaseline(),
        KeywordSuspicionBaseline(),
        RuleBasedClassifier(),
    ]
    
    results = {}
    
    for baseline in baselines:
        print(f"\n{'='*50}")
        print(f"Baseline: {baseline.name}")
        print("=" * 50)
        
        scores = run_baseline_evaluation(cases, baseline)
        results[baseline.name] = scores
        
        agg = aggregate_scores(scores)
        print(f"  Validity Accuracy: {agg['validity_accuracy']:.1%}")
        print(f"  Violation F1: {agg['mean_violation_f1']:.1%}")
        
        cal = compute_calibration_metrics(scores, cases)
        if cal:
            print(f"  False Invalid Rate: {cal.get('false_invalid_rate', 0):.1%}")
            print(f"  False Valid Rate: {cal.get('false_valid_rate', 0):.1%}")
    
    # Summary table
    print("\n" + "=" * 70)
    print("BASELINE COMPARISON SUMMARY")
    print("=" * 70)
    print(f"\n{'Baseline':<25} {'Accuracy':>10} {'False Inv':>12} {'False Val':>12}")
    print("-" * 60)
    
    for name, scores in results.items():
        agg = aggregate_scores(scores)
        cal = compute_calibration_metrics(scores, cases)
        acc = agg['validity_accuracy']
        fir = cal.get('false_invalid_rate', 0) if cal else 0
        fvr = cal.get('false_valid_rate', 0) if cal else 0
        print(f"{name:<25} {acc:>9.1%} {fir:>11.1%} {fvr:>11.1%}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
