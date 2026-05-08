"""
Evaluation runner for the Backtest Lie Detector benchmark.

Handles loading benchmark cases, calling models, saving results,
and supporting resumption of interrupted runs.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional

import jsonlines
from dotenv import load_dotenv
from tqdm import tqdm

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    EvaluationConfig,
    ScoredResponse,
)
from backtest_lie_detector.evals.model_clients import (
    BaseModelClient,
    get_client,
    parse_model_json,
    MockClient,
)
from backtest_lie_detector.evals.prompts import (
    format_benchmark_prompt,
    get_system_prompt,
)
from backtest_lie_detector.evals.scoring import score_response

load_dotenv()


def load_benchmark(path: str) -> list[BenchmarkCase]:
    """
    Load benchmark cases from a JSONL file.
    
    Args:
        path: Path to the benchmark JSONL file.
    
    Returns:
        List of BenchmarkCase objects.
    """
    cases = []
    with jsonlines.open(path, mode="r") as reader:
        for obj in reader:
            cases.append(BenchmarkCase.model_validate(obj))
    return cases


def save_benchmark(cases: list[BenchmarkCase], path: str) -> None:
    """
    Save benchmark cases to a JSONL file.
    
    Args:
        cases: List of benchmark cases.
        path: Output path for the JSONL file.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with jsonlines.open(path, mode="w") as writer:
        for case in cases:
            writer.write(case.model_dump(mode="json"))


def save_result(result: ScoredResponse, output_path: str) -> None:
    """
    Append a scored result to the output JSONL file.
    
    Args:
        result: The scored response to save.
        output_path: Path to the output file.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with jsonlines.open(output_path, mode="a") as writer:
        # Convert to dict, handling nested models
        data = result.model_dump(mode="json")
        writer.write(data)


def get_completed_ids(output_path: str, config_name: str) -> set[str]:
    """
    Get set of case IDs already completed for a specific config.
    
    Args:
        output_path: Path to the output JSONL file.
        config_name: Configuration name to filter by.
    
    Returns:
        Set of completed case IDs.
    """
    completed = set()
    
    if not Path(output_path).exists():
        return completed
    
    try:
        with jsonlines.open(output_path, mode="r") as reader:
            for obj in reader:
                if obj.get("config_name") == config_name:
                    completed.add(obj.get("case_id"))
    except Exception:
        pass
    
    return completed


def load_results(output_path: str) -> list[ScoredResponse]:
    """
    Load all scored responses from an output file.
    
    Args:
        output_path: Path to the output JSONL file.
    
    Returns:
        List of ScoredResponse objects.
    """
    results = []
    
    if not Path(output_path).exists():
        return results
    
    with jsonlines.open(output_path, mode="r") as reader:
        for obj in reader:
            results.append(ScoredResponse.model_validate(obj))
    
    return results


def run_single_case(
    case: BenchmarkCase,
    client: BaseModelClient,
    config: EvaluationConfig,
) -> ScoredResponse:
    """
    Run evaluation on a single benchmark case.
    
    Args:
        case: The benchmark case to evaluate.
        client: The model client to use.
        config: Evaluation configuration.
    
    Returns:
        Scored response.
    """
    # Build prompts
    system_prompt = get_system_prompt(config.system_prompt_type)
    user_prompt = format_benchmark_prompt(case, include_few_shot=config.few_shot_examples)
    
    # Call model
    try:
        raw_response, latency_ms = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    except Exception as e:
        # API error - return failed result
        return ScoredResponse(
            case_id=case.id,
            model_name=config.model_name,
            config_name=config.config_name,
            raw_response=f"API Error: {str(e)}",
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
    
    # Parse response
    parsed = parse_model_json(raw_response)
    
    # Score response
    scored = score_response(
        case=case,
        response=parsed,
        raw_response=raw_response,
        latency_ms=latency_ms,
        model_name=config.model_name,
        config_name=config.config_name,
    )
    
    return scored


def run_evaluation(
    benchmark_path: str,
    output_path: str,
    configs: list[EvaluationConfig],
    resume: bool = True,
    rate_limit_delay: float = 1.0,
    verbose: bool = True,
) -> dict[str, list[ScoredResponse]]:
    """
    Run evaluation on the benchmark for multiple configurations.
    
    Args:
        benchmark_path: Path to benchmark JSONL file.
        output_path: Path to save results.
        configs: List of evaluation configurations to run.
        resume: If True, skip already-completed cases.
        rate_limit_delay: Delay between API calls (seconds).
        verbose: If True, show progress bar.
    
    Returns:
        Dictionary mapping config name to list of scored responses.
    """
    # Load benchmark
    cases = load_benchmark(benchmark_path)
    print(f"Loaded {len(cases)} benchmark cases")
    
    results: dict[str, list[ScoredResponse]] = {}
    
    for config in configs:
        print(f"\n{'='*60}")
        print(f"Running config: {config.config_name}")
        print(f"Model: {config.model_name} ({config.provider})")
        print(f"Prompt type: {config.system_prompt_type}")
        print(f"{'='*60}")
        
        # Get client
        try:
            if config.model_name == "mock-model":
                client: BaseModelClient = MockClient()
            else:
                client = get_client(config.provider, config.model_name)
        except Exception as e:
            print(f"Error creating client: {e}")
            continue
        
        # Get completed cases for resume
        completed = get_completed_ids(output_path, config.config_name) if resume else set()
        if completed:
            print(f"Resuming: {len(completed)} cases already completed")
        
        # Filter to remaining cases
        remaining = [c for c in cases if c.id not in completed]
        print(f"Cases to evaluate: {len(remaining)}")
        
        if not remaining:
            print("All cases already completed for this config")
            # Load existing results
            all_results = load_results(output_path)
            results[config.config_name] = [
                r for r in all_results 
                if r.config_name == config.config_name
            ]
            continue
        
        config_results = []
        
        # Run evaluation
        iterator = tqdm(remaining, desc=config.config_name) if verbose else remaining
        
        for case in iterator:
            scored = run_single_case(case, client, config)
            
            # Save immediately
            save_result(scored, output_path)
            config_results.append(scored)
            
            # Rate limiting
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
        
        # Load all results for this config (including resumed)
        all_results = load_results(output_path)
        results[config.config_name] = [
            r for r in all_results 
            if r.config_name == config.config_name
        ]
        
        # Print summary
        config_all = results[config.config_name]
        parsed = [r for r in config_all if r.parse_success]
        correct = [r for r in parsed if r.validity_correct]
        
        print(f"\nResults for {config.config_name}:")
        print(f"  Total cases: {len(config_all)}")
        print(f"  Parse success: {len(parsed)}/{len(config_all)} ({len(parsed)/len(config_all)*100:.1f}%)")
        print(f"  Validity accuracy: {len(correct)}/{len(parsed)} ({len(correct)/len(parsed)*100:.1f}%)" if parsed else "  Validity accuracy: N/A")
    
    return results


def main():
    """Command-line entry point for running evaluations."""
    parser = argparse.ArgumentParser(
        description="Run Backtest Lie Detector evaluation"
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        default="data/benchmark/benchmark_v1.jsonl",
        help="Path to benchmark JSONL file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/results/model_outputs.jsonl",
        help="Path to save results"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model to evaluate"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic"],
        help="API provider"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="finance_auditor",
        choices=["minimal", "default", "finance_auditor"],
        help="System prompt type"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Delay between API calls (seconds)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, don't resume from existing results"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock client for testing"
    )
    
    args = parser.parse_args()
    
    # Build config
    config = EvaluationConfig(
        model_name="mock-model" if args.mock else args.model,
        config_name=f"{args.model}_{args.config}" if not args.mock else "mock_test",
        provider=args.provider,
        system_prompt_type=args.config,
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    # Run evaluation
    results = run_evaluation(
        benchmark_path=args.benchmark,
        output_path=args.output,
        configs=[config],
        resume=not args.no_resume,
        rate_limit_delay=args.rate_limit,
        verbose=True,
    )
    
    print("\nEvaluation complete!")
    for config_name, scores in results.items():
        print(f"\n{config_name}: {len(scores)} cases evaluated")


if __name__ == "__main__":
    main()
