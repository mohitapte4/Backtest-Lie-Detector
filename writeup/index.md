# Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors for Financial Research

*UChicago Generative AI for Finance, Spring 2026*

---

## Executive Summary

Large Language Models are increasingly used to write, review, and audit trading strategies and financial research. But can they catch the subtle data leakage issues that invalidate backtests? We created a benchmark to find out.

**Key Findings:**
> 1. LLMs are reliable at catching obvious point-in-time violations but **overly cautious** on edge cases
> 2. **The prompt-engineering effect is context-dependent**: leaner prompts (`minimal`, `default`) are sometimes fooled by subtle traps; specialized, few-shot, and chain-of-thought catch every trap
> 3. Models under-express uncertainty: even on cases with insufficient information they default to "invalid" rather than "ambiguous"
> 4. Domain priming via the `finance_auditor` prompt does **not** transfer to factual recall (see AA-Omniscience section)

**Main-Benchmark Results Summary (141 cases, Specialized / `zero_shot` prompt unless noted):**
- **GPT-4o (Generic):** 83.7% accuracy, 4.7% false valid rate
- **GPT-4o (Specialized):** 80.9% accuracy, **0.0% false valid rate**
- **GPT-4o + Chain-of-Thought:** **85.1% accuracy** (highest of any configuration), 0.0% false valid rate
- **Claude Sonnet 4.5:** 77.3% accuracy, 43.9% false invalid rate, 1.2% false valid rate
- **Claude Sonnet 4.6:** 80.9% accuracy, **12.2% false invalid rate** (least overcautious of any Claude variant), 1.2% false valid rate
- **Claude Haiku 4.5:** 74.5% accuracy, 41.5% false invalid rate, 1.2% false valid rate
- **GPT-4o-mini (Generic):** 64.5% accuracy, **0.0% false valid rate**, 95.1% false invalid rate
- **GPT-4o-mini (Specialized):** 62.4% accuracy, **0.0% false valid rate**, 97.6% false invalid rate
- **On 16 subtle false-valid-trap cases:** GPT-4o Generic missed 4; GPT-4o Specialized missed 0 (one flagged ambiguous); all Claude variants missed 0; GPT-4o-mini missed 0

Best configuration per metric (full 4-model × 5-strategy sweep on the main benchmark):
- Highest accuracy: **GPT-4o / chain-of-thought (85.1%)**
- Lowest false-valid rate: **Sonnet 4.5 / minimal (0.0%)** — ties multiple configs
- Lowest false-invalid rate (least overcautious): **GPT-4o / few-shot (9.8%)**

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

## The Benchmark

The main benchmark is 141 hand-curated cases organized into four modules. Two extension batteries — 15 chronology cases and 12 code cases — are evaluated separately, bringing the total evaluation matrix to **168 cases**. The chronology and code extensions exist to isolate temporal reasoning from finance-domain knowledge (see "Isolating Temporal Reasoning" below).

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Main Benchmark (141 cases)                          │
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

Among the 86 invalid cases, **16 are "false-valid traps"** — workflows with professional methodology language that hide subtle implementation-level bugs. These are the most informative cases for measuring whether a model can see past reassuring language; they get their own section below.

---

## Case Families (13 Source-Backed Families)

A large fraction of the main benchmark consists of hard cases based on real-world finance traps. Each family is tied to authoritative documentation:

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

## Comparison to Rule-Based Baselines

To check that the LLM approach is doing real work, we compared against four non-LLM baselines. All four are far worse than any LLM configuration on what matters most (false-valid rate):

| Baseline | Accuracy | False Invalid | False Valid |
|----------|----------|---------------|-------------|
| Always Invalid | 56.0% | 100.0% | 0.0% |
| Keyword Suspicion | 40.8% | 4.9% | 82.9% |
| Rule-Based | 38.4% | 14.6% | 81.4% |
| Always Valid | 32.8% | 0.0% | 100.0% |

The keyword and rule baselines hallucinate validity 81–83% of the time. Across our full 4-model × 5-strategy sweep on the main benchmark, the worst LLM configuration sits at 5.8% false-valid; the best at 0.0%. The improvement is real — LLMs are not just keyword-matching.

### Repair Quality

Beyond classification, we sampled 30 cases per model and graded the proposed repairs:

| Model | Correct | Partial | Wrong/Vague |
|-------|---------|---------|-------------|
| Claude Sonnet 4.5 | **66.7%** | 30.0% | 3.3% |
| GPT-4o (Specialized) | 40.0% | 36.7% | 23.3% |
| GPT-4o (Generic) | 36.7% | 26.7% | 36.7% |

Claude produces significantly better repairs despite having lower classification accuracy — suggesting its overcaution may reflect deeper engagement with the workflow rather than reflexive flagging.

---

## Selected Failure Examples

Two cases illustrate the dominant overcaution failure mode. Both are situations where the model decided the workflow was broken because something *sounded* suspicious, when in fact the methodology was sound:

**Case `hard_ibm_crsp_adjusted_return`** — A researcher uses the CRSP `ret` field for IBM in November 2021 (the Kyndryl spinoff month). Expected: **valid** (CRSP `ret` already incorporates spinoff adjustments). Models flag it as `identifier_time_travel` — they don't know CRSP handles corporate actions, and the word "spinoff" triggers a violation flag regardless of how it was actually handled.

**Case `cal_ambig_compustat_unknown_lag`** — Compustat data used for a June portfolio with unspecified lag methodology. Expected: **ambiguous** (need more information to determine validity). Models call it `invalid (accounting_availability_leakage)` — they assume the worst case rather than expressing uncertainty.

Both are the same underlying pattern: models would rather be wrong-in-a-cautious-direction than say "valid" or "ambiguous". Raw results for every case are in `outputs/results/*.jsonl`.

---

## Visualizations

The committed figures below are generated by `scripts/reproduction/generate_all_figures.py` from the JSONL result files in `outputs/results/`; `python scripts/reproduce.py` rebuilds the summary metrics and charts.

### Overall accuracy across 4 models × 5 prompting strategies

![All-model accuracy by prompting strategy](../outputs/figures/all_accuracy_by_strategy.png)

Four model variants × five prompting strategies = 20 configurations on the main benchmark. **GPT-4o + chain-of-thought tops the chart at 85.1%** — the only configuration above 84%. GPT-4o is consistently the strongest model regardless of strategy (80–85%). Claude Sonnet 4.5 and 4.6 cluster around 77–82% with relatively little spread across strategies. Claude Haiku 4.5 is the weakest variant (71–78%) and is the one model that is *hurt* by chain-of-thought (drops to 71%).

### Safety versus overcaution trade-off

![Safety versus overcaution by model and strategy](../outputs/figures/all_safety_vs_overcaution.png)

X-axis is false-invalid rate (overcaution); Y-axis is false-valid rate (missed violations); the red dashed line marks the practical 2% false-valid safety threshold. **Almost every configuration sits below the safety threshold** — only GPT-4o/default and GPT-4o/minimal cross it (5.8% FVR, both because they let through 4 of the 16 false-valid traps). The most useful corner is bottom-left (low both): GPT-4o/few-shot, GPT-4o/cot, and the entire Sonnet 4.6 family. The Sonnet 4.6 cluster around 10–15% false-invalid is the cleanest "calibrated" zone on the plot.

### How each prompting strategy moves each metric

![Prompting strategy trends across models](../outputs/figures/all_strategy_trends.png)

Three panels show how moving along the strategy axis (minimal → default → zero-shot → few-shot → CoT) changes accuracy, overcaution, and missed-violation rate per model. **Sonnet 4.6 is the only model that is essentially flat across all three panels** — its calibration is a property of the model, not the prompt. The other models all show meaningful prompt-sensitivity: GPT-4o accuracy climbs with CoT; Haiku 4.5 and Sonnet 4.5 false-invalid rate drops sharply as the prompt gets more elaborate.

### Accuracy by difficulty across all 20 configurations

![Accuracy by difficulty and prompting strategy](../outputs/figures/all_difficulty_heatmap.png)

Heatmap rows are difficulty buckets, columns are the 20 (model × strategy) configurations. **Easy cases are essentially solved** (78–94% across the board). The accuracy gap opens on hard cases — GPT-4o/cot leads at 82%, but Haiku 4.5/cot collapses to 65% (the lowest cell in the chart). Sonnet 4.6 is the most consistent across difficulties: 78%/82–88%/76–80% on easy/medium/hard — no single difficulty pulls it down.

---

## False-Valid Traps: What Makes a Bug Convincing

Sixteen of the 86 invalid cases were designed specifically to *fool* the model — workflows with subtle implementation bugs hidden behind professional methodology language. These cases isolate one question: can a model see past reassuring prose? They are the most diagnostic cases in the benchmark because the failure mode they expose is the dangerous one: approving a broken workflow.

### Trap-case results per configuration

| Configuration | Trap Accuracy | Approved as valid |
|---|---|---|
| Claude Sonnet 4.5 (any strategy) | **100%** | 0 / 16 |
| GPT-4o + zero_shot (specialized) | **93.8%** | 0 / 16 (1 flagged ambiguous) |
| GPT-4o + few_shot | **75.0%** | 0 / 16 (4 flagged ambiguous) |
| GPT-4o + chain_of_thought | **81.2%** | 0 / 16 (3 flagged ambiguous) |
| GPT-4o-mini (any strategy) | **100%** | 0 / 16 |
| GPT-4o + default | 87.5% | 2 / 16 |
| GPT-4o + minimal | 87.5% | 2 / 16 |
| Sonnet 4.6 + default | 68.8% | up to 5 / 16 |

**The dangerous failure (approving as valid) is concentrated entirely in the leanest prompts.** `zero_shot`, `few_shot`, and `chain_of_thought` all bring GPT-4o's approval count to zero; they sometimes mislabel a trap as `ambiguous`, which hurts accuracy but is not an approval. Sonnet 4.5 catches all 16 under every strategy — the strongest trap-detection performance of any model. Notably, Sonnet 4.6 is *worse* than 4.5 on this axis (up to 5 approvals with the `default` prompt) even though 4.6 wins on overcaution overall — the most important practical caveat about using 4.6 for high-stakes audits.

### The four traps the leanest GPT-4o prompt approves

The four false-valid traps that `default` GPT-4o approves illustrate *what kind of language fools a model*:

| Trap case | The bug | Reassuring phrase |
|---|---|---|
| `fvt_lag_from_datadate` | Fixed 6-month lag from fiscal end varies by firm; should use `rdq` / filing date | "conservative lag avoids look-ahead bias" |
| `fvt_dlret_replaces_ret` | Replaces RET with DLRET; should compound `(1+RET)*(1+DLRET) − 1` to keep last-trading-day return | "following best practices" |
| `fvt_adjusted_price_level` | Uses CRSP split-adjusted prices for a `< $5` level filter; should use actual quoted PRC | "ensure historical comparability" |
| `fvt_restated_despite_lag` | 2026 Compustat download contains values restated after the 2005-2015 backtest period | "lag fundamentals conservatively" |

The pattern is the same in every case: a phrase that *sounds* like sound methodology obscures a specific implementation mistake. The phrases that fooled the model are recognizable from finance textbooks and best-practice guides — that is the point.

---

> **Aside on GPT-4o-mini.** We also ran GPT-4o-mini on the main benchmark; it sits at 62–65% accuracy with a **95–98% false-invalid rate** and 0% false-valid rate. It catches every real bug but flags nearly every valid workflow as problematic — safe but useless. The smaller model appears to have learned a conservative heuristic ("financial research is often flawed; flag everything") rather than the nuanced temporal reasoning needed to distinguish real violations from sound methodology.

---

## Isolating Temporal Reasoning from Domain Knowledge

One question the main benchmark cannot answer on its own: when a model fails, *what* is it failing at — temporal reasoning, finance-domain knowledge, or both? Every case in the main benchmark mixes the two. Deciding whether "META on 2018-03-20" is an anachronism requires both knowing that META is a 2022 ticker and reasoning about whether 2018 < 2022.

Two extension batteries separate the axes:

| Battery | Cases | What it isolates |
|---------|-------|------------------|
| **Chronology** | 15 | Pure temporal ordering. Cases name no real tickers or filings — just events with explicit timestamps. Tests "did A happen before B?" without any finance recall. |
| **Code** | 12 | Same PIT-violation taxonomy but expressed as Python snippets instead of prose. Tests whether models can audit code semantics (wrong column choices, off-by-one shifts, comments that contradict the code) rather than just narrative. |

Both batteries are run as standalone evaluations (`scripts/reproduction/run_v6_chronology_only.py` and `scripts/reproduction/run_code_cases_eval.py`) on three configurations: GPT-4o (Generic), GPT-4o (Specialized), and Claude Sonnet 4.5.

### Chronology: overcaution is not a finance problem

![V6-only accuracy by model and prompting strategy](../outputs/figures/all_v6only_accuracy.png)

Every model hits **100%** on invalid (out-of-order) cases — anachronism detection itself is not the limiter. But on cases that are actually valid, the same models drop to **50–67%**. Stripping away CRSP semantics and ticker history did not improve calibration on valid cases. **The overcaution observed on the main benchmark is not specific to financial domain confusion** — it is a more general behavior of preferring "invalid" when any temporal complexity is present.

This matters for the earlier "overcaution comes from deeper understanding" hypothesis (suggested by Claude's high repair quality despite low accuracy): the chronology results weaken that hypothesis. Even cases requiring no domain understanding produce the same valid/invalid asymmetry, so overcaution is at least partly a response to surface-level temporal complexity, not just to deep semantic concerns.

### Code: the prompt paradox flips

When the workflow is Python code instead of prose, the ordering of models inverts in an interesting way:

| Model | Overall | Bug detection (8 invalid) | Trap-valid (4 correct snippets) |
|-------|--------:|--------------------------:|--------------------------------:|
| GPT-4o (Generic) | 67% | 88% | **25%** |
| GPT-4o (Specialized) | 58% | 88% | 0% |
| Claude Sonnet | 67% | **100%** | 0% |

Claude catches every code bug — including subtle ones like `code_shift_off_by_one` that the generic GPT-4o approves — but flags every single piece of correct code as buggy. The specialized GPT-4o prompt is no better than generic on bug detection (88% vs 88%) and is *worse* on correct code (0% vs 25%). On code, the "use specialized for safety" advice still holds for catching bugs but produces zero useful approvals.

### Overcaution across both batteries

Side-by-side, the asymmetry is consistent: for every (model, task) pair, accuracy on invalid is higher than accuracy on valid. This is the same shape we see on the main benchmark, but now on tasks that share *no surface features* with the finance benchmark — just the structural property of having a valid vs invalid label.

### What these extensions contribute

The chronology and code batteries together are 27 cases — small, and not meant as headline benchmarks. Their purpose is methodological: they give us two control conditions for separating capabilities. Future versions of the benchmark could exploit this:

1. **Cross-tabulate by what's required.** A case that requires *both* finance knowledge and temporal reasoning failing is less informative than a case that requires only one — chronology lets us isolate which axis broke.
2. **Test prompt interventions cleanly.** Adding "list your assumptions before deciding" to the prompt can now be tested on pure chronology (does it help reasoning?) and on code separately (does it help code reading?) before being deployed on the full finance benchmark.
3. **Quantify the overcaution prior.** If a model is 50% on chronology-valid cases — flipping a coin on workflows with no actual issue — that sets a floor on how good it can ever be on finance-valid cases without further intervention.

---

## AA-Omniscience: Does the BLD Prompt Transfer to Factual Recall?

The BLD `finance_auditor` system prompt encodes domain knowledge about *temporal reasoning* in finance: identifier validity, information availability, universe construction, and an explicit "do not assume validity" stance. A natural question is whether that domain priming also helps with *factual recall* of finance regulatory knowledge — exact ASC paragraph citations, PCAOB rule numbers, SEC filing requirements. We tested transferability by running the same prompt on a separate benchmark designed to measure factual recall and hallucination.

[AA-Omniscience](https://artificialanalysis.ai/) is a 6,000-question knowledge benchmark from Artificial Analysis. It scores models using the **Omniscience Index** (OI), which rewards correct answers and penalizes confident wrong ones while treating abstention as neutral:

$$\text{OI} = 100 \cdot \frac{c - i}{c + p + i + a}$$

where $c$, $p$, $i$, $a$ are counts of CORRECT, PARTIALLY_CORRECT, INCORRECT, and NOT_ATTEMPTED responses. The companion **hallucination rate** measures the fraction of non-correct responses that were outright wrong (rather than partial or abstained). We tested 100 Finance-domain questions on three configurations: GPT-4o with a plain "answer concisely" instruction, GPT-4o with the full BLD `finance_auditor` prompt, and Claude Sonnet 4.5 with the same BLD prompt. The full methodology is in [`writeup/AAOmniscience_results.md`](AAOmniscience_results.md).

### Overall Results

| Configuration | OI Index | Accuracy | Hallucination Rate | Correct | Partial | Incorrect | Abstained |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-4o Generic | **−30.0** | 33.0% | 94.0% | 33 | 4 | 63 | 0 |
| GPT-4o + BLD Specialized | **−31.0** | 31.0% | 89.9% | 31 | 5 | 62 | 2 |
| Claude Sonnet 4.5 + BLD Specialized | **−12.0** | 35.0% | 72.3% | 35 | 6 | 47 | 12 |
| GPT-4o published (Business) | −6.0 | — | 38.0% | — | — | — | — |
| Claude Sonnet published (Business) | +1.0 | — | 29.0% | — | — | — | — |

The bottom two rows are Artificial Analysis's own published OI scores for the same models on their Business-domain leaderboard. Our absolute scores are lower because we used GPT-4o as the grading judge (Artificial Analysis uses Gemini Flash); the *relative ordering* across our three configurations is internally valid since all used identical methodology.

### By Topic

| Topic | Questions | GPT-4o Generic | GPT-4o Specialized | Claude Sonnet |
|---|---:|---:|---:|---:|
| Accounting | 20 | −20.0 | −10.0 | −20.0 |
| Business & Management | 10 | −40.0 | −40.0 | **+30.0** |
| Corporate & Markets | 20 | −30.0 | −35.0 | −5.0 |
| Economics | 20 | −25.0 | −30.0 | +5.0 |
| Financial Institutions | 15 | −13.3 | −13.3 | −20.0 |
| Investments | 15 | −60.0 | −66.7 | −53.3 |

The Investments topic is the hardest across every configuration. These questions involve exact index methodology rules, specific thresholds, and precise institutional definitions — at the outer edge of what any of these models has reliably memorized.

### Three Findings

**1. Domain priming does not transfer to factual recall.** GPT-4o Generic (−30.0 OI) and GPT-4o Specialized (−31.0 OI) are statistically indistinguishable. Adding the four BLD principles — identifier validity, information availability, universe construction, do-not-assume-validity — does not help the model recall ASC paragraph numbers or PCAOB rule codes. This supports the central project framing: *temporal reasoning and factual recall are orthogonal capabilities*.

**2. The two benchmarks rank models differently.** GPT-4o leads BLD on every prompting strategy (highest accuracy: 85.1% with chain-of-thought). Claude Sonnet 4.5 leads AA-Omniscience (−12 OI vs −30/−31 for GPT-4o). Strong temporal reasoning does not imply strong factual recall, and vice versa. A model that excels at detecting "META could not have been used in 2018" is not necessarily better at recalling that "ASC 340-40-25-6 is the correct citation."

**3. Claude's advantage is calibration, not knowledge.** Claude's accuracy (35%) is only marginally higher than GPT-4o's (31–33%) — but Claude abstained from 12 questions while GPT-4o abstained from 0–2. Because OI treats abstention as neutral (rather than penalizing it like an incorrect answer), 12 abstentions avoid 12 potential −1 deductions. The 72.3% hallucination rate vs GPT-4o's 89.9–94% confirms the same pattern: when Claude attempts an answer it is wrong slightly less often, and it knows when not to attempt. This *willingness to abstain on uncertain regulatory detail* is precisely the calibration property AA-Omniscience was built to measure.

### What This Says About the BLD Project

The cross-benchmark experiment is a falsification test for the implicit claim that "domain priming makes models better at finance." It shows that the BLD prompt's effect is narrow and specific: it improves *temporal-validity auditing* (where it brings GPT-4o's false-valid rate to 0% on the main benchmark), but it does not generalize to *factual recall* on the same domain. This is a useful negative result. It bounds the practical scope of the BLD prompt — use it for what it was designed for, not as a generic "make the model better at finance" intervention.

---

## Limitations

1. **Five model variants tested** - GPT-4o, GPT-4o-mini, Claude Sonnet 4.5, Claude Sonnet 4.6, Claude Haiku 4.5. Reasoning-tier models (e.g. o1, o3, Claude Opus) are not in scope; adding them would test whether the overcaution pattern persists at higher capability.
2. **Five prompting strategies tested** - `minimal`, `default`, `zero_shot` (specialized finance-auditor), `few_shot` (3 examples), `chain_of_thought`. More strategies (self-critique, multi-pass, tool-use) could yield further gains.
3. **Ground truth requires domain expertise** - Some trap valid cases have debatable answers (see protocol above)
4. **Benchmark size** - 141 main cases plus 27 extension cases (chronology + code); covers main patterns but not exhaustively
5. **Extension batteries are small** - 15 chronology and 12 code cases are enough to expose the overcaution pattern but not to make fine-grained claims about specific case types
6. **No fine-tuning** - Using base model capabilities only
7. **English only** - All prompts and cases in English

---

## Reproducibility

### Quick Start

For the simplest no-API reproduction of committed outputs, run:

```bash
python scripts/reproduce.py
```

For a live API rerun, run `python scripts/reproduce.py --full-api` or execute the individual commands below.

```bash
# Clone and setup
git clone https://github.com/mohitapte4/Backtest-Lie-Detector
cd Backtest-Lie-Detector
pip install -e ".[all]"

# Generate the benchmark JSONLs (v5 is the main one)
python -m backtest_lie_detector.benchmark.build_cases v5

# Run the main V5 evaluation (requires V4 results to merge — see run_v4_comparison.py / run_claude_evaluation.py)
python scripts/reproduction/run_v4_comparison.py        # GPT-4o specialized + generic on V4
python scripts/reproduction/run_claude_evaluation.py    # Claude Sonnet on V4
python scripts/reproduction/run_v5_newcases_only.py     # 16 new V5 trap cases x 3 configs
python scripts/reproduction/compute_v5_metrics.py       # merges V4 + V5 into outputs/results/model_outputs_v5_*.jsonl
python scripts/reproduction/generate_v5_figures.py      # produces v5_*.png in outputs/figures/

# Run the V6 extension batteries
python scripts/reproduction/run_v6_chronology_only.py   # 15 chronology cases x 3 configs
python scripts/reproduction/run_code_cases_eval.py      # 12 code cases x 3 configs
python scripts/reproduction/generate_v6_figures.py      # produces v6_*.png in outputs/figures/
```

### Benchmark Versions
- `benchmark_v1.jsonl`: Original 42 cases
- `benchmark_v2.jsonl`: 69 cases (+adversarial, +WRDS)
- `benchmark_v3.jsonl`: 105 cases (+hard source-backed)
- `benchmark_v4.jsonl`: 125 cases (+calibration-focused)
- `benchmark_v5.jsonl`: **141 cases** (+16 false valid traps) — main benchmark
- `benchmark_v6.jsonl`: V5 + 15 chronology cases (the 12 code cases run as a separate battery)

### Output Files
- `outputs/results/ALL_EVALUATION_RESULTS.txt` — aggregate metrics summary.
- `outputs/results/*.jsonl` — committed model outputs for the prompting, Claude, V6-only, and AA-Omniscience comparisons.
- `outputs/figures/all_*.png` — committed figures shown in this writeup and generated by `scripts/reproduction/generate_all_figures.py`.

---

## Conclusion

LLMs are reliable as point-in-time auditors *for what the auditor task actually is*: catching real bugs. The dangerous failure mode — approving a broken workflow — happens between 0% and 5.8% of the time across the full 4-model × 5-strategy sweep, versus 81–83% for rule-based and keyword baselines. There is real understanding behind these numbers, not pattern matching.

The dominant failure mode is the *annoying* one: overcaution. Models flag 17–46% of valid workflows as broken depending on configuration. Claude Sonnet 4.6 is the most balanced calibrator (≤15% false-invalid across every strategy); GPT-4o + chain-of-thought has the highest accuracy (85.1%); GPT-4o + few-shot has the lowest overcaution (9.8% false-invalid); Sonnet 4.5 catches 100% of the subtle traps under every prompting strategy. Accuracy and repair quality are inversely correlated — Claude has the lowest overall accuracy but the best repair suggestions, suggesting its overcaution reflects deeper engagement rather than reflex flagging.

The two methodology extensions (chronology + code; AA-Omniscience) tell a single negative result: **the overcaution and the prompt-priming effects do not generalize**. Overcaution persists when the cases are stripped of finance content (chronology shows the same valid/invalid asymmetry); the domain-priming benefit from the `finance_auditor` prompt does not transfer to factual recall (AA-Omniscience OI is unchanged between Generic and Specialized GPT-4o). Both results bound the practical scope of the BLD approach — it is a *temporal-reasoning auditor*, not a *finance-domain enhancer*.

### Practical Recommendations

| Priority | Recommendation |
|----------|---------------|
| **Best Accuracy** | GPT-4o + chain-of-thought (85.1%) |
| **Maximum Safety** | Claude Sonnet 4.5 + any strategy (catches all 16 traps) |
| **Least Overcautious** | GPT-4o + few-shot (9.8% false-invalid) |
| **Most Balanced Calibration** | Claude Sonnet 4.6 (≤15% false-invalid across every strategy) |
| **Best Repairs** | Claude Sonnet 4.5 (67% correct repairs on sampled cases) |
| **Subtle / complex methodology** | Specialized (`zero_shot`) or `few_shot` prompt |
| **Simple / obvious cases** | `minimal` or `default` prompt |

---

## AI Usage Statement

This project was developed with AI assistance:

- **Code generation**: Claude assisted with implementation
- **Documentation**: AI helped draft docstrings and writeup
- **Benchmark cases**: Templates AI-generated, all human-reviewed

**Human contributions:**
- Benchmark design and methodology, including the chronology + code methodology contribution
- Ground truth validation (all 141 main-benchmark cases + 27 extension cases)
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
