# AA-Omniscience Finance Comparison: BLD Finance Auditor Prompt on Factual Recall

*UChicago Generative AI for Finance, Spring 2026*

---

## What is AA-Omniscience?

AA-Omniscience is a knowledge and hallucination benchmark developed by Artificial Analysis that rewards accuracy, punishes bad guesses, and provides a comprehensive view of which models produce factually reliable outputs across different domains. The benchmark contains 6,000 questions across 6 major domains, derived from authoritative academic and industry sources and generated automatically using an LLM-based question generation agent to ensure unambiguity, scalability, and factual precision.

The motivation behind the benchmark is that existing language model evaluations primarily measure general capabilities, yet reliable use of these models across a range of domains demands factual accuracy and recognition of knowledge gaps. AA-Omniscience is designed to measure both factual recall and **knowledge calibration** — not just whether a model gets the right answer, but whether it knows when it does not know. Among evaluated models, Claude 4.1 Opus attains the highest score (4.8), making it one of only three models to score above zero. These results reveal persistent factuality and calibration weaknesses across frontier models.

Artificial Analysis publishes scores for models on their overall performance across many dimensions. We specifically focused on the AA-Omniscience hallucination benchmark, which is one component of their evaluation suite. The website allows you to filter results by both model and domain, so we filtered to **GPT-4o (Nov)** and **Claude 4 Sonnet** — the two models we had run in BLD — and looked at their Business domain scores for comparison with our Finance domain results (see the Finance vs. Business note below).

---

## About the Dataset

AA-Omniscience covers 42 economically relevant topics within six domains. We obtained the dataset from Hugging Face.

## What We Tested

We ran the BLD finance auditor system prompt on 100 finance questions from AA-Omniscience, testing whether the BLD domain priming — which encodes knowledge about ticker changes, filing timing, and survivorship bias — helps or hurts factual financial recall relative to a generic prompt. The comparison is detailed in the How We Ran It section below.

---

## Finance vs. Business Domain

The public Hugging Face version of the dataset labels our question set as **Finance**, while the AA-Omniscience website leaderboard labels the same category as **Business**. Across all 42 topics in the dataset, Finance/Business was the only category with a differing name between the two sources. We assumed these refer to the same question set and used the published Business domain scores for comparison.

### Question Types

The 100 Finance questions span six topics and are highly specific — they require precise memorization of regulatory identifiers, exact paragraph citations, and specific rule numbers:

| Topic | Questions | Example Question Type |
|---|---|---|
| Accounting | 20 | Exact ASC paragraph citations (e.g., "ASC 606-10-25-15"), GAAP effective dates |
| Corporate & Markets | 20 | Specific regulatory provisions, SEC filing requirements |
| Economics | 20 | Precise definitions, exact institutional rules |
| Financial Institutions | 15 | PCAOB rule numbers, banking regulation specifics |
| Investments | 15 | Exact index methodology rules, specific thresholds |
| Business & Management | 10 | Specific standards and codes |

These are not conceptual questions. A correct answer to "Which paragraph identifier in ASC 340-40 states that costs to fulfill a contract must be expensed?" is `ASC 340-40-25-6` — being off by one paragraph number scores the same as a completely wrong answer.

---

## How AA-Omniscience Scores

### The Omniscience Index (OI)

AA-Omniscience uses a single scalar metric designed to penalize hallucination while rewarding appropriate abstention:

$$OI = 100 \cdot \frac{c - i}{c + p + i + a}$$

Where:
- **c** = number of correct answers
- **p** = number of partially correct answers
- **i** = number of incorrect answers
- **a** = number of abstentions (NOT_ATTEMPTED)

The index ranges from -100 to 100. A score of 0 means the model answered correctly as often as it answered incorrectly. Negative scores mean more incorrect than correct answers. Crucially, **abstaining is neutral** — it neither adds nor subtracts from the score — making abstention strictly better than guessing incorrectly.

### Hallucination Rate

AA-Omniscience also reports a hallucination rate, defined as the proportion of non-correct responses that were outright incorrect:

$$\text{Hallucination Rate} = \frac{i}{p + i + a}$$

This measures how often a model generates a wrong answer when it does not know the correct one, instead of giving a partial answer or refusing. A lower hallucination rate means the model is better calibrated — it abstains rather than fabricating a confident wrong answer.

### Grading Methodology

Each response is graded as one of four categories:
- **CORRECT**: Response contains the correct answer (exact or semantically equivalent)
- **PARTIALLY_CORRECT**: Response is on the right track but missing detail or precision
- **INCORRECT**: Response gives a wrong answer
- **NOT_ATTEMPTED**: Model refused, expressed uncertainty, or did not answer

The published AA-Omniscience leaderboard uses **Gemini Flash (Reasoning)** as the grading model. In our evaluation, we used **GPT-4o as the judge** since we already had OpenAI API access and it is a reasonable substitute. This methodological difference is the primary explanation for the gap between our absolute scores and published scores (discussed below).

---

## How We Ran It

### Model Configurations

We tested three configurations mirroring the BLD evaluation setup exactly:

| Config | Model | System Prompt |
|---|---|---|
| **GPT-4o Generic** | GPT-4o (Nov 2024) | Plain "answer concisely" instruction, no domain knowledge |
| **GPT-4o Specialized** | GPT-4o (Nov 2024) | Full BLD finance_auditor prompt + "answer concisely" |
| **Claude Sonnet Specialized** | Claude Sonnet 4.5 | Full BLD finance_auditor prompt + "answer concisely" |

GPT-4o receives both a generic and specialized configuration so we can isolate the effect of the BLD domain priming. Claude Sonnet receives only the specialized configuration, matching how it was run in BLD.

### Prompt Adaptation

The BLD `finance_auditor` system prompt contains a `{response_format}` placeholder that normally receives the JSON audit schema (validity, violations, explanation, repair, confidence). For AA-Omniscience, we replaced this placeholder with a plain factual instruction:

> *"Answer the following question with only the exact answer. Be as concise and precise as possible. Do not explain your reasoning."*

This preserves all four BLD domain knowledge principles (identifier validity, information availability, universe construction, do not assume validity) while asking for a plain-text answer rather than a structured JSON object.

The generic prompt uses no domain knowledge at all — just the same concise answer instruction with a minimal system prompt.

---

## Results

### OI Index Comparison

| Model | Config | Our OI Index | Published OI Index (Business) |
|---|---|---|---|
| GPT-4o (Nov) | Generic | **-30.0** | -6 |
| GPT-4o (Nov) | Specialized (BLD prompt) | **-31.0** | -6 |
| Claude Sonnet | Specialized (BLD prompt) | **-12.0** | +1 |

### Hallucination Rate Comparison

| Model | Config | Our Hallucination Rate | Published Hallucination Rate (Business) |
|---|---|---|---|
| GPT-4o (Nov) | Generic | **94.0%** | 38% |
| GPT-4o (Nov) | Specialized (BLD prompt) | **89.9%** | 38% |
| Claude Sonnet | Specialized (BLD prompt) | **72.3%** | 29% |

### Full Breakdown

| Config | OI Index | Accuracy | Halluc. Rate | Correct | Partial | Incorrect | Abstained |
|---|---|---|---|---|---|---|---|
| GPT-4o Generic | -30.0 | 33.0% | 94.0% | 33 | 4 | 63 | 0 |
| GPT-4o Specialized | -31.0 | 31.0% | 89.9% | 31 | 5 | 62 | 2 |
| Claude Sonnet Specialized | -12.0 | 35.0% | 72.3% | 35 | 6 | 47 | 12 |

### By Topic (OI Index)

| Topic | GPT-4o Generic | GPT-4o Specialized | Claude Sonnet |
|---|---|---|---|
| Accounting (20q) | -20.0 | -10.0 | -20.0 |
| Business & Management (10q) | -40.0 | -40.0 | **+30.0** |
| Corporate & Markets (20q) | -30.0 | -35.0 | -5.0 |
| Economics (20q) | -25.0 | -30.0 | +5.0 |
| Financial Institutions (15q) | -13.3 | -13.3 | -20.0 |
| Investments (15q) | -60.0 | -66.7 | -53.3 |

---

## Why the Results Look the Way They Do

### 1. Domain priming makes no difference for factual recall

GPT-4o generic (-30.0) and GPT-4o specialized (-31.0) are essentially identical. Adding four detailed principles about ticker changes, filing timing, and survivorship bias does not help the model recall specific ASC paragraph numbers or PCAOB rule codes. This supports the hypothesis that **temporal reasoning and factual recall are orthogonal capabilities** — the knowledge encoded in the BLD prompt is about how to reason about time, not about memorizing regulatory identifiers.

### 2. The benchmarks rank models differently

GPT-4o leads BLD (83.0% vs 78.0% for Claude Sonnet), but Claude Sonnet leads AA-Omniscience (-12 vs -30 for GPT-4o). This reversal confirms that the two benchmarks measure genuinely different things. Strong temporal reasoning does not imply strong factual recall, and vice versa.

### 3. Claude's abstention strategy explains its better OI score

Claude Sonnet abstained from 12 questions — GPT-4o abstained from 0 to 2. This is the primary driver of Claude's better OI index. Because the OI formula treats abstentions as neutral (score of 0) rather than penalizing them like incorrect answers (score of -1), a model that says "I don't know" 12 times avoids 12 potential -1 deductions. Claude's hallucination rate (72.3%) is also meaningfully lower than GPT-4o's (90–94%), meaning that when Claude does attempt an answer it is wrong slightly less often. This behavior — being willing to abstain on hard regulatory detail questions — is better calibrated for this type of benchmark.

### 4. Investments questions are hardest for all models

Investments is the worst-performing topic across all three configs (OI: -53 to -67). These questions involve exact index methodology rules, specific thresholds, and precise institutional definitions that appear to be at the outer edge of what any model has reliably memorized.

### 5. The gap between our scores and published scores is methodological

Our absolute scores are lower than published (ours: -30 vs published: -6 for GPT-4o; ours: -12 vs published: +1 for Claude Sonnet). We attribute this primarily to **judge model differences**: the published evaluation uses Gemini Flash (Reasoning) as the grading model, while we used GPT-4o. Different judge models may apply different thresholds for what counts as CORRECT vs PARTIALLY_CORRECT, particularly for answers that are close but not exact. The **relative rankings** between our configurations are internally valid since all three used identical methodology.

### 6. The high hallucination rates reflect the question design

With hallucination rates of 72–94%, these models are wrong most of the time when they attempt a non-trivial answer. This is by design — AA-Omniscience Finance questions test highly specific regulatory knowledge (exact paragraph numbers, exact rule codes, exact effective dates) where models have a strong tendency to produce confident but slightly-off answers. This is precisely the hallucination phenomenon the benchmark was built to measure.

---

## Summary

| | BLD (Temporal Reasoning) | AA-Omniscience (Factual Recall) |
|---|---|---|
| **GPT-4o leads** | Yes (83% vs 78%) | No (-30 vs -12) |
| **Domain prompt helps** | Yes (catches 100% of false-valid traps) | No (Generic -30 ≈ Specialized -31) |
| **Main failure mode** | False invalids (overcaution) | Hallucinated regulatory identifiers |
| **Claude advantage** | Lower false-valid rate | Better abstention behavior |

The two benchmarks test different capabilities. A model that excels at detecting temporal anachronisms in financial workflows is not necessarily better at recalling exact regulatory citations — and the BLD finance_auditor prompt, which encodes temporal reasoning principles, provides no measurable lift on factual recall tasks.
