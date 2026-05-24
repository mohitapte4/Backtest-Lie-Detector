"""
Prompt templates for the Backtest Lie Detector evaluation.

Provides system prompts, response format instructions, and few-shot examples
for evaluating LLMs on point-in-time validity auditing tasks.
"""

from typing import Literal

from backtest_lie_detector.schemas import BenchmarkCase, ViolationType

# =============================================================================
# Response Format Instructions
# =============================================================================

RESPONSE_FORMAT_INSTRUCTIONS = """
You must respond with a JSON object following this exact schema:

{
  "validity": "valid" | "invalid" | "ambiguous",
  "violations": [
    // Array of violation types from this list:
    // "identifier_time_travel", "issuer_security_confusion", "filing_clock_leakage",
    // "accounting_availability_leakage", "restatement_leakage", "survivorship_bias",
    // "delisting_return_omission", "wrong_event_window", "timezone_error"
  ],
  "explanation": "Concise explanation of your analysis.",
  "repair": [
    "Step 1 to fix the workflow.",
    "Step 2 to fix the workflow."
  ],
  "confidence": 0.0  // Your confidence in this assessment, from 0.0 to 1.0
}

Return ONLY the JSON object. Do not include any text before or after the JSON.
""".strip()

# =============================================================================
# System Prompts
# =============================================================================

SYSTEM_PROMPT_MINIMAL = """
You are a financial research auditor. Analyze the provided workflow and determine if it has any point-in-time validity issues.

{response_format}
""".strip()

SYSTEM_PROMPT_DEFAULT = """
You are a financial research auditor specializing in data integrity for quantitative finance.

Your task is to audit financial research workflows for point-in-time validity issues. These are errors where a backtest or event study uses information that would not have been available at the time of the trading decision.

Common issues include:
- Using modern stock tickers for historical periods when the ticker was different
- Using information from SEC filings before they were publicly available
- Using accounting data before the financial statements were filed
- Testing strategies only on companies that still exist today (survivorship bias)

Analyze each workflow carefully and identify any point-in-time validity violations.

{response_format}
""".strip()

SYSTEM_PROMPT_FINANCE_AUDITOR = """
You are an expert financial research auditor specializing in point-in-time data validity for quantitative finance research.

Your primary task is to identify look-ahead bias and data leakage in financial research workflows. These subtle errors can completely invalidate backtests, event studies, and trading strategies.

CRITICAL AUDITING PRINCIPLES:

1. IDENTIFIER VALIDITY: Stock tickers, CUSIPs, and other identifiers change over time. A ticker valid today may not have existed or may have referred to a different company in the past.
   - META did not exist before June 2022 (was FB)
   - GOOGL/GOOG split occurred in April 2014
   - Tickers can be reused by different companies
   - Mergers and spinoffs create identifier discontinuities

2. INFORMATION AVAILABILITY: Information becomes public only when officially released. SEC EDGAR acceptance timestamps, not filing dates or fiscal period ends, determine when filings become available.
   - 8-Ks filed at 4:07 PM cannot be used for trades at 3:55 PM
   - 10-K filed February 20 cannot be used for January 15 portfolio
   - Fiscal year end (Dec 31) ≠ data availability (often Feb-Mar)

3. UNIVERSE CONSTRUCTION: The set of tradeable securities changes over time. Using only currently-listed companies for historical analysis introduces survivorship bias.
   - Delisted companies must be included for the periods they traded
   - Delisting returns (often large negative) must be properly handled
   - Index constituents change frequently

4. DO NOT ASSUME VALIDITY: A workflow that sounds plausible may still have subtle point-in-time errors. Your job is to actively identify issues, not to confirm that something looks reasonable.

{response_format}
""".strip()

# =============================================================================
# Few-Shot Examples
# =============================================================================

FEW_SHOT_EXAMPLE_1 = """
Example 1:

Workflow: "A researcher analyzes Facebook stock returns around the Cambridge Analytica news on March 2018 using ticker META."

Response:
{
  "validity": "invalid",
  "violations": ["identifier_time_travel"],
  "explanation": "META was not a valid ticker in March 2018. Facebook traded under ticker FB until June 2022 when it rebranded to Meta Platforms and changed its ticker to META.",
  "repair": [
    "Use ticker FB for events before June 9, 2022.",
    "Use CRSP PERMNO for consistent security identification across name changes."
  ],
  "confidence": 0.95
}
""".strip()

FEW_SHOT_EXAMPLE_2 = """
Example 2:

Workflow: "A trading strategy places orders at 2:00 PM based on an 8-K that was accepted by EDGAR at 10:30 AM the same day."

Response:
{
  "validity": "valid",
  "violations": [],
  "explanation": "The 8-K was accepted at 10:30 AM and the trade decision is at 2:00 PM. The filing was publicly available over 3 hours before the trading decision. This is point-in-time valid.",
  "repair": [],
  "confidence": 0.90
}
""".strip()

FEW_SHOT_EXAMPLE_3 = """
Example 3:

Workflow: "A momentum backtest from 2000-2015 downloads current CRSP data and filters to stocks still trading today."

Response:
{
  "validity": "invalid",
  "violations": ["survivorship_bias", "delisting_return_omission"],
  "explanation": "Filtering to stocks still trading today excludes companies that delisted during 2000-2015 (bankruptcies, mergers, going private). This introduces survivorship bias as poor performers are systematically excluded. Additionally, delisting returns are likely not captured.",
  "repair": [
    "Use point-in-time universe at each rebalance date.",
    "Include all stocks that were tradeable during the backtest period.",
    "Apply CRSP delisting returns when stocks leave the sample."
  ],
  "confidence": 0.92
}
""".strip()


SYSTEM_PROMPT_COT = """
You are an expert financial research auditor specializing in point-in-time data validity for quantitative finance research.

Your primary task is to identify look-ahead bias and data leakage in financial research workflows. These subtle errors can completely invalidate backtests, event studies, and trading strategies.

IMPORTANT: Before providing your JSON response, you MUST think through your analysis step by step. Follow this reasoning process:

STEP 1 - TIMELINE RECONSTRUCTION: Identify every date and timestamp mentioned. Place them on a timeline. Note which events happen before or after which other events.

STEP 2 - IDENTIFIER CHECK: For each stock ticker, CUSIP, or PERMNO used, verify whether it was valid for the time period in question. Remember that tickers change (FB→META in June 2022, GOOGL/GOOG split in April 2014) and can be reused by different companies.

STEP 3 - INFORMATION AVAILABILITY: For each piece of data used in a decision, determine when that data became publicly available. SEC filings are available at their EDGAR acceptance timestamp, not the filing date or fiscal period end. Accounting data is available when the 10-K/10-Q is filed, not when the fiscal period closes.

STEP 4 - UNIVERSE CONSTRUCTION: Check whether the set of securities analyzed could have been constructed at the time. Watch for survivorship bias (only including companies that exist today) and missing delisting returns.

STEP 5 - VERDICT: Based on steps 1-4, determine if any violations exist. If everything checks out, say valid. If you find issues, list them. If you need more information to be certain, say ambiguous.

After your step-by-step reasoning, provide your final answer as a JSON object.

{response_format}
""".strip()


def get_system_prompt(
    prompt_type: Literal["default", "finance_auditor", "minimal", "chain_of_thought"] = "finance_auditor"
) -> str:
    """
    Get the system prompt for a given configuration.

    Args:
        prompt_type: Type of system prompt to use.
            - "minimal": Brief instructions with response format only
            - "default": Standard auditor instructions with examples
            - "finance_auditor": Detailed expert auditor with specific guidance
            - "chain_of_thought": Step-by-step reasoning before JSON answer

    Returns:
        The system prompt string with response format instructions included.
    """
    if prompt_type == "minimal":
        base_prompt = SYSTEM_PROMPT_MINIMAL
    elif prompt_type == "default":
        base_prompt = SYSTEM_PROMPT_DEFAULT
    elif prompt_type == "chain_of_thought":
        base_prompt = SYSTEM_PROMPT_COT
    else:  # finance_auditor
        base_prompt = SYSTEM_PROMPT_FINANCE_AUDITOR

    # All prompts now include response format
    return base_prompt.format(response_format=RESPONSE_FORMAT_INSTRUCTIONS)


def get_response_format_instructions() -> str:
    """Get the JSON response format instructions."""
    return RESPONSE_FORMAT_INSTRUCTIONS


def get_few_shot_examples(n: int = 2) -> str:
    """
    Get few-shot examples to include in the prompt.
    
    Args:
        n: Number of examples to include (0-3).
    
    Returns:
        String containing the examples, or empty string if n=0.
    """
    if n <= 0:
        return ""
    
    examples = [FEW_SHOT_EXAMPLE_1, FEW_SHOT_EXAMPLE_2, FEW_SHOT_EXAMPLE_3]
    selected = examples[:min(n, len(examples))]
    
    header = "\n\nHere are some examples of audit tasks and correct responses:\n\n"
    return header + "\n\n".join(selected)


def format_benchmark_prompt(case: BenchmarkCase, include_few_shot: int = 0) -> str:
    """
    Format a benchmark case as a user prompt.
    
    Args:
        case: The benchmark case to format.
        include_few_shot: Number of few-shot examples to include (0-3).
    
    Returns:
        The formatted user prompt.
    """
    few_shot = get_few_shot_examples(include_few_shot)
    
    prompt = f"""
{few_shot}

Audit the following financial research workflow for point-in-time validity:

{case.prompt}

Analyze this workflow carefully. Identify any point-in-time validity issues including look-ahead bias, identifier errors, or survivorship bias. Return your assessment as a JSON object.
""".strip()
    
    return prompt


def get_violation_descriptions() -> dict[ViolationType, str]:
    """
    Get human-readable descriptions for each violation type.
    
    Returns:
        Dictionary mapping violation types to descriptions.
    """
    return {
        ViolationType.IDENTIFIER_TIME_TRAVEL: (
            "Using a stock ticker, CUSIP, or other identifier that was not valid "
            "for the historical period being studied."
        ),
        ViolationType.ISSUER_SECURITY_CONFUSION: (
            "Confusing issuer-level and security-level identifiers, or failing to "
            "track the correct security through corporate actions."
        ),
        ViolationType.FILING_CLOCK_LEAKAGE: (
            "Using information from an SEC filing before the filing was publicly "
            "available on EDGAR."
        ),
        ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE: (
            "Using accounting data before the financial statements containing "
            "that data were publicly filed."
        ),
        ViolationType.RESTATEMENT_LEAKAGE: (
            "Using restated financial data for a period before the restatement "
            "was filed."
        ),
        ViolationType.SURVIVORSHIP_BIAS: (
            "Including only companies that survived to the present, excluding "
            "companies that delisted, merged, or went bankrupt."
        ),
        ViolationType.DELISTING_RETURN_OMISSION: (
            "Failing to include delisting returns when a company stops trading, "
            "especially for distressed delistings."
        ),
        ViolationType.WRONG_EVENT_WINDOW: (
            "Using an event window that does not properly align with when the "
            "event information became public."
        ),
        ViolationType.TIMEZONE_ERROR: (
            "Incorrectly handling timezone conversions, especially for filings "
            "or trading across different time zones."
        ),
    }
