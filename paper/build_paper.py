"""Compile the English TC-SSSAO paper only; no project-wide validation is run."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent
MAIN = "TC-SSSAO.tex"
PDF = MAIN.replace(".tex", ".pdf")
MAX_PASSES = 4
INTERMEDIATE_SUFFIXES = (
    ".aux", ".log", ".out", ".toc", ".lof", ".lot", ".fls",
    ".fdb_latexmk", ".xdv", ".bbl", ".blg", ".run.xml", ".bcf",
)


def clean_intermediates() -> list[str]:
    removed: list[str] = []
    for path in sorted(PAPER_DIR.iterdir()):
        if path.is_file() and (path.suffix in INTERMEDIATE_SUFFIXES or path.name.endswith(".synctex.gz")):
            path.unlink()
            removed.append(path.name)
    return removed


def main() -> int:
    log = ""
    for pass_no in range(1, MAX_PASSES + 1):
        proc = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", MAIN],
            cwd=PAPER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        log = proc.stdout
        if proc.returncode:
            print(f"FAIL: pdfLaTeX pass {pass_no} returned {proc.returncode}")
            print(log[-4000:])
            return 1
        if "Rerun to get" not in log and "Label(s) may have changed" not in log:
            break

    undefined = bool(re.search(r"(undefined references|Citation .* undefined|Reference .* undefined)", log, re.I))
    match = re.search(r"Output written on (.+?) \((\d+) pages?", log)
    pages = int(match.group(2)) if match else None
    report = {
        "status": "FAIL" if undefined else "PASS",
        "source": MAIN,
        "pdf": PDF,
        "pages": pages,
        "pdflatex_passes": pass_no,
        "undefined_citations": len(re.findall(r"Citation [`'].+?[`'] on page .+? undefined", log, re.I)),
        "undefined_references": len(re.findall(r"Reference [`'].+?[`'] on page .+? undefined", log, re.I)),
        "overfull_hbox": len(re.findall(r"Overfull \\hbox", log)),
        "underfull_vbox": len(re.findall(r"Underfull \\vbox", log)),
        "missing_figures": len(re.findall(r"File [`'].+?[`'] not found", log, re.I)),
    }
    (PAPER_DIR / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if undefined:
        print("FAIL: unresolved references or citations")
        return 1
    removed = clean_intermediates()
    print(f"OK: {PDF}, {pages} pages; overfull hbox {report['overfull_hbox']}; cleaned {len(removed)} intermediates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
