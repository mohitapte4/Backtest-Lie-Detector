"""
Run V4 benchmark evaluation on Claude Sonnet with generic prompt.
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
from backtest_lie_detector.evals.model_clients import AnthropicClient
from backtest_lie_detector.evals.prompts import get_system_prompt
from backtest_lie_detector.evals.scoring import (
    score_response,
    aggregate_scores,
    compute_calibration_metrics,
)


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client: AnthropicClient,
    output_path: str,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases."""
    
    system_prompt = get_system_prompt(config.system_prompt_type)
    
    scored_responses = []
    
    Path(output_path).unlink(missing_ok=True)
    
    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] Processing {case.id}...")
        
        try:
            raw_response, latency_ms = client.call(
                system_prompt=system_prompt,
                user_prompt=case.prompt,
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
                print(f"  Parse error: {e}")
            
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
            print(f"  Error: {e}")
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
    print("V4 CLAUDE SONNET EVALUATION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    print(f"\nLoaded {len(cases)} cases")
    
    output_path = "outputs/results/model_outputs_v4_claude_sonnet.jsonl"
    
    client = AnthropicClient(model="claude-sonnet-4-5")
    
    config = EvaluationConfig(
        model_name="claude-sonnet-4-5",
        config_name="claude-sonnet-generic",
        provider="anthropic",
        system_prompt_type="minimal",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    print(f"\nRunning Claude Sonnet evaluation with generic prompt...")
    print(f"Model: {client.model_name}")
    
    scores = run_evaluation(
        cases=cases,
        config=config,
        client=client,
        output_path=output_path,
    )
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    agg = aggregate_scores(scores)
    for metric, value in agg.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.3f}")
        else:
            print(f"  {metric}: {value}")
    
    calibration = compute_calibration_metrics(scores, cases)
    print(f"\nCalibration Metrics:")
    for metric, value in calibration.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.3f}")
        else:
            print(f"  {metric}: {value}")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
