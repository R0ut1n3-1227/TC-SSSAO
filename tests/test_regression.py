"""TC-SSSAO lightweight regression checks.

This suite validates repository integrity plus the two corrected test-coverage cases:
R2 genuine interval overlap and R15 missing respondsToEvent.
"""
from pathlib import Path
import sys
from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import SH

BASE = Path(__file__).resolve().parents[1]
ONTO = Namespace("https://w3id.org/tc-sssao#")


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print(f"[PASS] {msg}")


def main() -> int:
    ontology = Graph(); ontology.parse(BASE / "ontology/tc_sssao.owl", format="xml")
    rules = Graph(); rules.parse(BASE / "rules/tc_sssao_rules.ttl", format="turtle")
    pos = Graph(); pos.parse(BASE / "rules/tc_sssao_test_positive.ttl", format="turtle")
    neg = Graph(); neg.parse(BASE / "rules/tc_sssao_test_negative.ttl", format="turtle")
    case_schema = Graph(); case_schema.parse(BASE / "experiments/cz6a/data/case_schema.ttl", format="turtle")
    case_facts = Graph(); case_facts.parse(BASE / "experiments/cz6a/data/case_facts.ttl", format="turtle")

    require(len(ontology) > 0 and len(rules) > 0, "本体与规则文件可解析")
    require((ONTO.pos_r2_overlap_a, RDF.type, ONTO.SpaceEvent) in pos, "R2重叠正例A存在")
    require((ONTO.pos_r2_overlap_b, RDF.type, ONTO.SpaceEvent) in pos, "R2重叠正例B存在")

    # Execute the R2 SPARQL CONSTRUCT directly; no RDFS expansion is needed because the test nodes are direct SpaceEvent instances.
    shape = ONTO.EventOverlapRuleShape
    constructs = []
    for rule_node in rules.objects(shape, SH.rule):
        constructs.extend(str(x) for x in rules.objects(rule_node, SH.construct))
    require(len(constructs) == 1, "R2规则包含唯一SPARQL CONSTRUCT")
    inferred = Graph()
    for triple in pos.query(constructs[0]).graph:
        inferred.add(triple)
    require((ONTO.pos_r2_overlap_a, ONTO.overlapsWithEvent, ONTO.pos_r2_overlap_b) in inferred,
            "R2生成A到B的重叠关系")
    require((ONTO.pos_r2_overlap_b, ONTO.overlapsWithEvent, ONTO.pos_r2_overlap_a) in inferred,
            "R2生成B到A的重叠关系")

    measure = ONTO.neg_measure_no_event
    require((measure, RDF.type, ONTO.AvoidanceMeasure) in neg, "R15独立负例存在")
    require(not any(neg.objects(measure, ONTO.respondsToEvent)), "R15负例确实缺少respondsToEvent")
    require((ONTO.ResponseMeasureEventShape, RDF.type, SH.NodeShape) in rules, "R15 SHACL Shape存在")

    threat = ONTO.neg_threat_no_response
    require((threat, RDF.type, ONTO.PhysicalThreat) in neg, "R12独立负例存在")
    require(not any(neg.objects(threat, ONTO.requiresResponseMeasure)), "R12负例确实缺少requiresResponseMeasure")
    require((ONTO.SecurityThreatResponseShape, RDF.type, SH.NodeShape) in rules, "R12 SHACL Shape存在")

    require((ONTO.hasObservationTime, RDF.type, URIRef("http://www.w3.org/2002/07/owl#DatatypeProperty")) not in ontology,
            "主本体不再定义hasObservationTime属性（发布模式已收敛）")
    # 案例观测报告时间由案例局部属性 case:reportTime 记录。
    CASE_NS = Namespace("https://w3id.org/tc-sssao/data/cz6a-case#")
    require(not any(case_facts.triples((None, ONTO.hasObservationTime, None))),
            "CZ-6A案例不使用已移除的hasObservationTime属性")
    require(any(case_facts.triples((None, CASE_NS.reportTime, None))),
            "CZ-6A案例使用局部属性case:reportTime记录观测报告时间")
    require(len(case_schema) >= 8, "CZ-6A案例局部模式已声明")
    print("[PASS] 所有轻量回归断言通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
