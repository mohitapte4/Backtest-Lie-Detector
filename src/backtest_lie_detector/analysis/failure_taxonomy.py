"""
Failure taxonomy and analysis for benchmark results.

Categorizes model failures and generates failure reports.
"""

from collections import defaultdict
from enum import Enum
from typing import Optional

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    ScoredResponse,
    Validity,
    ViolationType,
)


class FailureCategory(str, Enum):
    """Categories of model failures."""
    
    FALSE_VALID = "false_valid"  # Model said valid, but workflow was invalid
    FALSE_INVALID = "false_invalid"  # Model said invalid, but workflow was valid
    WRONG_VIOLATION = "wrong_violation"  # Model identified wrong violation type
    MISSED_VIOLATION = "missed_violation"  # Model missed a specific violation
    EXTRA_VIOLATION = "extra_violation"  # Model flagged non-existent violation
    INCOMPLETE_REPAIR = "incomplete_repair"  # Repair suggestion was partial
    OVERCONFIDENT_WRONG = "overconfident_wrong"  # High confidence but wrong
    PARSE_FAILURE = "parse_failure"  # Response didn't parse as valid JSON


class FailureInstance:
    """A single failure instance with details."""
    
    def __init__(
        self,
        case: BenchmarkCase,
        scored: ScoredResponse,
        category: FailureCategory,
        details: str,
    ):
        self.case = case
        self.scored = scored
        self.category = category
        self.details = details
    
    def to_dict(self) -> dict:
        return {
            "case_id": self.case.id,
            "module": self.case.module.value,
            "difficulty": self.case.difficulty.value,
            "category": self.category.value,
            "details": self.details,
            "expected_validity": self.case.expected_validity.value,
            "predicted_validity": (
                self.scored.parsed_response.validity.value 
                if self.scored.parsed_response 
                else None
            ),
            "confidence": (
                self.scored.parsed_response.confidence 
                if self.scored.parsed_response 
                else None
            ),
        }


def categorize_failure(
    case: BenchmarkCase,
    scored: ScoredResponse,
) -> list[FailureInstance]:
    """
    Categorize all failures in a single scored response.
    
    Args:
        case: The benchmark case.
        scored: The scored model response.
    
    Returns:
        List of failure instances (may be empty if no failures).
    """
    failures = []
    
    # Check for parse failure
    if not scored.parse_success:
        failures.append(FailureInstance(
            case=case,
            scored=scored,
            category=FailureCategory.PARSE_FAILURE,
            details="Model response could not be parsed as valid JSON",
        ))
        return failures  # Can't analyze further without parsed response
    
    response = scored.parsed_response
    
    # Check validity errors
    if not scored.validity_correct:
        if case.expected_validity == Validity.INVALID and response.validity == Validity.VALID:
            failures.append(FailureInstance(
                case=case,
                scored=scored,
                category=FailureCategory.FALSE_VALID,
                details=(
                    f"Model marked workflow as valid, but it contains: "
                    f"{[v.value for v in case.expected_violations]}"
                ),
            ))
        elif case.expected_validity == Validity.VALID and response.validity == Validity.INVALID:
            failures.append(FailureInstance(
                case=case,
                scored=scored,
                category=FailureCategory.FALSE_INVALID,
                details=(
                    f"Model incorrectly flagged violations: "
                    f"{[v.value for v in response.violations]}"
                ),
            ))
        
        # Check for overconfidence
        if response.confidence > 0.7:
            failures.append(FailureInstance(
                case=case,
                scored=scored,
                category=FailureCategory.OVERCONFIDENT_WRONG,
                details=f"Model was {response.confidence:.0%} confident but got validity wrong",
            ))
    
    # Check violation-level errors
    expected_set = set(case.expected_violations)
    predicted_set = set(response.violations)
    
    # Missed violations
    missed = expected_set - predicted_set
    for violation in missed:
        failures.append(FailureInstance(
            case=case,
            scored=scored,
            category=FailureCategory.MISSED_VIOLATION,
            details=f"Missed violation: {violation.value}",
        ))
    
    # Extra violations
    extra = predicted_set - expected_set
    for violation in extra:
        failures.append(FailureInstance(
            case=case,
            scored=scored,
            category=FailureCategory.EXTRA_VIOLATION,
            details=f"Incorrectly flagged: {violation.value}",
        ))
    
    # Check repair quality
    if case.expected_violations and scored.repair_score < 0.5:
        failures.append(FailureInstance(
            case=case,
            scored=scored,
            category=FailureCategory.INCOMPLETE_REPAIR,
            details=f"Repair score: {scored.repair_score:.0%}, missing key repair elements",
        ))
    
    return failures


def categorize_all_failures(
    cases: list[BenchmarkCase],
    scores: list[ScoredResponse],
) -> list[FailureInstance]:
    """
    Categorize failures across all scored responses.
    
    Args:
        cases: List of benchmark cases.
        scores: List of scored responses.
    
    Returns:
        List of all failure instances.
    """
    case_map = {c.id: c for c in cases}
    all_failures = []
    
    for scored in scores:
        if scored.case_id not in case_map:
            continue
        
        case = case_map[scored.case_id]
        failures = categorize_failure(case, scored)
        all_failures.extend(failures)
    
    return all_failures


def aggregate_failures_by_category(
    failures: list[FailureInstance],
) -> dict[FailureCategory, list[FailureInstance]]:
    """Group failures by category."""
    by_category = defaultdict(list)
    for failure in failures:
        by_category[failure.category].append(failure)
    return dict(by_category)


def aggregate_failures_by_module(
    failures: list[FailureInstance],
) -> dict[str, list[FailureInstance]]:
    """Group failures by module."""
    by_module = defaultdict(list)
    for failure in failures:
        by_module[failure.case.module.value].append(failure)
    return dict(by_module)


def sample_failures_by_category(
    failures: list[FailureInstance],
    n_per_category: int = 3,
) -> dict[FailureCategory, list[FailureInstance]]:
    """
    Sample representative failures from each category.
    
    Args:
        failures: List of all failures.
        n_per_category: Number of examples per category.
    
    Returns:
        Dictionary mapping category to sampled failures.
    """
    by_category = aggregate_failures_by_category(failures)
    
    sampled = {}
    for category, category_failures in by_category.items():
        # Prioritize diverse modules
        by_module = defaultdict(list)
        for f in category_failures:
            by_module[f.case.module.value].append(f)
        
        # Sample from each module first
        samples = []
        modules = list(by_module.keys())
        while len(samples) < n_per_category and any(by_module.values()):
            for module in modules:
                if by_module[module] and len(samples) < n_per_category:
                    samples.append(by_module[module].pop(0))
        
        sampled[category] = samples
    
    return sampled


def generate_failure_report(
    cases: list[BenchmarkCase],
    scores: list[ScoredResponse],
    config_name: Optional[str] = None,
) -> str:
    """
    Generate a markdown report of failure analysis.
    
    Args:
        cases: List of benchmark cases.
        scores: List of scored responses.
        config_name: Optional config to filter to.
    
    Returns:
        Markdown-formatted report.
    """
    if config_name:
        scores = [s for s in scores if s.config_name == config_name]
    
    failures = categorize_all_failures(cases, scores)
    by_category = aggregate_failures_by_category(failures)
    by_module = aggregate_failures_by_module(failures)
    
    lines = []
    lines.append("# Failure Analysis Report")
    lines.append("")
    
    if config_name:
        lines.append(f"**Configuration:** {config_name}")
        lines.append("")
    
    # Summary statistics
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total scored responses: {len(scores)}")
    lines.append(f"- Total failure instances: {len(failures)}")
    lines.append(f"- Unique cases with failures: {len(set(f.case.id for f in failures))}")
    lines.append("")
    
    # By category
    lines.append("## Failures by Category")
    lines.append("")
    lines.append("| Category | Count | Description |")
    lines.append("|----------|-------|-------------|")
    
    category_descriptions = {
        FailureCategory.FALSE_VALID: "Model missed violations, called workflow valid",
        FailureCategory.FALSE_INVALID: "Model flagged valid workflow as invalid",
        FailureCategory.MISSED_VIOLATION: "Model missed a specific violation type",
        FailureCategory.EXTRA_VIOLATION: "Model flagged non-existent violation",
        FailureCategory.INCOMPLETE_REPAIR: "Repair suggestion was incomplete",
        FailureCategory.OVERCONFIDENT_WRONG: "High confidence on wrong answer",
        FailureCategory.PARSE_FAILURE: "Response did not parse as JSON",
    }
    
    for category in FailureCategory:
        count = len(by_category.get(category, []))
        desc = category_descriptions.get(category, "")
        lines.append(f"| {category.value} | {count} | {desc} |")
    
    lines.append("")
    
    # By module
    lines.append("## Failures by Module")
    lines.append("")
    for module, module_failures in sorted(by_module.items()):
        lines.append(f"### {module.replace('_', ' ').title()}")
        lines.append(f"- Total failures: {len(module_failures)}")
        
        # Break down by category for this module
        category_counts = defaultdict(int)
        for f in module_failures:
            category_counts[f.category.value] += 1
        
        for cat, count in sorted(category_counts.items()):
            lines.append(f"  - {cat}: {count}")
        
        lines.append("")
    
    # Example failures
    lines.append("## Example Failures")
    lines.append("")
    
    sampled = sample_failures_by_category(failures, n_per_category=2)
    
    for category, examples in sampled.items():
        if not examples:
            continue
        
        lines.append(f"### {category.value.replace('_', ' ').title()}")
        lines.append("")
        
        for i, example in enumerate(examples, 1):
            lines.append(f"**Example {i}:** Case `{example.case.id}` ({example.case.module.value})")
            lines.append("")
            lines.append(f"> {example.case.prompt[:200]}...")
            lines.append("")
            lines.append(f"- **Expected:** {example.case.expected_validity.value}")
            if example.scored.parsed_response:
                lines.append(f"- **Predicted:** {example.scored.parsed_response.validity.value}")
                lines.append(f"- **Confidence:** {example.scored.parsed_response.confidence:.0%}")
            lines.append(f"- **Issue:** {example.details}")
            lines.append("")
    
    return "\n".join(lines)


def get_failure_statistics(
    cases: list[BenchmarkCase],
    scores: list[ScoredResponse],
) -> dict:
    """
    Compute summary statistics about failures.
    
    Args:
        cases: List of benchmark cases.
        scores: List of scored responses.
    
    Returns:
        Dictionary of statistics.
    """
    failures = categorize_all_failures(cases, scores)
    by_category = aggregate_failures_by_category(failures)
    by_module = aggregate_failures_by_module(failures)
    
    # Compute rates
    total = len(scores)
    parsed = len([s for s in scores if s.parse_success])
    
    stats = {
        "total_responses": total,
        "parse_success_rate": parsed / total if total > 0 else 0,
        "total_failures": len(failures),
        "failure_rate": len(set(f.case.id for f in failures)) / total if total > 0 else 0,
    }
    
    # Category breakdown
    stats["by_category"] = {
        cat.value: len(by_category.get(cat, [])) 
        for cat in FailureCategory
    }
    
    # Module breakdown
    stats["by_module"] = {
        module: len(failures) 
        for module, failures in by_module.items()
    }
    
    # Most common failure type
    if by_category:
        most_common = max(by_category.items(), key=lambda x: len(x[1]))
        stats["most_common_failure"] = most_common[0].value
        stats["most_common_failure_count"] = len(most_common[1])
    
    # Overconfidence rate
    overconfident = by_category.get(FailureCategory.OVERCONFIDENT_WRONG, [])
    wrong = [s for s in scores if s.parse_success and not s.validity_correct]
    stats["overconfident_rate"] = len(overconfident) / len(wrong) if wrong else 0
    
    return stats
