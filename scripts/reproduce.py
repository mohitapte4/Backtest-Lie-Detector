"""One-command reproduction helper for the class-project results.

Default mode uses the committed result files to rebuild aggregate metrics and
figures without making API calls. Use ``--full-api`` only when you intend to
rerun the live OpenAI/Anthropic evaluations from scratch.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


NO_API_COMMANDS = [
    [PYTHON, "-m", "pytest"],
    [PYTHON, "scripts/reproduction/compute_all_metrics.py"],
    [PYTHON, "scripts/reproduction/generate_all_figures.py"],
]

FULL_API_COMMANDS = [
    [PYTHON, "scripts/reproduction/run_v4_comparison.py"],
    [PYTHON, "scripts/reproduction/run_claude_evaluation.py"],
    [PYTHON, "scripts/reproduction/run_v5_newcases_only.py"],
    [PYTHON, "scripts/reproduction/compute_v5_metrics.py"],
    [PYTHON, "scripts/reproduction/generate_v5_figures.py"],
    [PYTHON, "scripts/reproduction/run_v6_chronology_only.py"],
    [PYTHON, "scripts/reproduction/run_code_cases_eval.py"],
    [PYTHON, "scripts/reproduction/generate_v6_figures.py"],
]

AA_SMOKE_TEST = """
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
sys.path.insert(0, str(Path.cwd() / "scripts" / "reproduction"))

import run_aa_omniscience as aa

questions = aa.load_finance_questions("data/aa_omniscience/AA_Omniscience_finance.csv")
assert len(questions) == 100, len(questions)
assert aa.aa_omniscience_index(["CORRECT", "INCORRECT", "PARTIALLY_CORRECT", "NOT_ATTEMPTED"]) == 0.0
print(f"AA-Omniscience smoke test: loaded {len(questions)} finance questions")
"""


def run_command(command: list[str], *, env: dict[str, str]) -> None:
    """Run a command from the repository root with visible logging."""
    print("\n$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def build_env() -> dict[str, str]:
    """Build an environment that can import the local package from scripts."""
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce Backtest Lie Detector outputs.")
    parser.add_argument(
        "--full-api",
        action="store_true",
        help="Rerun live model evaluations before rebuilding figures. Requires API keys.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest in the no-API verification pass.",
    )
    args = parser.parse_args()

    env = build_env()

    commands = list(NO_API_COMMANDS)
    if args.skip_tests:
        commands = [cmd for cmd in commands if cmd[:3] != [PYTHON, "-m", "pytest"]]

    if args.full_api:
        api_commands = list(FULL_API_COMMANDS)
        for command in api_commands:
            run_command(command, env=env)

    for command in commands:
        run_command(command, env=env)

    run_command([PYTHON, "-c", AA_SMOKE_TEST], env=env)

    print("\nReproduction checks completed successfully.")


if __name__ == "__main__":
    main()
