# Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research

*UChicago Generative AI for Finance, Spring 2026*

---

## Executive Summary

Large Language Models are increasingly used to write, review, and audit trading strategies and financial research. But can they catch the subtle data leakage issues that invalidate backtests? We created a benchmark to find out.

**Key Findings (V5 Benchmark - Final):**
> 1. LLMs are excellent at catching obvious violations but **overly cautious** on edge cases
> 2. **Simple vs specialized prompts**: Generic prompts have higher accuracy on average, but **specialized prompts catch 100% of subtle violations**
> 3. Models struggle to express uncertainty when the correct answer is ambiguous
> 4. **The prompt engineering paradox is nuanced** - V5 false valid traps show specialized prompts matter for hard cases

**V5 Results Summary (141 cases):**
- **GPT-4o (Generic):** 83.0% accuracy, 4.7% false valid rate
- **GPT-4o (Specialized):** 80.9% accuracy, **0.0% false valid rate**
- **Claude Sonnet:** 78.0% accuracy, 1.2% false valid rate
- **On 16 subtle false-valid-trap cases:** Generic missed 3, Specialized/Claude missed 0

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

## Relationship to Hallucination Benchmarks

Existing LLM benchmarks like AA-Omniscience and TruthfulQA test whether models make up facts. They ask questions like "What year did X happen?" and measure whether the model gives correct answers or hallucinates incorrect ones. These benchmarks test factual recall.

Our benchmark tests something different: can LLMs recognize when events are out of chronological order? Instead of asking "What is the date?", we ask "Is this sequence of events possible given these dates?" This is anachronism detection rather than fact retrieval.

| Aspect | Hallucination Benchmarks | This Benchmark |
|--------|-------------------------|----------------|
| Tests | Does the LLM know facts? | Does the LLM understand temporal ordering? |
| Question type | "What is X?" | "Is this workflow chronologically valid?" |
| Failure mode | Making up facts | Missing anachronisms |
| Domain | General knowledge | Finance-specific workflows |

Both types of benchmarks measure reliability, but they target different capabilities. A model could score well on factual recall (knowing that META started trading June 9, 2022) but still miss the anachronism when that fact appears in context (using META for a June 1, 2022 trade). Our benchmark tests whether models can apply temporal knowledge to detect impossible sequences.

---

## Benchmark Evolution: V1 → V5

Our benchmark evolved over five iterations to create increasingly challenging tests:

| Version | Cases | Description | Key Finding |
|---------|-------|-------------|-------------|
| V1 | 42 | Original seed cases | 97.6% accuracy - too easy |
| V2 | 69 | +17 adversarial, +10 WRDS | 95.7% accuracy - harder |
| V3 | 105 | +36 hard source-backed | 84.8% accuracy - challenging |
| V4 | 125 | +20 calibration-focused | 79.2% accuracy - overcaution revealed |
| **V5** | **141** | +16 false valid traps | **Nuanced findings on prompt engineering** |

### V5 Benchmark Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                    V5 Benchmark Structure (141 cases)                │
├─────────────────────┬──────────────────┬───────────────────────────┤
│ Ticker Time Machine │ Filing Clock     │ Accounting Availability   │
│ (48 cases)          │ (31 cases)       │ (24 cases)                │
├─────────────────────┴──────────────────┴───────────────────────────┤
│              Survivorship & Delisting (38 cases)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Expected Validity:  Valid: 41  |  Invalid: 86  |  Ambiguous: 14   │
├─────────────────────────────────────────────────────────────────────┤
│  Special Tags:  trap_valid: 22 | false_valid_trap: 16 | near_miss: 17 │
└─────────────────────────────────────────────────────────────────────┘
```

**V5 False Valid Trap Cases (16 new):**
- Workflows with **professional language** that sounds point-in-time valid
- Hidden **implementation-level bugs** requiring dataset semantics knowledge
- All labeled as `invalid` but designed to trigger **false valid errors**

---

## Case Families (13 Source-Backed Families)

V3/V4 includes hard cases based on real-world finance traps. Each family is tied to authoritative documentation:

| # | Family | Example | Source |
|---|--------|---------|--------|
| 1 | **Ticker Reassignment** | Sears S → Sprint S, 2005 | CRSP Stock Header documentation |
| 2 | **Security Reorganization** | Manville bankruptcy PERMNO split | CRSP Event documentation |
| 3 | **FB-to-META Timing** | June 9, 2022 intraday transition | Meta SEC 8-K filing (June 2022) |
| 4 | **GOOG vs GOOGL** | Share class for governance studies | Alphabet Proxy Statement (2014) |
| 5 | **IBM/Kyndryl Spinoff** | November 2021 distribution | IBM SEC Form 10 filing |
| 6 | **SEC Filing Clock** | 5:30 PM acceptance rules | SEC EDGAR Filer Manual |
| 7 | **S&P Index Timing** | Announcement vs effective date | S&P Index Methodology Guide |
| 8 | **Erroneous Announcements** | Revoked index changes | Historical S&P press releases |
| 9 | **Compustat Current vs PIT** | Snapshot methodology | WRDS Compustat documentation |
| 10 | **As-Filed vs Standardized** | XBRL extraction differences | Compustat User Guide |
| 11 | **Adjusted Price Semantics** | Returns vs levels | CRSP Data Definitions Manual |
| 12 | **Delisting Returns** | Conservative imputation | Shumway (1997), Shumway & Warther (1999) |
| 13 | **Earnings Timing** | Pre-market vs after-close | I/B/E/S Timing Flag documentation |

---

## Ground Truth Labeling Protocol

### Validity Labels

Each benchmark case is labeled with one of three validity values:

| Label | Definition | Criteria |
|-------|------------|----------|
| **Valid** | Workflow is point-in-time correct | All data used was publicly available at decision time; identifiers correctly match the historical period |
| **Invalid** | Clear violation identifiable from prompt | At least one unambiguous point-in-time error is present |
| **Ambiguous** | Missing critical information | Cannot determine validity without additional context |

### When is "Ambiguous" Correct?

A case is labeled ambiguous **only** when the prompt lacks information required to determine point-in-time validity. The five categories that trigger ambiguous labels:

1. **Missing filing acceptance timestamp** - The filing date is given but not the exact acceptance time needed to determine same-day availability
2. **Unspecified accounting lag methodology** - Uses Compustat data but doesn't specify whether point-in-time snapshots or standard lag was applied
3. **Missing share-class purpose specification** - Uses GOOG vs GOOGL without clarifying if share class matters for the research question
4. **Missing event decision timestamp** - Trading decision time unclear relative to information release
5. **Unspecified data source version** - Doesn't clarify if using current download or historical snapshot

### Examples from Benchmark

| Case ID | Label | Why This Label |
|---------|-------|----------------|
| `cal_ambig_filing_no_timestamp` | Ambiguous | "Filed on March 15" - no acceptance time given |
| `cal_ambig_compustat_unknown_lag` | Ambiguous | Uses Compustat for June portfolio - lag method unspecified |
| `cal_valid_crsp_adjusted_return` | Valid | CRSP `ret` field correctly handles spinoff adjustments |
| `hard_meta_june9_intraday` | Invalid | Uses META at 10 AM on June 9, 2022 - ticker changed at market open |

---

## V4 Results: Multi-Model Comparison

### Model Leaderboard

| Configuration | Accuracy | False Invalid | False Valid | Ambiguous Acc |
|---------------|----------|---------------|-------------|---------------|
| GPT-4o (Generic) | **83.2%** | **22.0%** | 1.4% | 21.4% |
| GPT-4o (Specialized) | 79.2% | 36.6% | 1.4% | 28.6% |
| Claude Sonnet 4.5 | 75.2% | 43.9% | 1.4% | 14.3% |

### Baseline Comparison

| Baseline | Accuracy | False Invalid | False Valid |
|----------|----------|---------------|-------------|
| Always Invalid | 56.0% | 100.0% | 0.0% |
| Keyword Suspicion | 40.8% | 4.9% | 82.9% |
| Rule-Based | 38.4% | 14.6% | 81.4% |
| Always Valid | 32.8% | 0.0% | 100.0% |

**Key insight:** LLMs dramatically outperform rule-based approaches on violation detection (1.4% false valid vs 81-100%), while baselines help contextualize that LLM overcaution (22-44% false invalid) is still far better than naive "always invalid" (100%).

### Repair Quality Analysis

Beyond classification, we evaluated whether models propose *useful* repairs (30 cases sampled per model):

| Model | Correct | Partial | Wrong/Vague |
|-------|---------|---------|-------------|
| Claude Sonnet | **66.7%** | 30.0% | 3.3% |
| GPT-4o (Specialized) | 40.0% | 36.7% | 23.3% |
| GPT-4o (Generic) | 36.7% | 26.7% | 36.7% |

**Surprising finding:** Claude Sonnet produces significantly better repair suggestions despite lower classification accuracy. This suggests Claude's overcaution may stem from *deeper understanding* of potential issues, even when the workflow is actually valid.

### The Surprising Finding: Simpler Is Better

The generic prompt **outperformed** the specialized finance auditor prompt by 4 percentage points. This reveals a **prompt engineering paradox**: detailed domain expertise in the prompt may *increase* overcaution.

### The Key Insight: Asymmetric Errors

| Error Type | Specialized | Generic | Implication |
|------------|-------------|---------|-------------|
| False Valids (missed violations) | 1.4% | 1.4% | Both very safe |
| False Invalids (overcautious) | 36.6% | 22.0% | Specialized is more cautious |
| Valid Trap Accuracy | 59.1% | 72.7% | Generic handles edge cases better |

**Both prompts almost never approve truly invalid workflows** (1.4% false valid rate), but the specialized prompt's extensive guidance about pitfalls makes it more likely to flag valid workflows as problematic.

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

1. **Trust "valid" verdicts** - ~1% false valid rate means approval is reliable
2. **Scrutinize "invalid" verdicts** - 22-37% are false alarms, review carefully
3. **Consider simpler prompts** - detailed domain prompts may increase false positives
4. **Treat "ambiguous" as "might be valid"** - model under-reports ambiguity
5. **Provide detailed methodology** - unclear descriptions trigger false positives

### For LLM Developers

1. **Calibration matters** - models should express uncertainty appropriately
2. **Dataset semantics training needed** - CRSP/Compustat field meanings
3. **"Safe" ≠ "Good"** - overcaution reduces practical utility
4. **Prompt engineering is counterintuitive** - more expertise in prompt can hurt

### For Finance Education

1. **LLMs catch obvious violations** - useful teaching tool
2. **Edge cases reveal model limits** - trap valid cases are educational
3. **Point-in-time thinking is essential** - benchmark demonstrates importance

---

## Visualizations

### Key Figures (in `outputs/figures/`)

**V5 Figures:**
1. **v5_overall.png** - V5 accuracy, false invalid, and false valid rates
2. **v5_false_valid_traps.png** - Performance on the 16 subtle trap cases
3. **v5_vs_v4_comparison.png** - How false valid rates changed with new cases
4. **v5_nuanced_finding.png** - Performance by case difficulty type

**V4 Figures:**
5. **v4_multimodel_comparison.png** - 3-model accuracy and metrics comparison
6. **v4_llm_vs_baselines.png** - LLMs vs rule-based baselines
7. **v4_tradeoff_scatter.png** - Safety vs utility trade-off visualization

---

## V5 Results: The Prompt Engineering Reversal

V4 found that generic prompts outperform specialized prompts. **V5 adds nuance to this finding.**

### False Valid Trap Case Results

We designed 16 new cases that sound professional and valid but contain subtle implementation bugs:

| Model | Trap Accuracy | False Valids | Cases Missed |
|-------|--------------|--------------|--------------|
| Claude Sonnet | **100%** | 0/16 | None |
| GPT-4o (Specialized) | **93.8%** | 0/16 | None (1 flagged ambiguous) |
| GPT-4o (Generic) | 81.2% | **3/16** | 3 subtle bugs missed |

### Cases GPT-4o Generic Missed

| Case | Bug | Reassuring Language |
|------|-----|---------------------|
| `fvt_lag_from_datadate` | Uses 6-month lag from fiscal end instead of filing date | "lags fundamentals by 6 months" |
| `fvt_adjusted_price_level` | Uses split-adjusted prices for $5 price filter | "uses split-adjusted prices" |
| `fvt_current_industry` | Uses 2026 GICS codes for 2000-2020 backtest | "controls for industry effects" |

### The Nuanced Finding

**V4 conclusion (simplified):** "Generic prompts beat specialized prompts"

**V5 conclusion (nuanced):**
- For **obvious violations**: Generic prompts work fine and avoid overcaution
- For **subtle violations**: Specialized prompts significantly improve detection
- **Zero false valid rate** with specialized prompt across all 141 cases

### V4 vs V5 False Valid Rate Comparison

| Model | V4 FVR (125 cases) | V5 FVR (141 cases) | Change |
|-------|-------------------|-------------------|--------|
| GPT-4o (Generic) | 1.4% | **4.7%** | **+3.2%** |
| GPT-4o (Specialized) | 0.0% | **0.0%** | 0.0% |
| Claude Sonnet | 1.4% | 1.2% | -0.2% |

The false valid trap cases increased the generic prompt's false valid rate from 1.4% to 4.7%, while the specialized prompt maintained perfect safety.

### Practical Recommendation (Revised)

| Use Case | Recommended Prompt |
|----------|-------------------|
| Maximum safety (zero tolerance for false valids) | **Specialized** |
| Best accuracy-caution tradeoff | Generic |
| Repair suggestions important | Claude Sonnet |
| Simple/obvious cases | Generic |
| Complex methodology with reassuring language | **Specialized** |

---

## Limitations

1. **Two models tested** - GPT-4o and Claude Sonnet; more models would strengthen conclusions
2. **Two prompt variants** - More prompt engineering could yield better results
3. **Ground truth requires domain expertise** - Some trap valid cases have debatable answers (see protocol above)
4. **Benchmark size** - 141 cases covers main patterns but not exhaustively
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

# Generate V5 benchmark
python -m backtest_lie_detector.benchmark.build_cases v5

# Run V5 evaluation (only new cases - saves API calls)
python run_v5_newcases_only.py

# Combine with V4 results and compute metrics
python compute_v5_metrics.py

# Generate V5 figures
python generate_v5_figures.py
```

### Benchmark Versions
- `benchmark_v1.jsonl`: Original 42 cases
- `benchmark_v2.jsonl`: 69 cases (+adversarial, +WRDS)
- `benchmark_v3.jsonl`: 105 cases (+hard source-backed)
- `benchmark_v4.jsonl`: 125 cases (+calibration-focused)
- `benchmark_v5.jsonl`: **141 cases** (+16 false valid traps)

### Output Files
- `outputs/results/V5_RESULTS.md` - Complete V5 results summary
- `outputs/results/model_outputs_v5_*.jsonl` - Per-model V5 results
- `outputs/results/failure_casebook.md` - Detailed failure analysis
- `outputs/figures/v5_*.png` - V5 visualization plots

---

## Conclusion

**Main Findings (V5):** 
1. LLMs are reliable at catching obvious point-in-time violations (~99% catch rate)
2. Overcaution is the primary failure mode (20-44% false invalid rate)
3. **Prompt engineering matters, but is context-dependent:**
   - Generic prompts: higher overall accuracy, but miss subtle violations
   - Specialized prompts: lower accuracy due to overcaution, but **0% false valid rate**
4. **Accuracy and repair quality are inversely correlated** - Claude has lowest accuracy but best repairs
5. **Subtle violations require domain expertise** - generic prompts missed 3/16 false valid trap cases

**Practical Recommendations:**

| Priority | Recommendation |
|----------|---------------|
| **Maximum Safety** | Use specialized prompt (0% false valid rate) |
| **Best Accuracy** | Use generic prompt (83% accuracy) |
| **Best Repairs** | Use Claude Sonnet (67% correct repairs) |
| **Subtle/Complex Cases** | Use specialized prompt |
| **Simple/Obvious Cases** | Use generic prompt |

**The V5 insight:** The V4 finding that "generic beats specialized" was partially an artifact of obvious invalid cases. When we added 16 subtle violations with professional language, the generic prompt failed on 3 cases while specialized and Claude caught all 16.

**Compared to Baselines:** LLMs dramatically outperform rule-based approaches (0-4.7% vs 81% false valid rate), demonstrating genuine understanding beyond keyword matching.

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
