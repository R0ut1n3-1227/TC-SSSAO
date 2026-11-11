# -*- coding: utf-8 -*-
"""标准语义对齐应用脚本（发布构建的正式对齐步骤）。

真源关系：
    ontology/tc_sssao_alignments.ttl  = 标准语义对齐的唯一真源（人工可审计）；
    本脚本                        = 构建过程：从 ontology/tc_sssao.owl 移除语义上不成立
                                    的映射与失效声明，合并对齐模块，并执行图级
                                    一致性校验。

操作内容：
  A. 移除 2 条语义不成立的正式映射：
       hasObservationResult  ⊑ sosa:hasResult
       hasFeatureOfInterest  ⊑ sosa:hasFeatureOfInterest
  B. 移除 2 条随之失效的外部术语伪声明：
       sosa:hasResult / sosa:hasFeatureOfInterest a owl:ObjectProperty
  C. 移除 2 条概念错位的注解：
       ObservationData seeAlso sosa:Observation（数据≠观测活动）
       SpaceEvent seeAlso time:Instant + SpaceEvent reusedOntology time:
       （SpaceEvent 是领域事件，不是时间实体）
     以及 geo:asWKT 的本地伪声明（geo:asWKT 在主本体中仅作 seeAlso 注解值
     出现，注解值无需 DL 实体声明；geo:wktLiteral 仍被 rdfs:range /
     owl:someValuesFrom 逻辑位置使用，其 rdfs:Datatype 声明保留）。
  D. 合并 ontology/tc_sssao_alignments.ttl（排除模块自身的 owl:Ontology 头），
     并在主本体头加 rdfs:seeAlso 指向对齐模块 IRI（溯源链接，非 owl:imports）。

校验（构建即验证，任一失败即非零退出且不写回；描述性检查名）：
  alignment_inclusions_present  所有模块三元组（除模块头）均已并入主图；
  removed_alignments_absent     全部移除三元组均不存在；
  no_owl_imports                全图无 owl:imports；
  no_external_equivalent_axioms 无涉及外部术语的 owl:equivalentClass / owl:equivalentProperty；
  no_cross_type_subproperty     无 ObjectProperty↔DatatypeProperty 跨类型 subPropertyOf；
  external_terms_declared       外部术语（time/sosa/ssn/prov/geo）在逻辑位置出现时均有 OWL 2 DL
     实体声明（owl:Class / owl:ObjectProperty / owl:DatatypeProperty /
     rdfs:Datatype）；注解值（seeAlso 等）不要求声明。

用法：
    python scripts/build/apply_standard_alignments.py           # 应用对齐并写回
    python scripts/build/apply_standard_alignments.py --check   # 只校验当前文件状态

报告：data/current/standard_alignment_application.json
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[2]
OWL_PATH = ROOT / "ontology" / "tc_sssao.owl"
MODULE_PATH = ROOT / "ontology" / "tc_sssao_alignments.ttl"
REPORT_PATH = ROOT / "data" / "current" / "standard_alignment_application.json"

ONTO = "https://w3id.org/tc-sssao#"
MAIN_ONTOLOGY_IRI = URIRef("https://w3id.org/tc-sssao")
MODULE_IRI = URIRef("https://w3id.org/tc-sssao/alignments")


def u(local: str) -> URIRef:
    return URIRef(ONTO + local)


TIME = "http://www.w3.org/2006/time#"
SOSA = "http://www.w3.org/ns/sosa/"
SSN = "http://www.w3.org/ns/ssn/"
PROV = "http://www.w3.org/ns/prov#"
GEO = "http://www.opengis.net/ont/geosparql#"
EXT_NAMESPACES = {"OWL-Time": TIME, "SOSA": SOSA, "SSN": SSN,
                  "PROV-O": PROV, "GeoSPARQL": GEO}

# (subject, predicate, object, 移除依据)
REMOVALS = [
    (u("hasObservationResult"), RDFS.subPropertyOf, URIRef(SOSA + "hasResult"),
     "domain ObservationData / range SpaceObject，与 SOSA Observation→Result 语义不一致"),
    (u("hasFeatureOfInterest"), RDFS.subPropertyOf, URIRef(SOSA + "hasFeatureOfInterest"),
     "domain SSAData（数据→目标），SOSA hasFeatureOfInterest 用于观测活动，层次不同"),
    (URIRef(SOSA + "hasResult"), RDF.type, OWL.ObjectProperty,
     "映射移除后该伪声明失效"),
    (URIRef(SOSA + "hasFeatureOfInterest"), RDF.type, OWL.ObjectProperty,
     "映射移除后该伪声明失效"),
    (u("ObservationData"), RDFS.seeAlso, URIRef(SOSA + "Observation"),
     "ObservationData 是观测结果而非观测活动，改以 ⊑ sosa:Result 正式对齐"),
    (u("SpaceEvent"), RDFS.seeAlso, URIRef(TIME + "Instant"),
     "SpaceEvent 是领域事件而非时间实体"),
    (u("SpaceEvent"), u("reusedOntology"), URIRef(TIME),
     "随 SpaceEvent seeAlso time:Instant 一并移除（该复用声明仅依附于被移除映射）"),
    (URIRef(GEO + "asWKT"), RDF.type, OWL.DatatypeProperty,
     "geo:asWKT 在主本体中仅作 seeAlso 注解值出现（注解值无需 DL 实体声明），"
     "不保留本地伪声明；geo:wktLiteral 仍被 rdfs:range/owl:someValuesFrom 逻辑"
     "位置使用，声明保留"),
]

LOGICAL_PREDICATES = {RDFS.subClassOf, RDFS.subPropertyOf,
                      RDFS.domain, RDFS.range}
DECLARATION_TYPES = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
                     OWL.AnnotationProperty, RDFS.Datatype, OWL.Restriction}


def _is_ext(term) -> bool:
    return isinstance(term, URIRef) and any(
        str(term).startswith(ns) for ns in EXT_NAMESPACES.values())


def run(check_only: bool) -> int:
    g = Graph()
    g.parse(str(OWL_PATH), format="xml")
    before = len(g)

    report: dict = {
        "step": "标准语义对齐应用（apply_standard_alignments.py）",
        "check_only": check_only,
        "owl": "ontology/tc_sssao.owl",
        "module": "ontology/tc_sssao_alignments.ttl",
        "triples_before": before,
        "removals": [],
        "verifications": {},
    }

    # ---------- A/B/C：移除 ----------
    for s, p, o, why in REMOVALS:
        present = (s, p, o) in g
        report["removals"].append({
            "triple": [str(s), str(p), str(o)],
            "was_present": present,
            "reason": why,
        })
        if present and not check_only:
            g.remove((s, p, o))

    # ---------- D：合并对齐模块 ----------
    mod = Graph()
    mod.parse(str(MODULE_PATH), format="turtle")
    module_axioms = [t for t in mod if t[0] != MODULE_IRI]
    report["module_triples_total"] = len(mod)
    report["module_axioms_to_merge"] = len(module_axioms)
    if not check_only:
        for t in module_axioms:
            g.add(t)
        # 主本体头溯源链接（注解，非 owl:imports）
        g.add((MAIN_ONTOLOGY_IRI, RDFS.seeAlso, MODULE_IRI))

    # ---------- 校验 ----------
    fails: list[str] = []

    # 检查：对齐模块三元组全部并入
    missing = [t for t in module_axioms if t not in g]
    report["verifications"]["alignment_inclusions_present"] = {
        "pass": not missing, "missing_count": len(missing)}
    if missing:
        fails.append("alignment_inclusions_present: %d 条模块三元组未并入" % len(missing))

    # 检查：移除项全部不存在
    still = [r["triple"] for r in report["removals"]
             if (URIRef(r["triple"][0]), URIRef(r["triple"][1]),
                 URIRef(r["triple"][2])) in g]
    report["verifications"]["removed_alignments_absent"] = {
        "pass": not still, "still_present": still}
    if still:
        fails.append("removed_alignments_absent: %d 条应移除三元组仍存在" % len(still))

    # 检查：无 owl:imports
    imports = list(g.triples((None, OWL.imports, None)))
    report["verifications"]["no_owl_imports"] = {
        "pass": not imports, "count": len(imports)}
    if imports:
        fails.append("no_owl_imports: 存在 owl:imports（发布构建禁止）")

    # 检查：无 equivalentClass / equivalentProperty 涉及外部术语
    # （本体内部 sensor 分类法等价公理属既有设计，不在本检查范围）
    equiv = [(s, p, o) for s, p, o in
             list(g.triples((None, OWL.equivalentClass, None))) +
             list(g.triples((None, OWL.equivalentProperty, None)))
             if _is_ext(s) or _is_ext(o)]
    report["verifications"]["no_external_equivalent_axioms"] = {
        "pass": not equiv, "count": len(equiv),
        "note": "仅检查涉及 time/sosa/ssn/prov/geo 外部术语的等价公理；"
                "本体内部 equivalentClass（如 GroundRadarSensor 限制式定义）不属本检查范围"}
    if equiv:
        fails.append("no_external_equivalent_axioms: 存在涉及外部术语的 owl:equivalentClass/equivalentProperty")

    # 检查：无跨类型 subPropertyOf（ObjectProperty↔DatatypeProperty）
    cross = []
    for s, o in g.subject_objects(RDFS.subPropertyOf):
        s_obj = (s, RDF.type, OWL.ObjectProperty) in g
        s_data = (s, RDF.type, OWL.DatatypeProperty) in g
        o_obj = (o, RDF.type, OWL.ObjectProperty) in g
        o_data = (o, RDF.type, OWL.DatatypeProperty) in g
        if (s_obj and o_data) or (s_data and o_obj):
            cross.append((str(s), str(o)))
    report["verifications"]["no_cross_type_subproperty"] = {
        "pass": not cross, "cross_pairs": cross}
    if cross:
        fails.append("no_cross_type_subproperty: 存在跨类型 subPropertyOf: %s" % cross)

    # 检查：外部术语 DL 声明完整性（仅逻辑位置）
    undeclared: dict[str, list[str]] = {}
    for s, p, o in g:
        for term in (s, o):
            if not _is_ext(term):
                continue
            in_logical = (p in LOGICAL_PREDICATES) or (p == RDF.type)
            if not in_logical:
                continue
            if p == RDF.type and isinstance(o, URIRef) and \
                    str(o).startswith(str(OWL)):
                # (ext, rdf:type, owl:Xxx) 即声明本身
                continue
            if not any((term, RDF.type, dt) in g for dt in DECLARATION_TYPES):
                undeclared.setdefault(str(term), []).append(str(p))
    report["verifications"]["external_terms_declared"] = {
        "pass": not undeclared,
        "undeclared": {k: sorted(set(v)) for k, v in undeclared.items()}}
    if undeclared:
        fails.append("external_terms_declared: 外部术语缺少 DL 声明: %s" % sorted(undeclared))

    report["triples_after"] = len(g)
    report["overall_pass"] = not fails
    report["failures"] = fails

    # ---------- 写回 ----------
    if not check_only and not fails:
        g.serialize(destination=str(OWL_PATH), format="xml")
        report["written"] = True
    else:
        report["written"] = False

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(REPORT_PATH), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=1))

    out = sys.stdout.buffer
    out.write(("triples %d -> %d (module axioms merged: %d, removals: %d)\n" % (
        before, len(g), len(module_axioms),
        sum(1 for r in report["removals"] if r["was_present"]))).encode("utf-8"))
    for name, v in report["verifications"].items():
        out.write(("  %s: %s\n" % (name, "PASS" if v["pass"] else "FAIL")).encode("utf-8"))
    if fails:
        out.write(("OVERALL: FAIL — %s\n" % "; ".join(fails)).encode("utf-8"))
        return 1
    out.write(b"OVERALL: PASS%s\n" % (b" (check only, not written)" if check_only else b""))
    return 0


if __name__ == "__main__":
    sys.exit(run("--check" in sys.argv))
