"""
Compute detailed comparison metrics for prompting strategy evaluation.

Loads zero-shot, few-shot, and chain-of-thought results and produces
a breakdown by module, difficulty, and case tags.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import jsonlines
import pandas as pd

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.schemas import ScoredResponse, Validity, Module, Difficulty
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def load_results(filepath: str) -> list[ScoredResponse]:
    """Load results from jsonl file."""
    results = []
    if not Path(filepath).exists():
        print(f"  WARNING: {filepath} not found")
        return results
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def print_section(title: str):
    print(f"\n{'=' * 70}")
    print(title)
    print("=" * 70)


def compute_module_breakdown(results: list[ScoredResponse], cases) -> dict:
    """Compute accuracy broken down by module."""
    case_map = {c.id: c for c in cases}
    breakdown = {}

    for module in Module:
        module_results = [
            r for r in results
            if r.case_id in case_map
            and case_map[r.case_id].module == module
            and r.parse_success
        ]
        if not module_results:
            continue

        correct = sum(1 for r in module_results if r.validity_correct)
        breakdown[module.value] = {
            "n": len(module_results),
            "accuracy": correct / len(module_results),
        }

    return breakdown


def compute_difficulty_breakdown(results: list[ScoredResponse], cases) -> dict:
    """Compute accuracy broken down by difficulty."""
    case_map = {c.id: c for c in cases}
    breakdown = {}

    for diff in Difficulty:
        diff_results = [
            r for r in results
            if r.case_id in case_map
            and case_map[r.case_id].difficulty == diff
            and r.parse_success
        ]
        if not diff_results:
            continue

        correct = sum(1 for r in diff_results if r.validity_correct)
        breakdown[diff.value] = {
            "n": len(diff_results),
            "accuracy": correct / len(diff_results),
        }

    return breakdown


def compute_tag_breakdown(results: list[ScoredResponse], cases, tags: list[str]) -> dict:
    """Compute accuracy for specific case tags."""
    case_map = {c.id: c for c in cases}
    breakdown = {}

    for tag in tags:
        tag_cases = [
            c for c in cases
            if hasattr(c, "case_tags") and tag in c.case_tags
        ]
        tag_ids = set(c.id for c in tag_cases)

        tag_results = [
            r for r in results
            if r.case_id in tag_ids and r.parse_success
        ]
        if not tag_results:
            continue

        correct = sum(1 for r in tag_results if r.validity_correct)
        breakdown[tag] = {
            "n": len(tag_results),
            "accuracy": correct / len(tag_results),
        }

    return breakdown


def main():
    print_section("PROMPTING STRATEGY COMPARISON — DETAILED METRICS")

    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(cases)} V5 benchmark cases")

    strategies = {
        "Zero-Shot": "outputs/results/prompting_zero_shot.jsonl",
        "Few-Shot (3)": "outputs/results/prompting_few_shot.jsonl",
        "Chain-of-Thought": "outputs/results/prompting_cot.jsonl",
    }

    all_results = {}
    for name, path in strategies.items():
        all_results[name] = load_results(path)
        print(f"  {name}: {len(all_results[name])} results loaded")

    if not any(all_results.values()):
        print("\nNo results found. Run run_prompting_comparison.py first.")
        return

    # --- Overall metrics ---
    print_section("OVERALL METRICS")

    header = (
        f"{'Strategy':<22} {'Accuracy':>10} {'Parse':>8} "
        f"{'False Inv':>11} {'False Val':>11} {'Viol F1':>9} {'Repair':>8}"
    )
    print(f"\n{header}")
    print("-" * 82)

    for name, results in all_results.items():
        if not results:
            print(f"{name:<22} {'(no data)':>10}")
            continue

        agg = aggregate_scores(results)
        cal = compute_calibration_metrics(results, cases)

        acc = agg.get("validity_accuracy", 0) * 100
        parse = agg.get("parse_success_rate", 0) * 100
        f1 = agg.get("mean_violation_f1", 0) * 100
        repair = agg.get("mean_repair_score", 0) * 100
        fir = cal.get("false_invalid_rate", 0) * 100
        fvr = cal.get("false_valid_rate", 0) * 100

        print(
            f"{name:<22} {acc:>9.1f}% {parse:>7.1f}% "
            f"{fir:>10.1f}% {fvr:>10.1f}% {f1:>8.1f}% {repair:>7.1f}%"
        )

    # --- Module breakdown ---
    print_section("ACCURACY BY MODULE")

    modules = [m.value for m in Module]
    header = f"{'Module':<30} " + " ".join(f"{n:>16}" for n in all_results.keys())
    print(f"\n{header}")
    print("-" * (30 + 17 * len(all_results)))

    module_data = {
        name: compute_module_breakdown(results, cases)
        for name, results in all_results.items()
        if results
    }

    for mod in modules:
        row = f"{mod:<30} "
        for name in all_results.keys():
            if name in module_data and mod in module_data[name]:
                data = module_data[name][mod]
                row += f"{data['accuracy']*100:>12.1f}% ({data['n']:>2})"
            else:
                row += f"{'—':>16}"
        print(row)

    # --- Difficulty breakdown ---
    print_section("ACCURACY BY DIFFICULTY")

    header = f"{'Difficulty':<15} " + " ".join(f"{n:>16}" for n in all_results.keys())
    print(f"\n{header}")
    print("-" * (15 + 17 * len(all_results)))

    diff_data = {
        name: compute_difficulty_breakdown(results, cases)
        for name, results in all_results.items()
        if results
    }

    for diff in [d.value for d in Difficulty]:
        row = f"{diff:<15} "
        for name in all_results.keys():
            if name in diff_data and diff in diff_data[name]:
                data = diff_data[name][diff]
                row += f"{data['accuracy']*100:>12.1f}% ({data['n']:>2})"
            else:
                row += f"{'—':>16}"
        print(row)

    # --- Key tag breakdown ---
    print_section("ACCURACY ON KEY CASE TAGS")

    tags = ["trap_valid", "false_valid_trap", "near_miss", "ambiguous", "multi_violation"]

    header = f"{'Tag':<22} " + " ".join(f"{n:>16}" for n in all_results.keys())
    print(f"\n{header}")
    print("-" * (22 + 17 * len(all_results)))

    tag_data = {
        name: compute_tag_breakdown(results, cases, tags)
        for name, results in all_results.items()
        if results
    }

    for tag in tags:
        row = f"{tag:<22} "
        for name in all_results.keys():
            if name in tag_data and tag in tag_data[name]:
                data = tag_data[name][tag]
                row += f"{data['accuracy']*100:>12.1f}% ({data['n']:>2})"
            else:
                row += f"{'—':>16}"
        print(row)

    # --- Latency comparison ---
    print_section("LATENCY COMPARISON")

    header = f"{'Strategy':<22} {'Mean (ms)':>12} {'Median (ms)':>14} {'Max (ms)':>12}"
    print(f"\n{header}")
    print("-" * 62)

    for name, results in all_results.items():
        if not results:
            continue

        latencies = [r.latency_ms for r in results if r.latency_ms > 0]
        if latencies:
            mean_lat = sum(latencies) / len(latencies)
            sorted_lat = sorted(latencies)
            median_lat = sorted_lat[len(sorted_lat) // 2]
            max_lat = max(latencies)
            print(
                f"{name:<22} {mean_lat:>11.0f} {median_lat:>13.0f} {max_lat:>11.0f}"
            )

    # --- Key findings ---
    print_section("KEY FINDINGS")

    valid_strategies = {n: r for n, r in all_results.items() if r}

    if len(valid_strategies) >= 2:
        best_acc_name = max(
            valid_strategies,
            key=lambda n: aggregate_scores(valid_strategies[n]).get("validity_accuracy", 0),
        )
        best_acc = aggregate_scores(valid_strategies[best_acc_name]).get("validity_accuracy", 0)

        safest_name = min(
            valid_strategies,
            key=lambda n: compute_calibration_metrics(valid_strategies[n], cases).get("false_valid_rate", 1),
        )
        safest_fvr = compute_calibration_metrics(valid_strategies[safest_name], cases).get("false_valid_rate", 0)

        print(f"""
1. HIGHEST ACCURACY: {best_acc_name} ({best_acc*100:.1f}%)
2. LOWEST FALSE VALID RATE (safest): {safest_name} ({safest_fvr*100:.1f}%)

Reminder:
- False invalid = overcaution (flags valid workflows as broken)
- False valid  = missed violations (approves broken workflows)
- For production use, low false valid rate matters most
""")
    else:
        print("\nNeed at least 2 strategies with results to compare.")

    print("=" * 70)


if __name__ == "__main__":
    main()
