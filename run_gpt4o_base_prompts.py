"""
Run GPT-4o on V5 with the base prompts (minimal + default).

Complements the existing zero-shot/few-shot/CoT results with the
original prompt types for a complete comparison.
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
from backtest_lie_detector.evals.model_clients import OpenAIClient
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


def main():
    print("=" * 70)
    print("GPT-4o BASE PROMPTS EVALUATION")
    print("Minimal + Default prompts on V5 benchmark")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(cases)} V5 benchmark cases")

    client = OpenAIClient(model="gpt-4o")
    results = {}

    for strat_name, prompt_type in [("minimal", "minimal"), ("default", "default")]:
        config = EvaluationConfig(
            model_name="gpt-4o",
            config_name=f"gpt4o_{strat_name}",
            provider="openai",
            system_prompt_type=prompt_type,
            temperature=0.0,
            max_tokens=2000,
            few_shot_examples=0,
        )

        print(f"\n{'=' * 50}")
        print(f"GPT-4o / {strat_name} — V5 ({len(cases)} cases)")
        print("=" * 50)

        output_path = f"outputs/results/prompting_{strat_name}.jsonl"
        results[strat_name] = run_evaluation(
            cases=cases,
            config=config,
            client=client,
            output_path=output_path,
        )

    # Summary
    print(f"\n{'=' * 70}")
    print("GPT-4o BASE PROMPT RESULTS")
    print("=" * 70)

    header = f"{'Strategy':<22} {'Accuracy':>10} {'Parse':>8} {'False Inv':>11} {'False Val':>11}"
    print(f"\n{header}")
    print("-" * 64)

    for name, scores in results.items():
        agg = aggregate_scores(scores)
        acc = agg.get("validity_accuracy", 0) * 100
        parse = agg.get("parse_success_rate", 0) * 100

        parsed = [s for s in scores if s.parse_success and s.parsed_response]
        n_parsed = len(parsed) if parsed else 1
        false_inv = sum(1 for s in parsed if s.parsed_response.validity.value == "invalid" and not s.validity_correct)
        false_val = sum(1 for s in parsed if s.parsed_response.validity.value == "valid" and not s.validity_correct)

        print(f"{name:<22} {acc:>9.1f}% {parse:>7.1f}% {false_inv/n_parsed*100:>10.1f}% {false_val/n_parsed*100:>10.1f}%")

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
