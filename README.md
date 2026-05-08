# Backtest Lie Detector

**Benchmarking LLMs as Point-in-Time Auditors for Financial Research**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project provides a benchmark and evaluation framework to test whether Large Language Models (LLMs) can reliably detect point-in-time validity errors in financial research workflows. These errors—including look-ahead bias, ticker time-travel, filing timing mistakes, and survivorship bias—can silently invalidate backtests, event studies, and quantitative research.

### Core Research Question

> Can LLMs reliably audit financial research workflows for point-in-time validity?

### Why This Matters

LLMs are increasingly used to write, review, and audit trading strategies and financial research. However, they may miss subtle data leakage issues that would invalidate results in practice. This benchmark tests whether models can catch these critical errors.

## Benchmark Modules

The benchmark covers four categories of point-in-time errors:

| Module | Description | Example Error |
|--------|-------------|---------------|
| **Ticker Time Machine** | Historical identifier validity | Using META ticker for 2018 Facebook event |
| **Filing Clock** | Information availability timing | Trading on 8-K filed after decision time |
| **Accounting Availability** | Fiscal period vs. filing date | Using FY2022 data on Jan 15, 2023 before 10-K filed |
| **Survivorship & Delisting** | Universe construction bias | Backtesting only on currently-listed firms |

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

### Run Evaluation

```bash
# Run evaluation on benchmark
python -m backtest_lie_detector.evals.run_eval \
    --benchmark data/benchmark/benchmark_v1.jsonl \
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
│   └── benchmark/          # Benchmark cases (JSONL)
├── notebooks/
│   ├── 01_build_benchmark.ipynb
│   ├── 02_run_evals.ipynb
│   └── 03_analyze_results.ipynb
├── src/backtest_lie_detector/
│   ├── schemas.py          # Pydantic data models
│   ├── benchmark/          # Case generation
│   ├── evals/              # Evaluation harness
│   ├── analysis/           # Plots and failure analysis
│   └── app/                # Streamlit demo
├── outputs/
│   ├── results/            # Model outputs and scores
│   └── figures/            # Generated plots
├── writeup/                # Public-facing documentation
└── tests/                  # Unit tests
```

## Reproducing Results

1. **Setup**: Install dependencies and configure API keys
2. **Build Benchmark**: Run `notebooks/01_build_benchmark.ipynb` or use provided benchmark
3. **Run Evaluation**: Execute `notebooks/02_run_evals.ipynb` or use CLI
4. **Analyze Results**: Run `notebooks/03_analyze_results.ipynb` for metrics and plots

## Evaluation Metrics

- **Validity Accuracy**: Correct classification of workflow as valid/invalid
- **Violation Recall**: Proportion of true violations detected
- **Violation Precision**: Proportion of flagged violations that are real
- **Severity-Weighted Score**: Errors weighted by practical importance
- **Repair Accuracy**: Quality of proposed fixes

## Data Sources

- **Manual curation**: Hand-crafted cases with verified ground truth
- **WRDS CRSP**: Ticker history, delisting data (optional validation)
- **SEC EDGAR**: Filing timestamps (optional validation)

## Limitations

- Benchmark size is limited (~80 cases) for a class project
- Ground truth requires domain expertise and manual verification
- Repair scoring uses heuristics rather than formal verification
- Models may have seen similar examples in training data

## AI Usage Statement

This project was developed with assistance from AI tools:
- **Code generation**: Claude assisted with boilerplate code and structure
- **Documentation**: AI helped draft documentation and docstrings
- **Verification**: All benchmark cases and ground truth were manually reviewed

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use this benchmark, please cite:

```bibtex
@misc{backtest-lie-detector-2026,
  title={Backtest Lie Detector: Benchmarking LLMs as Point-in-Time Auditors},
  author={UChicago Generative AI for Finance Team},
  year={2026},
  url={https://github.com/your-org/backtest-lie-detector}
}
```
