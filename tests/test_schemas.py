"""Tests for schema validation."""

import pytest
from pydantic import ValidationError

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ModelResponse,
    ScoredResponse,
    EvaluationConfig,
    Module,
    Difficulty,
    Validity,
    ViolationType,
    SourceFields,
)


class TestBenchmarkCase:
    """Tests for BenchmarkCase schema."""
    
    def test_valid_case(self):
        """Test creating a valid benchmark case."""
        case = BenchmarkCase(
            id="test_case_001",
            module=Module.TICKER_TIME_MACHINE,
            difficulty=Difficulty.EASY,
            prompt="Test prompt for auditing.",
            expected_validity=Validity.INVALID,
            expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
            expected_repair=["Fix the ticker."],
            ground_truth_notes="Test notes.",
        )
        
        assert case.id == "test_case_001"
        assert case.module == Module.TICKER_TIME_MACHINE
        assert case.expected_validity == Validity.INVALID
        assert len(case.expected_violations) == 1
    
    def test_string_violations_converted(self):
        """Test that string violation types are converted to enums."""
        case = BenchmarkCase(
            id="test_case_002",
            module="filing_clock",
            difficulty="medium",
            prompt="Test prompt.",
            expected_validity="invalid",
            expected_violations=["filing_clock_leakage", "timezone_error"],
            expected_repair=[],
            ground_truth_notes="Notes.",
        )
        
        assert case.module == Module.FILING_CLOCK
        assert case.difficulty == Difficulty.MEDIUM
        assert ViolationType.FILING_CLOCK_LEAKAGE in case.expected_violations
        assert ViolationType.TIMEZONE_ERROR in case.expected_violations
    
    def test_valid_workflow_no_violations(self):
        """Test creating a valid workflow case with no violations."""
        case = BenchmarkCase(
            id="valid_case",
            module=Module.ACCOUNTING_AVAILABILITY,
            difficulty=Difficulty.EASY,
            prompt="A valid workflow.",
            expected_validity=Validity.VALID,
            expected_violations=[],
            expected_repair=[],
            ground_truth_notes="This workflow is correct.",
        )
        
        assert case.expected_validity == Validity.VALID
        assert len(case.expected_violations) == 0
    
    def test_source_fields(self):
        """Test source fields are properly stored."""
        case = BenchmarkCase(
            id="source_test",
            module=Module.TICKER_TIME_MACHINE,
            difficulty=Difficulty.MEDIUM,
            prompt="Test.",
            expected_validity=Validity.INVALID,
            expected_violations=[],
            expected_repair=[],
            ground_truth_notes="Notes.",
            source_fields=SourceFields(
                ticker="META",
                company="Meta Platforms",
                event_date="2018-03-20",
                historical_ticker="FB",
            ),
        )
        
        assert case.source_fields.ticker == "META"
        assert case.source_fields.historical_ticker == "FB"


class TestModelResponse:
    """Tests for ModelResponse schema."""
    
    def test_valid_response(self):
        """Test creating a valid model response."""
        response = ModelResponse(
            validity=Validity.INVALID,
            violations=[ViolationType.SURVIVORSHIP_BIAS],
            explanation="This workflow has survivorship bias.",
            repair=["Include delisted companies."],
            confidence=0.85,
        )
        
        assert response.validity == Validity.INVALID
        assert response.confidence == 0.85
    
    def test_confidence_clamped(self):
        """Test that confidence is clamped to [0, 1]."""
        response = ModelResponse(
            validity=Validity.VALID,
            violations=[],
            explanation="Valid.",
            repair=[],
            confidence=0.95,
        )
        
        assert 0.0 <= response.confidence <= 1.0
    
    def test_string_validity_converted(self):
        """Test that string validity is converted to enum."""
        response = ModelResponse(
            validity="invalid",
            violations=["identifier_time_travel"],
            explanation="Test.",
            repair=[],
            confidence=0.5,
        )
        
        assert response.validity == Validity.INVALID
    
    def test_invalid_violation_skipped(self):
        """Test that invalid violation types are skipped."""
        response = ModelResponse(
            validity="invalid",
            violations=["identifier_time_travel", "not_a_real_violation"],
            explanation="Test.",
            repair=[],
            confidence=0.5,
        )
        
        assert len(response.violations) == 1
        assert ViolationType.IDENTIFIER_TIME_TRAVEL in response.violations


class TestScoredResponse:
    """Tests for ScoredResponse schema."""
    
    def test_scored_response(self):
        """Test creating a scored response."""
        scored = ScoredResponse(
            case_id="test_001",
            model_name="gpt-4o",
            config_name="test_config",
            raw_response='{"validity": "invalid"}',
            parsed_response=None,
            parse_success=False,
            validity_correct=False,
            violation_precision=0.0,
            violation_recall=0.0,
            violation_f1=0.0,
            severity_weighted_recall=0.0,
            repair_score=0.0,
            confidence_when_wrong=None,
            latency_ms=500.0,
        )
        
        assert scored.case_id == "test_001"
        assert not scored.parse_success


class TestEvaluationConfig:
    """Tests for EvaluationConfig schema."""
    
    def test_valid_config(self):
        """Test creating a valid evaluation config."""
        config = EvaluationConfig(
            model_name="gpt-4o",
            config_name="test_run",
            provider="openai",
            system_prompt_type="finance_auditor",
            temperature=0.0,
            max_tokens=2000,
            few_shot_examples=0,
        )
        
        assert config.model_name == "gpt-4o"
        assert config.provider == "openai"
        assert config.temperature == 0.0
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = EvaluationConfig(
            model_name="test-model",
            config_name="minimal_test",
        )
        
        assert config.provider == "openai"
        assert config.system_prompt_type == "finance_auditor"
        assert config.temperature == 0.0
        assert config.few_shot_examples == 0
