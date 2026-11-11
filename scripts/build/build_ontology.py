# -*- coding: utf-8 -*-
"""TC-SSSAO 正式本体构建入口。

从 authoring source 构建并（可选）原子替换发布本体：

    python scripts/build/build_ontology.py           # 完整构建并原子替换
    python scripts/build/build_ontology.py --check   # 只构建+验证+与当前发布件比对，不替换

构建链（全部在临时沙箱中执行，正式 ontology/tc_sssao.owl 在所有检查通过前不受影响）：
    1. 从 src/tc_sssao 融合模块构建基础 schema（generate_fused_domain_layer）
    2. 导出 OWL（export_owl）
    3. 最终 schema normalization（modify_ontology）
    4. 合并标准对齐模块 ontology/tc_sssao_alignments.ttl（apply_standard_alignments，
       含六项图级校验，描述性检查名）

替换前验证：
    - namespace / Ontology IRI / versionIRI 与本体冻结的语义版本声明一致
      （ONTOLOGY_VERSION 常量，与 export_owl.py 镜像；属科学内容，非工程版本号）；
    - 最终统计等于发布口径（86 命名类 / 1 匿名类表达式 / 65 对象属性 /
      68 数据属性 / 12 注解属性 / 1703 三元组 / 16 条正式标准对齐公理）；
    - 无 owl:imports、无 owl:deprecated、无指向外部术语的 equivalentClass。

替换为原子操作（同盘 os.replace）；替换后自动重建 ontology anatomy（zh/en）。
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
OWL_PATH = ROOT / "ontology" / "tc_sssao.owl"
REPORT = ROOT / "data" / "current" / "ontology_build.json"

ONTO = "https://w3id.org/tc-sssao#"
ONTOLOGY_IRI = "https://w3id.org/tc-sssao"
EXT_NS = ("http://www.w3.org/2006/time#", "http://www.w3.org/ns/sosa/",
          "http://www.w3.org/ns/ssn/", "http://www.w3.org/ns/prov#",
          "http://www.opengis.net/ont/geosparql#")

CHAIN = [
    ("融合领域模块", "scripts/build/generate_fused_domain_layer.py"),
    ("导出 OWL", "scripts/build/export_owl.py"),
    ("模式规范化", "scripts/build/modify_ontology.py"),
    ("标准对齐合并", "scripts/build/apply_standard_alignments.py"),
]

# 发布统计口径（论文 4.2.1；与 scripts/report/generate_ontology_statistics.py
# 的 EXPECTED 互为镜像，漂移即 FAIL）
# 2026-09-06 终审 schema 修复重钉（归因）：1909→1873。删除全部状态类上
# transitsTo/transitsFrom/degradesTo/recoversTo 的 someValuesFrom 存在性限制
# 共 9 条（4 个具体状态类 8 条 + SituationState 父类 1 条），每条 4 个三元组
# （subClassOf + Restriction type + onProperty + someValuesFrom），−36；
# 这些公理断言"每个状态实例必然发生固定方向转移"，与 B3 条件式演化冲突。
# 规则逻辑（R1—R18/B1—B5）与属性定义未动；命名类/匿名类/属性/对齐数不变。
# 2026-09-14 规则元数据与领域本体分离重构：删除 ConstraintRule 及
# Axiom_R1–R18（6+18=24 个类）；本体不再将 R1–R18 输出为 owl:Class，
# R1–R18 规则定义仍保留在 rules/tc_sssao_rules.ttl 与 axioms.py。
# 2026-09-14 SituationState 层级简化：删除 ComprehensiveSituationState
#（−1 命名类）；四状态加 hasValue 限制与 maxCardinality 1，净 −1 类 +16 三元组。
# 旧基线 87 类/1590 三元组 → 新结构 86 类/1606 三元组。
# 2026-09-14 Core/Extension 分层：扩展类 14 个（Direct/Indirect/Promoting/Inhibiting
# CausalAssertion、4 种 StateTransition 子类型、CyberThreat、CyberSecurityRisk、
# TrackingSystem、SurveillanceSystem、MitigationMeasure、WarningMeasure），
# 已从原模块移至 extensions.py；本体命名类总数不变（86），
# 新增 onto:modelLayer annotation（+86 三元组，86 个类各 1 条），
# annotation_properties 11→12，triples 1606→1694。
EXPECTED_STATS = {
    "classes": 86,
    "anonymous_class_expressions": 1,
    "object_properties": 65,
    "datatype_properties": 68,    # +1: Stage 2D hasEncounterID (P1-1 fix)
    "annotation_properties": 12,
    "triples": 1703,              # +9: hasEncounterID DP def + SpaceEvent restriction
    "formal_alignments": 16,
}


def stats_of(g: Graph) -> dict:
    def n(t):
        return len({s for s in g.subjects(RDF.type, t)
                    if isinstance(s, URIRef) and str(s).startswith(ONTO)})
    return {
        "classes": n(OWL.Class),
        "anonymous_class_expressions": len({s for s in g.subjects(RDF.type, OWL.Class)
                                            if isinstance(s, BNode)}),
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


def _sanitize(text: str, sandbox: Path) -> str:
    """规范化输出中的本机路径（Closure Patch：报告 0 机器专属路径）。"""
    if not text:
        return text
    pairs = [
        (str(sandbox), "<TEMP_BUILD_DIR>"),
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
    check_only = "--check" in sys.argv
    # 本体冻结的语义版本声明（写入 owl:versionInfo/versionIRI；科学内容），
    # 与 export_owl.py 中的镜像常量保持一致；项目无工程版本号文件
    version = "1.0.0"
    report: dict = {"builder": "scripts/build/build_ontology.py",
                    "check_only": check_only, "chain": [], "validations": {}}

    sandbox = Path(tempfile.mkdtemp(prefix="tc_sssao_build_"))
    built_owl = sandbox / "ontology" / "tc_sssao.owl"
    try:
        (sandbox / "scripts").mkdir()
        (sandbox / "ontology").mkdir()
        shutil.copytree(ROOT / "src", sandbox / "src")
        shutil.copytree(ROOT / "scripts" / "build", sandbox / "scripts" / "build")
        for f in ("requirements.txt",):
            shutil.copy2(ROOT / f, sandbox / f)
        shutil.copy2(ROOT / "ontology" / "tc_sssao_alignments.ttl",
                     sandbox / "ontology" / "tc_sssao_alignments.ttl")

        for name, script in CHAIN:
            # PYTHONUTF8=1：链脚本中文输出在 Windows 管道下默认 GBK，
            # 直接 utf-8 解码会留下乱码；强制子进程 UTF-8 模式
            env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
            proc = subprocess.run([sys.executable, script], cwd=sandbox, env=env,
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            report["chain"].append({"step": name, "returncode": proc.returncode})
            if proc.returncode != 0:
                # 先消毒再截尾：避免截尾切在长路径中间留下半个路径碎片
                report["error"] = (f"链步骤失败：{name}\n"
                                   + _sanitize(proc.stdout or '', sandbox)[-500:]
                                   + _sanitize(proc.stderr or '', sandbox)[-500:])
                return _finish(report, 1)

        g = Graph()
        g.parse(str(built_owl), format="xml")

        # 命名空间 / 版本验证
        header_ok = (
            (URIRef(ONTOLOGY_IRI), RDF.type, OWL.Ontology) in g
            and (URIRef(ONTOLOGY_IRI), OWL.versionInfo, None) in g
            and any(str(v) == version for v in
                    g.objects(URIRef(ONTOLOGY_IRI), OWL.versionInfo))
            and (URIRef(ONTOLOGY_IRI), OWL.versionIRI,
                 URIRef(f"{ONTOLOGY_IRI}/{version}")) in g
        )
        report["validations"]["namespace_version"] = header_ok

        # 统计验证
        stats = stats_of(g)
        report["statistics"] = stats
        report["validations"]["statistics"] = stats == EXPECTED_STATS

        # 结构卫生
        no_imports = not list(g.triples((None, OWL.imports, None)))
        no_deprecated = not list(g.triples((None, OWL.deprecated, None)))
        ext_equiv = [(s, o) for s, p, o in
                     list(g.triples((None, OWL.equivalentClass, None))) +
                     list(g.triples((None, OWL.equivalentProperty, None)))
                     if any(str(t).startswith(ns) for t in (s, o)
                            if isinstance(t, URIRef) for ns in EXT_NS)]
        report["validations"]["no_owl_imports"] = no_imports
        report["validations"]["no_deprecated"] = no_deprecated
        report["validations"]["no_external_equivalences"] = not ext_equiv

        all_ok = all(report["validations"].values())
        report["all_validations_pass"] = all_ok
        if not all_ok:
            report["error"] = "构建验证未通过，未替换正式 OWL"
            return _finish(report, 1)

        # 与当前发布件比对（信息性）
        if OWL_PATH.exists():
            current = Graph()
            current.parse(str(OWL_PATH), format="xml")
            report["isomorphic_to_current"] = bool(isomorphic(current, g))
        else:
            report["isomorphic_to_current"] = None

        if check_only:
            report["replaced"] = False
            return _finish(report, 0)

        # 原子替换（先写临时文件，同盘 os.replace）
        tmp_official = OWL_PATH.with_suffix(".owl.build_tmp")
        shutil.copy2(built_owl, tmp_official)
        os.replace(tmp_official, OWL_PATH)
        report["replaced"] = True

        # 重建 anatomy
        env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            [sys.executable, "scripts/build/generate_ontology_anatomy.py"],
            cwd=ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        report["anatomy_rebuilt"] = proc.returncode == 0
        if proc.returncode != 0:
            report["error"] = ("OWL 已替换但 anatomy 重建失败："
                               + _sanitize(proc.stderr or "", sandbox)[-300:])
            return _finish(report, 1)
        return _finish(report, 0)
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def _finish(report: dict, code: int) -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(REPORT), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    out = sys.stdout.buffer
    stats = report.get("statistics", {})
    msg = ("build_ontology: %s triples=%s classes=%s OP=%s DP=%s AP=%s align=%s "
           "isomorphic_to_current=%s replaced=%s\n" % (
               "PASS" if code == 0 else "FAIL",
               stats.get("triples"), stats.get("classes"),
               stats.get("object_properties"), stats.get("datatype_properties"),
               stats.get("annotation_properties"), stats.get("formal_alignments"),
               report.get("isomorphic_to_current"), report.get("replaced")))
    out.write(msg.encode("utf-8"))
    if report.get("error"):
        out.write((report["error"] + "\n").encode("utf-8", errors="replace"))
    return code


if __name__ == "__main__":
    sys.exit(main())
