# -*- coding: utf-8 -*-
"""构建本体与英文论文，随后清理临时实验输出；不运行自动审核套件。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 构建运行记录只打印到 stdout。


def sanitize(text: str) -> str:
    """规范化输出尾巴中的本机路径（报告 0 机器专属路径）：先消毒再截尾。"""
    if not text:
        return text
    pairs = [
        (tempfile.gettempdir(), "<TEMP>"),
        (sys.executable, "<LOCAL_PYTHON_EXECUTABLE>"),
        (str(Path.home()), "<LOCAL_HOME>"),
        (str(ROOT), "<WORKSPACE_ROOT>"),
        (str(ROOT.parent), "<PROJECT_ROOT>"),
    ]
    for old, new in pairs:
        for variant in {old, old.replace("\\", "/")}:
            text = re.sub(re.escape(variant), new, text, flags=re.IGNORECASE)
    return text


STEPS = [
    ("1_build_ontology", "构建本体（authoring source → canonical OWL）",
     ["scripts/build/build_ontology.py"]),
    ("3_build_paper", "英文论文构建",
     ["scripts/build/build_english_paper.py"]),
    ("4_clean_generated_artifacts", "实验 outputs 静置清理",
     ["scripts/build/clean_generated_artifacts.py"]),
]


def main() -> int:
    report: dict = {"builder": "build_final_artifacts (flat workspace, 3-step)",
                    "steps": []}
    out = sys.stdout.buffer
    for step_id, title, cmd in STEPS:
        t0 = time.time()
        # 官方构建运行不产生 __pycache__（hygiene 要求工作区静置无缓存）；
        # PYTHONUTF8=1：子进程中文输出在 Windows 管道下默认 GBK，强制 UTF-8
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        proc = subprocess.run([sys.executable] + cmd, cwd=ROOT, env=env,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        dur = time.time() - t0
        ok = proc.returncode == 0
        report["steps"].append({
            "step": step_id, "title": title, "command": " ".join(cmd),
            "returncode": proc.returncode, "seconds": round(dur, 1),
            "stdout_tail": sanitize(proc.stdout or "")[-600:],
            "stderr_tail": sanitize(proc.stderr or "")[-600:],
            "status": "PASS" if ok else "FAIL",
        })
        out.write(("%s %s %s (%.1fs)\n" % (
            "PASS" if ok else "FAIL", step_id, title, dur)).encode("utf-8"))
        if not ok:
            report["status"] = "FAIL"
            report["stopped_at"] = step_id
            report["note"] = "任一步失败即停止"
            out.write((json.dumps(report, ensure_ascii=False, indent=1) + "\n"
                       ).encode("utf-8"))
            out.write(("STOPPED at %s\n" % step_id).encode("utf-8"))
            return 1
    report["status"] = "PASS"
    out.write((json.dumps(report, ensure_ascii=False, indent=1) + "\n"
               ).encode("utf-8"))
    out.write(("build_final_artifacts: ALL %d STEPS PASS "
               "(clean-room capable)\n" % len(STEPS)).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
