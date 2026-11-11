# -*- coding: utf-8 -*-
"""M5 Phase 2：发布模式范围检查（release schema scope check）。

判定（全部满足才 PASS）：
  S1 收敛后 OWL 中每个本地术语（类/对象属性/数据属性/注解属性）都出现在
     M5P2 决策清单中，且 action ∈ {KEEP, KEEP_AS_SCHEMA_EXTENSION}
     ——零未声明术语、零 DELETE 术语残留；
  S2 全部 KEEP_AS_SCHEMA_EXTENSION 术语均在
     data/decisions/schema_extension_justification.csv 中有逐条保留理由；
  S3 OWL 中无任何 owl:deprecated 标注（弃用走直接收敛，不打弃用标）；
  S4 OWL 术语集合与概念审计分类完全一致：
     ACTIVE_CORE + STANDARD_ALIGNED + SCHEMA_EXTENSION，
     DEAD=0 / DEPRECATION=0；
  S5 对齐模块引用的本地术语全部在发布模式中（无悬空对齐）。

输出：data/current/release_schema_scope_check.json；PASS 退出码 0。
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[2]
OWL_PATH = ROOT / "ontology" / "tc_sssao.owl"
ALIGN_PATH = ROOT / "ontology" / "tc_sssao_alignments.ttl"
DECISIONS = ROOT / "data" / "decisions" / "concept_decisions.json"
AUDIT = ROOT / "data" / "decisions" / "concept_usage_audit_final.json"
JUST_CSV = ROOT / "data" / "decisions" / "schema_extension_justification.csv"
OUT = ROOT / "data" / "current" / "release_schema_scope_check.json"

ONTO = "https://w3id.org/tc-sssao#"

DECL_TYPES = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
              OWL.AnnotationProperty)


def ln(uri: str) -> str:
    return uri[len(ONTO):] if uri.startswith(ONTO) else uri


def main() -> int:
    g = Graph()
    g.parse(str(OWL_PATH), format="xml")
    dec = json.load(io.open(str(DECISIONS), encoding="utf-8"))
    audit = json.load(io.open(str(AUDIT), encoding="utf-8"))
    just_terms = set()
    with io.open(str(JUST_CSV), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            just_terms.add(row["term"])

    action = {r["local_name"]: r["action"] for r in dec["rows"]}
    audit_cls = {r["local_name"]: r["decision"] for r in audit["rows"]}

    owl_terms = sorted({ln(str(s)) for s in g.subjects(RDF.type, None)
                        if str(s).startswith(ONTO)
                        and any((s, RDF.type, t) in g for t in DECL_TYPES)})

    # S1
    undeclared = [t for t in owl_terms if t not in action]
    deleted_present = [t for t in owl_terms if action.get(t) == "DELETE"]
    s1 = not undeclared and not deleted_present

    # S2
    ext_missing_just = sorted(t for t, a in action.items()
                              if a == "KEEP_AS_SCHEMA_EXTENSION"
                              and t not in just_terms)
    just_stale = sorted(t for t in just_terms
                        if action.get(t) != "KEEP_AS_SCHEMA_EXTENSION")
    s2 = not ext_missing_just and not just_stale

    # S3
    deprecated = sorted({ln(str(s)) for s in g.subjects(OWL.deprecated, None)
                         if str(s).startswith(ONTO)})
    s3 = not deprecated

    # S4
    by_audit = {}
    for t in owl_terms:
        by_audit.setdefault(audit_cls.get(t, "NOT_IN_AUDIT"), []).append(t)
    dead = by_audit.get("DEAD", [])
    depr = by_audit.get("DEPRECATION", [])
    not_in_audit = by_audit.get("NOT_IN_AUDIT", [])
    audit_terms = set(audit_cls)
    owl_set = set(owl_terms)
    audit_not_in_owl = sorted(audit_terms - owl_set)
    s4 = not dead and not depr and not not_in_audit and not audit_not_in_owl

    # S5
    ga = Graph()
    ga.parse(str(ALIGN_PATH), format="turtle")
    dangling_align = sorted({ln(str(s)) for s in ga.subjects()
                             if isinstance(s, URIRef)
                             and str(s).startswith(ONTO)
                             and ln(str(s)) not in owl_set})
    s5 = not dangling_align

    checks = {
        "S1_all_terms_declared_kept": {
            "pass": s1, "owl_term_count": len(owl_terms),
            "undeclared": undeclared, "deleted_still_present": deleted_present},
        "S2_extension_justification_complete": {
            "pass": s2,
            "extension_terms": sum(1 for a in action.values()
                                   if a == "KEEP_AS_SCHEMA_EXTENSION"),
            "missing_justification": ext_missing_just,
            "justification_for_non_extension": just_stale},
        "S3_no_deprecated_annotation": {
            "pass": s3, "deprecated_terms": deprecated},
        "S4_schema_audit_consistent": {
            "pass": s4,
            "ACTIVE_CORE": len(by_audit.get("ACTIVE_CORE", [])),
            "STANDARD_ALIGNED": len(by_audit.get("STANDARD_ALIGNED", [])),
            "SCHEMA_EXTENSION": len(by_audit.get("SCHEMA_EXTENSION", [])),
            "DEAD": len(dead), "DEPRECATION": len(depr),
            "not_in_audit": not_in_audit,
            "audit_terms_missing_in_owl": audit_not_in_owl},
        "S5_no_dangling_alignment": {
            "pass": s5, "dangling_terms": dangling_align},
    }
    overall = all(c["pass"] for c in checks.values())
    doc = {
        "spec": "M5 Phase 2：发布模式范围检查",
        "scope_definition": ("发布模式 = M5P2 决策清单中 KEEP/KEEP_AS_SCHEMA_EXTENSION "
                             "术语；每个术语必须是 ACTIVE_CORE/STANDARD_ALIGNED 或具"
                             "显式扩展保留理由；零弃用标注；零悬空对齐"),
        "checks": checks,
        "status": "PASS" if overall else "FAIL",
    }
    io.open(str(OUT), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))

    out = sys.stdout.buffer
    for name, c in checks.items():
        out.write(("%s %s\n" % ("PASS" if c["pass"] else "FAIL", name)
                   ).encode("utf-8"))
    out.write(("terms=%d status=%s\n" % (len(owl_terms), doc["status"])
               ).encode("utf-8"))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
