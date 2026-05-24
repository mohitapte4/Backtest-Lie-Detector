"""
Run V5 evaluation on ONLY the 16 new false_valid_trap cases.

This saves API calls by not re-running the 125 V4 cases.
Results will be combined with existing V4 outputs for full V5 metrics.
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
from backtest_lie_detector.benchmark.build_cases import get_false_valid_trap_cases_only
from backtest_lie_detector.evals.model_clients import OpenAIClient, AnthropicClient
from backtest_lie_detector.evals.prompts import get_system_prompt
from backtest_lie_detector.evals.scoring import score_response, aggregate_scores


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client,
    output_path: str,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases."""
    
    system_prompt = get_system_prompt(config.system_prompt_type)
    scored_responses = []
    
    Path(output_path).unlink(missing_ok=True)
    
    for i, case in enumerate(cases):
        print(f"  [{i+1}/{len(cases)}] {case.id}...")
        
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
    print("V5 FALSE VALID TRAP CASES EVALUATION")
    print("Running only 16 new cases on all 3 model configurations")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Load only the false valid trap cases
    cases = get_false_valid_trap_cases_only()
    print(f"\nLoaded {len(cases)} false_valid_trap cases")
    
    results = {}
    
    # Configuration 1: GPT-4o Generic
    print("\n" + "=" * 50)
    print("Model 1: GPT-4o (Generic Prompt)")
    print("=" * 50)
    
    gpt_generic_client = OpenAIClient(model="gpt-4o")
    gpt_generic_config = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt-4o-minimal",
        provider="openai",
        system_prompt_type="minimal",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    results["gpt-4o-generic"] = run_evaluation(
        cases=cases,
        config=gpt_generic_config,
        client=gpt_generic_client,
        output_path="outputs/results/v5_new_gpt4o_generic.jsonl",
    )
    
    # Configuration 2: GPT-4o Specialized
    print("\n" + "=" * 50)
    print("Model 2: GPT-4o (Specialized Prompt)")
    print("=" * 50)
    
    gpt_spec_config = EvaluationConfig(
        model_name="gpt-4o",
        config_name="gpt-4o-finance-auditor",
        provider="openai",
        system_prompt_type="finance_auditor",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    results["gpt-4o-specialized"] = run_evaluation(
        cases=cases,
        config=gpt_spec_config,
        client=gpt_generic_client,
        output_path="outputs/results/v5_new_gpt4o_specialized.jsonl",
    )
    
    # Configuration 3: Claude Sonnet
    print("\n" + "=" * 50)
    print("Model 3: Claude Sonnet (Generic Prompt)")
    print("=" * 50)
    
    claude_client = AnthropicClient(model="claude-sonnet-4-5")
    claude_config = EvaluationConfig(
        model_name="claude-sonnet-4-5",
        config_name="claude-sonnet-generic",
        provider="anthropic",
        system_prompt_type="minimal",
        temperature=0.0,
        max_tokens=2000,
        few_shot_examples=0,
    )
    
    results["claude-sonnet"] = run_evaluation(
        cases=cases,
        config=claude_config,
        client=claude_client,
        output_path="outputs/results/v5_new_claude_sonnet.jsonl",
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("FALSE VALID TRAP CASES RESULTS (16 cases)")
    print("=" * 70)
    
    print(f"\n{'Model':<30} {'Accuracy':>10} {'Parse':>10} {'False Valid':>12}")
    print("-" * 65)
    
    for name, scores in results.items():
        agg = aggregate_scores(scores)
        acc = agg.get("validity_accuracy", 0) * 100
        parse = agg.get("parse_success_rate", 0) * 100
        
        # Calculate false valid rate on these invalid cases
        parsed = [s for s in scores if s.parse_success and s.parsed_response]
        false_valids = sum(1 for s in parsed if s.parsed_response.validity.value == "valid")
        fvr = false_valids / len(parsed) * 100 if parsed else 0
        
        print(f"{name:<30} {acc:>9.1f}% {parse:>9.1f}% {fvr:>11.1f}%")
    
    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nOutput files saved to:")
    print("  - outputs/results/v5_new_gpt4o_generic.jsonl")
    print("  - outputs/results/v5_new_gpt4o_specialized.jsonl")
    print("  - outputs/results/v5_new_claude_sonnet.jsonl")


if __name__ == "__main__":
    main()
