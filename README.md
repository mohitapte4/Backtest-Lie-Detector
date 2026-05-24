# Backtest Lie Detector

**Benchmarking LLMs as point-in-time auditors for financial research.**

This repository is the class-project codebase for evaluating whether large
language models can spot temporal validity errors in backtests, event studies,
and quantitative finance workflows. The project focuses on mistakes such as
look-ahead bias, ticker time travel, filing-clock leakage, survivorship bias,
and incorrect use of delisting or corporate-action data.

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
| `writeup/` | Human-facing project writeups and supporting analysis notes. |
| `docs/` | GitHub Pages build assets. |
| `tests/` | Unit tests for schemas, scoring, and point-in-time validators. |

## Benchmark version history

Do not delete these files; they document the project evolution.

| Version | Cases | File | Main addition |
| --- | ---: | --- | --- |
| V1 | 42 | `data/benchmark/benchmark_v1.jsonl` | Original seed benchmark |
| V2 | 69 | `data/benchmark/benchmark_v2.jsonl` | Adversarial + WRDS-backed cases |
| V3 | 105 | `data/benchmark/benchmark_v3.jsonl` | Hard source-backed cases |
| V4 | 125 | `data/benchmark/benchmark_v4.jsonl` | Calibration, valid traps, ambiguous cases |
| V5 | 141 | `data/benchmark/benchmark_v5.jsonl` | False-valid traps |
| V6 | 156 | `data/benchmark/benchmark_v6.jsonl` | V5 plus chronology/temporal-ordering cases |

The V6 code-auditing battery is intentionally separate from the JSONL benchmark:
`src/backtest_lie_detector/benchmark/code_cases.py` defines 12 code-snippet
cases evaluated by `scripts/reproduction/run_code_cases_eval.py`.

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

### Full live API rerun

This reruns the main live model evaluations before rebuilding metrics and
figures. It requires valid OpenAI and Anthropic keys and overwrites matching
files under `outputs/results/`.

```bash
python scripts/reproduce.py --full-api
```

The full API path runs:

```bash
python scripts/reproduction/run_v4_comparison.py
python scripts/reproduction/run_claude_evaluation.py
python scripts/reproduction/run_v5_newcases_only.py
python scripts/reproduction/compute_v5_metrics.py
python scripts/reproduction/generate_v5_figures.py
python scripts/reproduction/run_v6_chronology_only.py
python scripts/reproduction/run_code_cases_eval.py
python scripts/reproduction/generate_v6_figures.py
python scripts/reproduction/compute_all_metrics.py
python scripts/reproduction/generate_all_figures.py
```

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

For a dry run without API calls:

```bash
python -m backtest_lie_detector.evals.run_eval \
  --benchmark data/benchmark/benchmark_v5_sample.jsonl \
  --output outputs/results/mock_sample.jsonl \
  --mock
```

## Latest merged analyses

- **Claude and prompting analysis:** `scripts/reproduction/run_claude_prompting_comparison.py`,
  `scripts/reproduction/run_prompting_comparison.py`,
  `scripts/reproduction/compute_all_metrics.py`, and
  `writeup/prompting_and_claude_evaluation.md`.
- **AA-Omniscience comparison:** `scripts/reproduction/run_aa_omniscience.py`,
  `data/aa_omniscience/AA_Omniscience_finance.csv`, and
  `writeup/AAOmniscience_results.md`.
- **Rule baselines:** `scripts/reproduction/run_baseline_evaluation.py`.

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
  author={UChicago Generative AI for Finance Team},
  year={2026},
  url={https://github.com/mohitapte4/Backtest-Lie-Detector}
}
```

## License

MIT License. See `LICENSE`.
