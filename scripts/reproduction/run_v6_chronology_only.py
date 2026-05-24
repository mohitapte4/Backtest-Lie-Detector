"""
Run V6 evaluation on ONLY the 15 chronology cases.

This tests pure temporal reasoning without domain complexity.
These cases isolate the "anachronism detection" capability.
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
    Validity,
)
from backtest_lie_detector.benchmark.build_cases import get_chronology_cases_only
from backtest_lie_detector.evals.model_clients import OpenAIClient, AnthropicClient
from backtest_lie_detector.evals.prompts import get_system_prompt
from backtest_lie_detector.evals.scoring import score_response


def run_evaluation(
    cases: list[BenchmarkCase],
    config: EvaluationConfig,
    client,
    output_path: str,
) -> list[ScoredResponse]:
    """Run evaluation on benchmark cases."""
    
    system_prompt = get_system_prompt(config.system_prompt_type)
    scored_responses = []
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
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
            
            # Print quick result
            if parsed_response:
                expected = case.expected_validity.value
                predicted = parsed_response.validity.value
                correct = "OK" if expected == predicted else "WRONG"
                print(f"    [{correct}] Expected: {expected}, Predicted: {predicted}")
            
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


def print_detailed_results(cases: list[BenchmarkCase], results: dict):
    """Print detailed per-case results."""
    print("\n" + "=" * 90)
    print("DETAILED RESULTS BY CASE")
    print("=" * 90)
    
    print(f"\n{'Case ID':<40} {'Expected':<10} {'GPT-Gen':<10} {'GPT-Spec':<10} {'Claude':<10}")
    print("-" * 90)
    
    for case in cases:
        expected = case.expected_validity.value
        
        gpt_gen = "-"
        gpt_spec = "-"
        claude = "-"
        
        for scored in results.get("gpt-4o-generic", []):
            if scored.case_id == case.id and scored.parsed_response:
                pred = scored.parsed_response.validity.value
                mark = "OK" if pred == expected else "X"
                gpt_gen = f"{pred[:3]}({mark})"
        
        for scored in results.get("gpt-4o-specialized", []):
            if scored.case_id == case.id and scored.parsed_response:
                pred = scored.parsed_response.validity.value
                mark = "OK" if pred == expected else "X"
                gpt_spec = f"{pred[:3]}({mark})"
        
        for scored in results.get("claude-sonnet", []):
            if scored.case_id == case.id and scored.parsed_response:
                pred = scored.parsed_response.validity.value
                mark = "OK" if pred == expected else "X"
                claude = f"{pred[:3]}({mark})"
        
        print(f"{case.id:<40} {expected:<10} {gpt_gen:<10} {gpt_spec:<10} {claude:<10}")


def main():
    print("=" * 70)
    print("V6 CHRONOLOGY CASES EVALUATION")
    print("Testing Pure Temporal Reasoning (Anachronism Detection)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Load only the chronology cases
    cases = get_chronology_cases_only()
    print(f"\nLoaded {len(cases)} chronology cases")
    
    # Print case breakdown
    valid_cases = [c for c in cases if c.expected_validity == Validity.VALID]
    invalid_cases = [c for c in cases if c.expected_validity == Validity.INVALID]
    print(f"  - Valid cases: {len(valid_cases)}")
    print(f"  - Invalid cases: {len(invalid_cases)}")
    
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
        output_path="outputs/results/v6_chronology_gpt4o_generic.jsonl",
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
        output_path="outputs/results/v6_chronology_gpt4o_specialized.jsonl",
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
        output_path="outputs/results/v6_chronology_claude_sonnet.jsonl",
    )
    
    # Print detailed results
    print_detailed_results(cases, results)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"CHRONOLOGY CASES SUMMARY ({len(cases)} cases)")
    print("=" * 70)
    
    print(f"\n{'Model':<30} {'Accuracy':>10} {'Valid Acc':>12} {'Invalid Acc':>12}")
    print("-" * 70)
    
    for name, scores in results.items():
        parsed = [s for s in scores if s.parse_success and s.parsed_response]
        total_correct = sum(1 for s in parsed if s.validity_correct)
        acc = total_correct / len(parsed) * 100 if parsed else 0
        
        # Valid case accuracy
        valid_correct = 0
        valid_total = 0
        for s in parsed:
            case = next((c for c in cases if c.id == s.case_id), None)
            if case and case.expected_validity == Validity.VALID:
                valid_total += 1
                if s.validity_correct:
                    valid_correct += 1
        valid_acc = valid_correct / valid_total * 100 if valid_total > 0 else 0
        
        # Invalid case accuracy
        invalid_correct = 0
        invalid_total = 0
        for s in parsed:
            case = next((c for c in cases if c.id == s.case_id), None)
            if case and case.expected_validity == Validity.INVALID:
                invalid_total += 1
                if s.validity_correct:
                    invalid_correct += 1
        invalid_acc = invalid_correct / invalid_total * 100 if invalid_total > 0 else 0
        
        print(f"{name:<30} {acc:>9.1f}% {valid_acc:>11.1f}% {invalid_acc:>11.1f}%")
    
    print("\n" + "=" * 70)
    print("KEY FINDING: Pure Temporal Reasoning")
    print("=" * 70)
    print("""
These cases test whether LLMs can detect anachronisms - events that are
out of chronological order. Unlike other benchmark cases that require
knowledge of CRSP semantics or corporate actions, these are pure
"did event A happen before event B?" puzzles.

High accuracy here suggests good temporal reasoning capability.
Low accuracy (especially on invalid cases) suggests the model
may miss anachronisms even when dates/times are explicit.
""")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nOutput files saved to:")
    print("  - outputs/results/v6_chronology_gpt4o_generic.jsonl")
    print("  - outputs/results/v6_chronology_gpt4o_specialized.jsonl")
    print("  - outputs/results/v6_chronology_claude_sonnet.jsonl")


if __name__ == "__main__":
    main()
