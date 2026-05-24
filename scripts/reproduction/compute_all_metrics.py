"""
Compute detailed comparison metrics across all models and prompting strategies.

Loads GPT-4o and Claude results for V5 and V6-only benchmarks,
producing breakdowns by module, difficulty, and case tags.
"""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import jsonlines

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.benchmark.code_cases import CODE_CASES
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics
from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    ScoredResponse,
)

SCORED_RESPONSE_REQUIRED_FIELDS = {
    "case_id",
    "model_name",
    "raw_response",
    "parse_success",
    "validity_correct",
    "violation_precision",
    "violation_recall",
    "violation_f1",
    "severity_weighted_recall",
    "repair_score",
}


def load_results(filepath: str) -> list[ScoredResponse]:
    """Load BLD ScoredResponse results from a JSONL file.

    The results directory can also contain outputs from adjacent experiments
    (for example AA-Omniscience) with their own schema. Those files are not
    inputs to this BLD aggregate report, so skip them instead of failing during
    auto-discovery.
    """
    results = []
    if not Path(filepath).exists():
        return results
    with jsonlines.open(filepath) as reader:
        for record in reader:
            if not SCORED_RESPONSE_REQUIRED_FIELDS.issubset(record):
                return []
            results.append(ScoredResponse.model_validate(record))
    return results


def print_section(title: str):
    print(f"\n{'=' * 90}")
    print(title)
    print("=" * 90)


def compute_overall_metrics(results: list[ScoredResponse], cases) -> dict:
    """Compute overall metrics for a set of results."""
    if not results:
        return {}

    agg = aggregate_scores(results)
    cal = compute_calibration_metrics(results, cases)

    return {
        "accuracy": agg.get("validity_accuracy", 0),
        "parse_rate": agg.get("parse_success_rate", 0),
        "false_inv": cal.get("false_invalid_rate", 0),
        "false_val": cal.get("false_valid_rate", 0),
        "viol_f1": agg.get("mean_violation_f1", 0),
        "repair": agg.get("mean_repair_score", 0),
        "n": agg.get("total_cases", 0),
    }


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


def print_overview_table(all_results: dict, cases, title: str):
    """Print the main overview table for a set of results."""
    print_section(title)

    header = (
        f"{'Model / Strategy':<35} {'Acc':>7} {'Parse':>7} "
        f"{'F.Inv':>7} {'F.Val':>7} {'F1':>7} {'Repair':>7}"
    )
    print(f"\n{header}")
    print("-" * 80)

    for name, results in all_results.items():
        if not results:
            print(f"{name:<35} {'(no data)':>7}")
            continue

        m = compute_overall_metrics(results, cases)
        print(
            f"{name:<35} {m['accuracy']*100:>6.1f}% {m['parse_rate']*100:>6.1f}% "
            f"{m['false_inv']*100:>6.1f}% {m['false_val']*100:>6.1f}% "
            f"{m['viol_f1']*100:>6.1f}% {m['repair']*100:>6.1f}%"
        )


def print_breakdown_table(all_results: dict, cases, breakdown_fn, labels: list[str], title: str, label_col_width: int = 30):
    """Print a breakdown table (by module, difficulty, or tags)."""
    print_section(title)

    # Only include results that have data
    valid_names = [n for n in all_results if all_results[n]]
    if not valid_names:
        print("  No data available.")
        return

    header = f"{'':>{label_col_width}} " + " ".join(f"{n:>18}" for n in valid_names)
    print(f"\n{header}")
    print("-" * (label_col_width + 1 + 19 * len(valid_names)))

    breakdowns = {
        name: breakdown_fn(all_results[name], cases)
        for name in valid_names
    }

    for label in labels:
        row = f"{label:>{label_col_width}} "
        for name in valid_names:
            if label in breakdowns[name]:
                data = breakdowns[name][label]
                row += f"{data['accuracy']*100:>13.1f}% ({data['n']:>2})"
            else:
                row += f"{'—':>18}"
        print(row)


def main():
    # =========================================================================
    # Load benchmarks
    # =========================================================================
    v5_cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"Loaded {len(v5_cases)} V5 benchmark cases")

    v6_all = load_benchmark("data/benchmark/benchmark_v6.jsonl")
    v5_ids = set(c.id for c in v5_cases)
    v6_only_cases = [c for c in v6_all if c.id not in v5_ids]
    code_cases = [BenchmarkCase.model_validate(c) for c in CODE_CASES]
    v6_only_cases.extend(code_cases)
    print(f"Loaded {len(v6_only_cases)} V6-only cases (chronology + code)")

    # =========================================================================
    # Auto-discover all result files
    # =========================================================================
    results_dir = Path("outputs/results")

    def classify_result_file(filepath: Path, v5_ids: set) -> tuple[str, str]:
        """Classify a result file into a display name and benchmark type (v5/v6only).

        Returns (display_name, benchmark_type) where benchmark_type is
        'v5', 'v6only', or 'auto' (needs case ID inspection).
        """
        name = filepath.stem

        # Explicit v5/v6only suffix
        if name.endswith("_v5"):
            bench = "v5"
            name = name[:-3]
        elif name.endswith("_v6only"):
            bench = "v6only"
            name = name[:-7]
        else:
            bench = "auto"

        # Build display name from filename
        # Known prefixes → model name
        model_map = {
            "claude_sonnet45": "Sonnet 4.5",
            "claude_sonnet46": "Sonnet 4.6",
            "claude_haiku45": "Haiku 4.5",
            "claude_opus45": "Opus 4.5",
            "gpt4o": "GPT-4o",
            "gpt4o_mini": "GPT-4o Mini",
            "prompting": "GPT-4o",
        }

        strategy_map = {
            "minimal": "minimal",
            "default": "default",
            "zero_shot": "zero-shot",
            "few_shot": "few-shot",
            "cot": "cot",
            "chain_of_thought": "cot",
            "finance_auditor": "zero-shot",
        }

        display_model = None
        display_strat = None

        for prefix, model_label in sorted(model_map.items(), key=lambda x: -len(x[0])):
            if name.startswith(prefix + "_") or name == prefix:
                display_model = model_label
                remainder = name[len(prefix):].lstrip("_")
                for strat_key, strat_label in sorted(strategy_map.items(), key=lambda x: -len(x[0])):
                    if remainder == strat_key or remainder.startswith(strat_key):
                        display_strat = strat_label
                        break
                if not display_strat:
                    display_strat = remainder.replace("_", "-") if remainder else "default"
                break

        if not display_model:
            display_model = name.split("_")[0]
            remainder = "_".join(name.split("_")[1:])
            display_strat = remainder.replace("_", "-") if remainder else "unknown"

        display_name = f"{display_model} / {display_strat}"
        return display_name, bench

    print("\nAuto-discovering result files...")
    all_v5 = {}
    all_v6 = {}

    if results_dir.exists():
        for filepath in sorted(results_dir.glob("*.jsonl")):
            results = load_results(str(filepath))
            if not results:
                continue

            display_name, bench_type = classify_result_file(filepath, v5_ids)

            if bench_type == "v6only":
                all_v6[display_name] = results
                print(f"  [V6-only] {display_name}: {len(results)} results ({filepath.name})")
            elif bench_type == "v5":
                all_v5[display_name] = results
                print(f"  [V5]      {display_name}: {len(results)} results ({filepath.name})")
            else:
                # Auto-detect by checking case IDs
                result_ids = set(r.case_id for r in results)
                v5_overlap = len(result_ids & v5_ids)
                if v5_overlap > len(result_ids) * 0.5:
                    all_v5[display_name] = results
                    print(f"  [V5]      {display_name}: {len(results)} results ({filepath.name})")
                else:
                    all_v6[display_name] = results
                    print(f"  [V6-only] {display_name}: {len(results)} results ({filepath.name})")

    if not all_v5 and not all_v6:
        print("\nNo results found. Run the evaluation scripts first.")
        return

    # =========================================================================
    # V5 RESULTS
    # =========================================================================
    if all_v5:
        print_overview_table(all_v5, v5_cases, "V5 BENCHMARK — OVERALL METRICS (141 cases)")

        print_breakdown_table(
            all_v5, v5_cases,
            compute_module_breakdown,
            [m.value for m in Module],
            "V5 — ACCURACY BY MODULE",
            label_col_width=30,
        )

        print_breakdown_table(
            all_v5, v5_cases,
            compute_difficulty_breakdown,
            [d.value for d in Difficulty],
            "V5 — ACCURACY BY DIFFICULTY",
            label_col_width=15,
        )

        tags = ["trap_valid", "false_valid_trap", "near_miss", "ambiguous", "multi_violation"]
        print_breakdown_table(
            all_v5, v5_cases,
            lambda r, c: compute_tag_breakdown(r, c, tags),
            tags,
            "V5 — ACCURACY ON KEY CASE TAGS",
            label_col_width=22,
        )

        # Latency
        print_section("V5 — LATENCY COMPARISON")
        header = f"{'Model / Strategy':<35} {'Mean (ms)':>12} {'Median (ms)':>14} {'Max (ms)':>12}"
        print(f"\n{header}")
        print("-" * 75)

        for name, results in all_v5.items():
            latencies = [r.latency_ms for r in results if r.latency_ms > 0]
            if latencies:
                mean_lat = sum(latencies) / len(latencies)
                sorted_lat = sorted(latencies)
                median_lat = sorted_lat[len(sorted_lat) // 2]
                max_lat = max(latencies)
                print(f"{name:<35} {mean_lat:>11.0f} {median_lat:>13.0f} {max_lat:>11.0f}")

    # =========================================================================
    # V6-ONLY RESULTS
    # =========================================================================
    if all_v6:
        print_overview_table(all_v6, v6_only_cases, "V6-ONLY — OVERALL METRICS (chronology + code cases)")

    # =========================================================================
    # KEY FINDINGS
    # =========================================================================
    if all_v5:
        print_section("KEY FINDINGS — V5")

        best_acc_name = max(
            all_v5,
            key=lambda n: compute_overall_metrics(all_v5[n], v5_cases).get("accuracy", 0),
        )
        best_acc = compute_overall_metrics(all_v5[best_acc_name], v5_cases)["accuracy"]

        safest_name = min(
            all_v5,
            key=lambda n: compute_overall_metrics(all_v5[n], v5_cases).get("false_val", 1),
        )
        safest_fvr = compute_overall_metrics(all_v5[safest_name], v5_cases)["false_val"]

        least_overcautious = min(
            all_v5,
            key=lambda n: compute_overall_metrics(all_v5[n], v5_cases).get("false_inv", 1),
        )
        least_fi = compute_overall_metrics(all_v5[least_overcautious], v5_cases)["false_inv"]

        print(f"""
1. HIGHEST ACCURACY:        {best_acc_name} ({best_acc*100:.1f}%)
2. SAFEST (lowest FVR):     {safest_name} ({safest_fvr*100:.1f}%)
3. LEAST OVERCAUTIOUS:      {least_overcautious} ({least_fi*100:.1f}% false invalid)

Reminder:
- False invalid = overcaution (flags valid workflows as broken)
- False valid  = missed violations (approves broken workflows)
- For production use, low false valid rate matters most
""")

    print("=" * 90)


def main_with_save():
    """Run main() and save output to a summary file."""
    old_stdout = sys.stdout
    buffer = io.StringIO()
    sys.stdout = TeeOutput(old_stdout, buffer)

    main()

    sys.stdout = old_stdout

    summary_path = "outputs/results/ALL_EVALUATION_RESULTS.txt"
    Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())

    print(f"\nSummary saved to: {summary_path}")


class TeeOutput:
    """Write to both a stream and a buffer simultaneously."""
    def __init__(self, stream, buffer):
        self.stream = stream
        self.buffer = buffer

    def write(self, data):
        self.stream.write(data)
        self.buffer.write(data)

    def flush(self):
        self.stream.flush()
        self.buffer.flush()


if __name__ == "__main__":
    main_with_save()
