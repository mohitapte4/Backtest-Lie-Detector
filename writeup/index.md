# Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research

*UChicago Generative AI for Finance, Spring 2026*

---

## Executive Summary

Large Language Models are increasingly used to write, review, and audit trading strategies and financial research. But can they catch the subtle data leakage issues that invalidate backtests? We created a benchmark to find out.

**Key Finding (V4 Benchmark):**
> LLMs are excellent at catching obvious point-in-time violations, but they are **overly cautious** and struggle to distinguish truly invalid workflows from valid-but-suspicious ones. They also struggle to express uncertainty when the correct answer is ambiguous.

**Results Summary:**
- **GPT-4o achieves 79.2% overall accuracy** on our 125-case V4 benchmark
- **Zero false valids** - the model never approves a truly invalid workflow
- **29% false invalid rate** - valid workflows are frequently flagged incorrectly
- **21% ambiguous accuracy** - the model rarely identifies genuinely ambiguous cases
- **59% trap-valid accuracy** - sophisticated valid cases frequently trigger false alarms

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

## Benchmark Evolution: V1 → V4

Our benchmark evolved over four iterations to create increasingly challenging tests:

| Version | Cases | Description | Key Finding |
|---------|-------|-------------|-------------|
| V1 | 42 | Original seed cases | 97.6% accuracy - too easy |
| V2 | 69 | +17 adversarial, +10 WRDS | 95.7% accuracy - harder |
| V3 | 105 | +36 hard source-backed | 84.8% accuracy - challenging |
| **V4** | **125** | +20 calibration-focused | **79.2% accuracy** - overcaution revealed |

### V4 Benchmark Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                    V4 Benchmark Structure (125 cases)                │
├─────────────────────┬──────────────────┬───────────────────────────┤
│ Ticker Time Machine │ Filing Clock     │ Accounting Availability   │
│ (45 cases)          │ (27 cases)       │ (21 cases)                │
├─────────────────────┴──────────────────┴───────────────────────────┤
│              Survivorship & Delisting (32 cases)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Expected Validity:  Valid: 41  |  Invalid: 70  |  Ambiguous: 14   │
├─────────────────────────────────────────────────────────────────────┤
│  Special Tags:  trap_valid: 22  |  ambiguous: 14  |  multi: 8      │
└─────────────────────────────────────────────────────────────────────┘
```

**V4 Calibration Cases:**
- **8 Valid Trap Cases**: Look suspicious but are actually correct
- **8 Ambiguous Cases**: Correct answer is "needs more information"  
- **4 Hard Invalid Cases**: Subtle but real violations

---

## Case Families (13 Source-Backed Families)

V3/V4 includes hard cases based on real-world finance traps:

1. **Ticker Reassignment** (Sears S → Sprint S, 2005)
2. **Security Reorganization** (Manville bankruptcy PERMNO split)
3. **FB-to-META Timing** (June 9, 2022 intraday transition)
4. **GOOG vs GOOGL** (Share class for governance studies)
5. **IBM/Kyndryl Spinoff** (November 2021 distribution)
6. **SEC Filing Clock** (5:30 PM acceptance, next-day dissemination)
7. **S&P Index Announcement vs Effective** (5-day gap)
8. **Erroneous Index Announcements** (Revoked changes)
9. **Compustat Current vs PIT** (Snapshot methodology)
10. **As-Filed vs Standardized** (XBRL extraction differences)
11. **Adjusted Price Semantics** (Returns vs levels)
12. **Delisting Return Treatment** (Shumway methodology)
13. **Earnings Timing Windows** (Pre-market vs after-close)

---

## V4 Results: The Overcaution Discovery

### Overall Performance

| Configuration | Validity Accuracy | False Invalid Rate | Ambiguous Accuracy |
|---------------|-------------------|--------------------|--------------------|
| GPT-4o (Finance Auditor) | **79.2%** | 29.3% | 21.4% |
| GPT-4o (Generic) | 0%* | N/A | N/A |

*Generic prompt failed to produce parseable JSON responses

### The Key Insight: Asymmetric Errors

| Error Type | Count | Rate | Implication |
|------------|-------|------|-------------|
| False Valids (missed violations) | **0** | 0% | Model is safe |
| False Invalids (overcautious) | 12 | 29.3% of valid cases | Model is cautious |
| Ambiguous → Invalid | 10 | 71.4% of ambiguous | Model avoids uncertainty |

**The model never approves a truly invalid workflow**, but it frequently flags valid workflows as problematic.

### Performance by Case Tag

| Tag | Accuracy | Cases | Notes |
|-----|----------|-------|-------|
| `multi_violation` | 100% | 8 | Easy to catch multiple issues |
| `requires_identifier_reasoning` | 78.6% | 14 | Ticker/PERMNO logic |
| `requires_corporate_action_reasoning` | 62.5% | 8 | Spinoffs, splits |
| `requires_dataset_semantics` | 61.5% | 13 | CRSP/Compustat fields |
| `trap_valid` | 59.1% | 22 | Valid but suspicious |
| `requires_timestamp_reasoning` | 43.8% | 16 | Filing timing |
| `ambiguous` | 21.4% | 14 | Uncertainty expression |

---

## Failure Taxonomy

### Primary Failure Mode: Overcaution

The model errs toward caution in predictable ways:

1. **Dataset Semantics Blindness**: Doesn't understand that CRSP adjusted returns already incorporate spinoffs and dividends

2. **Timestamp Overcaution**: Assumes timing problems when methodology is sound

3. **Ambiguity Aversion**: Defaults to "invalid" rather than acknowledging uncertainty

4. **Trigger-Happy on Keywords**: Flags "spinoff" or "ticker change" without analyzing whether it was handled correctly

### Example Failures

**Case: `hard_ibm_crsp_adjusted_return`**
- Prompt: Researcher uses CRSP ret field for IBM in November 2021 (Kyndryl spinoff)
- Expected: Valid (CRSP ret already incorporates spinoff adjustment)
- Predicted: Invalid (identifier_time_travel)
- **Lesson**: Model doesn't know CRSP handles corporate actions

**Case: `cal_ambig_compustat_unknown_lag`**
- Prompt: Compustat data used for June portfolio, lag methodology unspecified
- Expected: Ambiguous (need more information)
- Predicted: Invalid (accounting_availability_leakage)
- **Lesson**: Model assumes worst case rather than expressing uncertainty

See `outputs/results/failure_casebook.md` for detailed analysis of 10 instructive failures.

---

## Practical Implications

### For Researchers Using LLMs as Auditors

1. **Trust "valid" verdicts** - zero false valid rate means approval is reliable
2. **Scrutinize "invalid" verdicts** - 29% are false alarms, review carefully
3. **Treat "ambiguous" as "might be valid"** - model under-reports ambiguity
4. **Provide detailed methodology** - unclear descriptions trigger false positives
5. **Explain your adjustments explicitly** - "using CRSP adjusted returns" helps

### For LLM Developers

1. **Calibration matters** - models should express uncertainty appropriately
2. **Dataset semantics training needed** - CRSP/Compustat field meanings
3. **"Safe" ≠ "Good"** - overcaution reduces practical utility

### For Finance Education

1. **LLMs catch obvious violations** - useful teaching tool
2. **Edge cases reveal model limits** - trap valid cases are educational
3. **Point-in-time thinking is essential** - benchmark demonstrates importance

---

## Visualizations

### Key Figures (in `outputs/figures/`)

1. **v4_summary.png** - Comprehensive results overview
2. **v4_calibration_breakdown.png** - Accuracy by validity type and tags
3. **v4_difficulty_breakdown.png** - Easy/Medium/Hard performance
4. **v4_module_accuracy.png** - Per-module breakdown
5. **v4_confidence_calibration.png** - Confidence vs accuracy
6. **v4_overcaution_analysis.png** - False invalid rate analysis

---

## Limitations

1. **Single model tested** - Only GPT-4o on V4 (Claude requires API access)
2. **Prompt sensitivity** - Generic prompt completely fails to produce valid JSON
3. **Ground truth ambiguity** - Some "trap valid" cases have debatable answers
4. **Benchmark size** - 125 cases covers main patterns but not exhaustively
5. **No fine-tuning** - Using base model capabilities only
6. **English only** - All prompts and cases in English

---

## Reproducibility

### Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/backtest-lie-detector
cd backtest-lie-detector
pip install -e ".[all]"

# Generate V4 benchmark
python -m backtest_lie_detector.benchmark.build_cases v4

# Run V4 evaluation
python run_v4_comparison.py

# Generate figures
python generate_v4_figures.py
```

### Benchmark Versions
- `benchmark_v1.jsonl`: Original 42 cases
- `benchmark_v2.jsonl`: 69 cases (+adversarial, +WRDS)
- `benchmark_v3.jsonl`: 105 cases (+hard source-backed)
- `benchmark_v4.jsonl`: 125 cases (+calibration-focused)

### Output Files
- `outputs/results/scores_v4.csv` - Per-case results
- `outputs/results/calibration_scores_v4.csv` - Calibration metrics
- `outputs/results/failure_casebook.md` - Detailed failure analysis
- `outputs/figures/v4_*.png` - Visualization plots

---

## Conclusion

**Main Finding:** LLMs are reliable at catching obvious point-in-time violations but suffer from significant overcaution when evaluating sophisticated, valid methodologies.

**Practical Recommendation:** Use LLMs as a first-pass screening tool with the understanding that:
- "Valid" verdicts can be trusted (0% false valid rate)
- "Invalid" verdicts require human review (29% false alarm rate)
- "Ambiguous" is under-reported (model defaults to invalid)

The benchmark reveals that financial domain knowledge - specifically understanding dataset semantics (CRSP adjusted returns, Compustat fields) and corporate action handling - remains a gap in current LLMs.

---

## AI Usage Statement

This project was developed with AI assistance:

- **Code generation**: Claude assisted with implementation
- **Documentation**: AI helped draft docstrings and writeup
- **Benchmark cases**: Templates AI-generated, all human-reviewed

**Human contributions:**
- Benchmark design and methodology
- Ground truth validation (all 125 cases)
- Results interpretation and failure analysis
- Case family research and source verification

---

## References

1. Shumway, T. (1997). "The Delisting Bias in CRSP Data"
2. Shumway, T. and Warther, V. (1999). "The Delisting Bias in CRSP's Nasdaq Data and Its Implications for the Size Effect"
3. Fama, E. and French, K. (1992). "The Cross-Section of Expected Stock Returns"
4. CRSP Database Documentation
5. SEC EDGAR Filing Documentation
6. Harvey, Liu, and Zhu (2016). "...and the Cross-Section of Expected Returns"

---

*Project completed for Generative and Agentic AI for Finance, Spring 2026*
