"""
Compare prompting strategies on Claude models: zero-shot vs few-shot vs chain-of-thought.

Runs Sonnet 4.5, Sonnet 4.6, and Haiku 4.5 on V5 benchmark (141 cases)
plus V6-only cases (chronology + code), saving results separately.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dotenv import load_dotenv
import jsonlines

load_dotenv()

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    EvaluationConfig,
    ModelResponse,
    ScoredResponse,
)
from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.benchmark.code_cases import CODE_CASES
from backtest_lie_detector.evals.model_clients import AnthropicClient
from backtest_lie_detector.evals.prompts import (
    get_system_prompt,
    format_benchmark_prompt,
)
from backtest_lie_detector.evals.scoring import score_response, aggregate_scores


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client,
    output_path: str,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases with a given prompting config."""

    system_prompt = get_system_prompt(config.system_prompt_type)
    scored_responses = []

    completed_ids = set()
    if Path(output_path).exists():
        with jsonlines.open(output_path) as reader:
            for record in reader:
                completed_ids.add(record.get("case_id"))
        print(f"  Resuming: {len(completed_ids)} cases already completed")

    remaining = [c for c in cases if c.id not in completed_ids]
    print(f"  Cases to evaluate: {len(remaining)}")

    if not remaining:
        print("  All cases already completed")
        with jsonlines.open(output_path) as reader:
            for record in reader:
                scored_responses.append(ScoredResponse.model_validate(record))
        return scored_responses

    for i, case in enumerate(remaining):
        print(f"  [{i+1}/{len(remaining)}] {case.id}...")

        try:
            user_prompt = format_benchmark_prompt(
                case, include_few_shot=config.few_shot_examples
            )

            raw_response, latency_ms = client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=config.max_tokens,
            )

            parsed_response = None
            try:
                response_text = raw_response
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                response_data = json.loads(response_text.strip())
                parsed_response = ModelResponse.model_validate(response_data)
            except Exception as e:
                print(f"    Parse error: {e}")

            scored = score_response(
                case=case,
                response=parsed_response,
                raw_response=raw_response,
                latency_ms=latency_ms,
                model_name=config.model_name,
                config_name=config.config_name,
            )

            scored_responses.append(scored)

            with jsonlines.open(output_path, mode="a") as writer:
                writer.write(scored.model_dump(mode="json"))

            delay = float(os.getenv("API_RATE_LIMIT_DELAY", "1.0"))
            time.sleep(delay)

        except Exception as e:
            print(f"    Error: {e}")
            scored = ScoredResponse(
                case_id=case.id,
                model_name=config.model_name,
                config_name=config.config_name,
                raw_response=f"Error: {e}",
                parsed_response=None,
                parse_success=False,
                validity_correct=False,
                violation_precision=0.0,
                violation_recall=0.0,
                violation_f1=0.0,
                severity_weighted_recall=0.0,
                repair_score=0.0,
                confidence_when_wrong=None,
                latency_ms=0.0,
            )
            scored_responses.append(scored)

            with jsonlines.open(output_path, mode="a") as writer:
                writer.write(scored.model_dump(mode="json"))

    return scored_responses


def print_summary(all_results: dict[str, list[ScoredResponse]], label: str):
    """Print a summary table for a set of results."""
    print(f"\n{'=' * 78}")
    print(f"{label} RESULTS")
    print("=" * 78)

    header = (
        f"{'Model + Strategy':<40} {'Accuracy':>10} {'Parse':>8} "
        f"{'False Inv':>11} {'False Val':>11}"
    )
    print(f"\n{header}")
    print("-" * 82)

    for name, scores in all_results.items():
        if not scores:
            continue
        agg = aggregate_scores(scores)
        acc = agg.get("validity_accuracy", 0) * 100
        parse = agg.get("parse_success_rate", 0) * 100

        parsed = [s for s in scores if s.parse_success and s.parsed_response]
        n_parsed = len(parsed) if parsed else 1

        false_inv = sum(
            1 for s in parsed
            if s.parsed_response.validity.value == "invalid"
            and s.validity_correct is False
        )
        false_val = sum(
            1 for s in parsed
            if s.parsed_response.validity.value == "valid"
            and s.validity_correct is False
        )

        fir = false_inv / n_parsed * 100
        fvr = false_val / n_parsed * 100

        print(
            f"{name:<40} {acc:>9.1f}% {parse:>7.1f}% "
            f"{fir:>10.1f}% {fvr:>10.1f}%"
        )


def main():
    print("=" * 78)
    print("CLAUDE PROMPTING STRATEGY COMPARISON")
    print("Sonnet 4.5 vs Sonnet 4.6 vs Haiku 4.5")
    print("Zero-Shot vs Few-Shot vs Chain-of-Thought")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 78)

    # --- Load benchmarks ---
    v5_cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(v5_cases)} V5 benchmark cases")

    v6_cases = load_benchmark("data/benchmark/benchmark_v6.jsonl")
    v5_ids = set(c.id for c in v5_cases)
    v6_only_cases = [c for c in v6_cases if c.id not in v5_ids]

    code_cases = [BenchmarkCase.model_validate(c) for c in CODE_CASES]
    v6_only_cases.extend(code_cases)
    print(f"Loaded {len(v6_only_cases)} V6-only cases (chronology + code)")

    # --- Model definitions ---
    models = {
        "sonnet-4.5": {
            "id": "claude-sonnet-4-5",
            "short": "sonnet45",
        },
        "sonnet-4.6": {
            "id": "claude-sonnet-4-6",
            "short": "sonnet46",
        },
        "haiku-4.5": {
            "id": "claude-haiku-4-5-20251001",
            "short": "haiku45",
        },
    }

    strategies = {
        "minimal": {
            "prompt_type": "minimal",
            "few_shot": 0,
            "max_tokens": 2000,
        },
        "default": {
            "prompt_type": "default",
            "few_shot": 0,
            "max_tokens": 2000,
        },
        "zero_shot": {
            "prompt_type": "finance_auditor",
            "few_shot": 0,
            "max_tokens": 2000,
        },
        "few_shot": {
            "prompt_type": "finance_auditor",
            "few_shot": 3,
            "max_tokens": 2000,
        },
        "cot": {
            "prompt_type": "chain_of_thought",
            "few_shot": 0,
            "max_tokens": 4000,
        },
    }

    v5_results = {}
    v6_results = {}

    for model_name, model_info in models.items():
        print(f"\n{'#' * 78}")
        print(f"# MODEL: {model_name} ({model_info['id']})")
        print(f"{'#' * 78}")

        client = AnthropicClient(model=model_info["id"])

        for strat_name, strat_info in strategies.items():
            label = f"{model_name} / {strat_name}"
            config_name = f"{model_info['short']}_{strat_name}"

            config = EvaluationConfig(
                model_name=model_info["id"],
                config_name=config_name,
                provider="anthropic",
                system_prompt_type=strat_info["prompt_type"],
                temperature=0.0,
                max_tokens=strat_info["max_tokens"],
                few_shot_examples=strat_info["few_shot"],
            )

            # --- V5 ---
            print(f"\n{'=' * 50}")
            print(f"{label} — V5 ({len(v5_cases)} cases)")
            print("=" * 50)

            v5_path = f"outputs/results/claude_{config_name}_v5.jsonl"
            v5_results[label] = run_evaluation(
                cases=v5_cases,
                config=config,
                client=client,
                output_path=v5_path,
            )

            # --- V6-only ---
            print(f"\n{'=' * 50}")
            print(f"{label} — V6-only ({len(v6_only_cases)} cases)")
            print("=" * 50)

            v6_path = f"outputs/results/claude_{config_name}_v6only.jsonl"
            v6_results[label] = run_evaluation(
                cases=v6_only_cases,
                config=config,
                client=client,
                output_path=v6_path,
            )

    # --- Print summaries ---
    print_summary(v5_results, "V5 BENCHMARK (141 cases)")
    print_summary(v6_results, "V6-ONLY (chronology + code cases)")

    print(f"\n{'=' * 78}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 78)

    print("\nV5 output files:")
    for model_info in models.values():
        for strat_name in strategies:
            print(f"  - outputs/results/claude_{model_info['short']}_{strat_name}_v5.jsonl")

    print("\nV6-only output files:")
    for model_info in models.values():
        for strat_name in strategies:
            print(f"  - outputs/results/claude_{model_info['short']}_{strat_name}_v6only.jsonl")

    print("\nRun compute_prompting_metrics.py for detailed analysis.")


if __name__ == "__main__":
    main()
