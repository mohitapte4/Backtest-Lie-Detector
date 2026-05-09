# Backtest Lie Detector

**Benchmarking LLMs as Point-in-Time Auditors for Financial Research**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project provides a benchmark and evaluation framework to test whether Large Language Models (LLMs) can reliably detect point-in-time validity errors in financial research workflows. These errors—including look-ahead bias, ticker time-travel, filing timing mistakes, and survivorship bias—can silently invalidate backtests, event studies, and quantitative research.

### Key Finding (V4 Benchmark)

> LLMs are excellent at catching obvious violations (**0% false valid rate**) but are **overly cautious** (**29% false invalid rate**) and struggle to express uncertainty (**21% ambiguous accuracy**).

### Results Summary

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Overall Accuracy | 79.2% | Good but not production-ready |
| False Valid Rate | 0% | Never misses true violations |
| False Invalid Rate | 29.3% | Frequently flags valid workflows |
| Ambiguous Accuracy | 21.4% | Poor at expressing uncertainty |
| Trap Valid Accuracy | 59.1% | Struggles with sophisticated valid cases |

## Benchmark Versions

| Version | Cases | Key Features |
|---------|-------|--------------|
| V1 | 42 | Original seed cases |
| V2 | 69 | +17 adversarial, +10 WRDS-backed |
| V3 | 105 | +36 hard source-backed (13 families) |
| **V4** | **125** | +20 calibration cases (trap valid, ambiguous) |

## Benchmark Modules

| Module | V4 Cases | Description |
|--------|----------|-------------|
| **Ticker Time Machine** | 45 | Historical identifier validity |
| **Filing Clock** | 27 | Information availability timing |
| **Accounting Availability** | 21 | Fiscal period vs. filing date |
| **Survivorship & Delisting** | 32 | Universe construction bias |

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/backtest-lie-detector.git
cd backtest-lie-detector

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[all]"

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Required API Keys

```env
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key  # Optional
WRDS_USERNAME=your-wrds-username              # Optional for data validation
```

### Generate Benchmark

```bash
# Set PYTHONPATH
export PYTHONPATH=src  # On Windows: $env:PYTHONPATH="src"

# Generate V4 benchmark (default)
python -m backtest_lie_detector.benchmark.build_cases v4

# Or specific versions
python -m backtest_lie_detector.benchmark.build_cases v1  # 42 cases
python -m backtest_lie_detector.benchmark.build_cases v2  # 69 cases
python -m backtest_lie_detector.benchmark.build_cases v3  # 105 cases
```

### Run V4 Evaluation

```bash
# Full V4 comparison (specialized vs generic prompts)
python run_v4_comparison.py

# Generate analysis figures
python generate_v4_figures.py
```

### Alternative: Run Single Evaluation

```bash
python -m backtest_lie_detector.evals.run_eval \
    --benchmark data/benchmark/benchmark_v4.jsonl \
    --output outputs/results/model_outputs.jsonl \
    --model gpt-4o \
    --config finance_auditor
```

### Launch Demo App

```bash
streamlit run src/backtest_lie_detector/app/streamlit_app.py
```

## Project Structure

```
backtest-lie-detector/
├── data/
│   └── benchmark/
│       ├── benchmark_v1.jsonl     # 42 original cases
│       ├── benchmark_v2.jsonl     # 69 cases (+adversarial, +WRDS)
│       ├── benchmark_v3.jsonl     # 105 cases (+hard source-backed)
│       └── benchmark_v4.jsonl     # 125 cases (+calibration)
├── src/backtest_lie_detector/
│   ├── schemas.py                 # Pydantic data models
│   ├── benchmark/
│   │   ├── examples.py            # Seed cases (14)
│   │   ├── adversarial_cases.py   # Adversarial cases (17)
│   │   ├── wrds_cases.py          # WRDS-backed cases (10)
│   │   ├── hard_cases.py          # Hard source-backed (36)
│   │   ├── calibration_cases.py   # Calibration cases (20)
│   │   └── build_cases.py         # Case generation utilities
│   ├── evals/
│   │   ├── prompts.py             # System prompts
│   │   ├── model_clients.py       # API wrappers
│   │   ├── scoring.py             # Metrics and scoring
│   │   └── run_eval.py            # Evaluation runner
│   ├── analysis/
│   │   └── plots.py               # Visualization functions
│   └── app/
│       └── streamlit_app.py       # Demo application
├── outputs/
│   ├── results/
│   │   ├── scores_v4.csv          # V4 evaluation results
│   │   ├── calibration_scores_v4.csv
│   │   └── failure_casebook.md    # Detailed failure analysis
│   └── figures/
│       ├── v4_summary.png
│       ├── v4_calibration_breakdown.png
│       └── ...
├── writeup/
│   └── index.md                   # Public-facing writeup
├── notebooks/
│   ├── 01_build_benchmark.ipynb
│   ├── 02_run_evals.ipynb
│   └── 03_analyze_results.ipynb
├── run_v4_comparison.py           # V4 evaluation script
├── generate_v4_figures.py         # V4 figure generation
└── tests/
```

## Reproducing V4 Results

```bash
# 1. Install dependencies
pip install -e ".[all]"

# 2. Set API key
export OPENAI_API_KEY=your-key

# 3. Generate benchmark
export PYTHONPATH=src
python -m backtest_lie_detector.benchmark.build_cases v4

# 4. Run evaluation (takes ~20 minutes for 250 API calls)
python run_v4_comparison.py

# 5. Generate figures
python generate_v4_figures.py

# 6. View results
# - outputs/results/scores_v4.csv
# - outputs/results/failure_casebook.md
# - outputs/figures/v4_summary.png
```

## Evaluation Metrics

### Standard Metrics
- **Validity Accuracy**: Correct classification of workflow as valid/invalid/ambiguous
- **Violation Recall**: Proportion of true violations detected
- **Violation Precision**: Proportion of flagged violations that are real
- **Severity-Weighted Score**: Errors weighted by practical importance
- **Repair Score**: Quality of proposed fixes (keyword-based heuristic)

### V4 Calibration Metrics
- **False Invalid Rate**: Valid cases incorrectly flagged as invalid
- **False Valid Rate**: Invalid cases incorrectly approved
- **Ambiguous Accuracy**: Correct identification of genuinely ambiguous cases
- **Valid Trap Accuracy**: Performance on trap_valid tagged cases
- **Overcaution Score**: Combined measure of overcautious behavior

## Case Tags (V4)

| Tag | Count | Description |
|-----|-------|-------------|
| `trap_valid` | 22 | Valid but looks suspicious |
| `ambiguous` | 14 | Correct answer needs more info |
| `multi_violation` | 8 | 2+ interacting violations |
| `requires_timestamp_reasoning` | 16 | Filing/event timing |
| `requires_identifier_reasoning` | 14 | Ticker/PERMNO logic |
| `requires_dataset_semantics` | 13 | CRSP/Compustat fields |
| `requires_corporate_action_reasoning` | 8 | Spinoffs, splits, mergers |

## Data Sources

- **Manual curation**: Hand-crafted cases with verified ground truth
- **WRDS CRSP**: Ticker history, delisting data, corporate actions
- **SEC EDGAR**: Filing timestamps
- **Academic literature**: Shumway (1997), Fama-French (1992)

## Limitations

1. **Single model tested on V4**: Only GPT-4o evaluated (Claude requires API access)
2. **Prompt sensitivity**: Generic prompt fails to produce valid JSON
3. **Benchmark size**: 125 cases covers main patterns but not exhaustively
4. **Ground truth ambiguity**: Some trap_valid cases have debatable answers
5. **No fine-tuning**: Using base model capabilities only
6. **English only**: All prompts and cases in English

## AI Usage Statement

This project was developed with assistance from AI tools:

- **Code generation**: Claude assisted with implementation
- **Documentation**: AI helped draft documentation and docstrings
- **Benchmark cases**: Templates AI-generated, all 125 cases human-reviewed

**Human contributions:**
- Benchmark design and methodology
- Ground truth validation for all cases
- Results interpretation and failure analysis
- Case family research and source verification

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

```bibtex
@misc{backtest-lie-detector-2026,
  title={Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors},
  author={UChicago Generative AI for Finance Team},
  year={2026},
  url={https://github.com/your-org/backtest-lie-detector}
}
```

---

*Project completed for Generative and Agentic AI for Finance, Spring 2026*
