"""
Build interactive Plotly charts for the Backtest Lie Detector results.

Each chart-building function is pure: takes loaded data, returns a
plotly.graph_objects.Figure. The main() orchestrator loads all data, builds
the figures, and writes them to docs/charts/ as both standalone HTML files
(viewable on their own) and snippet HTML files (to be embedded into
docs/index.html).

The notebook (notebooks/00_main_report.ipynb) imports these same functions
to render the figures interactively in Jupyter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import jsonlines
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from backtest_lie_detector.benchmark.build_cases import (
    generate_v5_cases,
    get_chronology_cases_only,
    get_code_cases_only,
)
from backtest_lie_detector.evals.scoring import (
    aggregate_scores,
    compute_calibration_metrics,
)
from backtest_lie_detector.schemas import ScoredResponse, Validity


# =============================================================================
# Style — AA-Omniscience-inspired clean palette
# =============================================================================

MODEL_COLORS = {
    "Haiku 4.5":  "#e67e22",
    "Sonnet 4.5": "#9b59b6",
    "Sonnet 4.6": "#e74c3c",
    "GPT-4o":     "#2980b9",
}
STRATEGY_SYMBOLS = {
    "minimal":   "square",
    "default":   "diamond",
    "zero_shot": "circle",
    "few_shot":  "triangle-up",
    "cot":       "star",
}
STRATEGIES = ["minimal", "default", "zero_shot", "few_shot", "cot"]
MODELS = [
    ("Haiku 4.5",  "claude_haiku45_{strat}_v5.jsonl"),
    ("Sonnet 4.5", "claude_sonnet45_{strat}_v5.jsonl"),
    ("Sonnet 4.6", "claude_sonnet46_{strat}_v5.jsonl"),
    ("GPT-4o",     "prompting_{strat}.jsonl"),
]

BASE_LAYOUT = dict(
    font=dict(family="Helvetica, Arial, sans-serif", size=13, color="#2c3e50"),
    paper_bgcolor="white",
    plot_bgcolor="#f8f9fa",
    margin=dict(l=60, r=30, t=60, b=60),
    hovermode="closest",
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#dfe4ea", borderwidth=1),
)


# =============================================================================
# Data loading helpers
# =============================================================================


def load_results_jsonl(path: Path) -> list[ScoredResponse]:
    with jsonlines.open(path) as r:
        return [ScoredResponse.model_validate(rec) for rec in r]


def build_leaderboard_df(results_dir: Path) -> pd.DataFrame:
    v5 = generate_v5_cases()
    rows = []
    for model_label, pattern in MODELS:
        for strat in STRATEGIES:
            path = results_dir / pattern.format(strat=strat)
            if not path.exists():
                continue
            results = load_results_jsonl(path)
            agg = aggregate_scores(results)
            cal = compute_calibration_metrics(results, v5)
            rows.append({
                "model":              model_label,
                "strategy":           strat,
                "accuracy_pct":       round(agg["validity_accuracy"] * 100, 1),
                "false_invalid_pct":  round(cal["false_invalid_rate"] * 100, 1),
                "false_valid_pct":    round(cal["false_valid_rate"] * 100, 1),
                "viol_f1_pct":        round(agg["mean_violation_f1"] * 100, 1),
                "repair_score_pct":   round(agg["mean_repair_score"] * 100, 1),
                "mean_latency_ms":    round(agg["mean_latency_ms"], 0),
            })
    return pd.DataFrame(rows)


def build_trap_df(results_dir: Path) -> pd.DataFrame:
    v5 = generate_v5_cases()
    trap_ids = {c.id for c in v5 if "false_valid_trap" in (c.case_tags or [])}
    rows = []
    for model_label, pattern in MODELS:
        for strat in STRATEGIES:
            path = results_dir / pattern.format(strat=strat)
            if not path.exists():
                continue
            results = [r for r in load_results_jsonl(path) if r.case_id in trap_ids]
            if not results:
                continue
            n_correct = sum(r.validity_correct for r in results)
            n_approved = sum(
                1 for r in results
                if r.parsed_response and r.parsed_response.validity == Validity.VALID
            )
            rows.append({
                "model":             model_label,
                "strategy":          strat,
                "trap_accuracy_pct": round(100 * n_correct / len(results), 1),
                "approved_as_valid": n_approved,
                "n_traps":           len(results),
            })
    return pd.DataFrame(rows)


def build_v6_df(results_dir: Path) -> pd.DataFrame:
    chrono = get_chronology_cases_only()
    code = get_code_cases_only()
    chrono_map = {c.id: c for c in chrono}
    code_map = {c.id: c for c in code}

    def acc(results, case_map):
        parsed = [r for r in results if r.parse_success and r.case_id in case_map]
        valid_r   = [r for r in parsed if case_map[r.case_id].expected_validity == Validity.VALID]
        invalid_r = [r for r in parsed if case_map[r.case_id].expected_validity == Validity.INVALID]
        return dict(
            overall=round(100 * sum(r.validity_correct for r in parsed) / max(len(parsed), 1), 1),
            valid  =round(100 * sum(r.validity_correct for r in valid_r)  / max(len(valid_r), 1), 1),
            invalid=round(100 * sum(r.validity_correct for r in invalid_r)/ max(len(invalid_r), 1), 1),
        )

    configs = [
        ("GPT-4o (Generic)",     "v6_chronology_gpt4o_generic.jsonl",     "code_cases_gpt4o_generic.jsonl"),
        ("GPT-4o (Specialized)", "v6_chronology_gpt4o_specialized.jsonl", "code_cases_gpt4o_specialized.jsonl"),
        ("Claude Sonnet 4.5",    "v6_chronology_claude_sonnet.jsonl",     "code_cases_claude_sonnet.jsonl"),
    ]
    rows = []
    for label, chrono_file, code_file in configs:
        chrono_a = acc(load_results_jsonl(results_dir / chrono_file), chrono_map)
        code_a   = acc(load_results_jsonl(results_dir / code_file),   code_map)
        rows.append({
            "config":              label,
            "chrono_overall":      chrono_a["overall"],
            "chrono_valid":        chrono_a["valid"],
            "chrono_invalid":      chrono_a["invalid"],
            "code_overall":        code_a["overall"],
            "code_bug_detect":     code_a["invalid"],
            "code_trap_valid":     code_a["valid"],
        })
    return pd.DataFrame(rows)


def build_aa_df(results_dir: Path) -> pd.DataFrame:
    configs = [
        ("GPT-4o (Generic)",        "aa_omniscience_gpt4o_generic.jsonl"),
        ("GPT-4o (BLD Specialized)", "aa_omniscience_gpt4o_specialized.jsonl"),
        ("Claude Sonnet (BLD)",      "aa_omniscience_claude_sonnet.jsonl"),
    ]
    rows = []
    for label, fname in configs:
        grades = []
        with jsonlines.open(results_dir / fname) as r:
            for rec in r:
                grades.append(rec["grade"])
        c = sum(1 for g in grades if g == "CORRECT")
        p = sum(1 for g in grades if g == "PARTIALLY_CORRECT")
        i = sum(1 for g in grades if g == "INCORRECT")
        a = sum(1 for g in grades if g == "NOT_ATTEMPTED")
        total = c + p + i + a
        rows.append({
            "config":         label,
            "oi_index":       round(100 * (c - i) / total, 1) if total else 0.0,
            "halluc_pct":     round(100 * i / max(p + i + a, 1), 1),
            "correct":        c,
            "abstained":      a,
            "incorrect":      i,
        })
    return pd.DataFrame(rows)


# =============================================================================
# Chart-building functions (pure: take data, return Figure)
# =============================================================================


def fig_leaderboard(df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart: x = model, color = strategy, y = accuracy. Rich hover."""
    fig = go.Figure()
    for strat in STRATEGIES:
        sub = df[df["strategy"] == strat]
        sub = sub.set_index("model").reindex([m for m, _ in MODELS]).reset_index()
        hover_text = [
            f"<b>{r['model']} / {strat}</b><br>"
            f"Accuracy: {r['accuracy_pct']}%<br>"
            f"False invalid: {r['false_invalid_pct']}%<br>"
            f"False valid: {r['false_valid_pct']}%<br>"
            f"Violation F1: {r['viol_f1_pct']}%<br>"
            f"Repair score: {r['repair_score_pct']}%<br>"
            f"Mean latency: {int(r['mean_latency_ms'])} ms"
            for _, r in sub.iterrows()
        ]
        fig.add_trace(go.Bar(
            name=strat,
            x=sub["model"],
            y=sub["accuracy_pct"],
            text=[f"{v:.0f}%" if pd.notna(v) else "" for v in sub["accuracy_pct"]],
            textposition="outside",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
        ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="V5 accuracy by model and prompting strategy",
        xaxis_title="",
        yaxis_title="Accuracy (%)",
        yaxis=dict(range=[0, 100], gridcolor="#dfe4ea"),
        barmode="group",
        height=480,
    )
    return fig


def fig_safety_overcaution(df: pd.DataFrame) -> go.Figure:
    """Scatter: X = false_invalid, Y = false_valid. Color by model, symbol by strategy.

    The signature chart — every config as a single point. The 2% threshold
    line separates safe (below) from dangerous (above).
    """
    fig = go.Figure()
    for model in [m for m, _ in MODELS]:
        sub = df[df["model"] == model]
        for _, row in sub.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["false_invalid_pct"]],
                y=[row["false_valid_pct"]],
                mode="markers",
                marker=dict(
                    color=MODEL_COLORS[model],
                    symbol=STRATEGY_SYMBOLS[row["strategy"]],
                    size=14,
                    line=dict(color="white", width=1),
                ),
                name=f"{model} / {row['strategy']}",
                legendgroup=model,
                showlegend=False,  # we use custom legend traces below
                hovertemplate=(
                    f"<b>{model} / {row['strategy']}</b><br>"
                    f"Accuracy: {row['accuracy_pct']}%<br>"
                    f"False invalid: {row['false_invalid_pct']}%<br>"
                    f"False valid: {row['false_valid_pct']}%<br>"
                    "<extra></extra>"
                ),
            ))

    # Legend proxies for models (one entry per model)
    for model in [m for m, _ in MODELS]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(color=MODEL_COLORS[model], size=12),
            name=model, legendgroup="models", legendgrouptitle_text="Model",
        ))
    # Legend proxies for strategies
    for strat in STRATEGIES:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(color="#7f8c8d", symbol=STRATEGY_SYMBOLS[strat], size=12),
            name=strat, legendgroup="strategies", legendgrouptitle_text="Strategy",
        ))

    # 2% false-valid threshold line
    fig.add_hline(
        y=2.0, line_dash="dash", line_color="#e74c3c", opacity=0.6,
        annotation_text="2% false-valid safety threshold",
        annotation_position="top right",
        annotation=dict(font=dict(color="#e74c3c", size=11)),
    )

    fig.update_layout(
        **BASE_LAYOUT,
        title="Safety vs overcaution — the signature view",
        xaxis_title="False-invalid rate (overcaution) →",
        yaxis_title="False-valid rate (missed violations) →",
        xaxis=dict(gridcolor="#dfe4ea"),
        yaxis=dict(gridcolor="#dfe4ea"),
        height=540,
    )
    return fig


def fig_trap_cases(df: pd.DataFrame) -> go.Figure:
    """Bar chart of trap accuracy with approved-as-valid counts in tooltip + text."""
    df = df.copy()
    df["label"] = df["model"] + " / " + df["strategy"]
    df = df.sort_values("approved_as_valid", ascending=True).reset_index(drop=True)

    colors = [
        "#27ae60" if a == 0 else "#e67e22" if a <= 2 else "#c0392b"
        for a in df["approved_as_valid"]
    ]
    hover = [
        f"<b>{r['model']} / {r['strategy']}</b><br>"
        f"Trap accuracy: {r['trap_accuracy_pct']}% ({int(r['trap_accuracy_pct']/100*r['n_traps'])}/{int(r['n_traps'])})<br>"
        f"<b>Approved as valid: {int(r['approved_as_valid'])}/{int(r['n_traps'])}</b><br>"
        f"(green = 0 approvals, orange = 1-2, red = 3+)"
        for _, r in df.iterrows()
    ]

    fig = go.Figure(go.Bar(
        x=df["trap_accuracy_pct"],
        y=df["label"],
        orientation="h",
        marker=dict(color=colors),
        text=[
            f"{r['trap_accuracy_pct']:.0f}%  ({int(r['approved_as_valid'])} approved)"
            for _, r in df.iterrows()
        ],
        textposition="auto",
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
    ))
    layout = {**BASE_LAYOUT, "margin": dict(l=180, r=30, t=60, b=60)}
    fig.update_layout(
        **layout,
        title="Performance on the 16 V5 false-valid trap cases",
        xaxis_title="Trap accuracy (%)",
        yaxis_title="",
        xaxis=dict(range=[0, 110], gridcolor="#dfe4ea"),
        height=640,
    )
    return fig


def fig_v6(df: pd.DataFrame) -> go.Figure:
    """Side-by-side bars: each config shown for chronology and code metrics."""
    fig = go.Figure()
    metrics = [
        ("Chronology — overall",    "chrono_overall",  "#16a085"),
        ("Chronology — valid",      "chrono_valid",    "#27ae60"),
        ("Chronology — invalid",    "chrono_invalid",  "#2ecc71"),
        ("Code — overall",          "code_overall",    "#e67e22"),
        ("Code — bug detection",    "code_bug_detect", "#c0392b"),
        ("Code — trap-valid",       "code_trap_valid", "#f39c12"),
    ]
    for label, col, color in metrics:
        fig.add_trace(go.Bar(
            name=label,
            x=df["config"],
            y=df[col],
            text=[f"{v:.0f}%" for v in df[col]],
            textposition="outside",
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{label}: %{{y}}%<extra></extra>",
        ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="V6 batteries: chronology (15 cases) + code (12 cases)",
        xaxis_title="",
        yaxis_title="Accuracy (%)",
        yaxis=dict(range=[0, 110], gridcolor="#dfe4ea"),
        barmode="group",
        height=540,
    )
    return fig


def fig_aa_omniscience(df: pd.DataFrame) -> go.Figure:
    """OI vs hallucination rate scatter, our 3 configs + published reference points."""
    fig = go.Figure()
    # Our results
    config_colors = {
        "GPT-4o (Generic)":         "#3498db",
        "GPT-4o (BLD Specialized)": "#2ecc71",
        "Claude Sonnet (BLD)":      "#9b59b6",
    }
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["halluc_pct"]],
            y=[row["oi_index"]],
            mode="markers+text",
            marker=dict(
                color=config_colors.get(row["config"], "#34495e"),
                size=20,
                line=dict(color="white", width=2),
            ),
            text=[row["config"]],
            textposition="top center",
            name=row["config"],
            hovertemplate=(
                f"<b>{row['config']}</b><br>"
                f"OI index: {row['oi_index']}<br>"
                f"Hallucination rate: {row['halluc_pct']}%<br>"
                f"Correct: {int(row['correct'])} / "
                f"Incorrect: {int(row['incorrect'])} / "
                f"Abstained: {int(row['abstained'])}"
                "<extra></extra>"
            ),
        ))

    # Published AA-Omniscience Business-domain reference points (from the writeup)
    published = [
        ("GPT-4o (published Business)",  38.0, -6.0),
        ("Claude Sonnet (published)",    29.0,  1.0),
    ]
    for label, hr, oi in published:
        fig.add_trace(go.Scatter(
            x=[hr], y=[oi],
            mode="markers+text",
            marker=dict(color="#bdc3c7", size=16, symbol="x", line=dict(width=2)),
            text=[label], textposition="bottom center",
            name=label,
            hovertemplate=f"<b>{label}</b><br>Published OI: {oi}<br>Hallucination rate: {hr}%<extra></extra>",
            showlegend=False,
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="#7f8c8d", opacity=0.5,
                  annotation_text="OI = 0 (correct = incorrect)",
                  annotation_position="bottom right",
                  annotation=dict(font=dict(color="#7f8c8d", size=11)))

    fig.update_layout(
        **BASE_LAYOUT,
        title="AA-Omniscience finance recall: BLD prompt vs published",
        xaxis_title="Hallucination rate (%) →",
        yaxis_title="Omniscience Index (higher = better)",
        xaxis=dict(gridcolor="#dfe4ea"),
        yaxis=dict(gridcolor="#dfe4ea", zerolinecolor="#bdc3c7"),
        height=520,
        showlegend=False,
    )
    return fig


# =============================================================================
# Main
# =============================================================================


CHART_BUILDERS = [
    ("leaderboard",        fig_leaderboard,        build_leaderboard_df),
    ("safety_overcaution", fig_safety_overcaution, build_leaderboard_df),
    ("trap_cases",         fig_trap_cases,         build_trap_df),
    ("v6_batteries",       fig_v6,                 build_v6_df),
    ("aa_omniscience",     fig_aa_omniscience,     build_aa_df),
]


def main():
    results_dir = REPO_ROOT / "outputs" / "results"
    charts_dir = REPO_ROOT / "docs" / "charts"
    snippets_dir = charts_dir / "snippets"
    charts_dir.mkdir(parents=True, exist_ok=True)
    snippets_dir.mkdir(parents=True, exist_ok=True)

    # Cache the dataframes that get reused.
    df_cache: dict = {}

    for name, fig_fn, df_fn in CHART_BUILDERS:
        if df_fn not in df_cache:
            df_cache[df_fn] = df_fn(results_dir)
        fig = fig_fn(df_cache[df_fn])

        # Standalone HTML (viewable directly, plotly.js bundled)
        standalone_path = charts_dir / f"{name}.html"
        pio.write_html(fig, str(standalone_path), include_plotlyjs="cdn", full_html=True)

        # Snippet HTML for embedding (no <html> wrapper, plotly.js NOT included
        # — the parent page must load Plotly via CDN once).
        snippet_path = snippets_dir / f"{name}.html"
        pio.write_html(fig, str(snippet_path), include_plotlyjs=False, full_html=False)

        print(f"  {name:22s} -> {standalone_path.relative_to(REPO_ROOT)} + snippet")

    print(f"\nWrote {len(CHART_BUILDERS)} charts to {charts_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
