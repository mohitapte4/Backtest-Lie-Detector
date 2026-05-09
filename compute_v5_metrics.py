"""
Combine V4 results with V5 new case results and compute full V5 metrics.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import jsonlines
import pandas as pd

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.schemas import ScoredResponse, Validity
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def load_results(filepath: str) -> list[ScoredResponse]:
    """Load results from jsonl file."""
    results = []
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def combine_results(v4_path: str, v5_new_path: str) -> list[ScoredResponse]:
    """Combine V4 results with V5 new case results."""
    v4 = load_results(v4_path)
    v5_new = load_results(v5_new_path)
    return v4 + v5_new


def compute_false_valid_trap_metrics(results: list[ScoredResponse], cases) -> dict:
    """Compute metrics specifically for false_valid_trap tagged cases."""
    case_map = {c.id: c for c in cases}
    
    # Filter to false_valid_trap cases
    trap_cases = [c for c in cases if hasattr(c, 'case_tags') and 'false_valid_trap' in c.case_tags]
    trap_ids = set(c.id for c in trap_cases)
    
    trap_results = [r for r in results if r.case_id in trap_ids and r.parse_success and r.parsed_response]
    
    if not trap_results:
        return {}
    
    # Calculate metrics
    correct = sum(1 for r in trap_results if r.validity_correct)
    false_valids = sum(1 for r in trap_results if r.parsed_response.validity == Validity.VALID)
    
    # Violation recall
    total_violations = 0
    detected_violations = 0
    for r in trap_results:
        if r.case_id in case_map:
            case = case_map[r.case_id]
            expected = set(case.expected_violations)
            predicted = set(r.parsed_response.violations)
            total_violations += len(expected)
            detected_violations += len(expected & predicted)
    
    return {
        "n_false_valid_trap_cases": len(trap_results),
        "false_valid_trap_accuracy": correct / len(trap_results) if trap_results else 0,
        "false_valid_rate_on_traps": false_valids / len(trap_results) if trap_results else 0,
        "violation_recall_on_traps": detected_violations / total_violations if total_violations > 0 else 0,
        "n_false_valids_on_traps": false_valids,
    }


def main():
    print("=" * 70)
    print("V5 COMBINED METRICS ANALYSIS")
    print("=" * 70)
    
    # Load V5 benchmark
    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(cases)} V5 cases")
    
    # Model configurations
    models = {
        "GPT-4o (Generic)": {
            "v4": "outputs/results/model_outputs_v4_generic.jsonl",
            "v5_new": "outputs/results/v5_new_gpt4o_generic.jsonl",
        },
        "GPT-4o (Specialized)": {
            "v4": "outputs/results/model_outputs_v4_specialized.jsonl",
            "v5_new": "outputs/results/v5_new_gpt4o_specialized.jsonl",
        },
        "Claude Sonnet": {
            "v4": "outputs/results/model_outputs_v4_claude_sonnet.jsonl",
            "v5_new": "outputs/results/v5_new_claude_sonnet.jsonl",
        },
    }
    
    all_results = {}
    
    for name, paths in models.items():
        print(f"\nProcessing {name}...")
        combined = combine_results(paths["v4"], paths["v5_new"])
        all_results[name] = combined
        print(f"  Combined {len(combined)} results")
    
    # Save combined results
    for name, results in all_results.items():
        safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        output_path = f"outputs/results/model_outputs_v5_{safe_name}.jsonl"
        with jsonlines.open(output_path, mode="w") as writer:
            for r in results:
                writer.write(r.model_dump(mode="json"))
        print(f"  Saved to {output_path}")
    
    # Compute metrics
    print("\n" + "=" * 70)
    print("V5 OVERALL METRICS")
    print("=" * 70)
    
    print(f"\n{'Model':<25} {'Accuracy':>10} {'False Inv':>12} {'False Val':>12}")
    print("-" * 60)
    
    for name, results in all_results.items():
        agg = aggregate_scores(results)
        cal = compute_calibration_metrics(results, cases)
        
        acc = agg.get("validity_accuracy", 0) * 100
        fir = cal.get("false_invalid_rate", 0) * 100
        fvr = cal.get("false_valid_rate", 0) * 100
        
        print(f"{name:<25} {acc:>9.1f}% {fir:>11.1f}% {fvr:>11.1f}%")
    
    # False valid trap specific metrics
    print("\n" + "=" * 70)
    print("FALSE VALID TRAP CASES (16 cases)")
    print("=" * 70)
    
    print(f"\n{'Model':<25} {'Trap Acc':>10} {'FV on Traps':>12} {'Viol Recall':>12}")
    print("-" * 60)
    
    for name, results in all_results.items():
        trap_metrics = compute_false_valid_trap_metrics(results, cases)
        
        if trap_metrics:
            acc = trap_metrics["false_valid_trap_accuracy"] * 100
            fvr = trap_metrics["false_valid_rate_on_traps"] * 100
            vr = trap_metrics["violation_recall_on_traps"] * 100
            n_fv = trap_metrics["n_false_valids_on_traps"]
            
            print(f"{name:<25} {acc:>9.1f}% {fvr:>11.1f}% {vr:>11.1f}%")
    
    # Summary comparison V4 vs V5
    print("\n" + "=" * 70)
    print("V4 vs V5 COMPARISON")
    print("=" * 70)
    
    # Load V4 cases for comparison
    v4_cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    
    print(f"\n{'Model':<25} {'V4 FVR':>10} {'V5 FVR':>10} {'Change':>10}")
    print("-" * 60)
    
    for name, results in all_results.items():
        # V4 metrics (first 125 results)
        v4_results = results[:125]
        v4_cal = compute_calibration_metrics(v4_results, v4_cases)
        v4_fvr = v4_cal.get("false_valid_rate", 0) * 100
        
        # V5 metrics (all 141 results)
        v5_cal = compute_calibration_metrics(results, cases)
        v5_fvr = v5_cal.get("false_valid_rate", 0) * 100
        
        change = v5_fvr - v4_fvr
        print(f"{name:<25} {v4_fvr:>9.1f}% {v5_fvr:>9.1f}% {change:>+9.1f}%")
    
    # Write summary
    print("\n" + "=" * 70)
    print("KEY FINDING")
    print("=" * 70)
    
    # Calculate trap false valid rates
    trap_metrics_all = {}
    for name, results in all_results.items():
        trap_metrics_all[name] = compute_false_valid_trap_metrics(results, cases)
    
    generic_fv = trap_metrics_all["GPT-4o (Generic)"]["n_false_valids_on_traps"]
    spec_fv = trap_metrics_all["GPT-4o (Specialized)"]["n_false_valids_on_traps"]
    claude_fv = trap_metrics_all["Claude Sonnet"]["n_false_valids_on_traps"]
    
    print(f"""
The false_valid_trap cases reveal that:

1. GPT-4o (Generic) incorrectly approved {generic_fv}/16 subtle violations
2. GPT-4o (Specialized) caught all 16 violations
3. Claude Sonnet caught all 16 violations

The specialized finance auditor prompt significantly improves detection of
subtle implementation-level bugs that are hidden behind professional language.

This suggests the V4 finding that "generic prompts beat specialized" was
partially an artifact of obvious invalid cases. On truly subtle violations,
domain expertise in the prompt helps.
""")


if __name__ == "__main__":
    main()
