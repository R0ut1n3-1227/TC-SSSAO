# -*- coding: utf-8 -*-
"""source→OWL 重建一致性检查：从 src/tc_sssao + ontology/tc_sssao_alignments.ttl
在临时目录完整重建 tc_sssao.owl，与正式 ontology/tc_sssao.owl 做图级比对。

检查项：
  R1 重建链四步全部成功（融合 → 导出 → 模式规范化 → 标准对齐合并）；
  R2 统计一致：classes / object properties / datatype properties /
     annotation properties / triples；
  R3 16 条正式标准对齐公理一致；
  R4 URI 级三元组零差异；
  R5 全图同构（rdflib.compare.isomorphic，含 bnode 结构）。

历史注记（2026-09-06 最终工作区整理）：官方 OWL 曾含 27 条无宿主
intersectionOf bnode 碎片（已删除类 GroundOpticalSensor/GroundInfraredSensor
的 equivalentClass 残余 + 3 条单成员列表），1936→1909 后源码链与发布件
精确同构；手术记录 orphan_fragment_removal.json 为历史过程文件，
未保留在活动树（仅存于项目外备份）。

输出：data/current/source_to_owl_rebuild_check.json；PASS 退出码 0。

    python scripts/validate/check_source_rebuild.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rdflib import BNode, Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "current" / "source_to_owl_rebuild_check.json"

ONTO = "https://w3id.org/tc-sssao#"
EXT_NS = ("http://www.w3.org/2006/time#", "http://www.w3.org/ns/sosa/",
          "http://www.w3.org/ns/ssn/", "http://www.w3.org/ns/prov#",
          "http://www.opengis.net/ont/geosparql#")

CHAIN = [
    ("融合领域模块", "scripts/build/generate_fused_domain_layer.py"),
    ("导出 OWL", "scripts/build/export_owl.py"),
    ("模式规范化", "scripts/build/modify_ontology.py"),
    ("标准对齐合并", "scripts/build/apply_standard_alignments.py"),
]


def counts(g: Graph) -> dict:
    def n(t):
        return len({s for s in g.subjects(RDF.type, t)
                    if isinstance(s, URIRef) and str(s).startswith(ONTO)})
    return {
        "classes": n(OWL.Class),
        "object_properties": n(OWL.ObjectProperty),
        "datatype_properties": n(OWL.DatatypeProperty),
        "annotation_properties": n(OWL.AnnotationProperty),
        "triples": len(g),
        "formal_alignments": len({(s, p, o) for s, p, o in g
                                  if str(s).startswith(ONTO)
                                  and p in (RDFS.subClassOf, RDFS.subPropertyOf)
                                  and isinstance(o, URIRef)
                                  and any(str(o).startswith(ns) for ns in EXT_NS)}),
    }


def uri_level(g: Graph) -> set:
    return {(s, p, o) for s, p, o in g
            if not isinstance(s, BNode) and not isinstance(o, BNode)}


def sanitize(text: str, sandbox: Path) -> str:
    """规范化输出尾巴中的本机路径（Closure Patch：报告 0 机器专属路径）。

    沙箱目录 → <TEMP_REBUILD_DIR>；系统临时目录 → <TEMP>；Python 解释器 →
    <LOCAL_PYTHON_EXECUTABLE>；用户主目录 → <LOCAL_HOME>；工作区根 →
    <WORKSPACE_ROOT>。两种斜杠形态、大小写不敏感。
    """
    if not text:
        return text
    pairs = [
        (str(sandbox), "<TEMP_REBUILD_DIR>"),
        (tempfile.gettempdir(), "<TEMP>"),
        (sys.executable, "<LOCAL_PYTHON_EXECUTABLE>"),
        (str(Path.home()), "<LOCAL_HOME>"),
        (str(ROOT), "<WORKSPACE_ROOT>"),
    ]
    for old, new in pairs:
        for variant in {old, old.replace("\\", "/")}:
            text = re.sub(re.escape(variant), new, text, flags=re.IGNORECASE)
    return text


def main() -> int:
    report: dict = {
        "check": "source→OWL rebuild consistency",
        "chain": [name for name, _ in CHAIN],
        "steps": [],
    }
    sandbox = Path(tempfile.mkdtemp(prefix="tc_sssao_rebuild_"))
    try:
        # 搭建最小可构建沙箱
        (sandbox / "scripts").mkdir()
        (sandbox / "ontology").mkdir()
        shutil.copytree(ROOT / "src", sandbox / "src")
        shutil.copytree(ROOT / "scripts" / "build", sandbox / "scripts" / "build")
        for f in ("requirements.txt",):
            shutil.copy2(ROOT / f, sandbox / f)
        shutil.copy2(ROOT / "ontology" / "tc_sssao_alignments.ttl",
                     sandbox / "ontology" / "tc_sssao_alignments.ttl")

        chain_ok = True
        for name, script in CHAIN:
            # PYTHONUTF8=1：链脚本中文输出在 Windows 管道下默认 GBK，
            # 直接 utf-8 解码会留下乱码；强制子进程 UTF-8 模式
            env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run([sys.executable, script], cwd=sandbox, env=env,
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            ok = proc.returncode == 0
            # 先消毒再截尾：避免截尾切在长路径中间留下半个路径碎片
            report["steps"].append({"step": name, "script": script,
                                    "returncode": proc.returncode,
                                    "tail": sanitize(proc.stdout or "",
                                                     sandbox)[-200:]})
            chain_ok = chain_ok and ok
        report["R1_chain_completed"] = chain_ok

        rebuilt_path = sandbox / "ontology" / "tc_sssao.owl"
        if not chain_ok or not rebuilt_path.exists():
            report["status"] = "FAIL"
            report["error"] = "rebuild chain failed or produced no OWL"
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            return 1

        official = Graph()
        official.parse(str(ROOT / "ontology" / "tc_sssao.owl"), format="xml")
        rebuilt = Graph()
        rebuilt.parse(str(rebuilt_path), format="xml")

        co, cr = counts(official), counts(rebuilt)
        report["official"] = co
        report["rebuilt"] = cr
        report["R2_counts_match"] = co == cr
        report["R3_formal_alignments"] = {
            "official": co["formal_alignments"],
            "rebuilt": cr["formal_alignments"],
            "match": co["formal_alignments"] == cr["formal_alignments"] == 16,
        }
        uo, ur = uri_level(official), uri_level(rebuilt)
        report["R4_uri_level_diff"] = {
            "only_official": len(uo - ur), "only_rebuilt": len(ur - uo),
            "match": uo == ur,
        }
        iso = bool(isomorphic(official, rebuilt))
        report["R5_isomorphic"] = iso

        overall = (chain_ok and report["R2_counts_match"]
                   and report["R3_formal_alignments"]["match"]
                   and report["R4_uri_level_diff"]["match"] and iso)
        report["core_semantic_difference"] = 0 if overall else 1
        report["status"] = "PASS" if overall else "FAIL"
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    out = sys.stdout.buffer
    out.write(("source→OWL rebuild: %s (official %d triples, rebuilt %s, "
               "isomorphic=%s)\n" % (
                   report["status"], report.get("official", {}).get("triples", -1),
                   report.get("rebuilt", {}).get("triples", "?"),
                   report.get("R5_isomorphic"))).encode("utf-8"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
