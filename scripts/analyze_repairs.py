"""
Analyze repair quality across models.

Categorizes repairs as: Correct, Partially Correct, Wrong/Vague
based on keyword matching and ground truth comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
import jsonlines
import pandas as pd

from backtest_lie_detector.benchmark.build_cases import load_benchmark
from backtest_lie_detector.schemas import ScoredResponse, BenchmarkCase
from backtest_lie_detector.evals.scoring import REPAIR_KEYWORDS_V2


def load_model_results(filepath: str) -> list[ScoredResponse]:
    """Load scored responses from jsonl file."""
    results = []
    with jsonlines.open(filepath) as reader:
        for record in reader:
            results.append(ScoredResponse.model_validate(record))
    return results


def classify_repair(
    predicted_repair: list[str],
    expected_repair: list[str],
    expected_violations: list[str],
) -> str:
    """
    Classify repair quality as Correct, Partial, or Wrong.
    
    Rules:
    - Correct: Mentions key concepts for each violation and overlaps with expected
    - Partial: Mentions some relevant concepts but misses key elements
    - Wrong: No relevant concepts or empty when repair needed
    """
    if not expected_violations:
        # No violations = no repair needed
        if not predicted_repair:
            return "Correct"
        return "Partial"  # Unnecessary repair
    
    if not predicted_repair:
        return "Wrong"  # Missing required repair
    
    repair_text = " ".join(predicted_repair).lower()
    expected_text = " ".join(expected_repair).lower()
    
    # Check keyword coverage for each violation
    violation_scores = []
    for violation in expected_violations:
        keywords = REPAIR_KEYWORDS_V2.get(violation, [])
        if not keywords:
            violation_scores.append(0.5)
            continue
        
        matches = sum(1 for kw in keywords if kw.lower() in repair_text)
        score = min(1.0, matches / 2)  # Need at least 2 keywords for full credit
        violation_scores.append(score)
    
    # Check overlap with expected repair
    expected_words = set(w for w in expected_text.split() if len(w) > 3)
    repair_words = set(w for w in repair_text.split() if len(w) > 3)
    
    overlap = len(expected_words & repair_words) / len(expected_words) if expected_words else 0
    
    avg_violation_score = sum(violation_scores) / len(violation_scores) if violation_scores else 0
    combined_score = (avg_violation_score + overlap) / 2
    
    if combined_score >= 0.5:
        return "Correct"
    elif combined_score >= 0.2:
        return "Partial"
    else:
        return "Wrong"


def analyze_model_repairs(
    results: list[ScoredResponse],
    cases: list[BenchmarkCase],
    sample_size: int = 30,
) -> dict:
    """
    Analyze repair quality for a model's results.
    
    Samples cases stratified by difficulty and analyzes repair quality.
    """
    case_map = {c.id: c for c in cases}
    
    # Stratify by difficulty
    by_difficulty = {"easy": [], "medium": [], "hard": []}
    for result in results:
        if result.case_id not in case_map:
            continue
        case = case_map[result.case_id]
        if result.parse_success and result.parsed_response:
            by_difficulty[case.difficulty.value].append((result, case))
    
    # Sample 10 from each difficulty level
    sampled = []
    for diff in ["easy", "medium", "hard"]:
        items = by_difficulty[diff][:10]  # Take first 10 (or fewer)
        sampled.extend(items)
    
    # Classify repairs
    classifications = {"Correct": 0, "Partial": 0, "Wrong": 0}
    
    for result, case in sampled:
        predicted_repair = result.parsed_response.repair
        expected_repair = case.expected_repair
        expected_violations = [v.value for v in case.expected_violations]
        
        quality = classify_repair(predicted_repair, expected_repair, expected_violations)
        classifications[quality] += 1
    
    total = sum(classifications.values())
    return {
        "total_analyzed": total,
        "correct": classifications["Correct"],
        "partial": classifications["Partial"],
        "wrong": classifications["Wrong"],
        "correct_pct": classifications["Correct"] / total * 100 if total > 0 else 0,
        "partial_pct": classifications["Partial"] / total * 100 if total > 0 else 0,
        "wrong_pct": classifications["Wrong"] / total * 100 if total > 0 else 0,
    }


def main():
    print("=" * 70)
    print("REPAIR QUALITY ANALYSIS")
    print("=" * 70)
    
    cases = load_benchmark("data/benchmark/benchmark_v4.jsonl")
    
    models = {
        "GPT-4o (Generic)": "outputs/results/model_outputs_v4_generic.jsonl",
        "GPT-4o (Specialized)": "outputs/results/model_outputs_v4_specialized.jsonl",
        "Claude Sonnet": "outputs/results/model_outputs_v4_claude_sonnet.jsonl",
    }
    
    results_summary = {}
    
    for name, filepath in models.items():
        print(f"\nAnalyzing: {name}")
        try:
            results = load_model_results(filepath)
            analysis = analyze_model_repairs(results, cases)
            results_summary[name] = analysis
            
            print(f"  Cases analyzed: {analysis['total_analyzed']}")
            print(f"  Correct: {analysis['correct']} ({analysis['correct_pct']:.1f}%)")
            print(f"  Partial: {analysis['partial']} ({analysis['partial_pct']:.1f}%)")
            print(f"  Wrong:   {analysis['wrong']} ({analysis['wrong_pct']:.1f}%)")
        except FileNotFoundError:
            print(f"  File not found: {filepath}")
    
    # Summary table
    print("\n" + "=" * 70)
    print("REPAIR QUALITY SUMMARY")
    print("=" * 70)
    print(f"\n{'Model':<25} {'Correct':>10} {'Partial':>10} {'Wrong':>10}")
    print("-" * 60)
    
    for name, analysis in results_summary.items():
        print(f"{name:<25} {analysis['correct_pct']:>9.1f}% {analysis['partial_pct']:>9.1f}% {analysis['wrong_pct']:>9.1f}%")


if __name__ == "__main__":
    main()
