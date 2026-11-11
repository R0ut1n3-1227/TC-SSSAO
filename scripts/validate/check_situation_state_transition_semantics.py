"""状态关系语义防回归检查。

该独立闸门验证 transitsTo/recoversTo 不会由状态类成员资格自动产生，
并验证当前 B2、B3 的实例级前件能够按预期建立 transitsTo。它不改变
ontology、R1—R18、B1—B5，也不计入 semantic regression 58/58 口径。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.utils.shacl_utils import validate_diagnostic_graph_fixed_point  # noqa: E402

ONTO = Namespace("https://w3id.org/tc-sssao#")
TEST = Namespace("https://w3id.org/tc-sssao/data/state-transition-regression#")
OUT = ROOT / "data" / "current" / "situation_state_transition_semantics.json"

PREFIXES = """@prefix onto: <https://w3id.org/tc-sssao#> .
@prefix test: <https://w3id.org/tc-sssao/data/state-transition-regression#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def graph(body: str) -> Graph:
    result = Graph()
    result.parse(data=PREFIXES + body, format="turtle")
    return result


def infer(body: str) -> Graph:
    _, _, _, result, _, _ = validate_diagnostic_graph_fixed_point(graph(body))
    return result


def main() -> int:
    cases = []

    # T1：类成员资格本身不得强制生成 Normal -> Attention。
    t1 = infer('''
test:NormalOnly a onto:NormalSituationState ;
    onto:hasStateID "T1-NORMAL"^^xsd:string ;
    onto:hasSeverityRank 0 .
''')
    t1_forbidden = list(t1.triples((TEST.NormalOnly, ONTO.transitsTo, None)))
    cases.append({
        "id": "T1",
        "description": "仅声明 NormalSituationState，不得派生 transitsTo",
        "pass": not t1_forbidden,
        "forbidden_found": [[str(x) for x in triple] for triple in t1_forbidden],
    })

    # T2：危险状态的类成员资格本身不得强制生成恢复关系。
    t2 = infer('''
test:DangerousOnly a onto:DangerousSituationState ;
    onto:hasStateID "T2-DANGEROUS"^^xsd:string ;
    onto:hasSeverityRank 3 .
''')
    t2_forbidden = list(t2.triples((TEST.DangerousOnly, ONTO.recoversTo, None)))
    cases.append({
        "id": "T2",
        "description": "仅声明 DangerousSituationState，不得派生 recoversTo",
        "pass": not t2_forbidden,
        "forbidden_found": [[str(x) for x in triple] for triple in t2_forbidden],
    })

    # T3：显式 StateTransition 具备源/目标状态时，B2 应建立 transitsTo。
    t3 = infer('''
test:B2Source a onto:NormalSituationState ;
    onto:hasStateID "T3-SOURCE"^^xsd:string ;
    onto:hasSeverityRank 0 .
test:B2Target a onto:AttentionSituationState ;
    onto:hasStateID "T3-TARGET"^^xsd:string ;
    onto:hasSeverityRank 1 .
test:B2Transition a onto:StateTransition ;
    onto:hasSourceState test:B2Source ;
    onto:hasTargetState test:B2Target .
''')
    t3_expected = (TEST.B2Source, ONTO.transitsTo, TEST.B2Target)
    cases.append({
        "id": "T3",
        "description": "满足 B2 的显式 StateTransition 应建立 transitsTo",
        "pass": t3_expected in t3,
        "expected": [str(x) for x in t3_expected],
    })

    # T4：同一目标对的两个相邻风险快照满足 B3 时，应建立状态演化。
    t4 = infer('''
test:Primary a onto:SpaceObject .
test:Secondary a onto:SpaceObject .
test:Risk1 a onto:CollisionRiskEvent ;
    onto:hasEventID "T4-R1"^^xsd:string ;
    onto:hasEncounterID "T4-ENC-01"^^xsd:string ;
    onto:hasPrimaryObject test:Primary ;
    onto:hasSecondaryObject test:Secondary ;
    onto:hasOccurrenceTime "2026-01-01T00:00:00Z"^^xsd:dateTime ;
    onto:precedesEvent test:Risk2 ;
    onto:leadsToState test:State1 .
test:Risk2 a onto:CollisionRiskEvent ;
    onto:hasEventID "T4-R2"^^xsd:string ;
    onto:hasEncounterID "T4-ENC-01"^^xsd:string ;
    onto:hasPrimaryObject test:Primary ;
    onto:hasSecondaryObject test:Secondary ;
    onto:hasOccurrenceTime "2026-01-01T01:00:00Z"^^xsd:dateTime ;
    onto:leadsToState test:State2 .
test:State1 a onto:NormalSituationState ;
    onto:hasStateID "T4-S1"^^xsd:string ;
    onto:hasSeverityRank 0 .
test:State2 a onto:AttentionSituationState ;
    onto:hasStateID "T4-S2"^^xsd:string ;
    onto:hasSeverityRank 1 .
''')
    t4_expected = (TEST.State1, ONTO.transitsTo, TEST.State2)
    cases.append({
        "id": "T4",
        "description": "满足 B3 的相邻风险快照应建立 transitsTo",
        "pass": t4_expected in t4,
        "expected": [str(x) for x in t4_expected],
    })

    passed = sum(bool(case["pass"]) for case in cases)
    report = {
        "check": "situation state transition semantics",
        "scope": "independent final gate; semantic regression remains 58/58",
        "result": f"{passed}/{len(cases)} PASS",
        "pass": passed == len(cases),
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report["result"])
    for case in cases:
        print(f"{case['id']}: {'PASS' if case['pass'] else 'FAIL'} - {case['description']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
