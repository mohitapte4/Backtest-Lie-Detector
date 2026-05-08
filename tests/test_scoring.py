"""Tests for scoring functions."""

import pytest

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ModelResponse,
    Module,
    Difficulty,
    Validity,
    ViolationType,
)
from backtest_lie_detector.evals.scoring import (
    score_validity,
    score_violations,
    score_severity_weighted,
    score_repair_heuristic,
    score_response,
    aggregate_scores,
    SEVERITY_WEIGHTS,
)


class TestScoreValidity:
    """Tests for validity scoring."""
    
    def test_correct_valid(self):
        assert score_validity(Validity.VALID, Validity.VALID) is True
    
    def test_correct_invalid(self):
        assert score_validity(Validity.INVALID, Validity.INVALID) is True
    
    def test_incorrect_false_valid(self):
        assert score_validity(Validity.INVALID, Validity.VALID) is False
    
    def test_incorrect_false_invalid(self):
        assert score_validity(Validity.VALID, Validity.INVALID) is False
    
    def test_ambiguous_match(self):
        assert score_validity(Validity.AMBIGUOUS, Validity.AMBIGUOUS) is True


class TestScoreViolations:
    """Tests for violation precision/recall/F1 scoring."""
    
    def test_perfect_match(self):
        expected = [ViolationType.SURVIVORSHIP_BIAS, ViolationType.DELISTING_RETURN_OMISSION]
        predicted = [ViolationType.SURVIVORSHIP_BIAS, ViolationType.DELISTING_RETURN_OMISSION]
        
        precision, recall, f1 = score_violations(expected, predicted)
        
        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0
    
    def test_partial_match(self):
        expected = [ViolationType.SURVIVORSHIP_BIAS, ViolationType.DELISTING_RETURN_OMISSION]
        predicted = [ViolationType.SURVIVORSHIP_BIAS]
        
        precision, recall, f1 = score_violations(expected, predicted)
        
        assert precision == 1.0  # 1/1 predicted are correct
        assert recall == 0.5  # 1/2 expected were found
        assert 0 < f1 < 1
    
    def test_no_predictions(self):
        expected = [ViolationType.FILING_CLOCK_LEAKAGE]
        predicted = []
        
        precision, recall, f1 = score_violations(expected, predicted)
        
        # No predictions made, so precision is 0 (or undefined treated as 0)
        # Recall is 0 because we missed everything
        assert recall == 0.0  # Missed everything
        assert f1 == 0.0
    
    def test_false_positives(self):
        expected = []
        predicted = [ViolationType.TIMEZONE_ERROR]
        
        precision, recall, f1 = score_violations(expected, predicted)
        
        assert precision == 0.0  # All predictions are wrong
        # When nothing is expected, recall behavior depends on implementation
    
    def test_both_empty(self):
        precision, recall, f1 = score_violations([], [])
        
        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0


class TestScoreSeverityWeighted:
    """Tests for severity-weighted recall."""
    
    def test_all_violations_caught(self):
        expected = [ViolationType.FILING_CLOCK_LEAKAGE]  # Weight 3
        predicted = [ViolationType.FILING_CLOCK_LEAKAGE]
        
        score = score_severity_weighted(expected, predicted)
        assert score == 1.0
    
    def test_no_violations_caught(self):
        expected = [ViolationType.FILING_CLOCK_LEAKAGE]
        predicted = []
        
        score = score_severity_weighted(expected, predicted)
        assert score == 0.0
    
    def test_severity_matters(self):
        # Missing a high-severity violation should hurt more
        expected_high = [ViolationType.FILING_CLOCK_LEAKAGE]  # Weight 3
        expected_low = [ViolationType.TIMEZONE_ERROR]  # Weight 2
        
        # Both miss all violations
        score_high = score_severity_weighted(expected_high, [])
        score_low = score_severity_weighted(expected_low, [])
        
        # Both should be 0 when nothing is caught
        assert score_high == 0.0
        assert score_low == 0.0
    
    def test_weighted_partial(self):
        expected = [
            ViolationType.FILING_CLOCK_LEAKAGE,  # Weight 3
            ViolationType.TIMEZONE_ERROR,  # Weight 2
        ]
        predicted = [ViolationType.FILING_CLOCK_LEAKAGE]  # Caught the heavy one
        
        score = score_severity_weighted(expected, predicted)
        
        # Expected: 3 / (3 + 2) = 0.6
        assert score == 3.0 / 5.0


class TestScoreRepairHeuristic:
    """Tests for repair quality scoring."""
    
    def test_good_repair(self):
        violations = [ViolationType.IDENTIFIER_TIME_TRAVEL]
        expected_repair = ["Use the historical ticker FB instead of META."]
        predicted_repair = ["Use the historical ticker valid on the event date."]
        
        score = score_repair_heuristic(violations, expected_repair, predicted_repair)
        
        # Should get partial credit for mentioning "historical ticker"
        assert score > 0
    
    def test_empty_repair_when_needed(self):
        violations = [ViolationType.SURVIVORSHIP_BIAS]
        expected_repair = ["Include delisted companies."]
        predicted_repair = []
        
        score = score_repair_heuristic(violations, expected_repair, predicted_repair)
        assert score == 0.0
    
    def test_no_repair_needed(self):
        violations = []
        expected_repair = []
        predicted_repair = []
        
        score = score_repair_heuristic(violations, expected_repair, predicted_repair)
        assert score == 1.0


class TestScoreResponse:
    """Tests for full response scoring."""
    
    def test_perfect_response(self):
        case = BenchmarkCase(
            id="test",
            module=Module.TICKER_TIME_MACHINE,
            difficulty=Difficulty.EASY,
            prompt="Test prompt.",
            expected_validity=Validity.INVALID,
            expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
            expected_repair=["Use historical ticker."],
            ground_truth_notes="Test.",
        )
        
        response = ModelResponse(
            validity=Validity.INVALID,
            violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
            explanation="The ticker was not valid.",
            repair=["Use the historical ticker."],
            confidence=0.9,
        )
        
        scored = score_response(
            case=case,
            response=response,
            raw_response="{}",
            latency_ms=100.0,
            model_name="test",
            config_name="test",
        )
        
        assert scored.validity_correct is True
        assert scored.violation_precision == 1.0
        assert scored.violation_recall == 1.0
        assert scored.parse_success is True
    
    def test_parse_failure(self):
        case = BenchmarkCase(
            id="test",
            module=Module.FILING_CLOCK,
            difficulty=Difficulty.MEDIUM,
            prompt="Test.",
            expected_validity=Validity.INVALID,
            expected_violations=[],
            expected_repair=[],
            ground_truth_notes="Test.",
        )
        
        scored = score_response(
            case=case,
            response=None,  # Parse failed
            raw_response="Invalid JSON",
            latency_ms=100.0,
            model_name="test",
            config_name="test",
        )
        
        assert scored.parse_success is False
        assert scored.validity_correct is False
        assert scored.violation_f1 == 0.0


class TestAggregateScores:
    """Tests for score aggregation."""
    
    def test_empty_scores(self):
        result = aggregate_scores([])
        assert result == {}
    
    def test_basic_aggregation(self):
        from backtest_lie_detector.schemas import ScoredResponse
        
        scores = [
            ScoredResponse(
                case_id="1",
                model_name="test",
                config_name="test",
                raw_response="",
                parsed_response=None,
                parse_success=True,
                validity_correct=True,
                violation_precision=0.8,
                violation_recall=0.6,
                violation_f1=0.7,
                severity_weighted_recall=0.7,
                repair_score=0.5,
                latency_ms=100.0,
            ),
            ScoredResponse(
                case_id="2",
                model_name="test",
                config_name="test",
                raw_response="",
                parsed_response=None,
                parse_success=True,
                validity_correct=False,
                violation_precision=0.4,
                violation_recall=0.4,
                violation_f1=0.4,
                severity_weighted_recall=0.4,
                repair_score=0.3,
                latency_ms=200.0,
            ),
        ]
        
        result = aggregate_scores(scores)
        
        assert result["total_cases"] == 2
        assert result["parse_success_rate"] == 1.0
        assert result["validity_accuracy"] == 0.5  # 1/2
        assert abs(result["mean_violation_precision"] - 0.6) < 0.001  # (0.8 + 0.4) / 2
