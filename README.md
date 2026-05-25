# Backtest Lie Detector

**Benchmarking LLMs as point-in-time auditors for financial research.**

This repository is the class-project codebase for evaluating whether large
language models can spot temporal validity errors in backtests, event studies,
and quantitative finance workflows. The project focuses on mistakes such as
look-ahead bias, ticker time travel, filing-clock leakage, survivorship bias,
and incorrect use of delisting or corporate-action data.

## Submission files

Mapping of each submission requirement to where it lives in this repo:

| Requirement | Location |
| --- | --- |
| Primary notebook / report file with the core work | [`notebooks/00_main_report.ipynb`](notebooks/00_main_report.ipynb) — full end-to-end pipeline with embedded figures and a live-demo cell. |
| Audience-facing writeup (scannable without setup) | Published at [backtest-lie-detector.pagehaven.io](https://backtest-lie-detector.pagehaven.io/) (hosted on PageHaven). Source files: [`docs/index.html`](docs/index.html) and markdown at [`writeup/index.md`](writeup/index.md). |
| README with reproduction instructions | This file — see [Reproduce the submitted outputs](#reproduce-the-submitted-outputs). |
| Package notes | [`requirements.txt`](requirements.txt) and [`pyproject.toml`](pyproject.toml) (`pip install -e ".[all]"`). |
| Supporting code, prompts, schemas, scripts | Installable package at [`src/backtest_lie_detector/`](src/backtest_lie_detector/) (schemas, prompts, model clients, scoring, validators, benchmark generators). Reproduction scripts at [`scripts/reproduction/`](scripts/reproduction/). |
| AI usage statement | [`writeup/index.md` § AI Usage Statement](writeup/index.md#ai-usage-statement). |

## What is in the repo?

| Area | Purpose |
| --- | --- |
| `src/backtest_lie_detector/` | Installable Python package: schemas, benchmark generation, model clients, prompts, scoring, validators, baseline rules, and app code. |
| `data/benchmark/` | Preserved benchmark history from V1 through V6, plus small sample files. |
| `data/aa_omniscience/` | Finance subset used for the AA-Omniscience comparison. |
| `scripts/reproduction/` | Current scripts for reproducing the reported evaluations, metrics, and figures. |
| `scripts/legacy/` | Older V1-V4 analysis/figure scripts kept for version history, not the main reproduction path. |
| `outputs/results/` | Committed latest result files and aggregate summaries. Live reruns also write here. |
| `outputs/figures/` | Committed latest generated figures. |
| `writeup/` | Human-facing project writeups. Start with [`writeup/index.md`](writeup/index.md). |
| `docs/` | GitHub Pages build assets (hand-styled HTML mirror of the writeup). |
| `tests/` | Unit tests for schemas, scoring, and point-in-time validators. |

The canonical numerical summary across every model / strategy / battery is committed at [`outputs/results/ALL_EVALUATION_RESULTS.txt`](outputs/results/ALL_EVALUATION_RESULTS.txt) and is rebuilt by `scripts/reproduction/compute_all_metrics.py`.

## Benchmark version history

Do not delete these files; they document the project evolution.

| Version | Cases | File | Main addition |
| --- | ---: | --- | --- |
| V1 | 42 | `data/benchmark/benchmark_v1.jsonl` | Original seed benchmark |
| V2 | 69 | `data/benchmark/benchmark_v2.jsonl` | Adversarial + WRDS-backed cases |
| V3 | 105 | `data/benchmark/benchmark_v3.jsonl` | Hard source-backed cases |
| V4 | 125 | `data/benchmark/benchmark_v4.jsonl` | Calibration, valid traps, ambiguous cases |
| V5 | 141 | `data/benchmark/benchmark_v5.jsonl` | False-valid traps |
| V6 | 156 | `data/benchmark/benchmark_v6.jsonl` | V5 (141) plus 15 chronology/temporal-ordering cases |

The V6 code-auditing battery is intentionally separate from the JSONL benchmark:
[`src/backtest_lie_detector/benchmark/code_cases.py`](src/backtest_lie_detector/benchmark/code_cases.py)
defines 12 code-snippet cases evaluated by
[`scripts/reproduction/run_code_cases_eval.py`](scripts/reproduction/run_code_cases_eval.py).
Counting code cases, the V6 evaluation matrix covers 168 distinct cases
(141 V5 + 15 chronology + 12 code).

## Quick start

```bash
git clone https://github.com/mohitapte4/Backtest-Lie-Detector.git
cd Backtest-Lie-Detector

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

For live model evaluations, copy `.env.example` to `.env` and add:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
API_RATE_LIMIT_DELAY=1.0
```

## Reproduce the submitted outputs

### Fast no-API check

This uses the committed latest result files, rebuilds aggregate metrics and
figures, runs unit tests, and smoke-tests the AA-Omniscience loader.

```bash
python scripts/reproduce.py
```

If you only want to rebuild metrics and figures:

```bash
python scripts/reproduce.py --skip-tests
```

### Full live API rerun — core V4/V5/V6 tracks

`python scripts/reproduce.py --full-api` reruns the *core* live model
evaluations before rebuilding metrics and figures. It covers the original
three-config matrix (GPT-4o generic + specialized, Claude Sonnet 4.5) on V4
and V5, plus the V6 chronology and code batteries. It requires valid OpenAI
and Anthropic keys and overwrites matching files under `outputs/results/`.

```bash
python scripts/reproduce.py --full-api
```

The `--full-api` path runs these scripts in order:

```bash
python scripts/reproduction/run_v4_comparison.py
python scripts/reproduction/run_claude_evaluation.py
python scripts/reproduction/run_v5_newcases_only.py
python scripts/reproduction/compute_v5_metrics.py
python scripts/reproduction/generate_v5_figures.py
python scripts/reproduction/run_v6_chronology_only.py
python scripts/reproduction/run_code_cases_eval.py
python scripts/reproduction/generate_v6_figures.py
```

It then runs `compute_all_metrics.py` and `generate_all_figures.py` as part
of the no-API pass that follows.

### Extended evaluations (not covered by `--full-api`)

The 4-model × 5-strategy expansion and the AA-Omniscience comparison are run
through their own scripts. They are *not* invoked by `scripts/reproduce.py`
and must be triggered manually. Each script writes its own JSONL files into
`outputs/results/`, where `compute_all_metrics.py` will pick them up.

**Heads up on cost:** the Claude prompting-comparison script alone runs ~2,400
API calls (~$15, ~45 min); the four GPT-4o scripts together run ~800 calls
(~$8); AA-Omniscience adds ~600 calls (~$3). Running the full extended set
costs roughly $25-30 of API credit and ~75 minutes wall-clock at the default
1-second rate limit. Per-script estimates are in
[`writeup/prompting_and_claude_evaluation.md`](writeup/prompting_and_claude_evaluation.md).
The rule baselines are local-only and free.

```bash
# GPT-4o across 5 prompting strategies (minimal, default, zero_shot, few_shot, cot)
python scripts/reproduction/run_gpt4o_base_prompts.py        # minimal + default on V5
python scripts/reproduction/run_prompting_comparison.py      # zero_shot + few_shot + cot on V5
python scripts/reproduction/run_gpt4o_v6only.py              # all 5 strategies on V6-only

# Claude Sonnet 4.5, Sonnet 4.6, Haiku 4.5 across all 5 strategies on V5 + V6-only
python scripts/reproduction/run_claude_prompting_comparison.py

# GPT-4o-mini baseline on V5
python scripts/reproduction/run_gpt4o_mini_evaluation.py

# AA-Omniscience finance-recall comparison (100 questions x 3 configs)
python scripts/reproduction/run_aa_omniscience.py

# Rule-based and naive baselines
python scripts/reproduction/run_baseline_evaluation.py

# Re-aggregate everything
python scripts/reproduction/compute_all_metrics.py
python scripts/reproduction/generate_all_figures.py
```

See [`writeup/prompting_and_claude_evaluation.md`](writeup/prompting_and_claude_evaluation.md)
for the rationale, expected API cost, and runtime estimates of these scripts.

### What success looks like

After a successful reproduction:

- `outputs/results/ALL_EVALUATION_RESULTS.txt` is regenerated and should match
  the committed copy (small floating-point differences are normal; absolute
  metrics can shift 1-3 percentage points across runs because the API is not
  fully deterministic even at `temperature=0`).
- `outputs/figures/all_*.png` and `outputs/figures/v5_*.png` /
  `outputs/figures/v6_*.png` are regenerated and match the committed copies
  pixel-near (figure layouts are deterministic; only the bar heights move
  with the underlying numbers).
- `pytest` reports all tests passing.
- The AA-Omniscience smoke test prints `loaded 100 finance questions`.

A `git status` / `git diff outputs/` after `python scripts/reproduce.py` is a
quick way to sanity-check that the committed outputs reflect the current code.

## Rebuild benchmark JSONL files

The benchmark generators are deterministic and can regenerate any preserved
version:

```bash
python -m backtest_lie_detector.benchmark.build_cases v1
python -m backtest_lie_detector.benchmark.build_cases v2
python -m backtest_lie_detector.benchmark.build_cases v3
python -m backtest_lie_detector.benchmark.build_cases v4
python -m backtest_lie_detector.benchmark.build_cases v5
python -m backtest_lie_detector.benchmark.build_cases v6
```

## Run a single evaluation manually

```bash
python -m backtest_lie_detector.evals.run_eval \
  --benchmark data/benchmark/benchmark_v5.jsonl \
  --output outputs/results/example_v5_gpt4o.jsonl \
  --model gpt-4o \
  --provider openai \
  --config finance_auditor
```

The `--config` flag accepts `minimal`, `default`, or `finance_auditor` only.
Chain-of-thought and few-shot strategies are not wired into this CLI; use
[`scripts/reproduction/run_prompting_comparison.py`](scripts/reproduction/run_prompting_comparison.py)
for those.

For a dry run without API calls:

```bash
python -m backtest_lie_detector.evals.run_eval \
  --benchmark data/benchmark/benchmark_v5_sample.jsonl \
  --output outputs/results/mock_sample.jsonl \
  --mock
```

## Writeups

- [`writeup/index.md`](writeup/index.md) — main project report: motivation,
  benchmark design, V1-V6 evolution, results, prompt-engineering findings,
  and the V6 chronology + code methodology contribution.
- [`writeup/prompting_and_claude_evaluation.md`](writeup/prompting_and_claude_evaluation.md)
  — the 4-model × 5-strategy expansion: instructions for reproducing the
  Sonnet 4.5 / 4.6, Haiku 4.5, and GPT-4o prompting-comparison runs.
- [`writeup/AAOmniscience_results.md`](writeup/AAOmniscience_results.md) —
  AA-Omniscience finance-recall comparison: tests whether the BLD
  `finance_auditor` prompt transfers to factual recall.

## Tests and lint

```bash
pytest
python -m ruff check src tests scripts/reproduction scripts/legacy
```

The project currently uses `pyproject.toml` as the canonical dependency and
tooling configuration. `requirements.txt` is retained only for environments
that do not support editable installs with extras.

## Citation

```bibtex
@misc{backtest-lie-detector-2026,
  title={Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors},
  author={Mohit Apte and Anya Zakharov and Lucie Martin and Myra Singh},
  year={2026},
  note={UChicago FINM 33200 (Generative and Agentic AI for Finance), Spring 2026},
  url={https://github.com/mohitapte4/Backtest-Lie-Detector}
}
```

## License

MIT License. See `LICENSE`.
