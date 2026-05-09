# Backtest Lie Detector

**Benchmarking LLMs as Point-in-Time Auditors for Financial Research**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project provides a benchmark and evaluation framework to test whether Large Language Models (LLMs) can reliably detect point-in-time validity errors in financial research workflows. These errors—including look-ahead bias, ticker time-travel, filing timing mistakes, and survivorship bias—can silently invalidate backtests, event studies, and quantitative research.

### Key Findings (V5 Benchmark - Final)

> 1. LLMs catch violations reliably (**0-4.7% false valid rate**)
> 2. Overcaution is the main failure mode (**20-44% false invalid rate**)
> 3. **Prompt engineering is context-dependent**: generic wins on accuracy, specialized wins on safety
> 4. Accuracy and repair quality are inversely correlated
> 5. **Subtle violations require domain expertise** in prompts

### V5 Results Summary (141 cases)

| Model | Accuracy | False Invalid | False Valid | On 16 Trap Cases |
|-------|----------|---------------|-------------|------------------|
| GPT-4o (Generic) | **83.0%** | **19.5%** | 4.7% | Missed 3/16 |
| GPT-4o (Specialized) | 80.9% | 29.3% | **0.0%** | **0/16 missed** |
| Claude Sonnet 4.5 | 78.0% | 43.9% | 1.2% | **0/16 missed** |

### The V5 Insight

V4 found generic prompts beat specialized. V5 adds nuance:
- **Obvious violations**: Generic prompts work fine
- **Subtle violations**: Specialized prompts catch 100% vs 81% for generic
- **Maximum safety**: Use specialized (0% false valid rate)

## Benchmark Versions

| Version | Cases | Key Features |
|---------|-------|--------------|
| V1 | 42 | Original seed cases |
| V2 | 69 | +17 adversarial, +10 WRDS-backed |
| V3 | 105 | +36 hard source-backed (13 families) |
| V4 | 125 | +20 calibration cases (trap valid, ambiguous) |
| **V5** | **141** | **+16 false valid traps** (subtle violations) |

## Benchmark Modules

| Module | V5 Cases | Description |
|--------|----------|-------------|
| **Ticker Time Machine** | 48 | Historical identifier validity |
| **Filing Clock** | 31 | Information availability timing |
| **Accounting Availability** | 24 | Fiscal period vs. filing date |
| **Survivorship & Delisting** | 38 | Universe construction bias |

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

# Generate V5 benchmark (default)
python -m backtest_lie_detector.benchmark.build_cases v5

# Or specific versions
python -m backtest_lie_detector.benchmark.build_cases v1  # 42 cases
python -m backtest_lie_detector.benchmark.build_cases v2  # 69 cases
python -m backtest_lie_detector.benchmark.build_cases v3  # 105 cases
python -m backtest_lie_detector.benchmark.build_cases v4  # 125 cases
```

### Run V5 Evaluation

```bash
# Run only the 16 new false valid trap cases (saves API calls)
python run_v5_newcases_only.py

# Combine with V4 results and compute metrics
python compute_v5_metrics.py

# Generate V5 figures
python generate_v5_figures.py
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
│       ├── benchmark_v4.jsonl     # 125 cases (+calibration)
│       └── benchmark_v5.jsonl     # 141 cases (+false valid traps)
├── src/backtest_lie_detector/
│   ├── schemas.py                 # Pydantic data models
│   ├── benchmark/
│   │   ├── examples.py            # Seed cases (14)
│   │   ├── adversarial_cases.py   # Adversarial cases (17)
│   │   ├── wrds_cases.py          # WRDS-backed cases (10)
│   │   ├── hard_cases.py          # Hard source-backed (36)
│   │   ├── calibration_cases.py   # Calibration cases (20)
│   │   ├── false_valid_traps.py   # V5 false valid traps (16)
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
├── run_v4_comparison.py           # GPT-4o V4 evaluation script
├── run_v5_newcases_only.py        # V5 false valid trap evaluation
├── compute_v5_metrics.py          # Combine V4+V5 results
├── generate_v5_figures.py         # V5 figure generation
├── run_claude_evaluation.py       # Claude Sonnet evaluation
├── run_baseline_evaluation.py     # Rule-based baselines
├── scripts/
│   └── analyze_repairs.py         # Repair quality analysis
└── tests/
```

## Reproducing V5 Results

```bash
# 1. Install dependencies
pip install -e ".[all]"

# 2. Set API keys
export OPENAI_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key  # For Claude

# 3. Generate benchmark
export PYTHONPATH=src
python -m backtest_lie_detector.benchmark.build_cases v5

# 4. Run V5 evaluation (only 48 API calls for new cases)
python run_v5_newcases_only.py

# 5. Combine results and compute metrics
python compute_v5_metrics.py

# 6. Generate figures
python generate_v5_figures.py

# 7. View results
# - outputs/results/V5_RESULTS.md
# - outputs/results/model_outputs_v5_*.jsonl
# - outputs/figures/v5_*.png
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

## Case Tags (V5)

| Tag | Count | Description |
|-----|-------|-------------|
| `trap_valid` | 22 | Valid but looks suspicious |
| `false_valid_trap` | 16 | Invalid but sounds valid (V5 new) |
| `near_miss` | 17 | Almost valid or almost invalid |
| `ambiguous` | 14 | Correct answer needs more info |
| `multi_violation` | 8 | 2+ interacting violations |
| `requires_timestamp_reasoning` | 22 | Filing/event timing |
| `requires_dataset_semantics` | 21 | CRSP/Compustat fields |
| `requires_identifier_reasoning` | 14 | Ticker/PERMNO logic |
| `requires_corporate_action_reasoning` | 10 | Spinoffs, splits, mergers |

## Data Sources

- **Manual curation**: Hand-crafted cases with verified ground truth
- **WRDS CRSP**: Ticker history, delisting data, corporate actions
- **SEC EDGAR**: Filing timestamps
- **Academic literature**: Shumway (1997), Fama-French (1992)

## Limitations

1. **Two models tested**: GPT-4o and Claude Sonnet; more models would strengthen conclusions
2. **Two prompt variants**: More prompt engineering could yield better results
3. **Benchmark size**: 141 cases covers main patterns but not exhaustively
4. **Ground truth requires expertise**: Some trap_valid cases have debatable answers
5. **No fine-tuning**: Using base model capabilities only
6. **English only**: All prompts and cases in English

## AI Usage Statement

This project was developed with assistance from AI tools:

- **Code generation**: Claude assisted with implementation
- **Documentation**: AI helped draft documentation and docstrings
- **Benchmark cases**: Templates AI-generated, all 141 cases human-reviewed

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
