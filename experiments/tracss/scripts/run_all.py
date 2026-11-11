"""Run the TraCSS adaptation pipeline end to end (01 -> 06).

Read-only on raw TraCSS downloads, ESA artifacts, rules, and ontology.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    "01_field_audit.py",
    "02_build_adapter.py",
    "03_distribution_audit.py",
    "04_risk_state_eval.py",
    "05_dangerous_analysis.py",
    "06_esa_comparison.py",
]


def main() -> int:
    # PYTHONDONTWRITEBYTECODE: keep the workspace free of __pycache__
    # (hygiene rule H3), including for the read-only ESA import in step 04.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for step in STEPS:
        print(f"=== {step} ===", flush=True)
        proc = subprocess.run([sys.executable, str(HERE / step)],
                              cwd=str(HERE), env=env)
        if proc.returncode != 0:
            print(f"FAILED: {step} (exit {proc.returncode})")
            return proc.returncode
    print("ALL STEPS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
