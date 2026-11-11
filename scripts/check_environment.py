"""TC-SSSAO 实验环境检查（M4 Phase 1，spec 第 10 节）。

打印 Python 与关键依赖版本，并与 requirements.txt 的精确锁定值比对：
- 全部匹配 -> PASS（退出码 0）
- 任一缺失或版本不符 -> FAIL（退出码 1）
- Python 主版本不在推荐区间 -> warning（不直接 FAIL）

本脚本不自动安装任何软件。
"""
from __future__ import annotations

import platform
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 推荐 Python 区间（含下界、不含上界）。验证环境为 3.14.2。
RECOMMENDED_PYTHON = ((3, 10), (3, 15))

# 显示名 -> importlib metadata 分发名
PACKAGES = [
    ("RDFLib", "rdflib"),
    ("pySHACL", "pyshacl"),
    ("owlrl", "owlrl"),
    ("owlready2", "owlready2"),
]


def read_pinned() -> dict[str, str]:
    pinned: dict[str, str] = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.\-]+)", line)
        if m:
            pinned[m.group(1).lower()] = m.group(2)
    return pinned


def main() -> int:
    print("TC-SSSAO environment check")
    print("=" * 40)
    py = platform.python_version()
    print(f"Python version : {py} ({sys.executable})")

    warnings: list[str] = []
    py_tuple = tuple(int(x) for x in py.split(".")[:2])
    if not (RECOMMENDED_PYTHON[0] <= py_tuple < RECOMMENDED_PYTHON[1]):
        warnings.append(
            f"Python {py} 不在推荐区间 "
            f"[{'.'.join(map(str, RECOMMENDED_PYTHON[0]))}, "
            f"{'.'.join(map(str, RECOMMENDED_PYTHON[1]))})；"
            f"验证环境为 3.14.2，其他版本未实测。"
        )

    pinned = read_pinned()
    ok = True
    for display, dist in PACKAGES:
        try:
            actual = metadata.version(dist)
        except metadata.PackageNotFoundError:
            print(f"{display:<12}: NOT INSTALLED (expected {pinned.get(dist, '?')})")
            ok = False
            continue
        expected = pinned.get(dist)
        status = "OK" if actual == expected else f"MISMATCH (expected {expected})"
        if actual != expected:
            ok = False
        print(f"{display:<12}: {actual}  {status}")

    for w in warnings:
        print(f"WARNING: {w}")
    print("=" * 40)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
