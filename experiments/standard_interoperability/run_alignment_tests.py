# -*- coding: utf-8 -*-
"""M5 Phase 1 spec 第 12 节：标准互操作测试 T1—T4。

对 ontology/tc_sssao.owl（已并入 tc_sssao_alignments.ttl 对齐模块）+ 各标准
合成测试数据做 RDFS 闭包，断言标准词汇类型/属性推断按预期产生。

  T1 OWL-Time   time_alignment.ttl
  T2 SOSA/SSN   sosa_alignment.ttl
  T3 PROV-O     prov_alignment.ttl
  T4 GeoSPARQL  geosparql_alignment.ttl

另含 REMOVED 组负向检查：确认已移除的错误映射不在 schema 中
（防止回归，与 scripts/build/apply_standard_alignments.py 的
removed_alignments_absent 检查互补）。

输出：
  experiments/standard_interoperability/outputs/standard_alignment_test_results.json
  experiments/standard_interoperability/outputs/standard_alignment_test_results.csv

退出码：全部通过 0，否则 1。
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import owlrl
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCHEMA = ROOT / "ontology" / "tc_sssao.owl"
OUT_DIR = HERE / "outputs"

ONTO = "https://w3id.org/tc-sssao#"
TIME = "http://www.w3.org/2006/time#"
SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"
GEO = "http://www.opengis.net/ont/geosparql#"
OWL = "http://www.w3.org/2002/07/owl#"


def o(local: str) -> URIRef:
    return URIRef(ONTO + local)


# (test_id, 数据文件, [(检查名, 期望三元组, 期望是否在闭包后出现)])
TESTS = [
    ("T1_OWL-Time", "temporal_alignment.ttl", [
        ("TimeInstant_infers_time_Instant",
         (o("InteropInstant_A"), RDF.type, URIRef(TIME + "Instant")), True),
        ("TimeInterval_infers_time_Interval",
         (o("InteropInterval_A"), RDF.type, URIRef(TIME + "Interval")), True),
        ("occursAtTime_infers_time_hasTime",
         (o("InteropEvent_A"), URIRef(TIME + "hasTime"), o("InteropInstant_A")), True),
        ("occursInTimeInterval_infers_time_hasTime",
         (o("InteropEvent_B"), URIRef(TIME + "hasTime"), o("InteropInterval_A")), True),
    ]),
    ("T2_SOSA_SSN", "sosa_alignment.ttl", [
        ("Sensor_subclass_infers_sosa_Sensor",
         (o("InteropRadar"), RDF.type, URIRef(SOSA + "Sensor")), True),
        ("ObservationActivity_infers_sosa_Observation",
         (o("InteropObsAct"), RDF.type, URIRef(SOSA + "Observation")), True),
        ("madeBySensor_infers_sosa_madeBySensor",
         (o("InteropObsAct"), URIRef(SOSA + "madeBySensor"), o("InteropRadar")), True),
        ("ObservationData_infers_sosa_Result",
         (o("InteropObsData"), RDF.type, URIRef(SOSA + "Result")), True),
        ("ObservationData_infers_prov_Entity_via_SSAData",
         (o("InteropObsData"), RDF.type, URIRef(PROV + "Entity")), True),
        # spec 第 12 节 T2 负向：本地属性不再错误生成 SOSA 关系
        ("hasObservationResult_does_not_infer_sosa_hasResult",
         (o("InteropObsData"), URIRef(SOSA + "hasResult"), o("InteropSatTarget")), False),
        ("hasFeatureOfInterest_does_not_infer_sosa_hasFeatureOfInterest",
         (o("InteropObsData"), URIRef(SOSA + "hasFeatureOfInterest"), o("InteropSatTarget")), False),
    ]),
    ("T3_PROV-O", "prov_alignment.ttl", [
        ("SSAData_subclass_infers_prov_Entity",
         (o("InteropData"), RDF.type, URIRef(PROV + "Entity")), True),
        ("SSAActivity_subclass_infers_prov_Activity",
         (o("InteropActivity"), RDF.type, URIRef(PROV + "Activity")), True),
        ("DataProvider_infers_prov_Agent",
         (o("InteropProvider"), RDF.type, URIRef(PROV + "Agent")), True),
        ("generatedByActivity_infers_prov_wasGeneratedBy",
         (o("InteropData"), URIRef(PROV + "wasGeneratedBy"), o("InteropActivity")), True),
        ("CausalAssertion_infers_prov_Entity",
         (o("InteropAssertion"), RDF.type, URIRef(PROV + "Entity")), True),
        ("hasCausalEvidence_infers_prov_wasDerivedFrom",
         (o("InteropAssertion"), URIRef(PROV + "wasDerivedFrom"), o("InteropData")), True),
        ("instance_level_wasAttributedTo_present",
         (o("InteropData"), URIRef(PROV + "wasAttributedTo"), o("InteropProvider")), True),
    ]),
    ("T4_GeoSPARQL", "geosparql_alignment.ttl", [
        ("SpaceObject_infers_geo_Feature",
         (o("InteropSat"), RDF.type, URIRef(GEO + "Feature")), True),
        ("Orbit_infers_geo_Feature",
         (o("InteropOrbit"), RDF.type, URIRef(GEO + "Feature")), True),
        ("feature_hasGeometry_pattern_present",
         (o("InteropSat"), URIRef(GEO + "hasGeometry"), o("InteropGeom_Sat")), True),
        ("orbit_hasGeometry_pattern_present",
         (o("InteropOrbit"), URIRef(GEO + "hasGeometry"), o("InteropGeom_Orbit")), True),
        # spec 第 12 节 T4 负向：Feature 不因错误 shortcut 被推断为 geo:Geometry
        ("SpaceObject_not_inferred_as_geo_Geometry",
         (o("InteropSat"), RDF.type, URIRef(GEO + "Geometry")), False),
        ("Orbit_not_inferred_as_geo_Geometry",
         (o("InteropOrbit"), RDF.type, URIRef(GEO + "Geometry")), False),
    ]),
]

# 负向检查：schema 中不得再出现已移除的错误映射（防回归）
REMOVED_SCHEMA_TRIPLES = [
    ("hasObservationResult_sub_sosa_hasResult_removed",
     (o("hasObservationResult"), RDFS.subPropertyOf, URIRef(SOSA + "hasResult"))),
    ("hasFeatureOfInterest_sub_sosa_hasFeatureOfInterest_removed",
     (o("hasFeatureOfInterest"), RDFS.subPropertyOf, URIRef(SOSA + "hasFeatureOfInterest"))),
    ("hasObjectWKTGeometry_property_removed",
     (o("hasObjectWKTGeometry"), RDF.type, URIRef(OWL + "DatatypeProperty"))),
    ("hasOrbitWKTGeometry_property_removed",
     (o("hasOrbitWKTGeometry"), RDF.type, URIRef(OWL + "DatatypeProperty"))),
    ("ObservationData_seeAlso_sosa_Observation_removed",
     (o("ObservationData"), RDFS.seeAlso, URIRef(SOSA + "Observation"))),
    ("SpaceEvent_seeAlso_time_Instant_removed",
     (o("SpaceEvent"), RDFS.seeAlso, URIRef(TIME + "Instant"))),
]


def main() -> int:
    schema = Graph()
    schema.parse(str(SCHEMA), format="xml")
    schema_count = len(schema)

    rows: list[dict] = []

    for test_id, fixture, expectations in TESTS:
        g = Graph()
        g.parse(str(SCHEMA), format="xml")
        g.parse(str(HERE / "data" / fixture), format="turtle")
        before = len(g)
        owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(g)
        after = len(g)
        for check_name, triple, expected_present in expectations:
            present = triple in g
            passed = present == expected_present
            rows.append({
                "test": test_id, "fixture": fixture, "check": check_name,
                "triple": " ".join(str(t) for t in triple),
                "expected_present": expected_present,
                "actual_present": present,
                "pass": passed,
                "closure_triples_before": before,
                "closure_triples_after": after,
            })

    # 负向 schema 检查（直接在 schema 图上）
    for check_name, triple in REMOVED_SCHEMA_TRIPLES:
        present = triple in schema
        rows.append({
            "test": "REMOVED_negative", "fixture": "(schema)",
            "check": check_name,
            "triple": " ".join(str(t) for t in triple),
            "expected_present": False,
            "actual_present": present,
            "pass": not present,
            "closure_triples_before": schema_count,
            "closure_triples_after": schema_count,
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "standard_alignment_test_results.json"
    csv_path = OUT_DIR / "standard_alignment_test_results.csv"
    n_pass = sum(1 for r in rows if r["pass"])
    doc = {
        "spec": "M5 Phase 1 第 12 节：标准互操作测试 T1—T4",
        "schema": "ontology/tc_sssao.owl（含 tc_sssao_alignments.ttl 合并结果）",
        "schema_triples": schema_count,
        "reasoning": "RDFS closure (owlrl.RDFS_Semantics)",
        "total_checks": len(rows),
        "passed": n_pass,
        "failed": len(rows) - n_pass,
        "overall_pass": n_pass == len(rows),
        "rows": rows,
    }
    io.open(str(json_path), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    with io.open(str(csv_path), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["test", "fixture", "check", "triple",
                                          "expected_present", "actual_present",
                                          "pass", "closure_triples_before",
                                          "closure_triples_after"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    out = sys.stdout.buffer
    for r in rows:
        out.write(("%s %-28s %-52s %s\n" % (
            "PASS" if r["pass"] else "FAIL", r["test"], r["check"],
            "inferred" if r["actual_present"] else "absent")).encode("utf-8"))
    out.write(("TOTAL: %d/%d PASS -> %s\n" % (
        n_pass, len(rows), "PASS" if n_pass == len(rows) else "FAIL")).encode("utf-8"))
    return 0 if n_pass == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
