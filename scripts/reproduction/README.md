# Reproduction scripts

Run these from the repository root.

## Recommended entry point

```bash
python scripts/reproduce.py
```

This no-API path runs tests, rebuilds aggregate metrics from committed results,
regenerates comparison figures, and smoke-tests the AA-Omniscience data loader.

For a live API rerun:

```bash
python scripts/reproduce.py --full-api
```

## Main scripts

| Script | Purpose |
| --- | --- |
| `run_v4_comparison.py` | GPT-4o generic and specialized prompts on V4. |
| `run_claude_evaluation.py` | Claude Sonnet on V4. |
| `run_v5_newcases_only.py` | Incremental V5 false-valid-trap cases. |
| `compute_v5_metrics.py` | Merge V4 and V5 incremental outputs. |
| `generate_v5_figures.py` | V5 figures used in the writeup. |
| `run_v6_chronology_only.py` | V6 chronology battery. |
| `run_code_cases_eval.py` | V6 code-auditing battery. |
| `generate_v6_figures.py` | V6 extension figures. |
| `compute_all_metrics.py` | Aggregate all committed model/prompting result files. |
| `generate_all_figures.py` | Generate all-model comparison figures. |
| `run_aa_omniscience.py` | AA-Omniscience finance comparison. |
| `run_baseline_evaluation.py` | Rule-based baseline evaluation. |

Older V1-V4 exploratory scripts live in `scripts/legacy/`.
