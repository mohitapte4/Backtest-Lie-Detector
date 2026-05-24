# Chain-of-Thought & Claude Model Evaluation

Instructions for reproducing and extending the prompting strategy comparison across GPT-4o and Claude models.

## What Was Added

- **Chain-of-thought prompting** — a new 5-step reasoning prompt (timeline reconstruction, identifier check, information availability, universe construction, verdict)
- **Few-shot prompting** — finance_auditor prompt with 3 worked examples
- **Claude model evaluations** — Sonnet 4.5, Sonnet 4.6, and Haiku 4.5 across all prompting strategies
- **V6-only case evaluations** — chronology + code cases tested on all models

## Results

Pre-computed results are committed in `outputs/results/`. To view the summary:

- **Full comparison table**: `outputs/results/ALL_EVALUATION_RESULTS.txt`
- **Figures**: `outputs/figures/all_*.png`

## Reproducing Results

### Setup

```bash
# Activate environment
$env:PYTHONPATH="src"  # PowerShell
export PYTHONPATH=src  # Bash
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# API keys needed in .env
OPENAI_API_KEY=your-key      # For GPT-4o runs
ANTHROPIC_API_KEY=your-key   # For Claude runs
```

### Run Scripts

```bash
# GPT-4o on V5 (requires OPENAI_API_KEY)
python scripts/reproduction/run_prompting_comparison.py          # zero-shot, few-shot, CoT
python scripts/reproduction/run_gpt4o_base_prompts.py            # minimal, default

# GPT-4o on V6-only cases (chronology + code)
python scripts/reproduction/run_gpt4o_v6only.py

# Claude models on V5 + V6-only (requires ANTHROPIC_API_KEY)
# Runs Sonnet 4.5, Sonnet 4.6, Haiku 4.5 with all 5 strategies
python scripts/reproduction/run_claude_prompting_comparison.py

# Compute metrics and save summary
python scripts/reproduction/compute_all_metrics.py

# Generate comparison figures
python scripts/reproduction/generate_all_figures.py
```

All run scripts support **resume** — if interrupted, re-run the same command and it picks up where it stopped.

### Estimated Costs

| Script | API Calls | Est. Cost | Time |
|--------|-----------|-----------|------|
| `scripts/reproduction/run_prompting_comparison.py` | 423 | ~$4 | ~8 min |
| `scripts/reproduction/run_gpt4o_base_prompts.py` | 282 | ~$3 | ~5 min |
| `scripts/reproduction/run_gpt4o_v6only.py` | 100 | ~$1 | ~3 min |
| `scripts/reproduction/run_claude_prompting_comparison.py` | 2,415 | ~$15 | ~45 min |

## Adding a New Model

The compute and figure scripts **auto-discover** result files. To add a new model:

1. Drop your result `.jsonl` files into `outputs/results/` with naming:
   - V5 results: `{model}_{strategy}_v5.jsonl`
   - V6-only results: `{model}_{strategy}_v6only.jsonl`
   - Or for GPT-4o style: `prompting_{strategy}.jsonl`
2. Re-run `python scripts/reproduction/compute_all_metrics.py` and `python scripts/reproduction/generate_all_figures.py`
3. Or create a new run script following the pattern in `scripts/reproduction/run_claude_prompting_comparison.py`

### Example: Adding Gemini

```python
# In a new run_gemini_comparison.py, define:
models = {
    "gemini-2.0": {
        "id": "gemini-2.0-flash",
        "short": "gemini20",
    },
}
# Name output files: claude_gemini20_zero_shot_v5.jsonl, etc.
# The compute/figure scripts will pick them up automatically.
```

## Prompting Strategies

| Strategy | System Prompt | Few-shot | Description |
|----------|--------------|----------|-------------|
| `minimal` | Minimal | 0 | Brief "you're a financial auditor" |
| `default` | Default | 0 | Standard auditor with common examples |
| `zero_shot` | Finance auditor | 0 | Detailed expert with specific guidance |
| `few_shot` | Finance auditor | 3 | Same as zero-shot + 3 worked examples |
| `cot` | Chain-of-thought | 0 | Step-by-step reasoning before JSON answer |

### Chain-of-Thought Steps

The CoT prompt instructs the model to reason through 5 steps before answering:

1. **Timeline reconstruction** — place all dates/timestamps on a timeline
2. **Identifier check** — verify tickers/CUSIPs were valid for the period
3. **Information availability** — confirm data was public at the decision point
4. **Universe construction** — check for survivorship bias
5. **Verdict** — synthesize into valid/invalid/ambiguous

Defined in `src/backtest_lie_detector/evals/prompts.py` as `SYSTEM_PROMPT_COT`.

## Key Files

| File | Purpose |
|------|---------|
| `src/backtest_lie_detector/evals/prompts.py` | All prompt templates including CoT |
| `src/backtest_lie_detector/schemas.py` | Data models (updated for `chain_of_thought`) |
| `scripts/reproduction/run_prompting_comparison.py` | GPT-4o zero-shot/few-shot/CoT on V5 |
| `scripts/reproduction/run_gpt4o_base_prompts.py` | GPT-4o minimal/default on V5 |
| `scripts/reproduction/run_gpt4o_v6only.py` | GPT-4o all strategies on V6-only |
| `scripts/reproduction/run_claude_prompting_comparison.py` | All Claude models, all strategies, V5 + V6-only |
| `scripts/reproduction/compute_all_metrics.py` | Auto-discovers results, computes metrics, saves summary |
| `scripts/reproduction/generate_all_figures.py` | Auto-discovers results, generates comparison charts |
