"""
Rule-based baseline classifiers for benchmark comparison.

These simple baselines help contextualize LLM performance by showing
what naive rules can achieve.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ModelResponse,
    ScoredResponse,
    Validity,
    ViolationType,
)
from backtest_lie_detector.evals.scoring import score_response


class BaselineClassifier(ABC):
    """Abstract base class for baseline classifiers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the baseline name."""
        pass
    
    @abstractmethod
    def classify(self, prompt: str) -> ModelResponse:
        """
        Classify a prompt and return a model response.
        
        Args:
            prompt: The workflow description to classify.
        
        Returns:
            ModelResponse with validity, violations, explanation, repair.
        """
        pass


class AlwaysInvalidBaseline(BaselineClassifier):
    """
    Baseline that always predicts invalid.
    
    This is the most conservative baseline - it assumes every workflow
    has a point-in-time error. Useful for understanding the base rate.
    """
    
    @property
    def name(self) -> str:
        return "always-invalid"
    
    def classify(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            validity=Validity.INVALID,
            violations=[ViolationType.SURVIVORSHIP_BIAS],
            explanation="This baseline always predicts invalid.",
            repair=["Review the workflow for point-in-time issues."],
            confidence=0.5,
        )


class AlwaysValidBaseline(BaselineClassifier):
    """
    Baseline that always predicts valid.
    
    This is the most permissive baseline - useful for understanding
    the invalid case prevalence.
    """
    
    @property
    def name(self) -> str:
        return "always-valid"
    
    def classify(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            validity=Validity.VALID,
            violations=[],
            explanation="This baseline always predicts valid.",
            repair=[],
            confidence=0.5,
        )


class KeywordSuspicionBaseline(BaselineClassifier):
    """
    Baseline that predicts invalid if suspicious keywords are present.
    
    This is a simple keyword-matching approach that flags common
    indicators of point-in-time issues.
    """
    
    SUSPICIOUS_KEYWORDS = [
        "current", "currently", "still listed", "still trading",
        "today", "now", "as of 2026", "as of 2025",
        "downloaded", "download current",
    ]
    
    @property
    def name(self) -> str:
        return "keyword-suspicion"
    
    def classify(self, prompt: str) -> ModelResponse:
        prompt_lower = prompt.lower()
        
        for keyword in self.SUSPICIOUS_KEYWORDS:
            if keyword in prompt_lower:
                return ModelResponse(
                    validity=Validity.INVALID,
                    violations=[ViolationType.SURVIVORSHIP_BIAS],
                    explanation=f"Flagged due to suspicious keyword: '{keyword}'",
                    repair=["Check for survivorship bias or look-ahead bias."],
                    confidence=0.6,
                )
        
        return ModelResponse(
            validity=Validity.VALID,
            violations=[],
            explanation="No suspicious keywords detected.",
            repair=[],
            confidence=0.5,
        )


class RuleBasedClassifier(BaselineClassifier):
    """
    Rule-based classifier using domain-specific heuristics.
    
    Implements simple rules for common point-in-time violations:
    - Ticker time travel (META before 2022, GOOGL before 2014)
    - Survivorship bias (current universe, still listed)
    - Filing clock (timing mismatches)
    - Accounting availability (FY end vs filing lag)
    """
    
    @property
    def name(self) -> str:
        return "rule-based"
    
    def classify(self, prompt: str) -> ModelResponse:
        prompt_lower = prompt.lower()
        violations = []
        explanations = []
        repairs = []
        
        # Rule 1: Ticker time travel - META before 2022
        if "meta" in prompt_lower and not "metadata" in prompt_lower:
            # Check for pre-2022 dates
            years_mentioned = re.findall(r'\b(19\d{2}|20[01]\d|202[01])\b', prompt)
            if years_mentioned:
                violations.append(ViolationType.IDENTIFIER_TIME_TRAVEL)
                explanations.append("META ticker used for pre-2022 period")
                repairs.append("Use FB ticker for periods before June 2022")
        
        # Rule 2: Ticker time travel - GOOGL before 2014
        if "googl" in prompt_lower:
            years = re.findall(r'\b(19\d{2}|200\d|201[0-3])\b', prompt)
            if years:
                violations.append(ViolationType.IDENTIFIER_TIME_TRAVEL)
                explanations.append("GOOGL ticker used for pre-2014 period")
                repairs.append("Use GOOG ticker for periods before April 2014")
        
        # Rule 3: Survivorship bias - current universe
        survivorship_keywords = [
            "currently listed", "still listed", "still trading",
            "current universe", "stocks that exist today",
            "companies that are still", "currently trading"
        ]
        for kw in survivorship_keywords:
            if kw in prompt_lower:
                violations.append(ViolationType.SURVIVORSHIP_BIAS)
                explanations.append(f"Survivorship bias indicator: '{kw}'")
                repairs.append("Use point-in-time universe including delisted companies")
                break
        
        # Rule 4: Filing clock - same day trading before filing
        # Look for patterns like "filed at X:XX PM" and "trade at Y:XX"
        filing_time_match = re.search(r'filed\s+(?:at\s+)?(\d{1,2}):?(\d{2})?\s*(pm|am)?', prompt_lower)
        trade_time_match = re.search(r'trade\s+(?:at\s+)?(\d{1,2}):?(\d{2})?\s*(pm|am)?', prompt_lower)
        
        if filing_time_match and trade_time_match:
            # Simple heuristic: if both mention PM times, check order
            if "pm" in prompt_lower and "before" not in prompt_lower:
                filing_hour = int(filing_time_match.group(1))
                trade_hour = int(trade_time_match.group(1))
                # If filing is in afternoon and trade seems concurrent
                if filing_hour >= 3 and trade_hour >= 3:
                    violations.append(ViolationType.FILING_CLOCK_LEAKAGE)
                    explanations.append("Potential same-day trading before filing availability")
                    repairs.append("Verify filing acceptance time precedes trade decision")
        
        # Rule 5: Accounting availability - FY end vs January/February decision
        if re.search(r'fiscal\s+year\s+(end|2022|2023)', prompt_lower) or "fy" in prompt_lower:
            if re.search(r'january|february|early\s+\d{4}', prompt_lower):
                if "march" not in prompt_lower and "april" not in prompt_lower:
                    violations.append(ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE)
                    explanations.append("Using fiscal year data before likely 10-K filing")
                    repairs.append("Use 6-month lag or verify actual filing date")
        
        # Rule 6: Check for delisting issues
        if "delisting" in prompt_lower or "delisted" in prompt_lower:
            if "missing" in prompt_lower or "exclude" in prompt_lower or "drop" in prompt_lower:
                violations.append(ViolationType.DELISTING_RETURN_OMISSION)
                explanations.append("Delisting returns may be missing")
                repairs.append("Apply CRSP delisting returns using dlret field")
        
        # Determine validity
        if violations:
            # Deduplicate violations
            violations = list(set(violations))
            return ModelResponse(
                validity=Validity.INVALID,
                violations=violations,
                explanation="; ".join(explanations),
                repair=repairs,
                confidence=0.7,
            )
        else:
            return ModelResponse(
                validity=Validity.VALID,
                violations=[],
                explanation="No rule-based violations detected.",
                repair=[],
                confidence=0.5,
            )


def run_baseline_evaluation(
    cases: list[BenchmarkCase],
    baseline: BaselineClassifier,
) -> list[ScoredResponse]:
    """
    Run a baseline classifier on benchmark cases.
    
    Args:
        cases: List of benchmark cases.
        baseline: The baseline classifier to use.
    
    Returns:
        List of scored responses.
    """
    results = []
    
    for case in cases:
        response = baseline.classify(case.prompt)
        
        scored = score_response(
            case=case,
            response=response,
            raw_response=f"Baseline: {baseline.name}",
            latency_ms=0.0,
            model_name=baseline.name,
            config_name=baseline.name,
        )
        results.append(scored)
    
    return results


def evaluate_all_baselines(cases: list[BenchmarkCase]) -> dict[str, list[ScoredResponse]]:
    """
    Evaluate all baseline classifiers on benchmark cases.
    
    Args:
        cases: List of benchmark cases.
    
    Returns:
        Dictionary mapping baseline name to scored responses.
    """
    baselines = [
        AlwaysInvalidBaseline(),
        AlwaysValidBaseline(),
        KeywordSuspicionBaseline(),
        RuleBasedClassifier(),
    ]
    
    results = {}
    for baseline in baselines:
        results[baseline.name] = run_baseline_evaluation(cases, baseline)
    
    return results
