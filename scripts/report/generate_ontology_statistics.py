"""从 canonical OWL 自动统计本体规模并与论文 4.2.1 口径对照。

    python scripts/report/generate_ontology_statistics.py

输出 data/current/ontology_statistics.json；统计值唯一来源是 ontology/tc_sssao.owl 本身，
EXPECTED 为论文 4.2.1 正文镜像值——漂移即 FAIL（论文不得沿用历史统计）。
口径：仅计 TC-SSSAO 命名空间（https://w3id.org/tc-sssao#）内的命名术语；
外部标准本体的 DL 声明（time/sosa/prov/geo 等）单独列出，不计入论文口径。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Graph, RDF, OWL, URIRef, BNode

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "current" / "ontology_statistics.json"

ONTO = "https://w3id.org/tc-sssao#"

# 论文 4.2.1 正文口径（唯一允许的来源是本脚本对最终 OWL 的实测）
# 2026-09-06 终审 schema 修复重钉（归因）：1909→1873。删除全部状态类上
# transitsTo/transitsFrom/degradesTo/recoversTo 存在性限制共 9 条（−36 三元组）：
# 原公理断言"每个状态实例必然发生固定方向转移"，与 B3 条件式演化冲突；
# 规则逻辑与属性定义未动。详见 temporal_causal_state.py 与 build_ontology.py
# EXPECTED_STATS 的归因注释。
# 2026-09-14 规则元数据与领域本体分离重构：删除 ConstraintRule 及
# Axiom_R1–R18（6+18=24 个类）；本体不再将 R1–R18 输出为 owl:Class，
# R1–R18 规则定义仍保留在 rules/tc_sssao_rules.ttl 与 axioms.py。
# 2026-09-14 SituationState 层级简化：删除 ComprehensiveSituationState
#（−1 命名类）；四状态加 hasValue 限制与 maxCardinality 1，净 −1 类 +16 三元组。
# 2026-09-14 Core/Extension 分层：扩展类 14 个新增 onto:modelLayer annotation，
# annotation_properties 11→12，triples 1606→1694。
EXPECTED = {
    "named_classes": 86,
    "anonymous_class_expressions": 1,
    "object_properties": 65,
    "datatype_properties": 68,    # Stage 2D: +1 hasEncounterID (P1-1)
    "ontology_triples": 1703,     # +9: DP def + SpaceEvent restriction
}


def main() -> int:
    g = Graph()
    g.parse(ROOT / "ontology" / "tc_sssao.owl", format="xml")

    def _onto_subjects(rdf_type) -> set:
        return {s for s in g.subjects(RDF.type, rdf_type)
                if isinstance(s, URIRef) and str(s).startswith(ONTO)}

    def _ext_subjects(rdf_type) -> set:
        return {s for s in g.subjects(RDF.type, rdf_type)
                if isinstance(s, URIRef) and not str(s).startswith(ONTO)}

    stats = {
        "named_classes": len(_onto_subjects(OWL.Class)),
        "anonymous_class_expressions": len({s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, BNode)}),
        "object_properties": len(_onto_subjects(OWL.ObjectProperty)),
        "datatype_properties": len(_onto_subjects(OWL.DatatypeProperty)),
        "ontology_triples": len(g),
    }
    external_declarations = {
        "classes": len(_ext_subjects(OWL.Class)),
        "object_properties": len(_ext_subjects(OWL.ObjectProperty)),
        "datatype_properties": len(_ext_subjects(OWL.DatatypeProperty)),
    }
    checks = {k: {"computed": stats[k], "paper_4_2_1": EXPECTED[k], "match": stats[k] == EXPECTED[k]}
              for k in EXPECTED}
    ok = all(c["match"] for c in checks.values())
    doc = {
        "source": "ontology/tc_sssao.owl",
        "method": "rdflib, ONTO 命名空间口径: named=IRI rdf:type owl:Class 且 IRI 属于 "
                  "https://w3id.org/tc-sssao#; anonymous=BNode rdf:type owl:Class; "
                  "object/datatype=同口径 owl:ObjectProperty/DatatypeProperty; triples=len(graph); "
                  "外部标准本体 DL 声明单列，不计入论文口径",
        "statistics": stats,
        "external_standard_declarations": external_declarations,
        "checks": checks,
        "status": "PASS" if ok else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False), "→", doc["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
