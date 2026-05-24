"""Analyze v3 benchmark results with detailed failure breakdown."""

import sys
sys.path.insert(0, 'src')

import json
from collections import defaultdict
from backtest_lie_detector.benchmark.build_cases import generate_v3_cases


def load_results(path: str) -> list[dict]:
    """Load scored results from JSONL file."""
    results = []
    with open(path, 'r') as f:
        for line in f:
            results.append(json.loads(line))
    return results


def analyze_v3_results():
    """Analyze v3 benchmark results."""
    results = load_results('outputs/results/model_outputs_v3.jsonl')
    
    # Load case metadata
    cases = generate_v3_cases()
    case_map = {c.id: c for c in cases}
    
    # Enrich results with case metadata
    for r in results:
        case = case_map.get(r['case_id'])
        if case:
            r['module'] = case.module.value
            r['difficulty'] = case.difficulty.value
            r['expected_validity'] = case.expected_validity.value
            r['expected_violations'] = [v.value for v in case.expected_violations]
            r['prompt'] = case.prompt[:80] + '...' if len(case.prompt) > 80 else case.prompt
        if r.get('parsed_response'):
            r['predicted_validity'] = r['parsed_response'].get('validity', 'unknown')
            r['predicted_violations'] = r['parsed_response'].get('violations', [])
            r['confidence'] = r['parsed_response'].get('confidence', 0.5)
        
        # Determine case type
        if r['case_id'].startswith('hard_'):
            r['case_type'] = 'Hard (v3)'
        elif r['case_id'].startswith(('trap_', 'subtle_', 'multi_')):
            r['case_type'] = 'Adversarial (v2)'
        elif r['case_id'].startswith('wrds_'):
            r['case_type'] = 'WRDS-backed (v2)'
        else:
            r['case_type'] = 'Original (v1)'
    
    print("=" * 70)
    print("V3 BENCHMARK RESULTS ANALYSIS")
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
    print(f"\nTotal Failures: {len(failures)}")
    
    # Categorize failures
    false_invalids = [r for r in failures if r.get('expected_validity') == 'valid']
    false_valids = [r for r in failures if r.get('expected_validity') == 'invalid']
    ambiguous_errors = [r for r in failures if r.get('expected_validity') == 'ambiguous']
    
    print(f"\n  False Invalids (valid->invalid): {len(false_invalids)}")
    print(f"  False Valids (invalid->valid): {len(false_valids)}")
    print(f"  Ambiguous Errors: {len(ambiguous_errors)}")
    
    # By case type
    print("\n" + "-" * 70)
    print("ACCURACY BY CASE TYPE")
    print("-" * 70)
    
    by_type = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in fa_results:
        by_type[r['case_type']]['total'] += 1
        if r['validity_correct']:
            by_type[r['case_type']]['correct'] += 1
    
    for case_type in ['Original (v1)', 'Adversarial (v2)', 'WRDS-backed (v2)', 'Hard (v3)']:
        if case_type in by_type:
            stats = by_type[case_type]
            pct = 100 * stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            print(f"  {case_type}: {stats['correct']}/{stats['total']} ({pct:.1f}%)")
    
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
    
    # Hard case family analysis
    print("\n" + "-" * 70)
    print("HARD CASE FAMILY ANALYSIS")
    print("-" * 70)
    
    hard_results = [r for r in fa_results if r['case_type'] == 'Hard (v3)']
    families = defaultdict(lambda: {"correct": 0, "total": 0})
    
    for r in hard_results:
        case_id = r['case_id']
        # Extract family from case_id
        if 'ticker_s' in case_id or 'ticker_c' in case_id:
            family = "Ticker Reassignment"
        elif 'manville' in case_id or 'gm_old' in case_id:
            family = "Security Reorganization"
        elif 'meta' in case_id:
            family = "FB-to-META Timing"
        elif 'goog' in case_id:
            family = "GOOG vs GOOGL"
        elif 'ibm' in case_id or 'kyndryl' in case_id:
            family = "IBM/Kyndryl Spin-off"
        elif 'filing_5' in case_id or 'filing_before' in case_id or 'acceptance' in case_id:
            family = "SEC Filing Clock"
        elif 'sp500' in case_id:
            family = "S&P Index Timing"
        elif 'erroneous' in case_id:
            family = "Erroneous Announcements"
        elif 'compustat' in case_id:
            family = "Compustat PIT"
        elif 'xbrl' in case_id or 'factset' in case_id:
            family = "As-filed vs Standardized"
        elif 'adjusted' in case_id:
            family = "Adjusted Price"
        elif 'delisting' in case_id:
            family = "Delisting Return"
        elif 'earnings' in case_id:
            family = "Earnings Timing"
        else:
            family = "Other"
        
        families[family]['total'] += 1
        if r['validity_correct']:
            families[family]['correct'] += 1
    
    for family, stats in sorted(families.items(), key=lambda x: x[1]['total'], reverse=True):
        pct = 100 * stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {family}: {stats['correct']}/{stats['total']} ({pct:.1f}%)")
    
    # Detailed failure list
    print("\n" + "-" * 70)
    print("ALL FAILURES (sorted by case type)")
    print("-" * 70)
    
    failures_sorted = sorted(failures, key=lambda x: (x['case_type'], x['case_id']))
    
    for i, f in enumerate(failures_sorted, 1):
        print(f"\n{i}. {f['case_id']}")
        print(f"   Type: {f['case_type']} | Module: {f['module']} | Difficulty: {f['difficulty']}")
        print(f"   Expected: {f.get('expected_validity', '?')}, Predicted: {f.get('predicted_validity', '?')}")
        if f.get('expected_violations'):
            print(f"   Expected violations: {f['expected_violations'][:3]}")
        if f.get('predicted_violations'):
            print(f"   Predicted violations: {f['predicted_violations'][:3]}")
    
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
    
    # Ambiguous case performance
    print("\n" + "-" * 70)
    print("AMBIGUOUS CASE PERFORMANCE")
    print("-" * 70)
    
    ambiguous_cases = [r for r in fa_results if r.get('expected_validity') == 'ambiguous']
    print(f"  Total ambiguous cases: {len(ambiguous_cases)}")
    
    if ambiguous_cases:
        predictions = defaultdict(int)
        for r in ambiguous_cases:
            predictions[r.get('predicted_validity', 'unknown')] += 1
        
        for pred, count in sorted(predictions.items()):
            print(f"    Predicted as {pred}: {count}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"""
Benchmark Evolution:
  v1: 42 cases, 97.6% accuracy
  v2: 69 cases, 95.7% accuracy  
  v3: 105 cases, {100*correct/total:.1f}% accuracy

The hard cases successfully challenged the model:
  - Original cases: {by_type['Original (v1)']['correct']}/{by_type['Original (v1)']['total']} ({100*by_type['Original (v1)']['correct']/by_type['Original (v1)']['total']:.1f}%)
  - Hard v3 cases: {by_type['Hard (v3)']['correct']}/{by_type['Hard (v3)']['total']} ({100*by_type['Hard (v3)']['correct']/by_type['Hard (v3)']['total']:.1f}%)

Key failure modes:
  - False invalids (overcautious): {len(false_invalids)}
  - False valids (missed violations): {len(false_valids)}
  - Ambiguous misjudged: {len(ambiguous_errors)}
""")
    print("=" * 70)


if __name__ == "__main__":
    analyze_v3_results()
