"""
Pydantic schemas for the Backtest Lie Detector benchmark.

Defines data models for benchmark cases, model responses, scored responses,
and evaluation configurations.
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Module(str, Enum):
    """Benchmark module categories."""
    
    TICKER_TIME_MACHINE = "ticker_time_machine"
    FILING_CLOCK = "filing_clock"
    ACCOUNTING_AVAILABILITY = "accounting_availability"
    SURVIVORSHIP_DELISTING = "survivorship_delisting"


class Difficulty(str, Enum):
    """Difficulty levels for benchmark cases."""
    
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Validity(str, Enum):
    """Validity classification for workflows."""
    
    VALID = "valid"
    INVALID = "invalid"
    AMBIGUOUS = "ambiguous"


class ViolationType(str, Enum):
    """Types of point-in-time violations that can occur in financial workflows."""
    
    # Original violation types
    IDENTIFIER_TIME_TRAVEL = "identifier_time_travel"
    ISSUER_SECURITY_CONFUSION = "issuer_security_confusion"
    FILING_CLOCK_LEAKAGE = "filing_clock_leakage"
    ACCOUNTING_AVAILABILITY_LEAKAGE = "accounting_availability_leakage"
    RESTATEMENT_LEAKAGE = "restatement_leakage"
    SURVIVORSHIP_BIAS = "survivorship_bias"
    DELISTING_RETURN_OMISSION = "delisting_return_omission"
    WRONG_EVENT_WINDOW = "wrong_event_window"
    TIMEZONE_ERROR = "timezone_error"
    
    # V5 violation types for subtle implementation bugs
    LINK_DATE_LEAKAGE = "link_date_leakage"  # CCM linkdt/linkenddt ignored
    DELISTING_RETURN_CONSTRUCTION = "delisting_return_construction"  # DLRET combination error
    ADJUSTED_PRICE_MISUSE = "adjusted_price_misuse"  # Adjusted price for level triggers
    CURRENT_METADATA_LEAKAGE = "current_metadata_leakage"  # Current industry/exchange codes
    INDEX_TIMING_LEAKAGE = "index_timing_leakage"  # Announce vs effective date
    FORECAST_TIMING_LEAKAGE = "forecast_timing_leakage"  # IBES availability timing
    INTRADAY_DATA_LEAKAGE = "intraday_data_leakage"  # Future intraday data used
    CORPORATE_ACTION_TIMING = "corporate_action_timing"  # M&A announce vs complete


class SourceFields(BaseModel):
    """
    Source data fields providing context for benchmark cases.
    
    These fields capture the specific data points relevant to validating
    the ground truth of each benchmark case.
    """
    
    ticker: Optional[str] = Field(default=None, description="Stock ticker symbol")
    company: Optional[str] = Field(default=None, description="Company name")
    event_date: Optional[str] = Field(default=None, description="Date of the event being studied")
    decision_timestamp: Optional[str] = Field(
        default=None, 
        description="Timestamp when trading decision is made"
    )
    filing_timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp when filing was accepted by EDGAR"
    )
    permno: Optional[str] = Field(default=None, description="CRSP PERMNO identifier")
    cik: Optional[str] = Field(default=None, description="SEC CIK identifier")
    gvkey: Optional[str] = Field(default=None, description="Compustat GVKEY identifier")
    
    # Flexible additional fields for module-specific data
    historical_ticker: Optional[str] = Field(
        default=None, 
        description="Historical ticker that was valid at event time"
    )
    bad_ticker: Optional[str] = Field(
        default=None,
        description="Incorrect ticker used in the workflow"
    )
    fiscal_year_end: Optional[str] = Field(
        default=None,
        description="End date of fiscal year"
    )
    filing_date: Optional[str] = Field(
        default=None,
        description="Date when filing was submitted"
    )
    portfolio_date: Optional[str] = Field(
        default=None,
        description="Date when portfolio is formed"
    )
    backtest_start: Optional[str] = Field(
        default=None,
        description="Start date of backtest period"
    )
    backtest_end: Optional[str] = Field(
        default=None,
        description="End date of backtest period"
    )
    universe_filter: Optional[str] = Field(
        default=None,
        description="Description of universe filtering criteria"
    )
    
    # Generic extra fields for anything else
    extra: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional module-specific fields"
    )


class BenchmarkCase(BaseModel):
    """
    A single benchmark case for the point-in-time audit evaluation.
    
    Each case presents a financial workflow scenario and tests whether
    the model can correctly identify validity issues and propose repairs.
    """
    
    id: str = Field(description="Unique identifier for the case")
    module: Module = Field(description="Which benchmark module this case belongs to")
    difficulty: Difficulty = Field(description="Difficulty level of the case")
    prompt: str = Field(description="The natural-language audit task given to the model")
    expected_validity: Validity = Field(
        description="Whether the workflow is valid, invalid, or ambiguous"
    )
    expected_violations: list[ViolationType] = Field(
        default_factory=list,
        description="List of violations present in the workflow"
    )
    expected_repair: list[str] = Field(
        default_factory=list,
        description="Steps needed to repair the workflow"
    )
    ground_truth_notes: str = Field(
        description="Explanation of why the expected answer is correct"
    )
    source_fields: SourceFields = Field(
        default_factory=SourceFields,
        description="Source data for the case"
    )
    requires_data_validation: bool = Field(
        default=False,
        description="Whether ground truth requires external data validation"
    )
    data_source: str = Field(
        default="manual",
        description="Source of the case data (manual, WRDS CRSP, SEC EDGAR, etc.)"
    )
    case_tags: list[str] = Field(
        default_factory=list,
        description="Tags for case categorization (e.g., trap_valid, ambiguous, multi_violation)"
    )
    source_note: str = Field(
        default="",
        description="Citation or source reference for ground truth"
    )
    
    @field_validator("expected_violations", mode="before")
    @classmethod
    def convert_violations(cls, v: Any) -> list[ViolationType]:
        """Convert string violation types to enum values."""
        if isinstance(v, list):
            return [ViolationType(x) if isinstance(x, str) else x for x in v]
        return v


class ModelResponse(BaseModel):
    """
    Expected response format from an LLM auditing a financial workflow.
    
    Models are instructed to return responses in this JSON schema.
    """
    
    validity: Validity = Field(description="Classification of workflow validity")
    violations: list[ViolationType] = Field(
        default_factory=list,
        description="List of identified violations"
    )
    explanation: str = Field(description="Concise explanation of the analysis")
    repair: list[str] = Field(
        default_factory=list,
        description="Steps needed to make the workflow valid"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Model's confidence in its assessment (0-1)"
    )
    
    @field_validator("violations", mode="before")
    @classmethod
    def convert_violations(cls, v: Any) -> list[ViolationType]:
        """Convert string violation types to enum values."""
        if isinstance(v, list):
            result = []
            for x in v:
                if isinstance(x, str):
                    try:
                        result.append(ViolationType(x))
                    except ValueError:
                        # Skip invalid violation types
                        continue
                else:
                    result.append(x)
            return result
        return v
    
    @field_validator("validity", mode="before")
    @classmethod
    def convert_validity(cls, v: Any) -> Validity:
        """Convert string validity to enum value."""
        if isinstance(v, str):
            return Validity(v.lower())
        return v


class ScoredResponse(BaseModel):
    """
    A scored model response including all evaluation metrics.
    
    Contains both the raw/parsed response and computed scores.
    """
    
    case_id: str = Field(description="ID of the benchmark case")
    model_name: str = Field(description="Name of the model evaluated")
    config_name: str = Field(description="Evaluation configuration used")
    raw_response: str = Field(description="Raw text response from model")
    parsed_response: Optional[ModelResponse] = Field(
        default=None,
        description="Parsed JSON response, if successful"
    )
    parse_success: bool = Field(description="Whether JSON parsing succeeded")
    
    # Scoring metrics
    validity_correct: bool = Field(description="Whether validity classification is correct")
    violation_precision: float = Field(
        ge=0.0, le=1.0,
        description="Precision of violation detection"
    )
    violation_recall: float = Field(
        ge=0.0, le=1.0,
        description="Recall of violation detection"
    )
    violation_f1: float = Field(
        ge=0.0, le=1.0,
        description="F1 score for violation detection"
    )
    severity_weighted_recall: float = Field(
        ge=0.0, le=1.0,
        description="Recall weighted by violation severity"
    )
    repair_score: float = Field(
        ge=0.0, le=1.0,
        description="Heuristic score for repair quality"
    )
    confidence_when_wrong: Optional[float] = Field(
        default=None,
        description="Model confidence when validity was incorrect"
    )
    latency_ms: float = Field(description="API call latency in milliseconds")


class EvaluationConfig(BaseModel):
    """
    Configuration for running an evaluation.
    
    Specifies the model, prompting strategy, and generation parameters.
    """
    
    model_name: str = Field(description="Model identifier (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')")
    config_name: str = Field(description="Human-readable name for this configuration")
    provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="API provider to use"
    )
    system_prompt_type: Literal["default", "finance_auditor", "minimal"] = Field(
        default="finance_auditor",
        description="Type of system prompt to use"
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum tokens in response"
    )
    few_shot_examples: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Number of few-shot examples to include"
    )


class EvaluationResult(BaseModel):
    """
    Aggregated results from an evaluation run.
    
    Contains summary statistics across all benchmark cases.
    """
    
    config: EvaluationConfig = Field(description="Configuration used for this evaluation")
    total_cases: int = Field(description="Total number of cases evaluated")
    parse_success_rate: float = Field(description="Fraction of responses that parsed successfully")
    
    # Aggregate metrics
    validity_accuracy: float = Field(description="Overall validity classification accuracy")
    mean_violation_precision: float = Field(description="Mean violation precision")
    mean_violation_recall: float = Field(description="Mean violation recall")
    mean_violation_f1: float = Field(description="Mean violation F1")
    mean_severity_weighted_recall: float = Field(description="Mean severity-weighted recall")
    mean_repair_score: float = Field(description="Mean repair score")
    
    # Per-module metrics
    module_accuracy: dict[str, float] = Field(
        default_factory=dict,
        description="Validity accuracy by module"
    )
    
    # Confidence analysis
    mean_confidence: float = Field(description="Mean confidence across all responses")
    confidence_when_correct: float = Field(description="Mean confidence when correct")
    confidence_when_wrong: float = Field(description="Mean confidence when incorrect")
    overconfident_wrong_rate: float = Field(
        description="Fraction of wrong answers with confidence > 0.7"
    )


# Type aliases for convenience
BenchmarkCaseList = list[BenchmarkCase]
ScoredResponseList = list[ScoredResponse]
