"""Analyze v2 benchmark results with detailed failure breakdown."""

import sys
sys.path.insert(0, 'src')

import json
from collections import defaultdict
from backtest_lie_detector.schemas import Validity, ViolationType, BenchmarkCase
from backtest_lie_detector.benchmark.build_cases import generate_v2_cases


def load_results(path: str) -> list[dict]:
    """Load scored results from JSONL file."""
    results = []
    with open(path, 'r') as f:
        for line in f:
            results.append(json.loads(line))
    return results


def analyze_v2_results():
    """Analyze v2 benchmark results."""
    results = load_results('outputs/results/model_outputs_v2.jsonl')
    
    # Load case metadata
    cases = generate_v2_cases()
    case_map = {c.id: c for c in cases}
    
    # Enrich results with case metadata
    for r in results:
        case = case_map.get(r['case_id'])
        if case:
            r['module'] = case.module.value
            r['difficulty'] = case.difficulty.value
            r['expected_validity'] = case.expected_validity.value
            r['expected_violations'] = [v.value for v in case.expected_violations]
            r['prompt'] = case.prompt[:100] + '...' if len(case.prompt) > 100 else case.prompt
        if r.get('parsed_response'):
            r['predicted_validity'] = r['parsed_response'].get('validity', 'unknown')
            r['predicted_violations'] = r['parsed_response'].get('violations', [])
            r['confidence'] = r['parsed_response'].get('confidence', 0.5)
    
    print("=" * 70)
    print("V2 BENCHMARK RESULTS ANALYSIS")
    print("=" * 70)
    
    # Filter to just finance_auditor results
    fa_results = [r for r in results if 'finance_auditor' in r['config_name']]
    print(f"\nTotal results: {len(fa_results)}")
    
    # Overall metrics
    correct = sum(1 for r in fa_results if r['validity_correct'])
    total = len(fa_results)
    print(f"\nOverall Validity Accuracy: {correct}/{total} ({100*correct/total:.1f}%)")
    
    # Failures analysis
    failures = [r for r in fa_results if not r['validity_correct']]
    print(f"\nFailures: {len(failures)}")
    
    # Categorize failures
    false_invalids = [r for r in failures if r['expected_validity'] == 'valid']
    false_valids = [r for r in failures if r['expected_validity'] == 'invalid']
    
    print(f"\n  False Invalids (marked invalid when should be valid): {len(false_invalids)}")
    print(f"  False Valids (marked valid when should be invalid): {len(false_valids)}")
    
    # Detailed failure breakdown
    print("\n" + "-" * 70)
    print("DETAILED FAILURE ANALYSIS")
    print("-" * 70)
    
    for i, f in enumerate(failures, 1):
        print(f"\n{i}. Case: {f['case_id']}")
        print(f"   Module: {f['module']}")
        print(f"   Difficulty: {f['difficulty']}")
        print(f"   Expected: {f['expected_validity']}")
        print(f"   Predicted: {f['predicted_validity']}")
        if f['expected_violations']:
            print(f"   Expected violations: {f['expected_violations']}")
        if f['predicted_violations']:
            print(f"   Predicted violations: {f['predicted_violations']}")
    
    # By module
    print("\n" + "-" * 70)
    print("ACCURACY BY MODULE")
    print("-" * 70)
    
    by_module = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in fa_results:
        by_module[r['module']]['total'] += 1
        if r['validity_correct']:
            by_module[r['module']]['correct'] += 1
    
    for module, stats in sorted(by_module.items()):
        pct = 100 * stats['correct'] / stats['total']
        print(f"  {module}: {stats['correct']}/{stats['total']} ({pct:.1f}%)")
    
    # By difficulty
    print("\n" + "-" * 70)
    print("ACCURACY BY DIFFICULTY")
    print("-" * 70)
    
    by_difficulty = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in fa_results:
        by_difficulty[r['difficulty']]['total'] += 1
        if r['validity_correct']:
            by_difficulty[r['difficulty']]['correct'] += 1
    
    for diff in ['easy', 'medium', 'hard']:
        if diff in by_difficulty:
            stats = by_difficulty[diff]
            pct = 100 * stats['correct'] / stats['total']
            print(f"  {diff}: {stats['correct']}/{stats['total']} ({pct:.1f}%)")
    
    # Separate analysis for adversarial and WRDS cases
    print("\n" + "-" * 70)
    print("NEW CASE TYPES PERFORMANCE")
    print("-" * 70)
    
    adversarial = [r for r in fa_results if r['case_id'].startswith(('trap_', 'subtle_', 'multi_'))]
    wrds = [r for r in fa_results if r['case_id'].startswith('wrds_')]
    original = [r for r in fa_results if not r['case_id'].startswith(('trap_', 'subtle_', 'multi_', 'wrds_'))]
    
    for name, subset in [("Original (v1)", original), ("Adversarial", adversarial), ("WRDS-backed", wrds)]:
        if subset:
            correct = sum(1 for r in subset if r['validity_correct'])
            total = len(subset)
            print(f"  {name}: {correct}/{total} ({100*correct/total:.1f}%)")
    
    # Trap cases specifically
    trap_cases = [r for r in fa_results if r['case_id'].startswith('trap_')]
    if trap_cases:
        trap_correct = sum(1 for r in trap_cases if r['validity_correct'])
        print(f"\n  Trap Valid Cases (tests overcaution): {trap_correct}/{len(trap_cases)}")
        trap_failures = [r for r in trap_cases if not r['validity_correct']]
        if trap_failures:
            print("    Failures (incorrectly flagged as invalid):")
            for tf in trap_failures:
                print(f"      - {tf['case_id']}")
    
    # Multi-violation cases
    multi_cases = [r for r in fa_results if r['case_id'].startswith('multi_')]
    if multi_cases:
        multi_correct = sum(1 for r in multi_cases if r['validity_correct'])
        print(f"\n  Multi-Violation Cases: {multi_correct}/{len(multi_cases)}")
    
    # Violation detection analysis
    print("\n" + "-" * 70)
    print("VIOLATION DETECTION METRICS")
    print("-" * 70)
    
    total_precision = []
    total_recall = []
    
    for r in fa_results:
        if r['violation_precision'] is not None:
            total_precision.append(r['violation_precision'])
        if r['violation_recall'] is not None:
            total_recall.append(r['violation_recall'])
    
    if total_precision:
        avg_precision = sum(total_precision) / len(total_precision)
        print(f"  Average Precision: {avg_precision:.3f}")
    if total_recall:
        avg_recall = sum(total_recall) / len(total_recall)
        print(f"  Average Recall: {avg_recall:.3f}")
    
    # Confidence analysis
    print("\n" + "-" * 70)
    print("CONFIDENCE ANALYSIS")
    print("-" * 70)
    
    correct_confidences = [r.get('confidence', 0.5) for r in fa_results if r['validity_correct']]
    incorrect_confidences = [r.get('confidence', 0.5) for r in fa_results if not r['validity_correct']]
    
    if correct_confidences:
        print(f"  Mean confidence (correct): {sum(correct_confidences)/len(correct_confidences):.3f}")
    if incorrect_confidences:
        print(f"  Mean confidence (incorrect): {sum(incorrect_confidences)/len(incorrect_confidences):.3f}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    analyze_v2_results()
