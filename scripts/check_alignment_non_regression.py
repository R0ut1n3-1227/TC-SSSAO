# -*- coding: utf-8 -*-
"""M5 spec 第 31 节：标准对齐非回归检查（M5P1 + M5P2 双阶段口径）。

对照图：
  before = data/baselines/tc_sssao_pre_alignment_baseline.owl（M4 锁定态）
  after  = ontology/tc_sssao.owl（M5 对齐补丁 + M5P2 schema 收敛后）

判定标准（全部满足才 PASS）：
  A1 删除集合 ⊆ M5P1 允许的 10 条移除 ∪ M5P2 决策清单
     （concept_decisions.json 中 action=DELETE 的术语所接触的
     全部三元组）；
  A2 新增集合 ⊆ 对齐模块三元组（ontology/tc_sssao_alignments.ttl，除模块头）
     + 主本体头溯源 seeAlso（bnode 三元组单独处理）；
  A3 核心关系公理零变化：R1—R18/B1—B5 相关的保留 onto: 属性定义、
     保留术语间的类层级（subClassOf/subPropertyOf）、逆属性声明在
     before/after 完全一致（core_relations_changed == 0）；
     接触 DELETE 术语的层级三元组属计划内移除，不计入变化；
  A4 全部 KEEP/KEEP_AS_SCHEMA_EXTENSION 术语的声明在 after 中保留，
     且全部 DELETE 术语的声明在 after 中不存在；
  A5 after 中无孤儿 bnode、无引用 DELETE 术语的 bnode 三元组、
     无成员数 <2 的 AllDisjointClasses 结构。

输出：data/current/alignment_non_regression.json；PASS 退出码 0。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
BEFORE_PATH = ROOT / "data" / "baselines" / "tc_sssao_pre_alignment_baseline.owl"
AFTER_PATH = ROOT / "ontology" / "tc_sssao.owl"
MODULE_PATH = ROOT / "ontology" / "tc_sssao_alignments.ttl"
OUT = ROOT / "data" / "current" / "alignment_non_regression.json"

ONTO = "https://w3id.org/tc-sssao#"
MAIN_ONTOLOGY_IRI = URIRef("https://w3id.org/tc-sssao")
MODULE_IRI = URIRef("https://w3id.org/tc-sssao/alignments")

TIME = "http://www.w3.org/2006/time#"
SOSA = "http://www.w3.org/ns/sosa/"
GEO = "http://www.opengis.net/ont/geosparql#"


def u(local: str) -> URIRef:
    return URIRef(ONTO + local)


# spec 第 4 节允许的移除清单（M5P1 已执行的失效映射移除）
ALLOWED_REMOVALS = {
    (u("hasObservationResult"), RDFS.subPropertyOf, URIRef(SOSA + "hasResult")),
    (u("hasFeatureOfInterest"), RDFS.subPropertyOf, URIRef(SOSA + "hasFeatureOfInterest")),
    (URIRef(SOSA + "hasResult"), RDF.type, OWL.ObjectProperty),
    (URIRef(SOSA + "hasFeatureOfInterest"), RDF.type, OWL.ObjectProperty),
    (u("ObservationData"), RDFS.seeAlso, URIRef(SOSA + "Observation")),
    (u("SpaceEvent"), RDFS.seeAlso, URIRef(TIME + "Instant")),
    (u("SpaceEvent"), u("reusedOntology"), URIRef(TIME)),
    (URIRef(GEO + "asWKT"), RDF.type, OWL.DatatypeProperty),
}

# 2026-09-14 Core/Extension 分层新增 onto:modelLayer 注解属性声明
# Stage 2D (2026-10-11) P1-1: 新增 onto:hasEncounterID 数据属性供 B3 跨交会隔离
ALLOWED_ADDITIONS = {
    (u("modelLayer"), RDF.type, OWL.AnnotationProperty),
    (u("hasEncounterID"), RDF.type, OWL.DatatypeProperty),
    (u("hasEncounterID"), RDFS.domain, u("SpaceEvent")),
    (u("hasEncounterID"), RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#string")),
}

DECISIONS_PATH = ROOT / "data" / "decisions" / "concept_decisions.json"


def load_deleted_terms() -> set:
    """M5P2 决策清单中 action=DELETE 的 onto: 术语 URI 集合。"""
    dec = json.load(io.open(str(DECISIONS_PATH), encoding="utf-8"))
    return {URIRef(r["iri"]) for r in dec["rows"] if r["action"] == "DELETE"}

# 与 R1—R18/B1—B5 规则语义直接相关的核心关系（其定义三元组必须零变化）
CORE_RELATIONS = [
    "precedesEvent", "followsEvent", "overlapsWithEvent",
    "causesEvent", "causedByEvent", "hasCause", "hasEffect",
    "hasCausalEvidence", "leadsToState", "stateCausedByEvent",
    "transitsTo", "transitsFrom", "degradesTo", "recoversTo",
    "hasPrimaryObject", "hasSecondaryObject", "affectsObject",
    "hasOccurrenceTime", "hasStartTime", "hasEndTime",
    "hasCollisionProbability", "hasPredictedMissDistance",
    "hasCombinedHardBodyRadius", "hasSeverityRank", "hasEnvironmentLevel",
    "involvesObject", "hasOrbit", "generatesData", "generatedBy",
    "producesData", "generatedByActivity", "detectedFromData",
    "supportedByData", "producesRisk", "riskLeadsToState",
    "requiresResponseMeasure", "mitigatesRisk", "respondsToEvent",
]


def graph_only_uri_triples(g: Graph) -> set:
    """仅保留主谓宾均为 URIRef 的三元组（bnode/字面量另行处理）。"""
    return {t for t in g if all(isinstance(x, URIRef) for x in t)}


def graph_bnode_triples(g: Graph) -> set:
    """涉及匿名节点（bnode）的三元组：限制、互斥组、列表等匿名结构。"""
    return {t for t in g if any(isinstance(x, BNode) for x in t)}


def main() -> int:
    before = Graph()
    before.parse(str(BEFORE_PATH), format="xml")
    after = Graph()
    after.parse(str(AFTER_PATH), format="xml")
    module = Graph()
    module.parse(str(MODULE_PATH), format="turtle")

    b_uri = graph_only_uri_triples(before)
    a_uri = graph_only_uri_triples(after)
    removed = b_uri - a_uri
    added = a_uri - b_uri

    allowed_added = {t for t in module
                     if t[0] != MODULE_IRI and all(isinstance(x, URIRef) for x in t)}
    allowed_added.add((MAIN_ONTOLOGY_IRI, RDFS.seeAlso, MODULE_IRI))
    # 2026-09-14 Core/Extension 分层：onto:modelLayer 注解属性声明为允许新增
    allowed_added.update(ALLOWED_ADDITIONS)

    # A1 删除均在允许清单（M5P1 白名单 ∪ M5P2 DELETE 术语接触的三元组）
    deleted_terms = load_deleted_terms()

    def touches_deleted(t):
        return any(x in deleted_terms for x in t)

    unexpected_removed = {t for t in removed
                          if t not in ALLOWED_REMOVALS
                          and not touches_deleted(t)}
    m5p1_removed = len(removed & ALLOWED_REMOVALS)
    m5p2_removed = sum(1 for t in removed
                       if t not in ALLOWED_REMOVALS and touches_deleted(t))
    a1 = not unexpected_removed

    # A2 新增均在允许集合
    unexpected_added = added - allowed_added
    a2 = not unexpected_added

    # A3 核心关系定义零变化：以核心关系为主语的全部 URI 三元组；
    # 白名单内的三元组（模块对齐注解/子属性声明，如 hasCausalEvidence⊑prov:
    # wasDerivedFrom、precedesEvent seeAlso time:before）在比较时应从
    # 两侧同时排除，以避免将基线中已有的whitelist条目误报为"删除"。
    core_changed = []
    for rel in CORE_RELATIONS:
        s = u(rel)
        b_rel = {t for t in b_uri if t[0] == s and t not in allowed_added}
        a_rel = {t for t in a_uri if t[0] == s and t not in allowed_added}
        if b_rel != a_rel:
            core_changed.append({
                "relation": rel,
                "removed": sorted(map(str, b_rel - a_rel)),
                "added": sorted(map(str, a_rel - b_rel)),
            })
    # 核心类层级（保留术语间的 onto 内部 subClassOf）零变化；
    # 接触 DELETE 术语的层级三元组属计划内移除
    def onto_internal_hierarchy(gset):
        return {t for t in gset
                if t[1] in (RDFS.subClassOf, RDFS.subPropertyOf)
                and str(t[0]).startswith(ONTO) and str(t[2]).startswith(ONTO)
                and t[0] not in deleted_terms and t[2] not in deleted_terms}
    hier_diff = (onto_internal_hierarchy(b_uri) - onto_internal_hierarchy(a_uri)) | \
        (onto_internal_hierarchy(a_uri) - onto_internal_hierarchy(b_uri))
    a3 = not core_changed and not hier_diff

    # A4 保留术语声明不得丢失；DELETE 术语声明不得存在
    def onto_declarations(gset):
        return {t[0] for t in gset if t[1] == RDF.type
                and str(t[0]).startswith(ONTO)
                and t[2] in (OWL.Class, OWL.ObjectProperty,
                             OWL.DatatypeProperty, OWL.AnnotationProperty)}
    lost_declarations = (onto_declarations(b_uri) - onto_declarations(a_uri)) \
        - deleted_terms
    surviving_deleted = onto_declarations(a_uri) & deleted_terms
    a4 = not lost_declarations and not surviving_deleted

    # A5 bnode 结构健全性（after）：无孤儿、无 DELETE 术语引用、
    # 无成员 <2 的 AllDisjointClasses
    ref_after = {s for s, p, o in after}
    orphan_bnodes = sorted(str(bn) for bn in set(after.subjects())
                           if isinstance(bn, BNode) and bn not in ref_after)
    bnode_deleted_refs = sorted(
        "%s -%s-> %s" % (s, p, o) for s, p, o in graph_bnode_triples(after)
        if any(x in deleted_terms for x in (s, p, o)))
    bad_disjoint = []
    for hd in after.subjects(OWL.members, None):
        for ml in after.objects(hd, OWL.members):
            n = 0
            cur = ml
            while isinstance(cur, BNode):
                first = list(after.objects(cur, RDF.first))
                if first:
                    n += 1
                nxt = list(after.objects(cur, RDF.rest))
                cur = nxt[0] if nxt else None
            if n < 2:
                bad_disjoint.append(str(hd))
    a5 = not (orphan_bnodes or bnode_deleted_refs or bad_disjoint)

    doc = {
        "spec": "M5 第 31 节：标准对齐非回归检查（M5P1+M5P2 双阶段口径）",
        "before": "data/baselines/tc_sssao_pre_alignment_baseline.owl",
        "after": "ontology/tc_sssao.owl",
        "triples_before": len(before),
        "triples_after": len(after),
        "removed_count": len(removed),
        "removed_m5p1_whitelist": m5p1_removed,
        "removed_m5p2_pruning": m5p2_removed,
        "added_count": len(added),
        "checks": {
            "A1_removals_within_allowed": {
                "pass": a1,
                "unexpected_removed": sorted(map(str, unexpected_removed)),
            },
            "A2_additions_within_module": {
                "pass": a2,
                "unexpected_added": sorted(map(str, unexpected_added)),
            },
            "A3_core_relations_changed": {
                "pass": a3,
                "core_relations_changed": len(core_changed),
                "hierarchy_axioms_changed": len(hier_diff),
                "details": core_changed,
                "hierarchy_diff": sorted(map(str, hier_diff)),
            },
            "A4_declarations_consistent": {
                "pass": a4,
                "lost_kept_declarations": sorted(map(str, lost_declarations)),
                "surviving_deleted_declarations":
                    sorted(map(str, surviving_deleted)),
            },
            "A5_bnode_structures_sound": {
                "pass": a5,
                "orphan_bnodes": orphan_bnodes,
                "bnode_refs_to_deleted": bnode_deleted_refs,
                "degenerate_disjoint_structures": bad_disjoint,
            },
        },
    }
    overall = a1 and a2 and a3 and a4 and a5
    doc["overall_pass"] = overall
    doc["core_relations_changed_total"] = len(core_changed) + len(hier_diff)
    # spec 第 31 节要求的顶层判定键：
    #   core_relations_changed = 0 / new_standard_alignment_triples = N / status = PASS
    doc["core_relations_changed"] = doc["core_relations_changed_total"]
    doc["new_standard_alignment_triples"] = len(added)
    doc["status"] = "PASS" if overall else "FAIL"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(str(OUT), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))

    out = sys.stdout.buffer
    for name, c in doc["checks"].items():
        out.write(("%s %s\n" % ("PASS" if c["pass"] else "FAIL", name)).encode("utf-8"))
    out.write(("core_relations_changed=%d new_standard_alignment_triples=%d status=%s\n" % (
        doc["core_relations_changed"], doc["new_standard_alignment_triples"],
        doc["status"])).encode("utf-8"))
    if not overall:
        out.write(json.dumps(doc["checks"], ensure_ascii=False, indent=1).encode("utf-8"))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
