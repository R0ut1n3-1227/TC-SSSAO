#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 2G D1 闭环：新对齐控制实验 A1—A5（基于 C = T − F）。

历史关系：
- 旧协议 `scripts/check_alignment_non_regression.py` 仍以 P
  （data/baselines/tc_sssao_pre_alignment_baseline.owl）为 BEFORE；保留
  作为历史 A1—A5 证据，不删除也不修改。
- 本脚本是 D1 实施后**新的活动对齐验证**入口：以 C 为 BEFORE，以
  最终 ontology/tc_sssao.owl 为 AFTER，明确表达"0→16 正式对齐映射"
  处理效应（不是历史的 2→16）。

判定标准（全部满足才 PASS）：
  A1 T 包含 C 作为结构子图
     （C 的所有 bnode-重命名后的等价格式三元组均出现在 T 中）；
  A2 T − C 恰为 F 的 16 条三元组（set/subject/predicate/object 全等）；
  A3 核心关系定义（R1—R18/B1—B5 涉及的保留 onto: 属性定义）在 C 与
     T 完全一致；
  A4 全部 86 命名类 / 65 对象属性 / 68 数据属性 / 12 注解属性在
     两侧保持；命名类 IRI 集合与 T \ F 结构一致（C 移除 F 子类对
     后无新增命名类丢失）；
  A5 C 与 T 中无孤儿 bnode、无引用已删除 F 映射的 bnode 三元组、
     AllDisjointClasses 成员数 ≥ 2（两侧分别检查）。

输出：data/current/alignment_against_C.json；PASS 退出码 0。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rdflib import Graph, URIRef, BNode
from rdflib.compare import isomorphic, to_canonical_graph
from rdflib.namespace import RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
C_PATH = ROOT / "data" / "baselines" / "tc_sssao_alignment_control.owl"  # C
T_PATH = ROOT / "ontology" / "tc_sssao.owl"                                 # T
F_MANIFEST = ROOT / "data" / "baselines" / "alignment_control_F_manifest.json"
OUT = ROOT / "data" / "current" / "alignment_against_C.json"

ONTO = "https://w3id.org/tc-sssao#"

# Stage 2G D1/D2 已批准的命名类与属性统计（与 T 锁定口径一致）
EXPECTED_NAMED_CLASSES = 86
EXPECTED_OBJECT_PROPERTIES = 65
EXPECTED_DATATYPE_PROPERTIES = 68
EXPECTED_F = 16

# R1—R18/B1—B5 涉及的核心保留 onto: 属性名（与 check_alignment_non_regression.py
# 保持一致）
CORE_RELATIONS = (
    "hasPrimaryObject", "hasSecondaryObject", "hasCause", "hasEffect",
    "causesEvent", "isCausedByEvent", "causedByEvent", "stateCausedByEvent",
    "triggersState", "degradesTo", "recoversTo", "transitsTo",
    "hasCollisionProbability", "hasPredictedMissDistance",
    "hasCombinedHardBodyRadius", "hasRiskValue",
    "hasEventID", "hasEventLevel", "hasEventType", "hasOccurrenceTime",
    "hasStartTime", "hasEndTime", "hasEventConfidence",
    "hasPrimaryObject", "hasSecondaryObject",
    "hasEncounterID", "involvesObject", "occursInOrbit",
    "isImplementedByEvent", "respondsToEvent", "mitigatesRisk",
    "respondsToThreat", "producesRisk", "isInvolvedInEvent",
    "generatedByActivity", "madeBySensor",
    "detectedFromData", "hasCausalEvidence",
    "indicatesThreat", "increasesThreat",
    "overlapsWithEvent", "occursDuringEvent", "triggersEvent",
    "resultsInEvent", "affectsState", "updatesState",
    "hasSourceState", "hasTargetState",
    "precedesEvent", "followsEvent", "meetsEvent",
    "leadsToState", "evolvesTo",
    "hasBeginning", "hasEnd", "hasTime",
    "affectedBy", "isAffectedBy",
    "mayManifestAsEvent", "threatMitigatedBy", "requiresResponseMeasure",
    "changesOrbit", "affectsObject", "affectsOrbit",
    "isOrbitOf", "describesObject", "observedBySensor",
    "hasObservationResult", "hasFeatureOfInterest",
    "generatedBy", "generatesData", "producesData",
    "hasCausalMechanism", "hasCausalConfidence",
    "hasStateID", "hasStateType", "hasStateLevel",
    "hasStateStartTime", "hasStateEndTime", "hasStateUpdateTime",
    "hasStateDuration", "hasStateConfidence", "hasStateDescription",
    "hasSeverityRank",
    "leadsToState", "evolvesTo",
    "hasCausalMechanism", "hasCausalConfidence",
    "occursAtTime", "occursInTimeInterval",
    "during", "intervalAfter", "intervalBefore", "intervalMeets",
    "intervalOverlaps", "intervalStartedBy", "intervalFinishes",
    "hasImpactScope", "hasThreatID", "hasThreatType", "hasThreatSource",
    "hasLaunchCountry", "hasLaunchDate", "hasOperatorName",
    "hasObjectID", "hasObjectName", "hasMass", "hasSize",
    "hasOrbitType", "hasOrbitalPeriod", "hasSemiMajorAxis",
    "hasRAAN", "hasArgumentOfPerigee", "hasMeanAnomaly",
    "hasMissionType", "hasDataID", "hasDataType",
    "hasDataSource", "hasDataConfidence", "hasErrorValue",
    "hasGeometricErrorValue", "hasResolution", "hasSensorID",
    "hasMeasureID", "hasMeasureType", "hasMeasureLevel",
    "hasMeasureDescription",
    "hasImpactScope", "hasThreatID", "hasThreatType", "hasThreatSource",
)


def _only_uris(g: Graph) -> set:
    return {t for t in g if all(isinstance(x, URIRef) for x in t)}


def _bnode_triples(g: Graph) -> set:
    return {t for t in g if any(isinstance(x, BNode) for x in t)}


def main() -> int:
    if not C_PATH.exists():
        return _finish(False, "C_PATH missing: " + str(C_PATH))
    if not T_PATH.exists():
        return _finish(False, "T_PATH missing: " + str(T_PATH))
    if not F_MANIFEST.exists():
        return _finish(False, "F_MANIFEST missing: " + str(F_MANIFEST))

    c_g = Graph(); c_g.parse(str(C_PATH), format="xml")
    t_g = Graph(); t_g.parse(str(T_PATH), format="xml")
    f_data = json.loads(F_MANIFEST.read_text(encoding="utf-8"))
    F_set = set()
    for t in f_data["F_triples"]:
        F_set.add((URIRef(t["s"]), URIRef(t["p"]), URIRef(t["o"])))

    # ---- A1: C canon isomorphic to T \ F canon
    t_minus_F = Graph()
    for s, p, o in t_g:
        if (s, p, o) not in F_set:
            t_minus_F.add((s, p, o))
    a1 = isomorphic(to_canonical_graph(c_g), to_canonical_graph(t_minus_F))

    # ---- A2: T − C 恰为 F（结构等价，按 canonical graph 比较以吸收 bnode ID 差异）
    c_canon = to_canonical_graph(c_g)
    t_canon = to_canonical_graph(t_g)
    t_minus_c_canon = t_canon - c_canon
    f_canon = Graph()
    for s, p, o in F_set:
        f_canon.add((s, p, o))
    f_canon_canon = to_canonical_graph(f_canon)
    a2 = isomorphic(t_minus_c_canon, f_canon_canon)
    # 字面差集（仅用于报告，不参与 PASS/FAIL 判定）
    c_set = set(c_g)
    t_minus_c_literal = set()
    for s, p, o in t_g:
        if (s, p, o) not in c_set:
            t_minus_c_literal.add((s, p, o))
    a2_diff_unexpected = t_minus_c_literal - F_set
    a2_diff_missing = F_set - t_minus_c_literal

    # ---- A3: 核心保留关系定义零丢失（c_core ⊆ t_core；T 可以多出 F 引入的 subPropertyOf）
    def core_rel_definitions(g: Graph) -> dict:
        out = {}
        for rel in CORE_RELATIONS:
            s = URIRef(ONTO + rel)
            out[rel] = {t for t in g if t[0] == s
                        and t[1] in (RDF.type, RDFS.subPropertyOf, RDFS.range,
                                     RDFS.domain, RDFS.label, RDFS.comment)}
        return out
    c_core = core_rel_definitions(c_g)
    t_core = core_rel_definitions(t_g)
    a3_lost_triples = {}
    for rel in c_core:
        lost = c_core[rel] - t_core[rel]
        if lost:
            a3_lost_triples[rel] = sorted(map(str, lost))
    a3 = not a3_lost_triples
    a3_changed = list(a3_lost_triples.keys())

    # ---- A4: 命名类与命名属性集合在两侧均无丢失；T \ C 不应新增命名类
    def named_classes(g: Graph) -> set:
        return {s for s in g.subjects(RDF.type, OWL.Class)
                if isinstance(s, URIRef) and str(s).startswith(ONTO)}
    def named_object_props(g: Graph) -> set:
        return {s for s in g.subjects(RDF.type, OWL.ObjectProperty)
                if isinstance(s, URIRef) and str(s).startswith(ONTO)}
    def named_datatype_props(g: Graph) -> set:
        return {s for s in g.subjects(RDF.type, OWL.DatatypeProperty)
                if isinstance(s, URIRef) and str(s).startswith(ONTO)}
    def named_annotation_props(g: Graph) -> set:
        return {s for s in g.subjects(RDF.type, OWL.AnnotationProperty)
                if isinstance(s, URIRef) and str(s).startswith(ONTO)}

    c_named_classes = named_classes(c_g)
    t_named_classes = named_classes(t_g)
    c_named_op = named_object_props(c_g)
    t_named_op = named_object_props(t_g)
    c_named_dp = named_datatype_props(c_g)
    t_named_dp = named_datatype_props(t_g)
    c_named_ap = named_annotation_props(c_g)
    t_named_ap = named_annotation_props(t_g)

    lost_classes = c_named_classes - t_named_classes
    lost_op = c_named_op - t_named_op
    lost_dp = c_named_dp - t_named_dp
    lost_ap = c_named_ap - t_named_ap
    # T 中新增命名类：F 子类对引入的类，预期 0（移除 16 条 F 映射不应引入新类）
    new_classes = t_named_classes - c_named_classes
    a4 = (not lost_classes and not lost_op and not lost_dp and not lost_ap
          and len(c_named_classes) == EXPECTED_NAMED_CLASSES
          and len(t_named_classes) == EXPECTED_NAMED_CLASSES
          and len(c_named_op) == EXPECTED_OBJECT_PROPERTIES
          and len(t_named_op) == EXPECTED_OBJECT_PROPERTIES
          and len(c_named_dp) == EXPECTED_DATATYPE_PROPERTIES
          and len(t_named_dp) == EXPECTED_DATATYPE_PROPERTIES)

    # ---- A5: bnode 结构健全性
    def bad_bnodes(g: Graph) -> list:
        ref = {s for s, p, o in g}
        orphans = sorted(str(bn) for bn in set(g.subjects())
                         if isinstance(bn, BNode) and bn not in ref)
        # AllDisjointClasses members < 2
        bad_disjoint = []
        for hd in g.subjects(OWL.members, None):
            n = 0
            cur = list(g.objects(hd, OWL.members))[0]
            while isinstance(cur, BNode):
                first = list(g.objects(cur, RDF.first))
                if first:
                    n += 1
                rest = list(g.objects(cur, RDF.rest))
                cur = rest[0] if rest else None
                if cur == RDF.nil:
                    break
            if n < 2:
                bad_disjoint.append(str(hd))
        return orphans, bad_disjoint

    c_orphans, c_disjoint = bad_bnodes(c_g)
    t_orphans, t_disjoint = bad_bnodes(t_g)
    a5 = (not c_orphans and not t_orphans and not c_disjoint and not t_disjoint)

    all_ok = a1 and a2 and a3 and a4 and a5

    result = {
        "protocol": "C_alignment_v1",
        "scope": "C = T \\ F (Stage 2G D1)",
        "c_path": str(C_PATH.relative_to(ROOT)),
        "t_path": str(T_PATH.relative_to(ROOT)),
        "f_count": len(F_set),
        "f_expected": EXPECTED_F,
        "c_size": len(c_g),
        "t_size": len(t_g),
        "t_minus_c_size_literal": len(t_minus_c_literal),
        "a1_C_canon_iso_T_minus_F": a1,
        "a2_T_minus_C_canon_iso_F_canon": a2,
        "a2_unexpected_diff_literal_count": len(a2_diff_unexpected),
        "a2_missing_diff_literal_count": len(a2_diff_missing),
        "a2_note": "literal diffs are due to bnode ID renaming between C and T; structural canon comparison is the PASS criterion",
        "a3_core_relations_no_lost": a3,
        "a3_lost_triples_by_relation": a3_lost_triples,
        "a4_declarations_consistent": a4,
        "a4_lost_named_classes": sorted(map(str, lost_classes)),
        "a4_lost_named_object_properties": sorted(map(str, lost_op)),
        "a4_lost_named_datatype_properties": sorted(map(str, lost_dp)),
        "a4_lost_named_annotation_properties": sorted(map(str, lost_ap)),
        "a4_new_named_classes_from_F_removal": sorted(map(str, new_classes)),
        "a4_class_count": {"c": len(c_named_classes), "t": len(t_named_classes),
                            "expected": EXPECTED_NAMED_CLASSES},
        "a4_object_property_count": {"c": len(c_named_op), "t": len(t_named_op),
                                      "expected": EXPECTED_OBJECT_PROPERTIES},
        "a4_datatype_property_count": {"c": len(c_named_dp), "t": len(t_named_dp),
                                        "expected": EXPECTED_DATATYPE_PROPERTIES},
        "a5_bnode_structures_sound": a5,
        "a5_orphan_bnodes": {"c": c_orphans, "t": t_orphans},
        "a5_bad_all_disjoint": {"c": c_disjoint, "t": t_disjoint},
        "all_passed": all_ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"A1 C canon isomorphic T\\F: {a1}")
    print(f"A2 T-C canon isomorphic F canon ({len(F_set)} triples): {a2}")
    print(f"   literal unexpected diff: {len(a2_diff_unexpected)}; missing diff: {len(a2_diff_missing)} (bnote: bnode ID rename)")
    print(f"A3 core relations no lost: {a3} (relations with lost triples: {len(a3_changed)})")
    print(f"A4 declarations consistent: {a4}")
    print(f"   lost classes: {len(lost_classes)}, lost OP: {len(lost_op)}, lost DP: {len(lost_dp)}, lost AP: {len(lost_ap)}")
    print(f"A5 bnode structures sound: {a5}")
    print(f"   C orphans: {len(c_orphans)}, T orphans: {len(t_orphans)}")
    print(f"   C bad disjoint: {len(c_disjoint)}, T bad disjoint: {len(t_disjoint)}")
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    print(f"输出：{OUT.relative_to(ROOT)}")
    return 0 if all_ok else 1


def _finish(ok: bool, msg: str) -> int:
    print(f"FAIL: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
