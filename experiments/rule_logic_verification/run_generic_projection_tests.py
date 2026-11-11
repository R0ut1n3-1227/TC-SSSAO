# Controlled rule-contract diagnostics: intentional invalid/incomplete fixtures; not formal instance ingestion.
"""B4/B5 通用安全语义投影规则与 B2 独立桥接测试（非 CZ-6A 合成场景）。

M3 第一阶段（2026-09-04）新增。证明 B4/B5 不是“换名字后的案例专用规则”：
所有测试实例使用独立的 generic-projection 命名空间，不包含 CZ-6A 案例 IRI、
碎片数量（533/529）、轨道高度（813/847）或任何案例特定阈值。

- B4 正例：DebrisRiskEvent + RiskAssessmentData → PhysicalThreat + DebrisRisk
  + indicatesThreat + mayManifestAsEvent + producesRisk；
- B4 反例：DebrisRiskEvent 仅具普通 ObservationData 支撑（缺 RiskAssessmentData）
  → 不生成任何 B4 输出；
- B5 正例：ResponseMeasure respondsToEvent 该风险事件且 B4 已派生威胁/风险
  → 生成 requiresResponseMeasure/respondsToThreat/threatMitigatedBy/
  mitigatesRisk/mitigatedBy 全部五条响应关系；
- B5 反例：ResponseMeasure 响应的是另一个事件 → 不与当前威胁/风险建立关系；
- B2 正例：StateTransition hasSourceState/hasTargetState → transitsTo；
- B2 反例：StateTransition 缺少 hasTargetState → 不生成 transitsTo。

所有测试均为人工构造的规则边界数据，不对应真实事件。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef

ONTO = Namespace("https://w3id.org/tc-sssao#")
GP = Namespace("https://w3id.org/tc-sssao/data/generic-projection#")

HEADER = """@prefix onto: <https://w3id.org/tc-sssao#> .
@prefix gp: <https://w3id.org/tc-sssao/data/generic-projection#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def derived_iri(kind: str, event_iri: str) -> URIRef:
    digest = hashlib.sha256(event_iri.encode("utf-8")).hexdigest().lower()
    return URIRef(f"https://w3id.org/tc-sssao#derived_{kind}_{digest}")


def build_graph(body: str) -> Graph:
    g = Graph()
    g.parse(data=HEADER + body, format="turtle")
    return g


def run_rules_to_fixed_point(data: Graph, rules: Graph, max_iter: int = 10) -> Graph:
    from pyshacl import validate
    for _ in range(max_iter):
        before = len(data)
        validate(data_graph=data, shacl_graph=rules, inference="rdfs",
                 advanced=True, inplace=True, debug=False)
        if len(data) == before:
            break
    return data


# ---------- 夹具 ----------

def b4_fixture(support: str = "assessment") -> str:
    """B4 夹具：DebrisRiskEvent + 证据。support='assessment' 满足 B4 前件，
    'observation' 为普通观测数据（不满足）。"""
    support_decl = ("gp:AssessmentA a onto:RiskAssessmentData .\n"
                    "gp:RiskEvtA onto:supportedByData gp:AssessmentA .\n"
                    if support == "assessment" else
                    "gp:RiskEvtA onto:supportedByData gp:ObsA .\n")
    return f"""
gp:ObsA a onto:RadarObservationData .
{support_decl}
gp:RiskEvtA a onto:DebrisRiskEvent ;
    onto:hasEventID "GE-B4-{support.upper()}"^^xsd:string ;
    onto:detectedFromData gp:ObsA .
"""


def b5_fixture(responds_to_risk: bool = True) -> str:
    """B5 夹具：B4 正例基础 + 响应措施。responds_to_risk=False 时措施响应另一事件。"""
    target = "gp:RiskEvtA" if responds_to_risk else "gp:OtherEvt"
    other = ("" if responds_to_risk else
             'gp:OtherEvt a onto:TrackingEvent ;\n'
             '    onto:hasEventID "GE-B5-OTHER"^^xsd:string ;\n'
             "    onto:detectedFromData gp:ObsA .\n")
    return b4_fixture("assessment") + f"""
{other}gp:MeasureA a onto:ResponseMeasure ;
    onto:hasMeasureID "GM-A"^^xsd:string ;
    onto:respondsToEvent {target} .
"""


def b2_fixture(with_target: bool = True) -> str:
    """B2 夹具：StateTransition + 源/目标状态。"""
    target_line = "    onto:hasTargetState gp:StateY ;\n" if with_target else ""
    return f"""
gp:ObsB a onto:RadarObservationData .
gp:EvtB a onto:TrackingEvent ;
    onto:hasEventID "GE-B2"^^xsd:string ;
    onto:detectedFromData gp:ObsB .
gp:StateX a onto:NormalSituationState ;
    onto:hasStateID "GS-X"^^xsd:string .
gp:StateY a onto:WarningSituationState ;
    onto:hasStateID "GS-Y"^^xsd:string .
gp:TransA a onto:StateTransition ;
    onto:hasSourceState gp:StateX ;
{target_line}    onto:triggeredByEvent gp:EvtB .
"""


def main() -> int:
    base = Path(__file__).resolve().parent
    root = base
    for p in [base, *base.parents]:
        if (p / "rules" / "tc_sssao_rules.ttl").exists():
            root = p
            break
    rules = Graph(); rules.parse(root / "rules" / "tc_sssao_rules.ttl", format="turtle")
    # 规则前件的类型匹配依赖本体子类闭包，测试数据图需包含主本体（与主实验一致）
    ontology = Graph(); ontology.parse(root / "ontology" / "tc_sssao.owl", format="xml")
    config = Graph(); config.parse(root / "rules" / "tc_sssao_rule_config.ttl", format="turtle")

    evt = GP.RiskEvtA
    threat = derived_iri("physical_threat", str(evt))
    drisk = derived_iri("debris_risk", str(evt))

    b4_outputs = [
        (threat, RDF.type, ONTO.PhysicalThreat),
        (drisk, RDF.type, ONTO.DebrisRisk),
        (evt, ONTO.indicatesThreat, threat),
        (threat, ONTO.mayManifestAsEvent, evt),
        (threat, ONTO.producesRisk, drisk),
    ]
    b5_outputs = [
        (threat, ONTO.requiresResponseMeasure, GP.MeasureA),
        (GP.MeasureA, ONTO.respondsToThreat, threat),
        (threat, ONTO.threatMitigatedBy, GP.MeasureA),
        (GP.MeasureA, ONTO.mitigatesRisk, drisk),
        (drisk, ONTO.mitigatedBy, GP.MeasureA),
    ]

    tests: list[tuple[str, str, str, list[tuple], bool]] = [
        ("B4-正例", "DebrisRiskEvent 经 RiskAssessmentData 支撑，应生成派生威胁/风险及三条投影关系",
         b4_fixture("assessment"), b4_outputs, True),
        ("B4-反例-缺风险评估数据", "DebrisRiskEvent 仅具普通 ObservationData 支撑，不应生成任何 B4 输出",
         b4_fixture("observation"), b4_outputs, False),
        ("B5-正例", "ResponseMeasure respondsToEvent 该风险事件，应生成全部五条响应关系",
         b5_fixture(True), b5_outputs, True),
        ("B5-反例-响应其他事件", "ResponseMeasure 响应另一事件，不应与当前威胁/风险建立关系",
         b5_fixture(False), b5_outputs, False),
        ("B2-正例", "StateTransition 具有源/目标状态，应生成 transitsTo",
         b2_fixture(True), [(GP.StateX, ONTO.transitsTo, GP.StateY)], True),
        ("B2-反例-缺目标状态", "StateTransition 缺少 hasTargetState，不应生成 transitsTo",
         b2_fixture(False), [(GP.StateX, ONTO.transitsTo, GP.StateY)], False),
    ]

    results = []
    all_ok = True
    for tid, desc, body, triples, expect in tests:
        data = build_graph(body) + ontology + config
        run_rules_to_fixed_point(data, rules)
        detail = []
        case_ok = True
        for triple in triples:
            present = triple in data
            ok = present == expect
            case_ok = case_ok and ok
            detail.append({
                "triple": [str(x) for x in triple],
                "expected": expect, "actual": present, "pass": ok,
            })
        all_ok = all_ok and case_ok
        print(f"{tid}: {'符合预期' if case_ok else '与预期不符'}")
        results.append({"id": tid, "description": desc, "expect_outputs": expect,
                        "detail": detail, "pass": case_ok})

    out = base / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "generic_projection_test_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n全部{len(results)}项通用投影/桥接测试{'通过' if all_ok else '存在不符项'}")
    print(f"结果文件：{out / 'generic_projection_test_results.json'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
