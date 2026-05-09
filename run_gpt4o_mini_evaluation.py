"""
Run GPT-4o-mini evaluation on the full V5 benchmark.

This is an exploratory experiment to test whether the benchmark
distinguishes frontier models from smaller models.
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
    Validity,
)
from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.evals.model_clients import OpenAIClient
from backtest_lie_detector.evals.prompts import get_system_prompt
from backtest_lie_detector.evals.scoring import score_response, aggregate_scores


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client,
    output_path: str,
    resume: bool = True,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases with resume support."""
    
    system_prompt = get_system_prompt(config.system_prompt_type)
    scored_responses = []
    
    # Check for existing results to resume
    completed_ids = set()
    if resume and Path(output_path).exists():
        with jsonlines.open(output_path) as reader:
            for record in reader:
                scored_responses.append(ScoredResponse.model_validate(record))
                completed_ids.add(record["case_id"])
        print(f"  Resuming: found {len(completed_ids)} completed cases")
    
    remaining_cases = [c for c in cases if c.id not in completed_ids]
    print(f"  Running {len(remaining_cases)} remaining cases")
    
    for i, case in enumerate(remaining_cases):
        print(f"  [{len(completed_ids) + i + 1}/{len(cases)}] {case.id}...")
        
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
            
            delay = float(os.getenv("API_RATE_LIMIT_DELAY", "0.5"))
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


def compute_metrics(results: list[ScoredResponse], cases: list[BenchmarkCase]) -> dict:
    """Compute comprehensive metrics."""
    case_map = {c.id: c for c in cases}
    
    # Basic metrics
    parsed = [r for r in results if r.parse_success]
    correct = [r for r in parsed if r.validity_correct]
    
    # Validity breakdown
    invalid_cases = [c for c in cases if c.expected_validity.value == "invalid"]
    valid_cases = [c for c in cases if c.expected_validity.value == "valid"]
    ambiguous_cases = [c for c in cases if c.expected_validity.value == "ambiguous"]
    
    # False rates
    invalid_results = [r for r in parsed if r.case_id in {c.id for c in invalid_cases}]
    valid_results = [r for r in parsed if r.case_id in {c.id for c in valid_cases}]
    ambiguous_results = [r for r in parsed if r.case_id in {c.id for c in ambiguous_cases}]
    
    false_valids = [r for r in invalid_results if r.parsed_response and r.parsed_response.validity == Validity.VALID]
    false_invalids = [r for r in valid_results if r.parsed_response and r.parsed_response.validity == Validity.INVALID]
    
    # False valid trap cases
    trap_cases = [c for c in cases if hasattr(c, 'case_tags') and c.case_tags and 'false_valid_trap' in c.case_tags]
    trap_ids = {c.id for c in trap_cases}
    trap_results = [r for r in parsed if r.case_id in trap_ids]
    trap_correct = [r for r in trap_results if r.validity_correct]
    trap_false_valids = [r for r in trap_results if r.parsed_response and r.parsed_response.validity == Validity.VALID]
    
    # Trap-valid cases (appear suspicious but are valid)
    trap_valid_cases = [c for c in cases if hasattr(c, 'case_tags') and c.case_tags and 'trap_valid' in c.case_tags]
    trap_valid_ids = {c.id for c in trap_valid_cases}
    trap_valid_results = [r for r in parsed if r.case_id in trap_valid_ids]
    trap_valid_correct = [r for r in trap_valid_results if r.validity_correct]
    
    # Ambiguous accuracy
    ambiguous_correct = [r for r in ambiguous_results if r.parsed_response and r.parsed_response.validity == Validity.AMBIGUOUS]
    
    return {
        "total_cases": len(cases),
        "parsed": len(parsed),
        "parse_failures": len(results) - len(parsed),
        "parse_success_rate": len(parsed) / len(results) if results else 0,
        "accuracy": len(correct) / len(parsed) if parsed else 0,
        "false_valid_rate": len(false_valids) / len(invalid_results) if invalid_results else 0,
        "false_invalid_rate": len(false_invalids) / len(valid_results) if valid_results else 0,
        "ambiguous_accuracy": len(ambiguous_correct) / len(ambiguous_results) if ambiguous_results else 0,
        "n_invalid_cases": len(invalid_cases),
        "n_valid_cases": len(valid_cases),
        "n_ambiguous_cases": len(ambiguous_cases),
        "n_false_valids": len(false_valids),
        "n_false_invalids": len(false_invalids),
        # False valid trap specific
        "n_false_valid_trap_cases": len(trap_cases),
        "false_valid_trap_accuracy": len(trap_correct) / len(trap_results) if trap_results else 0,
        "false_valid_trap_approvals": len(trap_false_valids),
        # Trap valid specific
        "n_trap_valid_cases": len(trap_valid_cases),
        "trap_valid_accuracy": len(trap_valid_correct) / len(trap_valid_results) if trap_valid_results else 0,
    }


def main():
    print("=" * 70)
    print("GPT-4o-mini EVALUATION ON V5 BENCHMARK")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Load V5 benchmark
    cases = load_benchmark("data/benchmark/benchmark_v5.jsonl")
    print(f"\nLoaded {len(cases)} V5 cases")
    
    results = {}
    
    # Configuration 1: GPT-4o-mini Generic
    print("\n" + "=" * 50)
    print("Model: GPT-4o-mini (Generic Prompt)")
    print("=" * 50)
    
    try:
        mini_client = OpenAIClient(model="gpt-4o-mini")
        mini_generic_config = EvaluationConfig(
            model_name="gpt-4o-mini",
            config_name="gpt-4o-mini-generic",
            provider="openai",
            system_prompt_type="minimal",
            temperature=0.0,
            max_tokens=2000,
            few_shot_examples=0,
        )
        
        results["gpt-4o-mini-generic"] = run_evaluation(
            cases=cases,
            config=mini_generic_config,
            client=mini_client,
            output_path="outputs/results/model_outputs_v5_gpt4o_mini_generic.jsonl",
        )
        
        # Compute metrics
        metrics_generic = compute_metrics(results["gpt-4o-mini-generic"], cases)
        
        print("\n--- GPT-4o-mini Generic Results ---")
        print(f"Parse Success Rate: {metrics_generic['parse_success_rate']*100:.1f}%")
        print(f"Accuracy: {metrics_generic['accuracy']*100:.1f}%")
        print(f"False Valid Rate: {metrics_generic['false_valid_rate']*100:.1f}%")
        print(f"False Invalid Rate: {metrics_generic['false_invalid_rate']*100:.1f}%")
        print(f"Ambiguous Accuracy: {metrics_generic['ambiguous_accuracy']*100:.1f}%")
        print(f"False Valid Trap Accuracy: {metrics_generic['false_valid_trap_accuracy']*100:.1f}%")
        print(f"False Valid Trap Approvals: {metrics_generic['false_valid_trap_approvals']}/16")
        
    except Exception as e:
        print(f"Error running GPT-4o-mini generic: {e}")
        return
    
    # Configuration 2: GPT-4o-mini Specialized (optional, run if first succeeds)
    print("\n" + "=" * 50)
    print("Model: GPT-4o-mini (Specialized Prompt)")
    print("=" * 50)
    
    try:
        mini_spec_config = EvaluationConfig(
            model_name="gpt-4o-mini",
            config_name="gpt-4o-mini-specialized",
            provider="openai",
            system_prompt_type="finance_auditor",
            temperature=0.0,
            max_tokens=2000,
            few_shot_examples=0,
        )
        
        results["gpt-4o-mini-specialized"] = run_evaluation(
            cases=cases,
            config=mini_spec_config,
            client=mini_client,
            output_path="outputs/results/model_outputs_v5_gpt4o_mini_specialized.jsonl",
        )
        
        # Compute metrics
        metrics_spec = compute_metrics(results["gpt-4o-mini-specialized"], cases)
        
        print("\n--- GPT-4o-mini Specialized Results ---")
        print(f"Parse Success Rate: {metrics_spec['parse_success_rate']*100:.1f}%")
        print(f"Accuracy: {metrics_spec['accuracy']*100:.1f}%")
        print(f"False Valid Rate: {metrics_spec['false_valid_rate']*100:.1f}%")
        print(f"False Invalid Rate: {metrics_spec['false_invalid_rate']*100:.1f}%")
        print(f"Ambiguous Accuracy: {metrics_spec['ambiguous_accuracy']*100:.1f}%")
        print(f"False Valid Trap Accuracy: {metrics_spec['false_valid_trap_accuracy']*100:.1f}%")
        print(f"False Valid Trap Approvals: {metrics_spec['false_valid_trap_approvals']}/16")
        
    except Exception as e:
        print(f"Error running GPT-4o-mini specialized: {e}")
    
    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nOutput files saved to:")
    print("  - outputs/results/model_outputs_v5_gpt4o_mini_generic.jsonl")
    print("  - outputs/results/model_outputs_v5_gpt4o_mini_specialized.jsonl")


if __name__ == "__main__":
    main()
