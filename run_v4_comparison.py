"""
V4 Benchmark Comparison Script

Runs the v4 benchmark with two prompt configurations:
1. Specialized: GPT-4o with finance_auditor system prompt
2. Generic: GPT-4o with minimal system prompt

Outputs:
- model_outputs_v4_specialized.jsonl
- model_outputs_v4_generic.jsonl
- scores_v4.csv
- calibration_scores_v4.csv
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import jsonlines
import pandas as pd

load_dotenv()

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    EvaluationConfig,
    ModelResponse,
    ScoredResponse,
    Validity,
)
from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.evals.model_clients import OpenAIClient
from backtest_lie_detector.evals.prompts import get_system_prompt
from backtest_lie_detector.evals.scoring import (
    score_response,
    aggregate_scores,
    compute_calibration_metrics,
    compute_calibration_by_tag,
    scores_to_dataframe,
)


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client: OpenAIClient,
    output_path: str,
    resume_from: int = 0,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases."""
    
    # Get system prompt (already includes response format instructions for non-minimal)
    system_prompt = get_system_prompt(config.system_prompt_type)
    
    scored_responses = []
    
    # Resume support - load existing results
    if resume_from > 0 and Path(output_path).exists():
        with jsonlines.open(output_path, mode="r") as reader:
            for obj in reader:
                scored_responses.append(ScoredResponse.model_validate(obj))
        print(f"Resumed from {len(scored_responses)} existing results")
    
    # Process remaining cases
    cases_to_process = cases[len(scored_responses):]
    
    for i, case in enumerate(cases_to_process):
        current_idx = len(scored_responses) + 1
        print(f"[{current_idx}/{len(cases)}] Processing {case.id}...")
        
        try:
            # Call model
            raw_response, latency_ms = client.call(
                system_prompt=system_prompt,
                user_prompt=case.prompt,
            )
            
            # Parse response
            parsed_response = None
            try:
                # Try to extract JSON from response
                response_text = raw_response
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                response_data = json.loads(response_text.strip())
                parsed_response = ModelResponse.model_validate(response_data)
            except Exception as e:
                print(f"  Parse error: {e}")
            
            # Score response
            scored = score_response(
                case=case,
                response=parsed_response,
                raw_response=raw_response,
                latency_ms=latency_ms,
                model_name=config.model_name,
                config_name=config.config_name,
            )
            
            scored_responses.append(scored)
            
            # Save incrementally
            with jsonlines.open(output_path, mode="a") as writer:
                writer.write(scored.model_dump(mode="json"))
            
            # Rate limiting
            delay = float(os.getenv("API_RATE_LIMIT_DELAY", "1.0"))
            time.sleep(delay)
            
        except Exception as e:
            print(f"  Error processing case {case.id}: {e}")
            # Create failed response
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
    print("V4 BENCHMARK COMPARISON")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Load benchmark
    benchmark_path = "data/benchmark/benchmark_v4.jsonl"
    cases = load_benchmark(benchmark_path)
    print(f"\nLoaded {len(cases)} cases from {benchmark_path}")
    
    # Output paths
    output_dir = Path("outputs/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    specialized_output = output_dir / "model_outputs_v4_specialized.jsonl"
    generic_output = output_dir / "model_outputs_v4_generic.jsonl"
    
    # Initialize client
    client = OpenAIClient(model="gpt-4o")
    
    # Configuration 1: Specialized (finance_auditor)
    config_specialized = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt-4o-finance-auditor",
        provider="openai",
        system_prompt_type="finance_auditor",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    # Configuration 2: Generic (minimal)
    config_generic = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt-4o-minimal",
        provider="openai",
        system_prompt_type="minimal",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    results = {}
    
    # Run specialized prompt evaluation
    print("\n" + "=" * 70)
    print("Running SPECIALIZED prompt evaluation...")
    print("=" * 70)
    
    # Clear output file if starting fresh
    if specialized_output.exists():
        existing_count = sum(1 for _ in jsonlines.open(specialized_output))
        if existing_count < len(cases):
            print(f"Resuming specialized evaluation from case {existing_count + 1}")
        else:
            print(f"Specialized evaluation complete ({existing_count} cases)")
    else:
        specialized_output.unlink(missing_ok=True)
    
    specialized_scores = run_evaluation(
        cases=cases,
        config=config_specialized,
        client=client,
        output_path=str(specialized_output),
    )
    results["specialized"] = specialized_scores
    
    # Run generic prompt evaluation
    print("\n" + "=" * 70)
    print("Running GENERIC prompt evaluation...")
    print("=" * 70)
    
    if generic_output.exists():
        existing_count = sum(1 for _ in jsonlines.open(generic_output))
        if existing_count < len(cases):
            print(f"Resuming generic evaluation from case {existing_count + 1}")
        else:
            print(f"Generic evaluation complete ({existing_count} cases)")
    else:
        generic_output.unlink(missing_ok=True)
    
    generic_scores = run_evaluation(
        cases=cases,
        config=config_generic,
        client=client,
        output_path=str(generic_output),
    )
    results["generic"] = generic_scores
    
    # Compute aggregate scores
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    for name, scores in results.items():
        print(f"\n{name.upper()} PROMPT:")
        agg = aggregate_scores(scores)
        for metric, value in agg.items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.3f}")
            else:
                print(f"  {metric}: {value}")
        
        # Calibration metrics
        calibration = compute_calibration_metrics(scores, cases)
        print(f"\n  Calibration Metrics:")
        for metric, value in calibration.items():
            if isinstance(value, float):
                print(f"    {metric}: {value:.3f}")
            else:
                print(f"    {metric}: {value}")
    
    # Save combined scores CSV
    all_scores = []
    for scores in results.values():
        all_scores.extend(scores)
    
    df = scores_to_dataframe(all_scores)
    
    # Add expected validity from cases
    case_map = {c.id: c for c in cases}
    df["expected_validity"] = df["case_id"].map(
        lambda x: case_map[x].expected_validity.value if x in case_map else None
    )
    df["module"] = df["case_id"].map(
        lambda x: case_map[x].module.value if x in case_map else None
    )
    df["difficulty"] = df["case_id"].map(
        lambda x: case_map[x].difficulty.value if x in case_map else None
    )
    
    scores_csv = output_dir / "scores_v4.csv"
    df.to_csv(scores_csv, index=False)
    print(f"\nSaved scores to {scores_csv}")
    
    # Save calibration scores
    calibration_data = []
    for name, scores in results.items():
        cal = compute_calibration_metrics(scores, cases)
        cal["config"] = name
        calibration_data.append(cal)
    
    cal_df = pd.DataFrame(calibration_data)
    cal_csv = output_dir / "calibration_scores_v4.csv"
    cal_df.to_csv(cal_csv, index=False)
    print(f"Saved calibration scores to {cal_csv}")
    
    # Tag-based breakdown
    print("\n" + "=" * 70)
    print("TAG-BASED ACCURACY BREAKDOWN")
    print("=" * 70)
    
    for name, scores in results.items():
        tag_stats = compute_calibration_by_tag(scores, cases)
        print(f"\n{name.upper()}:")
        for tag, stats in sorted(tag_stats.items(), key=lambda x: -x[1]["total"]):
            print(f"  {tag}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")
    
    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
