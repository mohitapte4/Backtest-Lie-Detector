# Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research

*UChicago Generative AI for Finance, Spring 2026*

---

## Executive Summary

Large Language Models are increasingly used to write, review, and audit trading strategies and financial research. But can they catch the subtle data leakage issues that invalidate backtests? We created a benchmark to find out.

**Key Findings (v2 Benchmark):**
- **GPT-4o achieves 95.7% validity accuracy** on our 69-case benchmark with specialized prompting
- Adversarial cases (designed to be hard) achieve only **88.2% accuracy** - confirming genuine difficulty
- Models are **overcautious** - all 3 failures are valid cases flagged as invalid
- **WRDS-backed cases achieve 100%** accuracy - models have accurate real-world knowledge
- **Prompt engineering matters** - finance auditor prompt significantly outperforms minimal prompts

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

We created **69 realistic audit tasks** (v2 benchmark) across four modules:

```
┌────────────────────────────────────────────────────────────────┐
│                    Benchmark Structure (v2)                     │
├────────────────────┬─────────────────┬─────────────────────────┤
│ Ticker Time Machine│ Filing Clock    │ Accounting Availability │
│ (22 cases)         │ (15 cases)      │ (14 cases)              │
├────────────────────┴─────────────────┴─────────────────────────┤
│              Survivorship & Delisting (18 cases)                │
├─────────────────────────────────────────────────────────────────┤
│  Case Types: 42 Original + 17 Adversarial + 10 WRDS-backed     │
└────────────────────────────────────────────────────────────────┘
```

**Case Types:**
- **Original (42)**: Standard audit tasks across difficulty levels
- **Adversarial (17)**: "Trap valid" cases, subtle invalids, multi-violation
- **WRDS-backed (10)**: Real ticker changes and delistings from CRSP data

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

### Overall Performance (v2 Benchmark)

| Configuration | Validity Acc | Violation Recall | Cases |
|---------------|--------------|------------------|-------|
| GPT-4o (Finance Auditor) | **95.7%** | 86.0% | 69 |
| GPT-4o (Minimal) | 73.8%* | 52.3%* | 42* |

*Minimal prompt tested on v1 benchmark (42 cases)

The **22-point accuracy gap** between prompts demonstrates the importance of domain-specific instructions.

### Performance by Module

| Module | Accuracy | Cases |
|--------|----------|-------|
| Filing Clock | 100% | 15 |
| Ticker Time Machine | 95.5% | 22 |
| Survivorship/Delisting | 94.4% | 18 |
| Accounting Availability | 92.9% | 14 |

Key observations:
- **Filing Clock**: Perfect accuracy - timestamps are unambiguous
- **Ticker Time Machine**: Strong performance despite complex corporate actions
- **Accounting Availability**: Lowest accuracy - fiscal calendar reasoning is challenging
- **Survivorship Bias**: Good on obvious cases, challenged by subtle filtering

### Performance by Difficulty

| Difficulty | Easy | Medium | Hard |
|------------|------|--------|------|
| Accuracy   | 100% | 95.8% | 92.9% |
| Cases      | 17   | 24     | 28    |

Hard cases are genuinely harder, with a 7% error rate vs 0% for easy.

### Performance by Case Type

| Case Type | Accuracy | Purpose |
|-----------|----------|---------|
| Original | 97.6% | Standard benchmark tasks |
| Adversarial | 88.2% | Designed to challenge |
| WRDS-backed | 100% | Real financial data |

Adversarial cases achieved their goal: **11.8% error rate** vs 2.4% on original.

---

## Failure Analysis

All 3 failures on the v2 benchmark are **false invalids** (overcautious):

### Specific Failures

1. **`acct_preliminary_vs_final`**
   - Expected: Valid (using preliminary earnings is fine)
   - Predicted: Invalid (flagged as restatement_leakage)
   - Model incorrectly thinks preliminary data constitutes leakage

2. **`trap_ticker_change_day_correct`**
   - Expected: Valid (FB on June 9, 2022 morning is correct)
   - Predicted: Invalid (identifier_time_travel)
   - Model doesn't recognize same-day usage of old ticker is valid

3. **`trap_survivorship_includes_delisted`**
   - Expected: Valid (share code filtering is standard)
   - Predicted: Ambiguous
   - Model overcautious about share code 10/11 filtering

### Failure Pattern

The model errs **toward caution** - it flags valid workflows as suspicious rather than missing real violations. This is arguably a safer failure mode for compliance but reduces usability.

### Confidence When Wrong

| Prediction | Mean Confidence |
|------------|-----------------|
| Correct | 0.953 |
| Incorrect | 0.900 |

The model is slightly less confident on mistakes, but the gap is small. This suggests **confidence calibration could be improved**.

---

## Implications

### For Researchers Using LLMs

1. **LLMs are capable auditors** - 95.7% accuracy is strong for a first pass
2. **Prompt engineering is crucial** - 22-point gap between prompts
3. **Expect overcaution** - Valid workflows may be flagged
4. **Use as screening tool** - Human review still needed for flagged cases

### For LLM Developers

1. **Edge cases are hard** - "Trap valid" cases reveal overcaution
2. **Real data grounding works** - WRDS-backed cases are handled well
3. **Structured output helps** - JSON forcing reduces parse failures to 0%

### For Finance Education

1. **These errors matter** - Real research has been invalidated by these issues
2. **LLMs can teach awareness** - They catch most violations and explain them
3. **Point-in-time thinking is essential** - The benchmark is itself educational

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

1. **Benchmark size**: 69 cases covers main patterns but not exhaustively
2. **Ground truth**: Some edge cases (trap valid) have debatable correct answers
3. **Model versions**: Results may vary with model updates
4. **Prompt sensitivity**: Different prompts yield significantly different results
5. **Single model tested**: Only GPT-4o evaluated on v2 (Claude pending API access)
6. **No real trading**: We test detection, not actual backtesting impact

---

## Reproducibility

All code, data, and results are available at: [GitHub Repository]

### Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/backtest-lie-detector
cd backtest-lie-detector
pip install -e ".[all]"

# Run evaluation (v2 benchmark)
python -m backtest_lie_detector.evals.run_eval \
    --benchmark data/benchmark/benchmark_v2.jsonl \
    --model gpt-4o \
    --config finance_auditor

# Launch demo
streamlit run src/backtest_lie_detector/app/streamlit_app.py
```

### Benchmark Versions
- `benchmark_v1.jsonl`: Original 42 cases
- `benchmark_v2.jsonl`: Enhanced 69 cases with adversarial + WRDS-backed

---

## Conclusion

GPT-4o with specialized prompting achieves **95.7% accuracy** as a point-in-time auditor, making it a capable first-pass tool for catching data leakage in financial research. Key takeaways:

1. **Prompt engineering matters** - 22-point accuracy gap between prompts
2. **Models are overcautious** - they flag valid workflows more than they miss violations
3. **Adversarial cases work** - designed hard cases successfully challenge the model
4. **Real data grounding helps** - WRDS-backed cases achieve 100% accuracy

For practitioners, this suggests LLMs can serve as an **effective screening tool** that reduces human review burden, though flagged cases still require expert verification. The model's bias toward caution is arguably preferable to missing real violations.

Future work could explore:
- Fine-tuning on financial audit tasks
- Retrieval-augmented generation with CRSP/Compustat data
- Multi-model ensemble approaches
- Expanding the benchmark to 200+ cases

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
