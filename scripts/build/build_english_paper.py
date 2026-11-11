"""Build the sole formal English manuscript (paper/)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def main():
    paper_dir = ROOT / "paper"
    if not (paper_dir / "TC-SSSAO.tex").is_file():
        raise RuntimeError("paper/TC-SSSAO.tex is required to build the English manuscript")
    return subprocess.call([sys.executable, str(paper_dir / "build_paper.py")])

if __name__ == "__main__":
    import sys
    raise SystemExit(main())
