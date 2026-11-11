# Controlled rule-contract diagnostics: intentional invalid/incomplete fixtures; not formal instance ingestion.
"""hasCausalConfidence 可选化（M3 第一阶段）的 SHACL 约束测试。

CausalAssertion 的 hasCausalConfidence 由 exactly 1 放宽为 max 1（可选元数据）：
- 测试1：无 hasCausalConfidence 的合法 CausalAssertion → 通过（无 violation）；
- 测试2：一个 [0,1] 范围内的 xsd:float 值 → 通过；
- 测试3：两个置信度值 → CausalConfidenceRangeShape violation；
- 测试4：值 > 1 → CausalConfidenceRangeShape violation。

每个测试构造最小数据图（断言 + 原因/结果事件 + 观测证据，时间方向合法），
用主规则文件 rules/tc_sssao_rules.ttl 做 SHACL 验证，按 sourceShape 统计
CausalConfidenceRangeShape 违规数。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace

ONTO = Namespace("https://w3id.org/tc-sssao#")
CC = Namespace("https://w3id.org/tc-sssao/data/causal-confidence-test#")
SH = Namespace("http://www.w3.org/ns/shacl#")

HEADER = """@prefix onto: <https://w3id.org/tc-sssao#> .
@prefix cc: <https://w3id.org/tc-sssao/data/causal-confidence-test#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

BASE_DATA = """
cc:obs a onto:RadarObservationData .
cc:causeEvt a onto:SpaceEvent ;
    onto:hasEventID "CC-CAUSE"^^xsd:string ;
    onto:hasOccurrenceTime "2026-09-01T10:00:00Z"^^xsd:dateTime ;
    onto:hasStartTime "2026-09-01T10:00:00Z"^^xsd:dateTime ;
    onto:hasEndTime "2026-09-01T10:30:00Z"^^xsd:dateTime ;
    onto:detectedFromData cc:obs .
cc:effectEvt a onto:SpaceEvent ;
    onto:hasEventID "CC-EFFECT"^^xsd:string ;
    onto:hasOccurrenceTime "2026-09-01T11:00:00Z"^^xsd:dateTime ;
    onto:hasStartTime "2026-09-01T11:00:00Z"^^xsd:dateTime ;
    onto:hasEndTime "2026-09-01T11:30:00Z"^^xsd:dateTime ;
    onto:detectedFromData cc:obs .
"""

ASSERTION_HEAD = """
cc:assertion a onto:CausalAssertion ;
    onto:hasCause cc:causeEvt ;
    onto:hasEffect cc:effectEvt ;
    onto:hasCausalEvidence cc:obs"""

CASES = [
    ("无置信度值-应通过", ASSERTION_HEAD + " .\n", True),
    ("单个合法值-应通过", ASSERTION_HEAD + ' ;\n    onto:hasCausalConfidence "0.85"^^xsd:float .\n', True),
    ("两个置信度值-应违规", ASSERTION_HEAD + ' ;\n    onto:hasCausalConfidence "0.3"^^xsd:float, "0.4"^^xsd:float .\n', False),
    ("置信度大于1-应违规", ASSERTION_HEAD + ' ;\n    onto:hasCausalConfidence "1.5"^^xsd:float .\n', False),
]


def count_shape_violations(report_graph: Graph, shape) -> int:
    """统计归属于指定 NodeShape 的违规数。

    属性约束违规的 sh:sourceShape 指向 NodeShape 内 sh:property 的匿名
    属性形状而非 NodeShape 本身，因此按“sourceShape 等于 NodeShape 或其
    sh:path 落在该 NodeShape 的输入属性上”判定归属。
    """
    count = 0
    for v in report_graph.subjects(SH.sourceShape, None):
        ss = report_graph.value(v, SH.sourceShape)
        if ss == shape:
            count += 1
        elif ss is not None and report_graph.value(ss, SH.path) == ONTO.hasCausalConfidence:
            count += 1
    return count


def main() -> int:
    try:
        from pyshacl import validate
    except ImportError:
        print("缺少pyshacl。", file=sys.stderr)
        return 2

    base = Path(__file__).resolve().parent
    root = base
    for p in [base, *base.parents]:
        if (p / "rules" / "tc_sssao_rules.ttl").exists():
            root = p
            break
    rules = Graph(); rules.parse(root / "rules" / "tc_sssao_rules.ttl", format="turtle")
    ontology = Graph(); ontology.parse(root / "ontology" / "tc_sssao.owl", format="xml")

    results = []
    all_ok = True
    for name, body, expect_conforms in CASES:
        data = Graph(); data.parse(data=HEADER + BASE_DATA + body, format="turtle")
        data += ontology
        conforms, report_graph, _ = validate(
            data_graph=data, shacl_graph=rules, ont_graph=None,
            inference="rdfs", advanced=True, inplace=True, debug=False)
        conf_violations = count_shape_violations(report_graph, ONTO.CausalConfidenceRangeShape)
        if expect_conforms:
            ok = bool(conforms) and conf_violations == 0
        else:
            ok = (not conforms) and conf_violations >= 1
        all_ok = all_ok and ok
        print(f"{name}: conforms={conforms}, CausalConfidenceRangeShape违规={conf_violations} → "
              f"{'符合预期' if ok else '与预期不符'}")
        results.append({
            "case": name, "expect_conforms": expect_conforms,
            "conforms": bool(conforms),
            "causal_confidence_shape_violations": conf_violations,
            "pass": ok,
        })

    out = base / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "causal_confidence_test_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n全部{len(results)}项因果置信度约束测试{'通过' if all_ok else '存在不符项'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
