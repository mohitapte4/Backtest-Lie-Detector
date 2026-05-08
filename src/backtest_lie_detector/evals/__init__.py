"""Evaluation harness for running LLM benchmarks."""

from backtest_lie_detector.evals.model_clients import (
    BaseModelClient,
    OpenAIClient,
    AnthropicClient,
    get_client,
    parse_model_json,
)
from backtest_lie_detector.evals.prompts import (
    get_system_prompt,
    get_response_format_instructions,
    format_benchmark_prompt,
)
from backtest_lie_detector.evals.scoring import (
    score_validity,
    score_violations,
    score_response,
    aggregate_scores,
    aggregate_by_module,
    SEVERITY_WEIGHTS,
)
from backtest_lie_detector.evals.run_eval import run_evaluation

__all__ = [
    "BaseModelClient",
    "OpenAIClient",
    "AnthropicClient",
    "get_client",
    "parse_model_json",
    "get_system_prompt",
    "get_response_format_instructions",
    "format_benchmark_prompt",
    "score_validity",
    "score_violations",
    "score_response",
    "aggregate_scores",
    "aggregate_by_module",
    "SEVERITY_WEIGHTS",
    "run_evaluation",
]
