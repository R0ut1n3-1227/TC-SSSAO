# -*- coding: utf-8 -*-
"""活跃代码依赖边界检查（扁平单根工作区口径，2026-09-13 扁平化后修订）。

规则：
  B1 活跃代码（.py/.mjs/.tex/.ttl/.cfg/.toml）不得引用
     archive/、local_only/、release/、submission_final/、dist/、
     history/、references/、deliverables/、workspace/ 路径——
     旧层、外部层与已移除的包裹层一律禁止；这些目录在当前树中
     不存在，任何引用都是失效引用（防重建护栏由卫生检查 H8 承担）。
  B2 活跃 markdown 不得含指向上述区域内文件的相对链接
     （纯文字提及不算依赖）。

允许名单（功能所需，逐条注明理由）见 ALLOWED 注释。

输出：data/current/dependency_boundary_check.json；
invalid_dependencies=0 时退出码 0。

    python scripts/validate/check_active_dependency_boundaries.py
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "current" / "dependency_boundary_check.json"

SCAN_TOPS = ["scripts", "src", "tests", "experiments", "paper", "ontology",
             "rules", "docs", "data"]
CODE_SUFFIXES = {".py", ".mjs", ".tex", ".ttl", ".cfg", ".toml"}
MD_SUFFIXES = {".md"}

FORBIDDEN_ZONES = ("archive/", "local_only/", "release/", "submission_final/",
                   "dist/", "history/", "references/", "deliverables/",
                   "workspace/")

# (文件相对路径, 命中的 zone) -> 允许理由
# 这两个检查器*提及* forbidden zone 是出于模式定义/排除目的，不构成读取依赖。
ALLOWED = {
    ("scripts/validate/check_active_dependency_boundaries.py", None): "检查器模式定义",
    ("scripts/validate/check_workspace_hygiene.py", None): "检查器模式定义",
}

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def zone_of(ref: str) -> str | None:
    ref = ref.replace("\\", "/")
    while ref.startswith("../") or ref.startswith("./"):
        ref = ref[3:] if ref.startswith("../") else ref[2:]
    for z in FORBIDDEN_ZONES:
        if ref.startswith(z):
            return z
    return None


def main() -> int:
    invalid: list = []
    allowed_used: list = []

    for top in SCAN_TOPS:
        base = ROOT / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            suffix = p.suffix.lower()
            r = rel(p)
            try:
                text = p.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue

            if suffix in CODE_SUFFIXES:
                for i, line in enumerate(text.splitlines(), 1):
                    for zone in FORBIDDEN_ZONES:
                        if zone in line:
                            if (r, None) in ALLOWED or (r, zone) in ALLOWED:
                                key = (r, zone) if (r, zone) in ALLOWED else (r, None)
                                allowed_used.append(
                                    {"file": r, "line": i, "zone": zone,
                                     "reason": ALLOWED.get(key)})
                            else:
                                invalid.append(
                                    {"file": r, "line": i, "zone": zone,
                                     "snippet": line.strip()[:120]})
            elif suffix in MD_SUFFIXES:
                for m in MD_LINK.finditer(text):
                    target = m.group(1).split("#", 1)[0]
                    if re.match(r"^[a-z]+://", target):
                        continue
                    z = zone_of(target)
                    if z:
                        line = text[:m.start()].count("\n") + 1
                        invalid.append({"file": r, "line": line, "zone": z,
                                        "snippet": m.group(0)[:120]})

    report = {
        "check": "active dependency boundaries (flat single-root workspace)",
        "rules": {
            "B1": "active code must not reference archive/ local_only/ release/ "
                  "submission_final/ dist/ history/ references/ deliverables/ "
                  "workspace/ (removed legacy/external/wrapper layers)",
            "B2": "active markdown must not contain relative links into any "
                  "forbidden zone",
        },
        "scanned_tops": SCAN_TOPS,
        "invalid_dependencies": len(invalid),
        "invalid": invalid,
        "allowed_exceptions_used": allowed_used,
        "status": "PASS" if not invalid else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(OUT), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    out = sys.stdout.buffer
    out.write(("dependency boundaries: %s invalid_dependencies=%d\n" % (
        report["status"], len(invalid))).encode("utf-8"))
    for item in invalid[:20]:
        out.write(("  %s:%d [%s] %s\n" % (
            item["file"], item["line"], item["zone"], item["snippet"])
        ).encode("utf-8", errors="replace"))
    return 0 if not invalid else 1


if __name__ == "__main__":
    sys.exit(main())
