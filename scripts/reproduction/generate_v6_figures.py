"""
Generate V6 figures: chronology cases (pure temporal reasoning) and
code cases (auditing actual code instead of prose).

Reads:
    outputs/results/v6_chronology_{gpt4o_generic,gpt4o_specialized,claude_sonnet}.jsonl
    outputs/results/code_cases_{gpt4o_generic,gpt4o_specialized,claude_sonnet}.jsonl
Writes:
    outputs/figures/v6_chronology.png
    outputs/figures/v6_code.png
    outputs/figures/v6_overcaution_pattern.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt
import jsonlines

from backtest_lie_detector.schemas import ScoredResponse, Validity
from backtest_lie_detector.benchmark.build_cases import (
    get_chronology_cases_only,
    get_code_cases_only,
)


MODELS = [
    ("GPT-4o\n(Generic)",     "gpt4o_generic",     "#3498db"),
    ("GPT-4o\n(Specialized)", "gpt4o_specialized", "#2ecc71"),
    ("Claude\nSonnet",        "claude_sonnet",     "#9b59b6"),
]


def load_results(path: Path) -> list[ScoredResponse]:
    with jsonlines.open(path) as reader:
        return [ScoredResponse.model_validate(r) for r in reader]


def split_accuracies(results: list[ScoredResponse], cases) -> tuple[float, float, float]:
    """Return (overall, valid-only, invalid-only) accuracy as percentages."""
    case_map = {c.id: c for c in cases}
    parsed = [r for r in results if r.parse_success and r.parsed_response and r.case_id in case_map]
    if not parsed:
        return 0.0, 0.0, 0.0

    valid_r   = [r for r in parsed if case_map[r.case_id].expected_validity == Validity.VALID]
    invalid_r = [r for r in parsed if case_map[r.case_id].expected_validity == Validity.INVALID]

    overall = 100 * sum(r.validity_correct for r in parsed)   / len(parsed)
    valid   = 100 * sum(r.validity_correct for r in valid_r)  / len(valid_r)   if valid_r   else 0.0
    invalid = 100 * sum(r.validity_correct for r in invalid_r)/ len(invalid_r) if invalid_r else 0.0
    return overall, valid, invalid


def grouped_bar_chart(
    ax,
    model_labels: list[str],
    series: dict[str, list[float]],
    colors: list[str],
    ylabel: str,
    title: str,
    ymax: float = 110.0,
):
    """Plot grouped bars: one cluster per model, one bar per series."""
    n_groups = len(model_labels)
    n_series = len(series)
    x = np.arange(n_groups)
    width = 0.8 / n_series

    for i, (label, values) in enumerate(series.items()):
        offset = (i - (n_series - 1) / 2) * width
        bars = ax.bar(x + offset, values, width, label=label, color=colors[i])
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                    f"{v:.0f}%", ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(model_labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(0, ymax)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.3)


def main():
    results_dir = Path("outputs/results")
    figures_dir = Path("outputs/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Chronology ----------
    chrono_cases = get_chronology_cases_only()
    print(f"Loaded {len(chrono_cases)} chronology cases")

    chrono_overall, chrono_valid, chrono_invalid = [], [], []
    for _, slug, _ in MODELS:
        path = results_dir / f"v6_chronology_{slug}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Missing chronology results: {path}")
        o, v, i = split_accuracies(load_results(path), chrono_cases)
        chrono_overall.append(o); chrono_valid.append(v); chrono_invalid.append(i)

    fig, ax = plt.subplots(figsize=(10, 6))
    grouped_bar_chart(
        ax,
        model_labels=[m[0] for m in MODELS],
        series={
            "Overall":         chrono_overall,
            "Valid cases":     chrono_valid,
            "Invalid cases":   chrono_invalid,
        },
        colors=["#34495e", "#27ae60", "#c0392b"],
        ylabel="Accuracy (%)",
        title=f"V6 Chronology Cases: Pure Temporal Reasoning ({len(chrono_cases)} cases)",
    )
    fig.text(0.5, -0.02,
             "All models hit ~100% on invalid cases but flag many valid cases as invalid — "
             "overcaution generalizes beyond finance domain.",
             ha="center", fontsize=9, style="italic", color="#555")
    plt.tight_layout()
    plt.savefig(figures_dir / "v6_chronology.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v6_chronology.png")

    # ---------- Code ----------
    code_cases = get_code_cases_only()
    print(f"Loaded {len(code_cases)} code cases")

    code_overall, code_bug, code_trap = [], [], []
    for _, slug, _ in MODELS:
        path = results_dir / f"code_cases_{slug}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Missing code-case results: {path}")
        # bug detection = accuracy on invalid; trap valid = accuracy on valid
        o, valid_acc, invalid_acc = split_accuracies(load_results(path), code_cases)
        code_overall.append(o); code_bug.append(invalid_acc); code_trap.append(valid_acc)

    fig, ax = plt.subplots(figsize=(10, 6))
    grouped_bar_chart(
        ax,
        model_labels=[m[0] for m in MODELS],
        series={
            "Overall":           code_overall,
            "Bug detection":     code_bug,
            "Trap-valid (correct code)": code_trap,
        },
        colors=["#34495e", "#c0392b", "#27ae60"],
        ylabel="Accuracy (%)",
        title=f"V6 Code Cases: Auditing Python Code ({len(code_cases)} cases)",
    )
    fig.text(0.5, -0.02,
             "Claude leads on catching bugs (100%) but flags every correct snippet — "
             "the prompt paradox flips when the workflow is code.",
             ha="center", fontsize=9, style="italic", color="#555")
    plt.tight_layout()
    plt.savefig(figures_dir / "v6_code.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v6_code.png")

    # ---------- Overcaution pattern across V6 ----------
    fig, ax = plt.subplots(figsize=(10, 6))
    grouped_bar_chart(
        ax,
        model_labels=[m[0] for m in MODELS],
        series={
            "Chronology — valid":  chrono_valid,
            "Chronology — invalid": chrono_invalid,
            "Code — valid (trap)":  code_trap,
            "Code — invalid (bug)": code_bug,
        },
        colors=["#16a085", "#27ae60", "#e67e22", "#c0392b"],
        ylabel="Accuracy (%)",
        title="V6: Overcaution Persists Across Pure Temporal and Code Tasks",
    )
    fig.text(0.5, -0.02,
             "Across both task types, accuracy on invalid >> accuracy on valid for every model.",
             ha="center", fontsize=9, style="italic", color="#555")
    plt.tight_layout()
    plt.savefig(figures_dir / "v6_overcaution_pattern.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved v6_overcaution_pattern.png")

    print(f"\nAll V6 figures saved to {figures_dir}")


if __name__ == "__main__":
    main()
