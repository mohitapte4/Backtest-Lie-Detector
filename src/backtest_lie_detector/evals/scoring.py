"""
Scoring functions for the Backtest Lie Detector evaluation.

Computes validity accuracy, violation precision/recall/F1, severity-weighted
scores, and repair quality heuristics.
"""

from typing import Optional

import pandas as pd

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    EvaluationResult,
    EvaluationConfig,
    ModelResponse,
    Module,
    ScoredResponse,
    Validity,
    ViolationType,
)

# Severity weights for different violation types
# Higher weight = more serious error if missed
SEVERITY_WEIGHTS: dict[ViolationType, int] = {
    ViolationType.IDENTIFIER_TIME_TRAVEL: 2,
    ViolationType.ISSUER_SECURITY_CONFUSION: 2,
    ViolationType.FILING_CLOCK_LEAKAGE: 3,
    ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE: 3,
    ViolationType.RESTATEMENT_LEAKAGE: 3,
    ViolationType.SURVIVORSHIP_BIAS: 3,
    ViolationType.DELISTING_RETURN_OMISSION: 3,
    ViolationType.WRONG_EVENT_WINDOW: 2,
    ViolationType.TIMEZONE_ERROR: 2,
}

# Keywords for repair scoring heuristics
REPAIR_KEYWORDS: dict[ViolationType, list[str]] = {
    ViolationType.IDENTIFIER_TIME_TRAVEL: [
        "historical ticker", "permno", "cusip", "valid on", "point-in-time",
        "fb", "goog", "historical identifier"
    ],
    ViolationType.ISSUER_SECURITY_CONFUSION: [
        "permno", "security", "share class", "issuer", "cusip",
        "corporate action", "merger", "spinoff"
    ],
    ViolationType.FILING_CLOCK_LEAKAGE: [
        "after", "available", "edgar", "acceptance", "filing time",
        "next session", "before filing"
    ],
    ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE: [
        "filing date", "report date", "lag", "before filing",
        "10-k", "10-q", "available", "fiscal year end"
    ],
    ViolationType.RESTATEMENT_LEAKAGE: [
        "point-in-time", "original", "restated", "as-reported",
        "snapshot", "before restatement"
    ],
    ViolationType.SURVIVORSHIP_BIAS: [
        "point-in-time", "universe", "delisted", "existed",
        "include", "historical constituents"
    ],
    ViolationType.DELISTING_RETURN_OMISSION: [
        "delisting return", "dlret", "delisting", "final return",
        "crsp", "include"
    ],
    ViolationType.WRONG_EVENT_WINDOW: [
        "event window", "window", "timing", "announcement",
        "before", "after"
    ],
    ViolationType.TIMEZONE_ERROR: [
        "timezone", "et", "utc", "local time", "conversion",
        "eastern"
    ],
}


def score_validity(expected: Validity, predicted: Validity) -> bool:
    """
    Check if validity classification is correct.
    
    Args:
        expected: Ground truth validity.
        predicted: Model's predicted validity.
    
    Returns:
        True if the prediction matches expected.
    """
    return expected == predicted


def score_violations(
    expected: list[ViolationType],
    predicted: list[ViolationType]
) -> tuple[float, float, float]:
    """
    Compute precision, recall, and F1 for violation detection.
    
    Args:
        expected: Ground truth violations.
        predicted: Model's predicted violations.
    
    Returns:
        Tuple of (precision, recall, f1).
    """
    expected_set = set(expected)
    predicted_set = set(predicted)
    
    if not predicted_set:
        precision = 1.0 if not expected_set else 0.0
    else:
        true_positives = len(expected_set & predicted_set)
        precision = true_positives / len(predicted_set)
    
    if not expected_set:
        recall = 1.0 if not predicted_set else 0.0
    else:
        true_positives = len(expected_set & predicted_set)
        recall = true_positives / len(expected_set)
    
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    
    return precision, recall, f1


def score_severity_weighted(
    expected: list[ViolationType],
    predicted: list[ViolationType]
) -> float:
    """
    Compute severity-weighted recall for violations.
    
    More serious violations (higher weight) have greater impact on the score.
    
    Args:
        expected: Ground truth violations.
        predicted: Model's predicted violations.
    
    Returns:
        Severity-weighted recall score (0-1).
    """
    if not expected:
        return 1.0 if not predicted else 0.0
    
    predicted_set = set(predicted)
    
    total_weight = sum(SEVERITY_WEIGHTS.get(v, 1) for v in expected)
    caught_weight = sum(
        SEVERITY_WEIGHTS.get(v, 1) 
        for v in expected 
        if v in predicted_set
    )
    
    return caught_weight / total_weight if total_weight > 0 else 0.0


def score_repair_heuristic(
    expected_violations: list[ViolationType],
    expected_repair: list[str],
    predicted_repair: list[str]
) -> float:
    """
    Heuristic scoring for repair quality.
    
    Checks if the predicted repair mentions key concepts related to
    the violations that need to be fixed.
    
    Args:
        expected_violations: The violations that need repair.
        expected_repair: Ground truth repair steps.
        predicted_repair: Model's proposed repair steps.
    
    Returns:
        Repair score (0-1).
    """
    if not expected_violations:
        # If no violations, repair is not needed
        return 1.0 if not predicted_repair else 0.5
    
    if not predicted_repair:
        return 0.0
    
    # Combine all repair text
    repair_text = " ".join(predicted_repair).lower()
    expected_text = " ".join(expected_repair).lower()
    
    # Score based on keyword matching for each violation type
    scores = []
    for violation in expected_violations:
        keywords = REPAIR_KEYWORDS.get(violation, [])
        if not keywords:
            # No keywords defined, give partial credit
            scores.append(0.5)
            continue
        
        # Check how many keywords are mentioned
        matches = sum(1 for kw in keywords if kw.lower() in repair_text)
        keyword_score = min(1.0, matches / max(2, len(keywords) // 2))
        scores.append(keyword_score)
    
    # Also check overlap with expected repair
    expected_words = set(expected_text.split())
    repair_words = set(repair_text.split())
    
    if expected_words:
        overlap = len(expected_words & repair_words) / len(expected_words)
        scores.append(min(1.0, overlap * 2))  # Scale up overlap score
    
    return sum(scores) / len(scores) if scores else 0.0


def score_response(
    case: BenchmarkCase,
    response: Optional[ModelResponse],
    raw_response: str,
    latency_ms: float,
    model_name: str,
    config_name: str,
) -> ScoredResponse:
    """
    Score a model response against a benchmark case.
    
    Args:
        case: The benchmark case.
        response: Parsed model response (None if parsing failed).
        raw_response: Raw text from the model.
        latency_ms: API call latency in milliseconds.
        model_name: Name of the model.
        config_name: Name of the evaluation configuration.
    
    Returns:
        ScoredResponse with all metrics computed.
    """
    if response is None:
        # Parsing failed - give worst scores
        return ScoredResponse(
            case_id=case.id,
            model_name=model_name,
            config_name=config_name,
            raw_response=raw_response,
            parsed_response=None,
            parse_success=False,
            validity_correct=False,
            violation_precision=0.0,
            violation_recall=0.0,
            violation_f1=0.0,
            severity_weighted_recall=0.0,
            repair_score=0.0,
            confidence_when_wrong=None,
            latency_ms=latency_ms,
        )
    
    # Score validity
    validity_correct = score_validity(case.expected_validity, response.validity)
    
    # Score violations
    precision, recall, f1 = score_violations(
        case.expected_violations,
        response.violations
    )
    
    # Severity-weighted recall
    severity_weighted = score_severity_weighted(
        case.expected_violations,
        response.violations
    )
    
    # Repair score
    repair_score = score_repair_heuristic(
        case.expected_violations,
        case.expected_repair,
        response.repair
    )
    
    # Track confidence when wrong
    confidence_when_wrong = None
    if not validity_correct:
        confidence_when_wrong = response.confidence
    
    return ScoredResponse(
        case_id=case.id,
        model_name=model_name,
        config_name=config_name,
        raw_response=raw_response,
        parsed_response=response,
        parse_success=True,
        validity_correct=validity_correct,
        violation_precision=precision,
        violation_recall=recall,
        violation_f1=f1,
        severity_weighted_recall=severity_weighted,
        repair_score=repair_score,
        confidence_when_wrong=confidence_when_wrong,
        latency_ms=latency_ms,
    )


def aggregate_scores(scores: list[ScoredResponse]) -> dict:
    """
    Aggregate scores across all responses.
    
    Args:
        scores: List of scored responses.
    
    Returns:
        Dictionary with aggregate metrics.
    """
    if not scores:
        return {}
    
    n = len(scores)
    parsed = [s for s in scores if s.parse_success]
    n_parsed = len(parsed)
    
    return {
        "total_cases": n,
        "parse_success_rate": n_parsed / n if n > 0 else 0.0,
        "validity_accuracy": sum(s.validity_correct for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_violation_precision": sum(s.violation_precision for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_violation_recall": sum(s.violation_recall for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_violation_f1": sum(s.violation_f1 for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_severity_weighted_recall": sum(s.severity_weighted_recall for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_repair_score": sum(s.repair_score for s in parsed) / n_parsed if n_parsed > 0 else 0.0,
        "mean_latency_ms": sum(s.latency_ms for s in scores) / n if n > 0 else 0.0,
    }


def aggregate_by_module(
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase]
) -> dict[str, dict]:
    """
    Aggregate scores by benchmark module.
    
    Args:
        scores: List of scored responses.
        cases: List of benchmark cases (to get module mapping).
    
    Returns:
        Dictionary mapping module name to aggregate metrics.
    """
    case_map = {c.id: c for c in cases}
    
    module_scores: dict[Module, list[ScoredResponse]] = {m: [] for m in Module}
    
    for score in scores:
        if score.case_id in case_map:
            module = case_map[score.case_id].module
            module_scores[module].append(score)
    
    return {
        module.value: aggregate_scores(module_scores[module])
        for module in Module
    }


def aggregate_by_violation_type(
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase]
) -> dict[str, dict]:
    """
    Compute recall statistics for each violation type.
    
    Args:
        scores: List of scored responses.
        cases: List of benchmark cases.
    
    Returns:
        Dictionary mapping violation type to recall statistics.
    """
    case_map = {c.id: c for c in cases}
    
    violation_stats: dict[ViolationType, dict] = {}
    
    for violation in ViolationType:
        # Find all cases with this violation
        relevant_scores = []
        for score in scores:
            if score.case_id not in case_map:
                continue
            case = case_map[score.case_id]
            if violation in case.expected_violations:
                relevant_scores.append(score)
        
        if not relevant_scores:
            continue
        
        # Compute recall for this violation type
        detected = 0
        total = len(relevant_scores)
        
        for score in relevant_scores:
            if score.parsed_response and violation in score.parsed_response.violations:
                detected += 1
        
        violation_stats[violation.value] = {
            "total_cases": total,
            "detected": detected,
            "recall": detected / total if total > 0 else 0.0,
            "severity_weight": SEVERITY_WEIGHTS.get(violation, 1),
        }
    
    return violation_stats


def compute_evaluation_result(
    config: EvaluationConfig,
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase],
) -> EvaluationResult:
    """
    Compute full evaluation results for a configuration.
    
    Args:
        config: The evaluation configuration.
        scores: List of scored responses.
        cases: List of benchmark cases.
    
    Returns:
        EvaluationResult with all metrics.
    """
    agg = aggregate_scores(scores)
    module_agg = aggregate_by_module(scores, cases)
    
    # Extract per-module accuracy
    module_accuracy = {
        module: data.get("validity_accuracy", 0.0)
        for module, data in module_agg.items()
        if data
    }
    
    # Confidence analysis
    parsed = [s for s in scores if s.parse_success and s.parsed_response]
    correct = [s for s in parsed if s.validity_correct]
    wrong = [s for s in parsed if not s.validity_correct]
    
    mean_confidence = (
        sum(s.parsed_response.confidence for s in parsed) / len(parsed)
        if parsed else 0.0
    )
    
    confidence_correct = (
        sum(s.parsed_response.confidence for s in correct) / len(correct)
        if correct else 0.0
    )
    
    confidence_wrong = (
        sum(s.parsed_response.confidence for s in wrong) / len(wrong)
        if wrong else 0.0
    )
    
    # Overconfident wrong: high confidence (>0.7) but wrong
    overconfident_wrong = [
        s for s in wrong
        if s.parsed_response.confidence > 0.7
    ]
    overconfident_rate = len(overconfident_wrong) / len(wrong) if wrong else 0.0
    
    return EvaluationResult(
        config=config,
        total_cases=agg.get("total_cases", 0),
        parse_success_rate=agg.get("parse_success_rate", 0.0),
        validity_accuracy=agg.get("validity_accuracy", 0.0),
        mean_violation_precision=agg.get("mean_violation_precision", 0.0),
        mean_violation_recall=agg.get("mean_violation_recall", 0.0),
        mean_violation_f1=agg.get("mean_violation_f1", 0.0),
        mean_severity_weighted_recall=agg.get("mean_severity_weighted_recall", 0.0),
        mean_repair_score=agg.get("mean_repair_score", 0.0),
        module_accuracy=module_accuracy,
        mean_confidence=mean_confidence,
        confidence_when_correct=confidence_correct,
        confidence_when_wrong=confidence_wrong,
        overconfident_wrong_rate=overconfident_rate,
    )


def scores_to_dataframe(scores: list[ScoredResponse]) -> pd.DataFrame:
    """
    Convert scored responses to a pandas DataFrame.
    
    Args:
        scores: List of scored responses.
    
    Returns:
        DataFrame with one row per scored response.
    """
    rows = []
    for s in scores:
        row = {
            "case_id": s.case_id,
            "model_name": s.model_name,
            "config_name": s.config_name,
            "parse_success": s.parse_success,
            "validity_correct": s.validity_correct,
            "violation_precision": s.violation_precision,
            "violation_recall": s.violation_recall,
            "violation_f1": s.violation_f1,
            "severity_weighted_recall": s.severity_weighted_recall,
            "repair_score": s.repair_score,
            "latency_ms": s.latency_ms,
        }
        
        if s.parsed_response:
            row["predicted_validity"] = s.parsed_response.validity.value
            row["predicted_violations"] = ",".join(v.value for v in s.parsed_response.violations)
            row["confidence"] = s.parsed_response.confidence
        else:
            row["predicted_validity"] = None
            row["predicted_violations"] = None
            row["confidence"] = None
        
        rows.append(row)
    
    return pd.DataFrame(rows)


# =============================================================================
# V4 CALIBRATION METRICS
# =============================================================================

# Enhanced repair keywords for v2 scoring
REPAIR_KEYWORDS_V2: dict[ViolationType, list[str]] = {
    ViolationType.IDENTIFIER_TIME_TRAVEL: [
        "historical ticker", "permno", "point-in-time", "as-of date",
        "valid on", "cusip", "historical identifier", "fb", "goog",
        "use the ticker that was valid"
    ],
    ViolationType.ISSUER_SECURITY_CONFUSION: [
        "share class", "permno", "security", "issuer", "class a",
        "class b", "class c", "adr", "different securities"
    ],
    ViolationType.FILING_CLOCK_LEAKAGE: [
        "acceptance time", "dissemination", "next session", "before release",
        "filing time", "edgar", "after filing", "publicly available"
    ],
    ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE: [
        "report date", "filing date", "lag", "available before",
        "10-k", "10-q", "rdq", "fiscal year end", "months after"
    ],
    ViolationType.RESTATEMENT_LEAKAGE: [
        "point-in-time", "snapshot", "as-reported", "restated",
        "original filing", "compustat unrestated"
    ],
    ViolationType.SURVIVORSHIP_BIAS: [
        "point-in-time universe", "include delisted", "historical constituents",
        "existed at the time", "survivor", "avoid current"
    ],
    ViolationType.DELISTING_RETURN_OMISSION: [
        "dlret", "delisting return", "total return", "missing delisting",
        "crsp", "shumway", "impute", "-30%"
    ],
    ViolationType.WRONG_EVENT_WINDOW: [
        "event window", "pre-market", "after-close", "announcement time",
        "timing", "t+1", "correct window"
    ],
    ViolationType.TIMEZONE_ERROR: [
        "timezone", "eastern", "utc", "pacific", "et", "local time"
    ],
}


def compute_calibration_metrics(
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase]
) -> dict:
    """
    Compute calibration-focused metrics for V4 evaluation.
    
    These metrics assess model calibration, overcaution, and uncertainty handling.
    
    Args:
        scores: List of scored responses.
        cases: List of benchmark cases with tags.
    
    Returns:
        Dictionary with calibration metrics:
        - false_invalid_rate: fraction of valid cases predicted invalid
        - false_valid_rate: fraction of invalid cases predicted valid
        - ambiguous_accuracy: accuracy on ambiguous cases
        - valid_trap_accuracy: accuracy on trap_valid tagged cases
        - overcaution_score: combined measure of overcautious behavior
        - uncertainty_score: ability to express uncertainty appropriately
    """
    case_map = {c.id: c for c in cases}
    parsed = [s for s in scores if s.parse_success and s.parsed_response]
    
    if not parsed:
        return {}
    
    # Categorize by expected validity
    valid_cases = []
    invalid_cases = []
    ambiguous_cases = []
    trap_valid_cases = []
    
    for score in parsed:
        if score.case_id not in case_map:
            continue
        case = case_map[score.case_id]
        
        if case.expected_validity == Validity.VALID:
            valid_cases.append(score)
        elif case.expected_validity == Validity.INVALID:
            invalid_cases.append(score)
        elif case.expected_validity == Validity.AMBIGUOUS:
            ambiguous_cases.append(score)
        
        # Check for trap_valid tag
        if hasattr(case, 'case_tags') and 'trap_valid' in case.case_tags:
            trap_valid_cases.append(score)
    
    # False invalid rate: among valid cases, fraction predicted invalid
    false_invalids = sum(
        1 for s in valid_cases 
        if s.parsed_response.validity == Validity.INVALID
    )
    false_invalid_rate = false_invalids / len(valid_cases) if valid_cases else 0.0
    
    # False valid rate: among invalid cases, fraction predicted valid
    false_valids = sum(
        1 for s in invalid_cases
        if s.parsed_response.validity == Validity.VALID
    )
    false_valid_rate = false_valids / len(invalid_cases) if invalid_cases else 0.0
    
    # Ambiguous accuracy: among ambiguous cases, fraction predicted ambiguous
    ambiguous_correct = sum(
        1 for s in ambiguous_cases
        if s.parsed_response.validity == Validity.AMBIGUOUS
    )
    ambiguous_accuracy = ambiguous_correct / len(ambiguous_cases) if ambiguous_cases else 0.0
    
    # Among ambiguous cases, how many were predicted invalid (overcautious)
    ambiguous_to_invalid = sum(
        1 for s in ambiguous_cases
        if s.parsed_response.validity == Validity.INVALID
    )
    ambiguous_invalid_rate = ambiguous_to_invalid / len(ambiguous_cases) if ambiguous_cases else 0.0
    
    # Valid trap accuracy: among trap_valid tagged, fraction predicted valid
    trap_correct = sum(1 for s in trap_valid_cases if s.validity_correct)
    valid_trap_accuracy = trap_correct / len(trap_valid_cases) if trap_valid_cases else 0.0
    
    # Overcaution score: combined false_invalid + ambiguous->invalid behavior
    # Higher = more overcautious
    overcaution_score = (false_invalid_rate + ambiguous_invalid_rate) / 2
    
    # Uncertainty score: ability to choose ambiguous when appropriate
    # Also penalize for predicting ambiguous when not appropriate
    false_ambiguous = sum(
        1 for s in valid_cases + invalid_cases
        if s.parsed_response.validity == Validity.AMBIGUOUS
    )
    false_ambiguous_rate = false_ambiguous / (len(valid_cases) + len(invalid_cases)) if (valid_cases or invalid_cases) else 0.0
    
    # Good uncertainty: high ambiguous_accuracy, low false_ambiguous_rate
    uncertainty_score = ambiguous_accuracy * (1 - false_ambiguous_rate)
    
    return {
        "false_invalid_rate": false_invalid_rate,
        "false_valid_rate": false_valid_rate,
        "ambiguous_accuracy": ambiguous_accuracy,
        "ambiguous_invalid_rate": ambiguous_invalid_rate,
        "valid_trap_accuracy": valid_trap_accuracy,
        "overcaution_score": overcaution_score,
        "uncertainty_score": uncertainty_score,
        "n_valid_cases": len(valid_cases),
        "n_invalid_cases": len(invalid_cases),
        "n_ambiguous_cases": len(ambiguous_cases),
        "n_trap_valid_cases": len(trap_valid_cases),
        "n_false_invalids": false_invalids,
        "n_false_valids": false_valids,
    }


def score_repair_v2(
    predicted_repair: list[str],
    expected_violations: list[ViolationType],
    expected_repair: list[str]
) -> float:
    """
    Enhanced repair scoring with violation-specific keywords (V2).
    
    Scores based on coverage of required repair concepts for each violation type.
    
    Args:
        predicted_repair: Model's proposed repair steps.
        expected_violations: Violations that need fixing.
        expected_repair: Ground truth repair steps.
    
    Returns:
        Repair score (0.0-1.0).
    """
    if not expected_violations:
        return 1.0 if not predicted_repair else 0.5
    
    if not predicted_repair:
        return 0.0
    
    repair_text = " ".join(predicted_repair).lower()
    expected_text = " ".join(expected_repair).lower()
    
    scores = []
    
    for violation in expected_violations:
        keywords = REPAIR_KEYWORDS_V2.get(violation, [])
        if not keywords:
            scores.append(0.5)
            continue
        
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in repair_text)
        
        # Require at least 2 keyword matches for full credit
        min_required = min(2, len(keywords))
        keyword_score = min(1.0, matches / min_required)
        scores.append(keyword_score)
    
    # Overlap with expected repair text
    if expected_text:
        expected_words = set(w for w in expected_text.split() if len(w) > 3)
        repair_words = set(w for w in repair_text.split() if len(w) > 3)
        
        if expected_words:
            overlap = len(expected_words & repair_words) / len(expected_words)
            scores.append(min(1.0, overlap * 1.5))
    
    return sum(scores) / len(scores) if scores else 0.0


def compute_calibration_by_module(
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase]
) -> dict[str, dict]:
    """
    Compute calibration metrics broken down by module.
    
    Args:
        scores: List of scored responses.
        cases: List of benchmark cases.
    
    Returns:
        Dictionary mapping module name to calibration metrics.
    """
    case_map = {c.id: c for c in cases}
    
    module_scores: dict[Module, list[ScoredResponse]] = {m: [] for m in Module}
    module_cases: dict[Module, list[BenchmarkCase]] = {m: [] for m in Module}
    
    for score in scores:
        if score.case_id in case_map:
            case = case_map[score.case_id]
            module_scores[case.module].append(score)
            if case not in module_cases[case.module]:
                module_cases[case.module].append(case)
    
    return {
        module.value: compute_calibration_metrics(
            module_scores[module],
            module_cases[module]
        )
        for module in Module
        if module_scores[module]
    }


def compute_calibration_by_tag(
    scores: list[ScoredResponse],
    cases: list[BenchmarkCase]
) -> dict[str, dict]:
    """
    Compute accuracy metrics broken down by case tag.
    
    Args:
        scores: List of scored responses.
        cases: List of benchmark cases.
    
    Returns:
        Dictionary mapping tag to accuracy statistics.
    """
    case_map = {c.id: c for c in cases}
    parsed = [s for s in scores if s.parse_success]
    
    # Collect all tags
    all_tags = set()
    for case in cases:
        if hasattr(case, 'case_tags'):
            all_tags.update(case.case_tags)
    
    tag_stats = {}
    
    for tag in all_tags:
        tag_scores = []
        for score in parsed:
            if score.case_id not in case_map:
                continue
            case = case_map[score.case_id]
            if hasattr(case, 'case_tags') and tag in case.case_tags:
                tag_scores.append(score)
        
        if not tag_scores:
            continue
        
        correct = sum(1 for s in tag_scores if s.validity_correct)
        tag_stats[tag] = {
            "total": len(tag_scores),
            "correct": correct,
            "accuracy": correct / len(tag_scores),
        }
    
    return tag_stats
