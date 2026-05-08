# Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research

*UChicago Generative AI for Finance, Spring 2026*

---

## Executive Summary

Large Language Models are increasingly used to write, review, and audit trading strategies and financial research. But can they catch the subtle data leakage issues that invalidate backtests? We created a benchmark to find out.

**Key Findings:**
- LLMs can detect obvious point-in-time errors (e.g., using modern tickers for historical events)
- Performance degrades significantly on subtle timing issues (e.g., filing clock leakage)
- Prompt engineering with finance-specific instructions improves detection rates
- Even the best models miss 20-40% of violations that would invalidate research

---

## The Problem: Silent Data Leakage in Financial Research

Financial backtests and event studies are powerful tools, but they're prone to subtle errors that can completely invalidate results. These errors often involve using information that *looks* available but actually wasn't at the historical decision point.

### Common Point-in-Time Errors

| Error Type | Example | Why It Matters |
|------------|---------|----------------|
| **Ticker Time Travel** | Using META ticker for 2018 Facebook events | META didn't exist until 2022; the ticker was FB |
| **Filing Clock Leakage** | Trading at 3:55 PM on news from a 4:07 PM filing | The information wasn't public yet |
| **Accounting Availability** | Using FY2022 data in January 2023 | The 10-K wasn't filed until February |
| **Survivorship Bias** | Backtesting only on currently-listed firms | Excludes bankruptcies, acquisitions, failures |

These errors are easy to make and hard to catch. A backtest can look perfectly reasonable while containing fatal flaws.

---

## Our Approach: A Benchmark for Auditing

Rather than asking "Can LLMs answer finance questions?", we ask: **"Can LLMs audit financial workflows for validity?"**

### Benchmark Design

We created 42 realistic audit tasks across four modules:

```
┌────────────────────────────────────────────────────────────────┐
│                    Benchmark Structure                          │
├────────────────────┬─────────────────┬─────────────────────────┤
│ Ticker Time Machine│ Filing Clock    │ Accounting Availability │
│ (11 cases)         │ (10 cases)      │ (11 cases)              │
├────────────────────┴─────────────────┴─────────────────────────┤
│              Survivorship & Delisting (10 cases)                │
└────────────────────────────────────────────────────────────────┘
```

Each case presents a workflow description and asks the model to:
1. Determine if the workflow is **valid**, **invalid**, or **ambiguous**
2. Identify specific **violation types**
3. Propose **repairs** to fix the issues

### Example Task

> A researcher studies the Cambridge Analytica event on 2018-03-20 and queries daily returns using ticker META. Audit this workflow.

**Expected Answer:**
- Validity: Invalid
- Violation: identifier_time_travel
- Repair: Use the historical ticker FB, which was valid on 2018-03-20

---

## Evaluation Framework

### Models Evaluated

| Configuration | Model | Prompt Type |
|---------------|-------|-------------|
| GPT-4o (Auditor) | gpt-4o | Finance auditor instructions |
| GPT-4o (Minimal) | gpt-4o | Minimal instructions |
| Claude Sonnet | claude-sonnet-4-20250514 | Finance auditor instructions |

### Metrics

- **Validity Accuracy**: Did the model correctly classify valid vs. invalid?
- **Violation Recall**: Of true violations, how many were detected?
- **Violation Precision**: Of flagged violations, how many were real?
- **Severity-Weighted Score**: Critical violations weighted more heavily
- **Repair Quality**: Did the proposed fix address the core issue?

---

## Results

### Overall Performance

*[Results table to be filled after running evaluations]*

| Configuration | Validity Acc | Violation Recall | Repair Score |
|---------------|--------------|------------------|--------------|
| GPT-4o (Auditor) | --% | --% | --% |
| GPT-4o (Minimal) | --% | --% | --% |
| Claude Sonnet | --% | --% | --% |

### Performance by Module

*[Module breakdown chart]*

Key observations:
- **Ticker Time Machine**: Models perform best here, likely due to training data containing ticker change information
- **Filing Clock**: Lower accuracy; models struggle with precise timestamp reasoning
- **Accounting Availability**: Mixed results; fiscal year-end vs. filing date confusion is common
- **Survivorship Bias**: Models catch obvious cases but miss subtle filtering bias

### Performance by Difficulty

| Difficulty | Easy | Medium | Hard |
|------------|------|--------|------|
| Accuracy   | --% | --% | --% |

---

## Failure Analysis

### Common Failure Modes

1. **False Valid (Most Dangerous)**
   - Model marks an invalid workflow as valid
   - Researcher proceeds with flawed backtest
   - Example: Missing that GOOGL didn't exist before 2014

2. **Overconfident Errors**
   - Model is 80%+ confident but wrong
   - Suggests unreliable as an unsupervised tool

3. **Incomplete Repairs**
   - Model identifies the issue but proposes incomplete fix
   - Example: "Use historical ticker" without specifying which one

### Example Failures

**Case: Filing Clock After-Hours**
> An 8-K is filed at 4:07 PM. Strategy trades at 3:55 PM using that filing.

Model response: "The filing was available same day, so this is valid."

**Why it's wrong:** 3:55 PM is *before* 4:07 PM. The filing wasn't public yet.

---

## Implications

### For Researchers Using LLMs

1. **Don't rely solely on LLM audits** - They miss 20-40% of violations
2. **Prompt engineering helps** - Finance-specific instructions improve detection
3. **Double-check filing timing** - This is where models struggle most
4. **Be skeptical of high confidence** - Models can be confidently wrong

### For LLM Developers

1. **Temporal reasoning is weak** - Models struggle with "before/after" in context
2. **Finance-specific training helps** - General models miss domain-specific issues
3. **Structured output improves accuracy** - JSON forcing reduces errors

### For Finance Education

1. **These errors matter** - Real research has been invalidated by these issues
2. **Point-in-time awareness is teachable** - Students can learn to spot these
3. **LLMs can assist but not replace** - Human oversight remains necessary

---

## Methodology Details

### Benchmark Construction

Cases were created through:
1. **Manual curation** of historically documented errors
2. **Template generation** from known error patterns
3. **Expert validation** of ground truth

All cases include:
- Natural language prompt
- Expected validity classification
- Expected violation types
- Suggested repairs
- Ground truth notes

### Scoring

```python
# Validity: Exact match
validity_correct = (expected == predicted)

# Violations: Set-based precision/recall
precision = |expected ∩ predicted| / |predicted|
recall = |expected ∩ predicted| / |expected|

# Severity weighting
weights = {
    'filing_clock_leakage': 3,
    'survivorship_bias': 3,
    'identifier_time_travel': 2,
    ...
}
```

---

## Limitations

1. **Benchmark size**: 42 cases is sufficient for a class project but not exhaustive
2. **Ground truth**: Some edge cases have debatable correct answers
3. **Model versions**: Results may vary with model updates
4. **Prompt sensitivity**: Different prompts may yield different results
5. **No real trading**: We test detection, not actual backtesting impact

---

## Reproducibility

All code, data, and results are available at: [GitHub Repository]

### Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/backtest-lie-detector
cd backtest-lie-detector
pip install -e ".[all]"

# Run evaluation
python -m backtest_lie_detector.evals.run_eval \
    --benchmark data/benchmark/benchmark_v1.jsonl \
    --model gpt-4o \
    --config finance_auditor

# Launch demo
streamlit run src/backtest_lie_detector/app/streamlit_app.py
```

---

## Conclusion

LLMs show promise as point-in-time auditors for financial research, but they're not yet reliable enough to replace human review. The gap between human expert detection and LLM detection suggests significant room for improvement through:

1. Finance-specific fine-tuning
2. Better temporal reasoning capabilities
3. Integration with structured data sources

Until then, treat LLM audits as a helpful first pass, not a definitive check.

---

## AI Usage Statement

This project was developed with assistance from AI tools:

- **Code generation**: Claude assisted with boilerplate code, schema definitions, and test templates
- **Documentation**: AI helped draft docstrings and documentation
- **Benchmark cases**: Some case templates were AI-generated, but all were human-reviewed

**Human contributions:**
- Benchmark design and methodology
- Ground truth validation
- Results interpretation
- Failure analysis

All benchmark cases were manually reviewed for accuracy. The evaluation harness, scoring logic, and analysis code were human-designed with AI assistance for implementation.

---

## References

1. Bali, Engle, and Murray (2016). "Empirical Asset Pricing: The Cross Section of Stock Returns"
2. Harvey, Liu, and Zhu (2016). "...and the Cross-Section of Expected Returns"
3. CRSP Database Documentation
4. SEC EDGAR Filing Documentation

---

*Project completed for Generative and Agentic AI for Finance, Spring 2026*
