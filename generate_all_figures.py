"""
Generate comparison figures for all models and prompting strategies.

Produces charts for V5 and V6-only benchmarks across GPT-4o and Claude models
with minimal, default, zero-shot, few-shot, and chain-of-thought strategies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
import jsonlines

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.benchmark.code_cases import CODE_CASES
from backtest_lie_detector.schemas import BenchmarkCase, ScoredResponse, Validity, Module, Difficulty
from backtest_lie_detector.evals.scoring import aggregate_scores, compute_calibration_metrics


def load_results(filepath: str) -> list[ScoredResponse]:
    results = []
    if not Path(filepath).exists():
        return results
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def get_metrics(results, cases):
    if not results:
        return None
    agg = aggregate_scores(results)
    cal = compute_calibration_metrics(results, cases)
    return {
        "accuracy": agg.get("validity_accuracy", 0) * 100,
        "false_inv": cal.get("false_invalid_rate", 0) * 100,
        "false_val": cal.get("false_valid_rate", 0) * 100,
        "viol_f1": agg.get("mean_violation_f1", 0) * 100,
    }


def main():
    print("Loading benchmarks...")
    v5_cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")

    v6_all = load_benchmark("data/benchmark/benchmark_v6.jsonl")
    v5_ids = set(c.id for c in v5_cases)
    v6_only_cases = [c for c in v6_all if c.id not in v5_ids]
    code_cases = [BenchmarkCase.model_validate(c) for c in CODE_CASES]
    v6_only_cases.extend(code_cases)

    output_dir = Path("outputs/figures")
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Auto-discover V5 results ---
    strategy_labels = ["minimal", "default", "zero-shot", "few-shot", "cot"]
    strategy_keys = ["minimal", "default", "zero_shot", "few_shot", "cot"]

    strategy_map = {
        "minimal": "minimal", "default": "default",
        "zero_shot": "zero_shot", "zero-shot": "zero_shot",
        "few_shot": "few_shot", "few-shot": "few_shot",
        "cot": "cot", "chain_of_thought": "cot",
    }

    model_prefix_map = {
        "claude_sonnet45": "Sonnet 4.5",
        "claude_sonnet46": "Sonnet 4.6",
        "claude_haiku45": "Haiku 4.5",
        "claude_opus45": "Opus 4.5",
        "gpt4o_mini": "GPT-4o Mini",
        "gpt4o": "GPT-4o",
        "prompting": "GPT-4o",
    }

    results_dir = Path("outputs/results")
    models = {}

    if results_dir.exists():
        for filepath in sorted(results_dir.glob("*.jsonl")):
            name = filepath.stem

            # Determine if V5 or V6
            is_v5 = name.endswith("_v5") or (not name.endswith("_v6only") and "v6only" not in name)
            if not is_v5:
                continue

            clean = name.replace("_v5", "")

            model_label = None
            strat_key = None
            for prefix, label in sorted(model_prefix_map.items(), key=lambda x: -len(x[0])):
                if clean.startswith(prefix + "_") or clean == prefix:
                    model_label = label
                    remainder = clean[len(prefix):].lstrip("_")
                    for skey, mapped in sorted(strategy_map.items(), key=lambda x: -len(x[0])):
                        if remainder == skey:
                            strat_key = mapped
                            break
                    break

            if not model_label or not strat_key:
                continue

            if model_label not in models:
                models[model_label] = {}
            models[model_label][strat_key] = str(filepath)

    v5_data = {}
    for model, strats in models.items():
        v5_data[model] = {}
        for strat_key, path in strats.items():
            results = load_results(path)
            if results:
                v5_data[model][strat_key] = get_metrics(results, v5_cases)

    active_models = [m for m in models if v5_data[m]]
    if not active_models:
        print("No results found. Run evaluation scripts first.")
        return

    print(f"Found {len(active_models)} models: {', '.join(active_models)}")

    # Colors for strategies
    strat_colors = {
        "minimal": "#95a5a6",
        "default": "#7f8c8d",
        "zero_shot": "#3498db",
        "few_shot": "#2ecc71",
        "cot": "#e74c3c",
    }

    model_colors = {
        "GPT-4o": "#3498db",
        "Sonnet 4.5": "#9b59b6",
        "Sonnet 4.6": "#e74c3c",
        "Haiku 4.5": "#f39c12",
    }

    # =========================================================================
    # Figure 1: Accuracy by Strategy (grouped bar chart)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(14, 6))

    x = np.arange(len(active_models))
    n_strats = len(strategy_keys)
    width = 0.15

    for i, (strat_key, strat_label) in enumerate(zip(strategy_keys, strategy_labels)):
        accs = []
        for model in active_models:
            m = v5_data[model].get(strat_key)
            accs.append(m["accuracy"] if m else 0)

        bars = ax.bar(x + (i - n_strats/2 + 0.5) * width, accs, width,
                      label=strat_label, color=strat_colors[strat_key])

        for bar, acc in zip(bars, accs):
            if acc > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{acc:.0f}", ha="center", fontsize=7, fontweight="bold")

    ax.set_ylabel("Accuracy (%)")
    ax.set_title("V5 Benchmark: Accuracy by Model and Prompting Strategy", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(active_models)
    ax.legend(title="Strategy")
    ax.set_ylim(0, 100)
    ax.axhline(y=80, color="gray", linestyle="--", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / "all_accuracy_by_strategy.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved all_accuracy_by_strategy.png")

    # =========================================================================
    # Figure 2: False Invalid vs False Valid (scatter plot)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 8))

    markers = {"minimal": "s", "default": "D", "zero_shot": "o", "few_shot": "^", "cot": "*"}

    for model in active_models:
        for strat_key, strat_label in zip(strategy_keys, strategy_labels):
            m = v5_data[model].get(strat_key)
            if not m:
                continue
            ax.scatter(m["false_inv"], m["false_val"],
                       color=model_colors[model],
                       marker=markers[strat_key],
                       s=120, zorder=5,
                       label=f"{model} / {strat_label}")

    ax.set_xlabel("False Invalid Rate (%) — Overcaution →", fontsize=12)
    ax.set_ylabel("False Valid Rate (%) — Missed Violations →", fontsize=12)
    ax.set_title("Safety vs. Overcaution Trade-off", fontsize=14, fontweight="bold")

    ax.axhline(y=2, color="red", linestyle="--", alpha=0.3)
    ax.text(1, 2.3, "2% false valid threshold", fontsize=8, color="red", alpha=0.5)

    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=7)
    plt.tight_layout()
    plt.savefig(output_dir / "all_safety_vs_overcaution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved all_safety_vs_overcaution.png")

    # =========================================================================
    # Figure 3: Strategy comparison (one subplot per metric)
    # =========================================================================
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    metric_keys = ["accuracy", "false_inv", "false_val"]
    metric_labels = ["Accuracy (%)", "False Invalid Rate (%)", "False Valid Rate (%)"]
    metric_titles = ["Higher is Better", "Lower is Better (Overcaution)", "Lower is Better (Safety)"]

    for ax, mkey, mlabel, mtitle in zip(axes, metric_keys, metric_labels, metric_titles):
        x = np.arange(len(strategy_labels))

        for i, model in enumerate(active_models):
            vals = []
            for strat_key in strategy_keys:
                m = v5_data[model].get(strat_key)
                vals.append(m[mkey] if m else 0)

            ax.plot(x, vals, marker="o", label=model, color=model_colors[model], linewidth=2)

        ax.set_xticks(x)
        ax.set_xticklabels(strategy_labels, rotation=45, ha="right")
        ax.set_ylabel(mlabel)
        ax.set_title(mtitle)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    plt.suptitle("V5 Benchmark: How Prompting Strategy Affects Each Metric", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "all_strategy_trends.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved all_strategy_trends.png")

    # =========================================================================
    # Figure 4: Accuracy by difficulty (heatmap style)
    # =========================================================================
    fig, ax = plt.subplots(figsize=(14, 6))

    all_combos = []
    combo_labels = []
    for model in active_models:
        for strat_key, strat_label in zip(strategy_keys, strategy_labels):
            if v5_data[model].get(strat_key):
                all_combos.append((model, strat_key))
                combo_labels.append(f"{model}\n{strat_label}")

    case_map = {c.id: c for c in v5_cases}
    diff_labels = [d.value for d in Difficulty]

    heatmap_data = []
    for model, strat_key in all_combos:
        path = models[model][strat_key]
        results = load_results(path)
        row = []
        for diff in Difficulty:
            diff_results = [
                r for r in results
                if r.case_id in case_map
                and case_map[r.case_id].difficulty == diff
                and r.parse_success
            ]
            if diff_results:
                correct = sum(1 for r in diff_results if r.validity_correct)
                row.append(correct / len(diff_results) * 100)
            else:
                row.append(0)
        heatmap_data.append(row)

    heatmap_data = np.array(heatmap_data)

    im = ax.imshow(heatmap_data.T, cmap="RdYlGn", aspect="auto", vmin=50, vmax=100)

    ax.set_xticks(range(len(combo_labels)))
    ax.set_xticklabels(combo_labels, rotation=90, fontsize=7, ha="center")
    ax.set_yticks(range(len(diff_labels)))
    ax.set_yticklabels(diff_labels)
    ax.set_title("Accuracy by Difficulty Level", fontsize=14, fontweight="bold")

    for i in range(heatmap_data.shape[0]):
        for j in range(heatmap_data.shape[1]):
            val = heatmap_data[i, j]
            color = "white" if val < 70 else "black"
            ax.text(i, j, f"{val:.0f}%", ha="center", va="center", fontsize=7, color=color)

    plt.colorbar(im, label="Accuracy (%)")
    plt.tight_layout()
    plt.savefig(output_dir / "all_difficulty_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved all_difficulty_heatmap.png")

    # =========================================================================
    # Figure 5: Module breakdown (grouped bars per model, best strategy highlighted)
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    module_list = list(Module)
    case_map = {c.id: c for c in v5_cases}

    for ax, module in zip(axes.flat, module_list):
        x = np.arange(len(active_models))

        for i, (strat_key, strat_label) in enumerate(zip(strategy_keys, strategy_labels)):
            accs = []
            for model in active_models:
                path = models[model].get(strat_key, "")
                results = load_results(path)
                mod_results = [
                    r for r in results
                    if r.case_id in case_map
                    and case_map[r.case_id].module == module
                    and r.parse_success
                ]
                if mod_results:
                    correct = sum(1 for r in mod_results if r.validity_correct)
                    accs.append(correct / len(mod_results) * 100)
                else:
                    accs.append(0)

            ax.bar(x + (i - n_strats/2 + 0.5) * width, accs, width,
                   label=strat_label, color=strat_colors[strat_key])

        ax.set_xticks(x)
        ax.set_xticklabels(active_models, fontsize=9)
        ax.set_ylabel("Accuracy (%)")
        ax.set_title(module.value.replace("_", " ").title(), fontweight="bold")
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.2, axis="y")

    axes[0, 0].legend(title="Strategy", fontsize=7, title_fontsize=8)
    plt.suptitle("V5 Benchmark: Accuracy by Module", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "all_module_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved all_module_breakdown.png")

    # =========================================================================
    # Figure 6: V6-only results (if available)
    # =========================================================================
    # Auto-discover V6-only results
    v6_models = {}
    if results_dir.exists():
        for filepath in sorted(results_dir.glob("*_v6only.jsonl")):
            name = filepath.stem.replace("_v6only", "")

            model_label = None
            strat_key = None
            for prefix, label in sorted(model_prefix_map.items(), key=lambda x: -len(x[0])):
                if name.startswith(prefix + "_") or name == prefix:
                    model_label = label
                    remainder = name[len(prefix):].lstrip("_")
                    for skey, mapped in sorted(strategy_map.items(), key=lambda x: -len(x[0])):
                        if remainder == skey:
                            strat_key = mapped
                            break
                    break

            if not model_label or not strat_key:
                continue

            if model_label not in v6_models:
                v6_models[model_label] = {}
            v6_models[model_label][strat_key] = str(filepath)

    v6_data = {}
    has_v6 = False
    for model, strats in v6_models.items():
        v6_data[model] = {}
        for strat_key, path in strats.items():
            results = load_results(path)
            if results:
                v6_data[model][strat_key] = get_metrics(results, v6_only_cases)
                has_v6 = True

    if has_v6:
        v6_active = [m for m in v6_models if v6_data[m]]

        fig, ax = plt.subplots(figsize=(14, 6))

        x = np.arange(len(v6_active))
        for i, (strat_key, strat_label) in enumerate(zip(strategy_keys, strategy_labels)):
            accs = []
            for model in v6_active:
                m = v6_data[model].get(strat_key)
                accs.append(m["accuracy"] if m else 0)

            bars = ax.bar(x + (i - n_strats/2 + 0.5) * width, accs, width,
                          label=strat_label, color=strat_colors[strat_key])

            for bar, acc in zip(bars, accs):
                if acc > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                            f"{acc:.0f}", ha="center", fontsize=7, fontweight="bold")

        ax.set_ylabel("Accuracy (%)")
        ax.set_title("V6-Only Cases: Chronology + Code (New Case Types)", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(v6_active)
        ax.legend(title="Strategy")
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(output_dir / "all_v6only_accuracy.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("Saved all_v6only_accuracy.png")

    print(f"\nAll figures saved to {output_dir}/")


if __name__ == "__main__":
    main()
