# -*- coding: utf-8 -*-
"""删除可再生的实验 outputs/；需要时由对应实验运行器重新生成。

不修改实验输入、查询、规则或运行器。
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUTS = [
    "experiments/cz6a/outputs",
    "experiments/rule_logic_verification/outputs",
    "experiments/module_ablation/outputs",
    "experiments/standard_interoperability/outputs",
]


def _rmtree_retry(path: Path, attempts: int = 5) -> None:
    """Windows 上偶发文件锁（索引器/编辑器）：短退避重试 rmtree。"""
    for i in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(1.5 * (i + 1))
        except FileNotFoundError:
            return


def main() -> int:
    out = sys.stdout.buffer
    removed, absent = [], []
    for rel in OUTPUTS:
        d = ROOT / rel
        if d.exists():
            n = sum(1 for p in d.rglob("*") if p.is_file())
            _rmtree_retry(d)
            removed.append("%s（%d 个文件）" % (rel, n))
        else:
            absent.append(rel)
    for r in removed:
        out.write(("removed  %s\n" % r).encode("utf-8"))
    for a in absent:
        out.write(("absent   %s（允许不存在）\n" % a).encode("utf-8"))
    out.write(("clean_generated_artifacts: PASS (removed=%d absent=%d)\n"
               % (len(removed), len(absent))).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
