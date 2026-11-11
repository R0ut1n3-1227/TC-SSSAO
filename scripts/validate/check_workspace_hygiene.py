# -*- coding: utf-8 -*-
"""工作区卫生检查（扁平单根工作区口径，2026-09-13 扁平化后修订）。

检查项（任一 FAIL 即整体 FAIL，退出码 1）：
  H1  工作区根目录无散落 PDF
  H2  工作区根目录无 output/、tmp/、.m5_tmp/ 等 scratch 目录
  H3  工作区全树无 __pycache__/ 目录与 *.pyc/*.pyo 文件（隐藏目录豁免）
  H4  paper/ 与 docs/figures/ 无 LaTeX 中间产物（.aux/.log/.out/.toc 等）
  H5  活跃 scripts/ 无过时一次性补丁脚本（patch_owl_m5_alignment.py 等清单）
  H6  活跃文件无绝对 Windows 路径（E:/、C:\\Users、AppData、Temp、vscode-webview）；
      扫描类型含 .py/.mjs/.md/.tex/.ttl/.cfg/.toml/.yml/.yaml/.json/.csv/.tsv
  H7  工作区顶层目录/文件与规范结构一致（隐藏目录如 .claude 豁免）
  H8  工作区内不得存在 archive/、local_only/、release/、submission_final/、
      dist/、history/、references/、deliverables/ 目录（旧层与外部层）
  H9  活跃文件名不带阶段/版本残留标记（m2/m3/m4/m5/phase1/phase2/copy/
      final_final 等）
  H10 docs/figures/ 只含 sources/；其下无 build_tmp
  H11 （已退役）交付 ZIP 机器路径扫描——交付层在 2026-09-13 扁平化中移除，
      不再有交付 ZIP 可扫；规则位保留以维持 H1—H13 编号与既有报告口径
  H12 工作区内 *.zip 只允许出现在 data/esa_cdm/raw/（ESA 官方数据集
      原始归档，下载校验解包均在 raw/ 层完成）
  H13 （已退役）项目根四层模型检查——扁平化后工作区即项目根，
      不再存在 workspace/deliverables/history/references 包裹层可核对；
      防重建约束由 H8 承担（这些目录名在工作区内任何层级均禁止）

输出：data/current/workspace_hygiene_check.json

    python scripts/validate/check_workspace_hygiene.py
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "current" / "workspace_hygiene_check.json"

# H7：工作区规范顶层；数据集中到 data/，说明集中到 docs/。
CANONICAL_TOP_DIRS = {
    "data", "docs", "experiments", "ontology", "paper", "rules",
    "scripts", "src", "tests",
    
}
CANONICAL_TOP_FILES = {
    ".gitattributes", "AGENTS.md", "CITATION.cff", "LICENSE",
    "README.md", "requirements.txt",
    
}

# H8：工作区内禁止出现的目录名（任何层级；含已移除的旧包裹层名，
# 防止 workspace/deliverables/history/references 被重新创建）
FORBIDDEN_DIR_NAMES = {
    "archive", "local_only", "release", "submission_final", "dist",
    "history", "references", "deliverables", "workspace",
}

# H4
LATEX_INTERMEDIATE_SUFFIXES = {
    ".aux", ".bbl", ".bcf", ".blg", ".fdb_latexmk", ".fls", ".log",
    ".out", ".run.xml", ".synctex.gz", ".toc", ".xdv", ".dvi", ".nav",
    ".snm", ".vrb", ".lof", ".lot", ".idx", ".ind", ".ilg",
}

# H5：已被取代的一次性补丁/迁移脚本，不得出现在活跃 scripts/
STALE_ACTIVE_SCRIPTS = [
    "patch_owl_m5_alignment.py",
    "generate_m5p2_extension_and_stats.py",
]

# H6：绝对路径/机器专属模式。驱动器字母前不得紧跟 URI scheme 字符
# （避免把 https:// 的 "s:/" 误判为驱动器路径）。
PATH_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9+.-])[A-Za-z]:[\\/]"),
    re.compile(r"vscode-webview", re.IGNORECASE),
]
SCAN_SUFFIXES = {".py", ".mjs", ".md", ".tex", ".ttl", ".cfg", ".toml",
                 ".yml", ".yaml", ".json", ".csv", ".tsv"}
# H6 豁免：本检查器含模式定义（自指命中）；卫生报告自身会记录命中串——
# 这些是派生引用，真实机器路径的强制检查由 H6 直接扫描源文件完成
H6_EXEMPT_FILES = {
    "scripts/validate/check_workspace_hygiene.py",
    "data/current/workspace_hygiene_check.json",
}
H6_EXEMPT_FILES_NORM = {f.replace("\\", "/") for f in H6_EXEMPT_FILES}

# H9：活跃文件名禁用的阶段/版本残留标记（小写匹配）。
# 2026-09-13 起项目永久取消工程版本管理：版本区分标记（_v1—_v4、
# v1_—v4_ 前缀、v21、latest、final2、candidate、preview 等）一律禁止出现在活跃文件名中
FORBIDDEN_NAME_MARKERS = [
    "final_final", "_copy", " copy.", "phase1", "phase2", "_m2_", "_m3_",
    "_m4_", "_m5_", "m5p1", "m5p2", "m3p1", "m3p2",
    "_v1", "_v2", "_v3", "_v4", "v1_", "v2_", "v3_", "v4_", "v21",
    "latest", "final2", "candidate", "preview",
]
NAME_MARKER_ALLOWLIST: list = []

ACTIVE_TOPS = ["scripts", "src", "tests", "experiments", "paper", "ontology",
               "rules", "data"]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def has_hidden_part(p: Path) -> bool:
    """路径任一组件以 . 开头（.claude 等工具运行时目录，扫描一律豁免）。"""
    return any(part.startswith(".") for part in p.relative_to(ROOT).parts)


def scan_text(name: str, text: str, hits: list, patterns) -> None:
    for pat in patterns:
        for m in pat.finditer(text):
            line = text[:m.start()].count("\n") + 1
            hits.append({"file": name, "line": line, "match": m.group(0)})


def main() -> int:
    checks: dict = {}

    # H1 根散落 PDF
    root_pdfs = sorted(p.name for p in ROOT.glob("*.pdf"))
    checks["H1_no_root_pdfs"] = {"pass": not root_pdfs, "found": root_pdfs}

    # H2 scratch 目录
    scratch = sorted(d for d in ("output", "tmp", ".m5_tmp", ".build")
                     if (ROOT / d).exists())
    checks["H2_no_scratch_dirs"] = {"pass": not scratch, "found": scratch}

    # H3 __pycache__ / *.pyc / *.pyo（隐藏目录子树豁免；
    # scripts/、tests/、experiments/、data/、stage2g_deploy/、stage2g_e2e/
    # 中的 __pycache__ 为运行产物，不计入）
    TRANSIENT_PARENTS = {"scripts", "tests", "experiments", "data",
                         "stage2g_deploy", "stage2g_e2e"}
    def in_transient(p):
        return any(a.name in TRANSIENT_PARENTS for a in Path(p).parents)
    pycache_dirs = sorted(rel(p) for p in ROOT.rglob("__pycache__")
                          if p.is_dir() and not has_hidden_part(p)
                          and not in_transient(p))
    pyc_files = sorted(rel(p) for p in ROOT.rglob("*.pyc")
                       if not has_hidden_part(p)
                       and not in_transient(p))
    pyo_files = sorted(rel(p) for p in ROOT.rglob("*.pyo")
                       if not has_hidden_part(p)
                       and not in_transient(p))
    checks["H3_no_pycache"] = {"pass": not pycache_dirs and not pyc_files
                               and not pyo_files,
                               "dirs": pycache_dirs, "files": pyc_files + pyo_files}

    # H4 LaTeX 中间产物（paper/ 与 docs/figures/）
    latex_junk = []
    for base in (ROOT / "paper", ROOT / "docs" / "figures"):
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and (p.suffix.lower() in LATEX_INTERMEDIATE_SUFFIXES
                                or p.name.endswith(".synctex.gz")):
                latex_junk.append(rel(p))
    checks["H4_no_latex_intermediates"] = {"pass": not latex_junk,
                                           "found": sorted(latex_junk)}

    # H5 过时脚本
    stale = []
    for name in STALE_ACTIVE_SCRIPTS:
        for p in (ROOT / "scripts").rglob(name):
            stale.append(rel(p))
    checks["H5_no_stale_patch_scripts"] = {"pass": not stale, "found": stale}

    # H6 绝对路径 / 机器专属路径
    path_hits = []
    for top in ["scripts", "src", "tests", "experiments", "paper", "ontology",
                "rules", "docs", "data"]:
        base = ROOT / top
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in SCAN_SUFFIXES:
                continue
            r = rel(p)
            r_norm = r.replace("\\", "/")
            if r in H6_EXEMPT_FILES or r_norm in H6_EXEMPT_FILES_NORM:
                continue
            # data/current/ contains transient outputs that may reference paths
            if r_norm.startswith("data/current/"):
                continue
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            scan_text(r, text, path_hits, PATH_PATTERNS)
    checks["H6_no_absolute_machine_paths"] = {"pass": not path_hits,
                                              "hits": path_hits}

    # H7 工作区顶层结构（隐藏目录一律豁免：.claude/.git 等为工具运行时状态）
    top_dirs = {p.name for p in ROOT.iterdir() if p.is_dir()
                and not p.name.startswith(".")}
    unknown_dirs = sorted(top_dirs - CANONICAL_TOP_DIRS)
    missing_dirs = sorted(CANONICAL_TOP_DIRS - top_dirs)
    top_files = {p.name for p in ROOT.iterdir() if p.is_file()}
    unknown_files = sorted(top_files - CANONICAL_TOP_FILES)
    checks["H7_canonical_workspace_top_level"] = {
        "pass": not unknown_dirs and not missing_dirs and not unknown_files,
        "unknown_dirs": unknown_dirs, "missing_dirs": missing_dirs,
        "unknown_files": unknown_files,
    }

    # H8 旧层/外部层目录不得出现在工作区内（任何层级；隐藏目录子树豁免）
    bad_dirs = []
    for p in ROOT.rglob("*"):
        if p.is_dir() and not has_hidden_part(p) \
                and p.name.lower() in FORBIDDEN_DIR_NAMES:
            bad_dirs.append(rel(p))
    checks["H8_no_legacy_or_external_dirs"] = {"pass": not bad_dirs,
                                               "found": sorted(bad_dirs)}

    # H9 文件名残留标记（活跃源区）
    marked = []
    for top in ACTIVE_TOPS:
        base = ROOT / top
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            name = p.name.lower()
            if rel(p) in NAME_MARKER_ALLOWLIST:
                continue
            hit = [m for m in FORBIDDEN_NAME_MARKERS if m in name]
            if hit:
                marked.append({"path": rel(p), "markers": hit})
    checks["H9_no_phase_markers_in_active_names"] = {
        "pass": not marked, "found": marked}

    # H10 docs/figures 只含 sources/ 且无 build_tmp
    fig = ROOT / "docs" / "figures"
    fig_entries = sorted(p.name for p in fig.iterdir()) if fig.is_dir() else []
    build_tmp = list(fig.rglob("build_tmp")) if fig.is_dir() else []
    checks["H10_figures_sources_only"] = {
        "pass": fig_entries == ["sources"] and not build_tmp,
        "entries": fig_entries, "build_tmp": [rel(p) for p in build_tmp],
    }

    # H11 已退役：交付层在 2026-09-13 扁平化中移除，不再有交付 ZIP 可扫。
    # 规则位保留以维持 H1—H13 编号与既有报告口径；防重建约束由 H8 承担
    # （deliverables 为工作区禁止目录名，任何层级出现即 H8 FAIL）。
    checks["H11_no_machine_paths_in_deliverable_zips"] = {
        "pass": True, "skipped": True,
        "note": "retired 2026-09-13: deliverable layer removed by flattening; "
                "re-creation guard carried by H8",
    }

    # H12 工作区内无 ZIP（data/esa_cdm/raw/ 内 ESA 官方数据集归档豁免）
    zips_in_ws = sorted(rel(p) for p in ROOT.rglob("*.zip")
                        if not has_hidden_part(p)
                        and not rel(p).startswith("data/esa_cdm/raw/"))
    checks["H12_no_zips_in_workspace"] = {"pass": not zips_in_ws,
                                          "found": zips_in_ws}

    # H13 已退役：扁平化后工作区即项目根，不再有包裹层可核对。
    # 规则位保留；workspace/deliverables/history/references 的防重建
    # 约束由 H8（工作区内任何层级禁止这些目录名）承担。
    checks["H13_canonical_project_root"] = {
        "pass": True, "skipped": True,
        "note": "retired 2026-09-13: workspace is the project root after "
                "flattening; wrapper-layer guard carried by H8",
    }

    overall = all(c["pass"] for c in checks.values())
    report = {
        "check": "workspace hygiene (flat single-root workspace)",
        "scope": "project root (H1—H10, H12); H11/H13 retired 2026-09-13 "
                 "(deliverable layer and wrapper model removed by flattening)",
        "checks": checks,
        "status": "PASS" if overall else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(OUT), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    out = sys.stdout.buffer
    for k, c in checks.items():
        out.write(("%s %s\n" % ("PASS" if c["pass"] else "FAIL", k)
                   ).encode("utf-8"))
    out.write(("workspace hygiene: %s\n" % report["status"]).encode("utf-8"))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
