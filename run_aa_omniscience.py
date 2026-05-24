"""
Run AA-Omniscience Finance evaluation using BLD model configurations.

Tests whether the BLD finance_auditor system prompt — which encodes domain
knowledge about ticker changes, filing timing, and survivorship bias — helps
or hurts factual financial recall compared to a generic prompt.

Three configurations (mirroring BLD):
  1. GPT-4o Generic    → minimal "answer concisely" system prompt
  2. GPT-4o Specialized → BLD finance_auditor domain knowledge + "answer concisely"
  3. Claude Sonnet     → BLD finance_auditor domain knowledge + "answer concisely"

Grading uses GPT-4o as an LLM judge (matching AA-Omniscience's LLM-based grading
methodology, which uses Gemini Flash as judge). Each answer is graded as:
  CORRECT, PARTIALLY_CORRECT, INCORRECT, or NOT_ATTEMPTED

Scoring uses the exact AA-Omniscience OI formula:
  OI = 100 * (c - i) / (c + p + i + a)
  where c=correct, p=partially correct, i=incorrect, a=not attempted

Usage:
    export PYTHONPATH=src
    python run_aa_omniscience.py

Output files:
    outputs/results/aa_omniscience_gpt4o_generic.jsonl
    outputs/results/aa_omniscience_gpt4o_specialized.jsonl
    outputs/results/aa_omniscience_claude_sonnet.jsonl
"""

import os
import sys
import json
import time
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import jsonlines

load_dotenv()

from backtest_lie_detector.evals.model_clients import OpenAIClient, AnthropicClient
from backtest_lie_detector.evals.prompts import SYSTEM_PROMPT_FINANCE_AUDITOR


# =============================================================================
# Prompt construction
# =============================================================================

FACTUAL_RESPONSE_FORMAT = (
    "Answer the following question with only the exact answer. "
    "Be as concise and precise as possible. Do not explain your reasoning."
)

GENERIC_SYSTEM_PROMPT = (
    "You are a helpful financial research assistant. "
    + FACTUAL_RESPONSE_FORMAT
)

SPECIALIZED_SYSTEM_PROMPT = SYSTEM_PROMPT_FINANCE_AUDITOR.format(
    response_format=FACTUAL_RESPONSE_FORMAT
)

# LLM judge prompt — instructs GPT-4o to grade a response
JUDGE_SYSTEM_PROMPT = """You are an expert grader evaluating a language model's answer to a finance question.

Your task is to compare the model's response to the ground truth answer and assign exactly one grade:

CORRECT         — The response contains the correct answer (exact match or semantically equivalent).
PARTIALLY_CORRECT — The response is on the right track but missing detail, or is close but not exact.
INCORRECT       — The response gives a wrong answer.
NOT_ATTEMPTED   — The model refused, said it doesn't know, or did not attempt to answer.

Return only the single grade word. No explanation, no punctuation, nothing else."""

JUDGE_USER_TEMPLATE = """Question: {question}

Ground Truth Answer: {ground_truth}

Model Response: {response}

Grade:"""

VALID_GRADES = {"CORRECT", "PARTIALLY_CORRECT", "INCORRECT", "NOT_ATTEMPTED"}


# =============================================================================
# LLM grading
# =============================================================================

def grade_with_llm(
    question: str,
    ground_truth: str,
    response: str,
    judge_client: OpenAIClient,
) -> str:
    """
    Call GPT-4o to grade a model response against the ground truth.

    Returns one of: CORRECT, PARTIALLY_CORRECT, INCORRECT, NOT_ATTEMPTED.
    Falls back to INCORRECT if the judge returns an unexpected value.
    """
    user_prompt = JUDGE_USER_TEMPLATE.format(
        question=question,
        ground_truth=ground_truth,
        response=response,
    )
    try:
        raw, _ = judge_client.call(
            system_prompt=JUDGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=10,
        )
        grade = raw.strip().upper()
        if grade in VALID_GRADES:
            return grade
        # Handle partial matches (e.g. model says "CORRECT." or "partially correct")
        for valid in VALID_GRADES:
            if valid in grade:
                return valid
        return "INCORRECT"
    except Exception:
        return "INCORRECT"


# =============================================================================
# AA-Omniscience Index (exact OI formula)
# =============================================================================

def aa_omniscience_index(grades: list[str]) -> float:
    """
    OI = 100 * (c - i) / (c + p + i + a)

    c = CORRECT, p = PARTIALLY_CORRECT, i = INCORRECT, a = NOT_ATTEMPTED
    Range: -100 to 100. Positive only when correct > incorrect.
    """
    c = sum(1 for g in grades if g == "CORRECT")
    p = sum(1 for g in grades if g == "PARTIALLY_CORRECT")
    i = sum(1 for g in grades if g == "INCORRECT")
    a = sum(1 for g in grades if g == "NOT_ATTEMPTED")
    total = c + p + i + a
    return 100.0 * (c - i) / total if total > 0 else 0.0


# =============================================================================
# Data loading
# =============================================================================

def load_finance_questions(csv_path: str) -> list[dict]:
    """Load AA-Omniscience CSV, filtering to Finance domain."""
    questions = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("domain", "").strip().lower() == "finance":
                questions.append({
                    "question_id": row.get("question_id", row.get("id", "")).strip(),
                    "topic": row.get("topic", "").strip(),
                    "question": row.get("question", "").strip(),
                    "ground_truth": row.get("answer", row.get("ground_truth", "")).strip(),
                })
    return questions


# =============================================================================
# Evaluation runner
# =============================================================================

def run_config(
    questions: list[dict],
    config_name: str,
    system_prompt: str,
    model_client,
    judge_client: OpenAIClient,
    output_path: str,
    resume: bool = True,
) -> list[dict]:
    """Run one evaluation config with LLM-as-judge grading. Supports resume."""
    results = []
    completed_ids = set()

    if resume and Path(output_path).exists():
        with jsonlines.open(output_path) as reader:
            for record in reader:
                results.append(record)
                completed_ids.add(record["question_id"])
        print(f"  Resuming: found {len(completed_ids)} completed questions")

    remaining = [q for q in questions if q["question_id"] not in completed_ids]
    print(f"  Running {len(remaining)} remaining questions")

    delay = float(os.getenv("API_RATE_LIMIT_DELAY", "0.5"))

    for i, q in enumerate(remaining):
        print(f"  [{len(completed_ids) + i + 1}/{len(questions)}] {q['question_id']}...", end=" ", flush=True)

        try:
            raw_response, latency_ms = model_client.call(
                system_prompt=system_prompt,
                user_prompt=q["question"],
                temperature=0.0,
                max_tokens=200,
            )
            grade = grade_with_llm(
                question=q["question"],
                ground_truth=q["ground_truth"],
                response=raw_response,
                judge_client=judge_client,
            )
            grade_symbol = {"CORRECT": "✓", "PARTIALLY_CORRECT": "~",
                            "INCORRECT": "✗", "NOT_ATTEMPTED": "?"}
            print(grade_symbol.get(grade, "?"))
        except Exception as e:
            print(f"ERROR: {e}")
            raw_response = f"Error: {e}"
            grade = "INCORRECT"
            latency_ms = 0.0

        record = {
            "question_id": q["question_id"],
            "topic": q["topic"],
            "question": q["question"],
            "ground_truth": q["ground_truth"],
            "model_response": raw_response,
            "grade": grade,
            "config_name": config_name,
            "latency_ms": latency_ms,
        }
        results.append(record)

        with jsonlines.open(output_path, mode="a") as writer:
            writer.write(record)

        time.sleep(delay)

    return results


# =============================================================================
# Summary printing
# =============================================================================

TOPIC_ORDER = [
    "Accounting",
    "Business & Management",
    "Corporate & Markets",
    "Economics",
    "Financial Institutions",
    "Investments",
]


def print_summary(config_name: str, results: list[dict]) -> dict:
    grades = [r["grade"] for r in results]
    total = len(grades)

    c = sum(1 for g in grades if g == "CORRECT")
    p = sum(1 for g in grades if g == "PARTIALLY_CORRECT")
    i = sum(1 for g in grades if g == "INCORRECT")
    a = sum(1 for g in grades if g == "NOT_ATTEMPTED")
    accuracy = c / total * 100 if total else 0.0
    index = aa_omniscience_index(grades)
    # Hallucination rate: proportion of non-correct attempts that were incorrect
    # Formula: i / (p + i + a)  — from AA-Omniscience paper section 2.4.3
    hallucination_rate = i / (p + i + a) * 100 if (p + i + a) > 0 else 0.0

    print(f"\n=== {config_name} on AA-Omniscience Finance ({total} questions) ===")
    print(f"AA-Omniscience Index:  {index:.1f}   (range -100 to 100)")
    print(f"Accuracy (correct %):  {accuracy:.1f}%")
    print(f"Hallucination Rate:    {hallucination_rate:.1f}%  (incorrect / non-correct attempts)")
    print(f"Correct:               {c}/{total}")
    print(f"Partially Correct:     {p}/{total}")
    print(f"Incorrect:             {i}/{total}")
    print(f"Not Attempted:         {a}/{total}")

    # By topic
    topic_grades: dict[str, list[str]] = {}
    for r in results:
        t = r["topic"]
        topic_grades.setdefault(t, []).append(r["grade"])

    print("\nBy Topic (AA-Omni Index | Accuracy):")
    for topic in TOPIC_ORDER:
        if topic in topic_grades:
            tg = topic_grades[topic]
            n = len(tg)
            tc = sum(1 for g in tg if g == "CORRECT")
            topic_index = aa_omniscience_index(tg)
            label = f"  {topic} ({n}q):"
            print(f"{label:<42} {topic_index:>6.1f} | {tc/n*100:.1f}%")

    return {
        "config_name": config_name,
        "total": total,
        "n_correct": c,
        "n_partially_correct": p,
        "n_incorrect": i,
        "n_not_attempted": a,
        "accuracy": accuracy,
        "index": index,
        "hallucination_rate": hallucination_rate,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 70)
    print("AA-OMNISCIENCE FINANCE EVALUATION — BLD PROMPT COMPARISON")
    print("Grading: GPT-4o as LLM judge (CORRECT/PARTIALLY_CORRECT/INCORRECT/NOT_ATTEMPTED)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    csv_path = "data/aa_omniscience/AA_Omniscience_finance.csv"
    if not Path(csv_path).exists():
        print(f"\nERROR: CSV not found at {csv_path}")
        sys.exit(1)

    questions = load_finance_questions(csv_path)
    print(f"\nLoaded {len(questions)} Finance questions")

    topics: dict[str, int] = {}
    for q in questions:
        topics[q["topic"]] = topics.get(q["topic"], 0) + 1
    for topic in TOPIC_ORDER:
        if topic in topics:
            print(f"  {topic}: {topics[topic]}")

    Path("outputs/results").mkdir(parents=True, exist_ok=True)

    # Judge client — GPT-4o grades all responses
    judge_client = OpenAIClient(model="gpt-4o")

    all_metrics = []

    # ------------------------------------------------------------------
    # Config 1: GPT-4o Generic
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("Config 1: GPT-4o (Generic Prompt)")
    print("=" * 50)

    try:
        gpt4o_client = OpenAIClient(model="gpt-4o")
        results_generic = run_config(
            questions=questions,
            config_name="GPT-4o (Generic)",
            system_prompt=GENERIC_SYSTEM_PROMPT,
            model_client=gpt4o_client,
            judge_client=judge_client,
            output_path="outputs/results/aa_omniscience_gpt4o_generic.jsonl",
        )
        all_metrics.append(print_summary("GPT-4o (Generic)", results_generic))
    except Exception as e:
        print(f"Error: {e}")

    # ------------------------------------------------------------------
    # Config 2: GPT-4o Specialized
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("Config 2: GPT-4o (Specialized — BLD Finance Auditor Prompt)")
    print("=" * 50)

    try:
        results_specialized = run_config(
            questions=questions,
            config_name="GPT-4o (Specialized)",
            system_prompt=SPECIALIZED_SYSTEM_PROMPT,
            model_client=gpt4o_client,
            judge_client=judge_client,
            output_path="outputs/results/aa_omniscience_gpt4o_specialized.jsonl",
        )
        all_metrics.append(print_summary("GPT-4o (Specialized)", results_specialized))
    except Exception as e:
        print(f"Error: {e}")

    # ------------------------------------------------------------------
    # Config 3: Claude Sonnet Specialized
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("Config 3: Claude Sonnet (Specialized — BLD Finance Auditor Prompt)")
    print("=" * 50)

    try:
        claude_client = AnthropicClient(model="claude-sonnet-4-5")
        results_claude = run_config(
            questions=questions,
            config_name="Claude Sonnet (Specialized)",
            system_prompt=SPECIALIZED_SYSTEM_PROMPT,
            model_client=claude_client,
            judge_client=judge_client,
            output_path="outputs/results/aa_omniscience_claude_sonnet.jsonl",
        )
        all_metrics.append(print_summary("Claude Sonnet (Specialized)", results_claude))
    except Exception as e:
        print(f"Error: {e}")

    # ------------------------------------------------------------------
    # Cross-config comparison
    # ------------------------------------------------------------------
    if all_metrics:
        print("\n" + "=" * 70)
        print("SUMMARY COMPARISON")
        print("=" * 70)
        print(f"{'Config':<38} {'OI Index':>10} {'Accuracy':>10} {'Halluc.Rate':>12} {'C':>5} {'P':>5} {'I':>5} {'A':>5}")
        print("-" * 87)
        for m in all_metrics:
            print(
                f"{m['config_name']:<38} "
                f"{m['index']:>9.1f} "
                f"{m['accuracy']:>9.1f}% "
                f"{m['hallucination_rate']:>11.1f}% "
                f"{m['n_correct']:>5} "
                f"{m['n_partially_correct']:>5} "
                f"{m['n_incorrect']:>5} "
                f"{m['n_not_attempted']:>5}"
            )
        print("(C=Correct, P=Partially Correct, I=Incorrect, A=Not Attempted)")

    print("\n" + "=" * 70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\nOutput files:")
    print("  - outputs/results/aa_omniscience_gpt4o_generic.jsonl")
    print("  - outputs/results/aa_omniscience_gpt4o_specialized.jsonl")
    print("  - outputs/results/aa_omniscience_claude_sonnet.jsonl")


if __name__ == "__main__":
    main()
