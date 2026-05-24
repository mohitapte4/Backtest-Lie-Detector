"""
Compare prompting strategies: zero-shot vs few-shot vs chain-of-thought.

Runs GPT-4o on the V5 benchmark (141 cases) with three prompting strategies
and saves results for comparison.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

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
from backtest_lie_detector.evals.model_clients import OpenAIClient, AnthropicClient
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

    # Check for existing results to support resume
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


def main():
    print("=" * 70)
    print("PROMPTING STRATEGY COMPARISON")
    print("Zero-Shot vs Few-Shot vs Chain-of-Thought")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load V5 benchmark
    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(cases)} V5 benchmark cases")

    client = OpenAIClient(model="gpt-4o")
    results = {}

    # --- Config 1: Zero-shot (finance_auditor prompt, no examples) ---
    print("\n" + "=" * 50)
    print("Strategy 1: Zero-Shot (finance_auditor prompt)")
    print("=" * 50)

    zero_shot_config = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt4o_zero_shot",
        provider="openai",
        system_prompt_type="finance_auditor",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )

    results["Zero-Shot"] = run_evaluation(
        cases=cases,
        config=zero_shot_config,
        client=client,
        output_path="outputs/results/prompting_zero_shot.jsonl",
    )

    # --- Config 2: Few-shot (finance_auditor prompt + 3 examples) ---
    print("\n" + "=" * 50)
    print("Strategy 2: Few-Shot (3 examples)")
    print("=" * 50)

    few_shot_config = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt4o_few_shot",
        provider="openai",
        system_prompt_type="finance_auditor",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=3,
    )

    results["Few-Shot (3)"] = run_evaluation(
        cases=cases,
        config=few_shot_config,
        client=client,
        output_path="outputs/results/prompting_few_shot.jsonl",
    )

    # --- Config 3: Chain-of-thought ---
    print("\n" + "=" * 50)
    print("Strategy 3: Chain-of-Thought")
    print("=" * 50)

    cot_config = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt4o_cot",
        provider="openai",
        system_prompt_type="chain_of_thought",
        temperature=0.0,
        max_tokens=4000,
        few_shot_examples=0,
    )

    results["Chain-of-Thought"] = run_evaluation(
        cases=cases,
        config=cot_config,
        client=client,
        output_path="outputs/results/prompting_cot.jsonl",
    )

    # --- Summary ---
    print("\n" + "=" * 70)
    print("PROMPTING STRATEGY COMPARISON RESULTS")
    print("=" * 70)

    header = (
        f"{'Strategy':<22} {'Accuracy':>10} {'Parse':>10} "
        f"{'False Inv':>12} {'False Val':>12} {'Avg F1':>10}"
    )
    print(f"\n{header}")
    print("-" * 78)

    for name, scores in results.items():
        agg = aggregate_scores(scores)
        acc = agg.get("validity_accuracy", 0) * 100
        parse = agg.get("parse_success_rate", 0) * 100
        f1 = agg.get("mean_violation_f1", 0) * 100

        parsed = [s for s in scores if s.parse_success and s.parsed_response]

        invalid_cases = [s for s in parsed if s.parsed_response.validity.value != "valid"]
        valid_cases = [s for s in parsed if s.parsed_response.validity.value == "valid"]

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

        n_parsed = len(parsed) if parsed else 1
        fir = false_inv / n_parsed * 100
        fvr = false_val / n_parsed * 100

        print(
            f"{name:<22} {acc:>9.1f}% {parse:>9.1f}% "
            f"{fir:>11.1f}% {fvr:>11.1f}% {f1:>9.1f}%"
        )

    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nOutput files:")
    print("  - outputs/results/prompting_zero_shot.jsonl")
    print("  - outputs/results/prompting_few_shot.jsonl")
    print("  - outputs/results/prompting_cot.jsonl")
    print("\nRun compute_prompting_metrics.py for detailed analysis.")


if __name__ == "__main__":
    main()
