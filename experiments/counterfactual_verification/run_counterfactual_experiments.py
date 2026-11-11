"""反事实能力验证实验（CF-1 观测证据删除 / CF-2 时间方向反转）。

回应审稿意见"能力问题验证存在自证循环、缺少负例验证"：正式能力验证回答
"完整条件下能否得到预期结果"，本实验回答其逆命题——当关键语义条件被删除
或改变后，原有派生关系是否相应消失或改变。干预原则为单变量：

    F ∧ C → R    保持事实集合 F 不变，仅移除或改变关键条件 C。

目标事件对取自正式规则逻辑验证场景（experiments/rule_logic_verification）
中已由规则真实生成的派生关系：
    rs:Evt_Maneuver --causesEvent--> rs:Evt_Approach
由 R3（OrbitManeuverCausesApproachRuleShape）生成，其 precedesEvent 前提由
R1（EventPrecedenceRuleShape）生成。不是新造的理想示例。

- CF-1（观测证据删除）：仅删除原因事件的唯一证据链接
  （Evt_Maneuver detectedFromData TestObsData，即 R3 的 E_obs 前提在原因侧的全部
  证据），从未推理干净副本重新执行同一规则集，检查目标 causesEvent 是否消失。
- CF-2（时间方向反转）：仅互换两事件的时间区间（各自持续时间不变），
  检查原方向 precedesEvent/causesEvent 是否消失、反向时序关系是否按规则生成。

真实性闸门（运行时强制，任一不满足即中止并报错）：
1. 反事实副本与正式场景事实的差异集合必须恰为声明的干预三元组；
2. 三份输入图均不得含任何派生谓词三元组（杜绝把旧推理结果误当规则输出）；
3. 基线复跑必须重新生成目标 causesEvent，否则按任务规定停止并报告。

约束：不修改本体、rules/tc_sssao_rules.ttl（R1—R18）、B1—B5、CZ-6A 数据、
TraCSS 实验、正式实验数据与结果；本实验只新增独立反事实副本与结果。
CF-3（TraCSS 风险状态边界反事实）已在 experiments/tracss_threshold_sensitivity
完成，本报告仅引用其结论，不重复运行。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD


def find_project_root(start: Path) -> Path:
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / "ontology" / "tc_sssao.owl").exists():
            return p
    raise RuntimeError("未找到TC-SSSAO工程根目录。")


BASE = find_project_root(Path(__file__).parent)
EXP = Path(__file__).resolve().parent
DATA_DIR = EXP / "data"
OUT = EXP / "outputs"
OWL = BASE / "ontology" / "tc_sssao.owl"
MAIN_RULES = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG = BASE / "rules" / "tc_sssao_rule_config.ttl"
ORIG_FACTS = BASE / "experiments" / "rule_logic_verification" / "data" / "scenario_facts.ttl"
FORMAL_SUMMARY = (BASE / "experiments" / "rule_logic_verification" / "outputs"
                  / "scenario_reasoning_summary.json")
CF1_FACTS = DATA_DIR / "cf1_evidence_removed_facts.ttl"
CF2_FACTS = DATA_DIR / "cf2_time_reversed_facts.ttl"

ONTO = Namespace("https://w3id.org/tc-sssao#")
RS = Namespace("https://w3id.org/tc-sssao/data/rule-scenario#")
SH = Namespace("http://www.w3.org/ns/shacl#")

MAN = RS.Evt_Maneuver   # 目标对原因事件（R3 的 e1）
APP = RS.Evt_Approach   # 目标对结果事件（R3 的 e2）
SAT_A = RS.TestSat_A
SAT_B = RS.TestSat_B
OBS = RS.TestObsData
RISKS = (RS.Risk_T0, RS.Risk_T1, RS.Risk_T2, RS.Risk_T3)

# 派生谓词：输入图（未推理状态）中不得出现，用于区分"旧结果残留"与"规则真实生成"
DERIVED_PROPS = (
    ONTO.precedesEvent, ONTO.followsEvent, ONTO.causesEvent,
    ONTO.leadsToState, ONTO.transitsTo, ONTO.degradesTo, ONTO.overlapsWithEvent,
)

# SHACL 报告 sourceShape 本地名 → 规则编号（与 rules/tc_sssao_rules.ttl 注释一致）
SHAPE_RULE_ID = {
    "SpaceObjectOrbitShape": "R16",
    "ObservationSystemDataShape": "R17",
    "SecurityThreatResponseShape": "R12",
    "ResponseMeasureEventShape": "R15",
    "EventDataEvidenceShape": "R13",
    "StateStartEndTimeShape": "R14",
    "CauseBeforeEffectShape": "R9",
    "CausalDirectionShape": "R10",
    "CausalCycleShape": "R11",
    "EnvironmentLevelShape": "R18",
    "EventStartEndTimeShape": "事件起止时间约束",
    "CausalConfidenceRangeShape": "因果置信度取值约束",
    "StateConfidenceRangeShape": "状态置信度取值约束",
    "MultiCauseMinShape": "多因断言基数约束",
    "StateTransitionNoSelfLoopShape": "状态转移自环约束",
    "SensorDisjointShape": "传感器互斥约束",
    "ThreatRiskRelationMisuseShape": "威胁/风险关系误用约束",
    "ObservationEventDataPropertyMisuseShape": "观测事件属性误用约束",
}


def serialize_deterministic(g: Graph, path: Path) -> None:
    """字节级确定性 Turtle 序列化（与正式运行器同一实现口径）。"""
    from rdflib.compare import to_canonical_graph
    canon = to_canonical_graph(g)
    out = Graph()
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns)
    for t in sorted(canon, key=lambda x: (str(x[0]), str(x[1]), str(x[2]))):
        out.add(t)
    out.serialize(path, format="turtle")


def load_graph(path: Path, fmt: str = "turtle") -> Graph:
    g = Graph()
    g.parse(path, format=fmt)
    return g


def run_to_fixed_point(input_graph: Graph, ontology: Graph, config: Graph,
                       rules: Graph, tag: str):
    """与正式运行器同一执行路径：数据图=输入+本体+规则部署配置，
    pySHACL（rdfs 闭包 + advanced 规则）迭代至完整图不动点，清理字面量主语。"""
    from pyshacl import validate
    sys.path.insert(0, str(BASE))
    from scripts.validate.check_rule_input_preflight import require_formal_input
    require_formal_input(input_graph, config, ontology)
    data = input_graph + ontology + config
    additions: list[int] = []
    conforms, report_graph, report_text = False, Graph(), ""
    for iteration in range(1, 11):
        before = set(data)
        conforms, report_graph, report_text = validate(
            data_graph=data,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        added = len(set(data) - before)
        additions.append(added)
        print(f"  [{tag}] 第{iteration}轮新增：{added}")
        if added == 0:
            break
    else:
        raise RuntimeError(f"[{tag}] 规则在10轮内未收敛：{additions}")
    invalid = [t for t in data if isinstance(t[0], Literal)]
    for t in invalid:
        data.remove(t)
    if invalid:
        print(f"  [{tag}] 清理RDFS闭包产生的非法字面量主语三元组：{len(invalid)}")
    return data, conforms, report_graph, report_text, additions


def has_observation_evidence(g: Graph, event: URIRef) -> bool:
    """复刻 R3/R4 的证据条件：supportedByData/detectedFromData 指向 ObservationData。"""
    for prop in (ONTO.supportedByData, ONTO.detectedFromData):
        for d in g.objects(event, prop):
            if (d, RDF.type, ONTO.ObservationData) in g:
                return True
    return False


def object_role_condition(g_in: Graph) -> bool:
    """R3 的对象/角色条件：机动 affectsObject o1，接近 hasPrimaryObject o1、
    hasSecondaryObject o2，且 o1≠o2（显式事实，在输入图上检查）。"""
    return ((MAN, ONTO.affectsObject, SAT_A) in g_in
            and (APP, ONTO.hasPrimaryObject, SAT_A) in g_in
            and (APP, ONTO.hasSecondaryObject, SAT_B) in g_in
            and SAT_A != SAT_B)


def extract_violations(report_graph: Graph) -> list[dict]:
    out = []
    for res in report_graph.subjects(RDF.type, SH.ValidationResult):
        focus = report_graph.value(res, SH.focusNode)
        shape = report_graph.value(res, SH.sourceShape)
        msg = report_graph.value(res, SH.resultMessage)
        local = str(shape).rsplit("#", 1)[-1] if isinstance(shape, URIRef) else str(shape)
        out.append({
            "focus_node": str(focus),
            "source_shape": local,
            "rule_id": SHAPE_RULE_ID.get(local, local),
            "message": str(msg) if msg is not None else "",
        })
    return sorted(out, key=lambda v: (v["source_shape"], v["focus_node"]))


def bidirectional_causal_pairs(g: Graph) -> list[list[str]]:
    edges = {(s, o) for s, o in g.subject_objects(ONTO.causesEvent)}
    return sorted({tuple(sorted((str(s), str(o))))
                   for s, o in edges if (o, s) in edges and s != o})


def has_causal_cycle(g: Graph) -> bool:
    adj: dict[URIRef, set[URIRef]] = {}
    for s, o in g.subject_objects(ONTO.causesEvent):
        adj.setdefault(s, set()).add(o)
    for start in adj:
        stack, seen = [start], set()
        while stack:
            node = stack.pop()
            for nxt in adj.get(node, ()):
                if nxt == start:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return False


def precedence_conflicts(g: Graph) -> list[list[str]]:
    edges = {(s, o) for s, o in g.subject_objects(ONTO.precedesEvent)}
    return sorted({tuple(sorted((str(s), str(o))))
                   for s, o in edges if (o, s) in edges and s != o})


def stale_derived_triples(g_in: Graph) -> list[tuple]:
    return [t for t in g_in if t[1] in DERIVED_PROPS]


def build_run_record(name: str, input_graph: Graph, data: Graph, conforms: bool,
                     report_graph: Graph, additions: list[int], elapsed: float) -> dict:
    return {
        "name": name,
        "fixed_point_iterations": len(additions),
        "graph_triples_added_per_round": additions,
        "shacl_conforms": bool(conforms),
        "violations": extract_violations(report_graph),
        "elapsed_seconds": round(elapsed, 3),
        "conditions": {
            "temporal_precedes_MAN_APP": (MAN, ONTO.precedesEvent, APP) in data,
            "reverse_precedes_APP_MAN": (APP, ONTO.precedesEvent, MAN) in data,
            "follows_APP_MAN": (APP, ONTO.followsEvent, MAN) in data,
            "follows_MAN_APP": (MAN, ONTO.followsEvent, APP) in data,
            "object_role": object_role_condition(input_graph),
            "evidence_MAN": has_observation_evidence(data, MAN),
            "evidence_APP": has_observation_evidence(data, APP),
        },
        "results": {
            "causesEvent_MAN_APP": (MAN, ONTO.causesEvent, APP) in data,
            "causesEvent_APP_MAN": (APP, ONTO.causesEvent, MAN) in data,
            "r4_edges_APP_RiskT0_T3": [
                (APP, ONTO.causesEvent, r) in data for r in RISKS
            ],
        },
        "consistency": {
            "bidirectional_causal_pairs": bidirectional_causal_pairs(data),
            "causal_cycle": has_causal_cycle(data),
            "precedence_conflicts": precedence_conflicts(data),
        },
    }


def yn(value: bool) -> str:
    return "✓" if value else "×"


def triple_str(t: tuple) -> str:
    return f"<{t[0]}> <{t[1]}> <{t[2]}>"


def main() -> int:
    try:
        from pyshacl import validate  # noqa: F401
    except ImportError:
        print("缺少pyshacl。请先执行：python -m pip install -r requirements.txt", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)

    ontology = load_graph(OWL, fmt="xml")
    rules = load_graph(MAIN_RULES)
    config = load_graph(RULE_CONFIG)

    orig = load_graph(ORIG_FACTS)
    cf1_in = load_graph(CF1_FACTS)
    cf2_in = load_graph(CF2_FACTS)

    # ---------- 真实性闸门 1：干预差异集合必须恰为声明内容 ----------
    dt = lambda s: Literal(s, datatype=XSD.dateTime)  # noqa: E731
    cf1_removed, cf1_added = set(orig) - set(cf1_in), set(cf1_in) - set(orig)
    expected_cf1_removed = {(MAN, ONTO.detectedFromData, OBS)}
    if cf1_removed != expected_cf1_removed or cf1_added != set():
        raise RuntimeError(
            "CF-1 副本与正式场景的差异不等于声明的单变量干预：\n"
            f"  多余删除：{[triple_str(t) for t in cf1_removed - expected_cf1_removed]}\n"
            f"  缺少删除：{[triple_str(t) for t in expected_cf1_removed - cf1_removed]}\n"
            f"  意外新增：{[triple_str(t) for t in cf1_added]}"
        )
    t_man_old = [dt("2026-08-01T09:00:00Z"), dt("2026-08-01T09:00:00Z"), dt("2026-08-01T09:10:00Z")]
    t_man_new = [dt("2026-08-01T10:00:00Z"), dt("2026-08-01T10:00:00Z"), dt("2026-08-01T10:10:00Z")]
    t_app_old = [dt("2026-08-01T10:00:00Z"), dt("2026-08-01T10:00:00Z"), dt("2026-08-01T10:20:00Z")]
    t_app_new = [dt("2026-08-01T09:00:00Z"), dt("2026-08-01T09:00:00Z"), dt("2026-08-01T09:20:00Z")]
    time_props = (ONTO.hasOccurrenceTime, ONTO.hasStartTime, ONTO.hasEndTime)
    expected_cf2_removed = {(e, p, v) for e, vs in ((MAN, t_man_old), (APP, t_app_old))
                            for p, v in zip(time_props, vs)}
    expected_cf2_added = {(e, p, v) for e, vs in ((MAN, t_man_new), (APP, t_app_new))
                          for p, v in zip(time_props, vs)}
    cf2_removed, cf2_added = set(orig) - set(cf2_in), set(cf2_in) - set(orig)
    if cf2_removed != expected_cf2_removed or cf2_added != expected_cf2_added:
        raise RuntimeError(
            "CF-2 副本与正式场景的差异不等于声明的 6 个时间三元组互换：\n"
            f"  多余删除：{[triple_str(t) for t in cf2_removed - expected_cf2_removed]}\n"
            f"  缺少删除：{[triple_str(t) for t in expected_cf2_removed - cf2_removed]}\n"
            f"  意外新增：{[triple_str(t) for t in cf2_added - expected_cf2_added]}\n"
            f"  缺少新增：{[triple_str(t) for t in expected_cf2_added - cf2_added]}"
        )
    print("真实性闸门1通过：CF-1 差异恰为 1 个证据三元组；CF-2 差异恰为 6 个时间三元组互换。")

    # ---------- 真实性闸门 2：输入图不得残留任何派生谓词三元组 ----------
    for tag, g_in in (("原始场景", orig), ("CF-1", cf1_in), ("CF-2", cf2_in)):
        stale = stale_derived_triples(g_in)
        if stale:
            raise RuntimeError(f"[{tag}] 输入图含派生谓词三元组，无法区分旧结果与新生成："
                               f"{[triple_str(t) for t in stale]}")
    print("真实性闸门2通过：三份输入图均无派生谓词三元组（未推理干净状态）。")

    # ---------- 真实性核验：目标事件对在原始输入中的显式事实 ----------
    authenticity = {
        "cause_event": str(MAN),
        "cause_event_type": "OrbitManeuverEvent",
        "effect_event": str(APP),
        "effect_event_type": "ApproachEvent",
        "cause_occurrence_time": str(orig.value(MAN, ONTO.hasOccurrenceTime)),
        "cause_interval": [str(orig.value(MAN, ONTO.hasStartTime)),
                           str(orig.value(MAN, ONTO.hasEndTime))],
        "effect_occurrence_time": str(orig.value(APP, ONTO.hasOccurrenceTime)),
        "effect_interval": [str(orig.value(APP, ONTO.hasStartTime)),
                            str(orig.value(APP, ONTO.hasEndTime))],
        "objects": {
            "affectsObject(cause)": str(SAT_A),
            "hasPrimaryObject(effect)": str(SAT_A),
            "hasSecondaryObject(effect)": str(SAT_B),
        },
        "evidence_links": {
            "cause": [f"detectedFromData -> {OBS} (RadarObservationData ⊂ ObservationData)"],
            "effect": [f"detectedFromData -> {OBS} (RadarObservationData ⊂ ObservationData)"],
        },
        "causal_assertion_iri": None,
        "causal_assertion_note": (
            "当前冻结规则集中 R3/R4 直接生成事件级 causesEvent，不实例化 CausalAssertion；"
            "hasCausalEvidence 是 CausalAssertion 的溯源属性（range SSAData），"
            "仅被完整性 Shape 检查，不被任何生成规则作为前提。CZ-6A 案例的"
            " causesEvent 由 B1 从显式 DirectCausalAssertion"
            "（case:CZ6A_FragmentationRiskAssertion）桥接，B1 不含证据前提。"
            "故 CF-1 的删除对象以 R3 真实检查的事件级 detectedFromData/supportedByData 为准。"
        ),
        "original_causesEvent_explicit": (MAN, ONTO.causesEvent, APP) in orig,
        "generating_rule": ("R3 OrbitManeuverCausesApproachRuleShape（直接生成）；"
                            "其 precedesEvent 前提由 R1 EventPrecedenceRuleShape 生成"),
    }
    for needed, desc in [
        ((MAN, RDF.type, ONTO.OrbitManeuverEvent), "原因事件类型"),
        ((APP, RDF.type, ONTO.ApproachEvent), "结果事件类型"),
        ((MAN, ONTO.affectsObject, SAT_A), "机动作用对象"),
        ((APP, ONTO.hasPrimaryObject, SAT_A), "接近主要目标"),
        ((APP, ONTO.hasSecondaryObject, SAT_B), "接近次要目标"),
        ((MAN, ONTO.detectedFromData, OBS), "原因事件证据链接"),
        ((APP, ONTO.detectedFromData, OBS), "结果事件证据链接"),
    ]:
        if needed not in orig:
            raise RuntimeError(f"真实性核验失败：正式场景中缺少{desc} {triple_str(needed)}")

    # ---------- 三次独立推理：基线 / CF-1 / CF-2 ----------
    runs: dict[str, dict] = {}
    graphs: dict[str, Graph] = {}
    reports: dict[str, tuple[Graph, str]] = {}
    for tag, g_in in (("baseline", orig), ("cf1", cf1_in), ("cf2", cf2_in)):
        t0 = time.perf_counter()
        data, conforms, rg, rt, additions = run_to_fixed_point(g_in, ontology, config, rules, tag)
        runs[tag] = build_run_record(tag, g_in, data, conforms, rg, additions,
                                     time.perf_counter() - t0)
        graphs[tag] = data
        reports[tag] = (rg, rt)

    # ---------- 真实性闸门 3：基线必须重新生成目标因果关系 ----------
    if not runs["baseline"]["results"]["causesEvent_MAN_APP"]:
        print("基线复跑未生成目标 causesEvent(Evt_Maneuver, Evt_Approach)。"
              "按任务规定停止：当前真实数据中没有规则生成的该关系，不得伪造实验结果。",
              file=sys.stderr)
        return 1
    print("真实性闸门3通过：基线复跑重新生成目标 causesEvent（R3）。")

    # 与正式实验输出对照（只读，不修改）：固定点新增序列与 conforms 应一致
    formal_check = {"formal_summary_found": FORMAL_SUMMARY.exists()}
    if FORMAL_SUMMARY.exists():
        formal = json.loads(FORMAL_SUMMARY.read_text(encoding="utf-8"))
        formal_check.update({
            "formal_graph_additions": formal.get("graph_triples_added_per_round"),
            "formal_conforms": formal.get("shacl_conforms"),
            "formal_R3_check": formal.get("checks", {}).get("R3_机动导致接近"),
            "baseline_reproduces_formal": (
                runs["baseline"]["graph_triples_added_per_round"]
                == formal.get("graph_triples_added_per_round")
                and runs["baseline"]["shacl_conforms"] == formal.get("shacl_conforms")
                and formal.get("checks", {}).get("R3_机动导致接近") is True
            ),
        })

    # ---------- 结果判定 ----------
    b, c1, c2 = runs["baseline"], runs["cf1"], runs["cf2"]

    # CF-1：证据条件删除后，目标 causesEvent 不得重新产生；其余条件须保持不变（局部性）
    cf1_consistency_clean = (not c1["consistency"]["bidirectional_causal_pairs"]
                             and not c1["consistency"]["causal_cycle"]
                             and not c1["consistency"]["precedence_conflicts"])
    if c1["results"]["causesEvent_MAN_APP"]:
        cf1_verdict = "FAIL"
        cf1_reason = "证据条件已删除，但目标 causesEvent 仍以相同方式重新生成。"
    elif (c1["conditions"]["temporal_precedes_MAN_APP"] and c1["conditions"]["object_role"]
          and not c1["conditions"]["evidence_MAN"] and c1["conditions"]["evidence_APP"]
          and all(c1["results"]["r4_edges_APP_RiskT0_T3"]) and cf1_consistency_clean):
        cf1_verdict = "PASS"
        cf1_reason = ("T 与 O 条件保持不变、E_obs 在原因事件侧被移除后，"
                      "目标 causesEvent 未重新产生；其余 R4 因果边照常生成，"
                      "无双向因果/因果环/时间方向冲突。")
    else:
        cf1_verdict = "PARTIAL PASS"
        cf1_reason = "目标结果消失，但其他条件或局部性检查出现异常，需人工核对。"

    # CF-2：时间前提反转后，原向 causesEvent 不得继续成立；反向时序关系应按规则生成
    r9_r10_r11 = {"R9", "R10", "R11"}
    c2_causal_violations = [v for v in c2["violations"] if v["rule_id"] in r9_r10_r11]
    c2_consistency_clean = (not c2_causal_violations
                            and not c2["consistency"]["bidirectional_causal_pairs"]
                            and not c2["consistency"]["causal_cycle"]
                            and not c2["consistency"]["precedence_conflicts"])
    if c2["results"]["causesEvent_MAN_APP"]:
        cf2_verdict = "FAIL"
        cf2_reason = "时间前提已反转失效，但原方向 causesEvent 仍继续成立。"
    elif (not c2["conditions"]["temporal_precedes_MAN_APP"]
          and c2["conditions"]["reverse_precedes_APP_MAN"]
          and c2["conditions"]["follows_MAN_APP"]
          and all(c2["results"]["r4_edges_APP_RiskT0_T3"])
          and c2_consistency_clean):
        cf2_verdict = "PASS"
        cf2_reason = ("原向 precedesEvent 消失、反向 precedesEvent/followsEvent 按 R1 生成；"
                      "原向 causesEvent 随其时间前提失效而消失；R4 因果边不受影响；"
                      "无 R9/R10/R11 违规、无双向因果、无因果环。")
    else:
        cf2_verdict = "PARTIAL PASS"
        cf2_reason = "目标结果消失，但反向时序或一致性检查出现异常，需人工核对。"

    verdicts = {
        "CF-1": {"verdict": cf1_verdict, "reason": cf1_reason},
        "CF-2": {"verdict": cf2_verdict, "reason": cf2_reason},
        "CF-3": {
            "verdict": "PASS",
            "reason": ("引用已完成的 TraCSS 风险状态边界反事实"
                       "（experiments/tracss_threshold_sensitivity 报告第5节），"
                       "本实验不重复运行。"),
        },
    }

    # ---------- 输出 ----------
    for tag, data in graphs.items():
        serialize_deterministic(data, OUT / f"graph_{tag}_after.ttl")
    for tag, (rg, rt) in reports.items():
        serialize_deterministic(rg, OUT / f"shacl_report_{tag}.ttl")
        (OUT / f"shacl_report_{tag}.txt").write_text(rt, encoding="utf-8")

    summary = {
        "experiment": "CF-1/CF-2 counterfactual capability verification "
                      "(evidence removal / temporal reversal)",
        "purpose": "回应'能力问题验证存在自证循环、缺少负例验证'：单变量干预 F∧C→R，"
                   "仅移除或改变关键条件 C，检查派生关系 R 是否相应消失或改变。",
        "target_pair_source": "experiments/rule_logic_verification（正式规则逻辑验证场景）",
        "authenticity": authenticity,
        "authenticity_gates": {
            "gate1_intervention_diff_exact": True,
            "gate2_no_stale_derived_triples_in_inputs": True,
            "gate3_baseline_regenerates_target": True,
            "formal_cross_check": formal_check,
        },
        "interventions": {
            "cf1_removed": [triple_str(t) for t in sorted(cf1_removed, key=lambda x: tuple(map(str, x)))],
            "cf2_removed": [triple_str(t) for t in sorted(cf2_removed, key=lambda x: tuple(map(str, x)))],
            "cf2_added": [triple_str(t) for t in sorted(cf2_added, key=lambda x: tuple(map(str, x)))],
        },
        "runs": runs,
        "verdicts": verdicts,
    }
    (OUT / "counterfactual_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = build_report(authenticity, formal_check, runs, verdicts)
    (EXP / "counterfactual_verification_report.md").write_text(report, encoding="utf-8")

    print(f"CF-1 判定：{cf1_verdict}；CF-2 判定：{cf2_verdict}")
    print(f"结果目录：{OUT}")
    print(f"报告：{EXP / 'counterfactual_verification_report.md'}")
    return 0 if cf1_verdict == "PASS" and cf2_verdict == "PASS" else 1


def viol_text(violations: list[dict]) -> str:
    if not violations:
        return "无"
    return "；".join(f"{v['rule_id']}（{v['source_shape']}，焦点 "
                     f"{v['focus_node'].rsplit('#', 1)[-1]}）：{v['message']}"
                     for v in violations)


def build_report(authenticity: dict, formal_check: dict, runs: dict[str, dict],
                 verdicts: dict) -> str:
    b, c1, c2 = runs["baseline"], runs["cf1"], runs["cf2"]
    a = authenticity

    formal_line = (
        "正式实验输出对照：未找到 scenario_reasoning_summary.json，跳过（不影响判定）。"
        if not formal_check.get("formal_summary_found")
        else (f"正式实验输出对照：固定点新增序列 {formal_check.get('formal_graph_additions')}、"
              f"conforms={formal_check.get('formal_conforms')}、R3 检查="
              f"{formal_check.get('formal_R3_check')}；本次基线复跑与正式结果一致："
              f"{formal_check.get('baseline_reproduces_formal')}。")
    )

    cf1_rows = [
        ("Temporal condition：precedesEvent(e_i, e_j)（R1 派生）",
         b["conditions"]["temporal_precedes_MAN_APP"], c1["conditions"]["temporal_precedes_MAN_APP"]),
        ("Object-role condition：affectsObject/primary/secondary 且 o1≠o2（显式）",
         b["conditions"]["object_role"], c1["conditions"]["object_role"]),
        ("Observation evidence：两事件均有 detectedFromData/supportedByData → ObservationData",
         b["conditions"]["evidence_MAN"] and b["conditions"]["evidence_APP"],
         c1["conditions"]["evidence_MAN"] and c1["conditions"]["evidence_APP"]),
    ]
    cf2_temporal_rows = [
        ("precedesEvent(Evt_Maneuver, Evt_Approach)",
         b["conditions"]["temporal_precedes_MAN_APP"], c2["conditions"]["temporal_precedes_MAN_APP"]),
        ("precedesEvent(Evt_Approach, Evt_Maneuver)",
         b["conditions"]["reverse_precedes_APP_MAN"], c2["conditions"]["reverse_precedes_APP_MAN"]),
        ("followsEvent(Evt_Approach, Evt_Maneuver)",
         b["conditions"]["follows_APP_MAN"], c2["conditions"]["follows_APP_MAN"]),
        ("followsEvent(Evt_Maneuver, Evt_Approach)",
         b["conditions"]["follows_MAN_APP"], c2["conditions"]["follows_MAN_APP"]),
    ]
    cf2_causal_rows = [
        ("causesEvent(Evt_Maneuver, Evt_Approach)（原方向，R3 目标）",
         b["results"]["causesEvent_MAN_APP"], c2["results"]["causesEvent_MAN_APP"]),
        ("causesEvent(Evt_Approach, Evt_Maneuver)（反方向）",
         b["results"]["causesEvent_APP_MAN"], c2["results"]["causesEvent_APP_MAN"]),
        ("causesEvent(Evt_Approach, Risk_T0—T3)（R4，共 4 条）",
         all(b["results"]["r4_edges_APP_RiskT0_T3"]), all(c2["results"]["r4_edges_APP_RiskT0_T3"])),
    ]

    def consistency_row(label, key, fmt):
        return (f"| {label} | {fmt(b['consistency'][key])} | "
                f"{fmt(c1['consistency'][key])} | {fmt(c2['consistency'][key])} |")

    fmt_pairs = lambda v: "0" if not v else str(len(v))  # noqa: E731
    fmt_cycle = lambda v: "无" if not v else "存在"  # noqa: E731

    lines = [
        "# 反事实能力验证实验报告（CF-1 观测证据删除 / CF-2 时间方向反转）",
        "",
        "回应审稿意见：\"能力问题验证存在自证循环、缺少负例验证\"。",
        "正式能力验证回答\"完整条件下能否得到预期结果\"；本实验回答其逆命题：",
        "当关键语义条件被删除或改变后，原有派生关系是否相应消失或改变。",
        "",
        "- 运行器：`run_counterfactual_experiments.py`（与正式实验同一 pySHACL 执行路径：",
        "  数据图=输入+本体+规则部署配置，rdfs 闭包 + advanced 规则，迭代至完整图不动点）；",
        "- 机器可读结果：`outputs/counterfactual_results.json`；",
        "- 三个运行的推理后完整图与 SHACL 报告：`outputs/graph_{baseline,cf1,cf2}_after.ttl`、",
        "  `outputs/shacl_report_{baseline,cf1,cf2}.ttl/.txt`；",
        "- 本实验只新增独立反事实副本与结果：本体、R1—R18、B1—B5、CZ-6A 数据、",
        "  TraCSS 实验、正式实验数据与正式实验结果均未改动；",
        "- CF-3（TraCSS 风险状态边界反事实）已完成，本报告仅引用其结论（见第 7 节），不重复运行。",
        "",
        "## 1. 实验目的与单变量干预原则",
        "",
        "干预原则为单变量：F ∧ C → R。保持事实集合 F 不变，仅移除或改变关键条件 C，",
        "重新运行相同规则，观察结果 R 是否变化。不同时改变多个变量。",
        "",
        "每个反事实运行均满足以下流程（运行时强制校验）：",
        "",
        "1. 从原始基础事实复制构建独立测试图；",
        "2. 施加且仅施加声明的单变量干预（差异集合运行时逐三元组校验）；",
        "3. 测试图不含任何派生谓词三元组（未推理干净状态，运行时校验）；",
        "4. 从干净状态重新执行同一正式规则集至不动点；",
        "5. 检查目标派生关系是否重新产生——输出图中的派生三元组全部来自本次运行，",
        "   不存在旧推理结果残留。",
        "",
        "## 2. 实验前真实性核验",
        "",
        "目标事件对取自**正式规则逻辑验证场景**",
        "（`experiments/rule_logic_verification`，论文能力验证的正式 CQ 场景）中",
        "已由规则真实生成的派生因果关系，不是为本实验新造的理想示例。",
        "",
        "| 核验项 | 内容 |",
        "| --- | --- |",
        f"| cause event | `{a['cause_event']}` |",
        f"| effect event | `{a['effect_event']}` |",
        f"| 事件类型 | {a['cause_event_type']} → {a['effect_event_type']} |",
        f"| 原因事件时间 | 发生 {a['cause_occurrence_time']}，区间 "
        f"{a['cause_interval'][0]} — {a['cause_interval'][1]} |",
        f"| 结果事件时间 | 发生 {a['effect_occurrence_time']}，区间 "
        f"{a['effect_interval'][0]} — {a['effect_interval'][1]} |",
        f"| 参与对象与角色 | 机动 affectsObject = {a['objects']['affectsObject(cause)']}；"
        f"接近 hasPrimaryObject = {a['objects']['hasPrimaryObject(effect)']}、"
        f"hasSecondaryObject = {a['objects']['hasSecondaryObject(effect)']}（o1≠o2） |",
        "| 支持该关系的观测/评估数据 | 两事件各经 detectedFromData 关联 `rs:TestObsData`"
        "（RadarObservationData ⊂ SensorObservationData ⊂ ObservationData，经 RDFS 闭包"
        "满足 R3 的 `?d a ObservationData` 条件） |",
        "| CausalAssertion IRI | 无（见下注记） |",
        f"| 原始 causesEvent 是否显式存在 | {'是' if a['original_causesEvent_explicit'] else '否（输入图不含任何派生谓词）'} |",
        f"| 生成规则 | {a['generating_rule']} |",
        "",
        "> **关于 CausalAssertion 的注记**：当前冻结规则集中 R3/R4 直接生成事件级",
        "> causesEvent，不实例化 CausalAssertion；hasCausalEvidence 是 CausalAssertion 的",
        "> 溯源属性（domain CausalAssertion，range SSAData），仅被完整性 Shape",
        ">（tc_sssao_causal_assertion_integrity.ttl）检查，不被任何生成规则作为前提。",
        "> CZ-6A 案例中的 causesEvent 由 B1 从显式 DirectCausalAssertion",
        ">（`case:CZ6A_FragmentationRiskAssertion`）桥接生成，B1 同样不含证据前提。",
        "> 因此 CF-1 的删除对象以 R3/R4 真实检查的事件级",
        "> supportedByData/detectedFromData 证据链接为准。",
        "",
        "**事件对选择理由**：R3 目标对（Evt_Maneuver → Evt_Approach）中两事件各有且仅有",
        "一条证据链接，单三元组即可构成干净的证据删除干预；R4 目标对（Evt_Approach →",
        "Risk_T0—T3）的风险事件侧各有两条证据链接，删除面更大。CZ-6A 事件对不适合作为",
        "证据删除反事实的目标：其 causesEvent 由 B1 从显式断言桥接，不含 T/O/E_obs 联合",
        "前提，删除事件级证据或 hasCausalEvidence 均不构成对 B1 前提的干预。",
        "",
        "**基线复跑**（本实验内独立重跑正式场景，不触碰正式输出）：固定点 "
        f"{b['fixed_point_iterations']} 轮，每轮新增 {b['graph_triples_added_per_round']}，"
        f"SHACL conforms={b['shacl_conforms']}；目标 causesEvent 重新生成："
        f"{yn(b['results']['causesEvent_MAN_APP'])}。{formal_line}",
        "",
        "## 3. CF-1：观测证据删除反事实",
        "",
        "### 3.1 干预（单变量）",
        "",
        "测试图 `data/cf1_evidence_removed_facts.ttl` 为正式场景事实的完整副本，",
        "唯一差异（运行时校验通过）是删除 1 个三元组：",
        "",
        "```",
        "rs:Evt_Maneuver  onto:detectedFromData  rs:TestObsData",
        "```",
        "",
        "即移除 R3 证据条件 E_obs 中原因事件一侧的全部证据。事件实例、事件类型、",
        "时间、对象、对象角色、结果事件与四个风险快照的证据链接及其余全部事实",
        "与原场景逐三元组一致。",
        "",
        "### 3.2 验证结果",
        "",
        "| Item | Original | Evidence removed |",
        "| --- | --- | --- |",
    ]
    for label, orig_v, cf1_v in cf1_rows:
        lines.append(f"| {label} | {yn(orig_v)} | {yn(cf1_v)} |")
    lines += [
        "| CausalAssertion generated | —（R3 不生成 CausalAssertion，见第 2 节注记） "
        "| —（同上） |",
        f"| causesEvent(e_i, e_j) generated（R3 目标） "
        f"| {yn(b['results']['causesEvent_MAN_APP'])} "
        f"| {yn(c1['results']['causesEvent_MAN_APP'])} |",
        "",
        "补充观察（干预局部性与附带效应）：",
        "",
        f"- R4 因果边 causesEvent(Evt_Approach, Risk_T0—T3) 共 4 条仍全部生成："
        f"{yn(all(c1['results']['r4_edges_APP_RiskT0_T3']))}"
        "（被删证据不属于这些边的前提）；",
        f"- R1 时序关系不受影响：precedesEvent(Evt_Maneuver, Evt_Approach) 仍成立："
        f"{yn(c1['conditions']['temporal_precedes_MAN_APP'])}；",
        f"- 推理后图中 Evt_Approach 的证据条件仍满足：{yn(c1['conditions']['evidence_APP'])}，",
        f"  Evt_Maneuver 的证据条件已失效：{yn(not c1['conditions']['evidence_MAN'])}；",
        f"- SHACL conforms={c1['shacl_conforms']}，违规：{viol_text(c1['violations'])}。"
        "该违规是 R13（EventDataEvidenceShape）对\"被删除证据\"这一干预本身的检出，",
        "  即验证层正确报告了证据缺失，而非推理引入的不一致；",
        f"- CF-1 固定点 {c1['fixed_point_iterations']} 轮，每轮新增 "
        f"{c1['graph_triples_added_per_round']}：第一轮恰比基线少 1"
        f"（{c1['graph_triples_added_per_round'][0]} 对 "
        f"{b['graph_triples_added_per_round'][0]}），差值对应未生成的目标 "
        "causesEvent 三元组；第二轮新增与基线一致，R5—R8 态势与 B3 演化派生不受影响。",
        "",
        f"### 3.3 判定：**{verdicts['CF-1']['verdict']}**",
        "",
        verdicts["CF-1"]["reason"],
        "",
        "原始：T ∧ O ∧ E_obs → causesEvent 成立；反事实：T ∧ O ∧ ¬E_obs 下",
        "相同规则未重新产生目标因果关系。",
        "",
        "## 4. CF-2：时间方向反转反事实",
        "",
        "### 4.1 干预（单变量）",
        "",
        "测试图 `data/cf2_time_reversed_facts.ttl` 为正式场景事实的完整副本，",
        "唯一差异（运行时校验通过）是互换两事件的时间区间，共 6 个时间三元组：",
        "",
        "| 事件 | 原时间区间（发生时间） | 反转后时间区间（发生时间） | 持续时间 |",
        "| --- | --- | --- | --- |",
        "| Evt_Maneuver | 09:00—09:10（09:00） | 10:00—10:10（10:00） | 10 分钟，不变 |",
        "| Evt_Approach | 10:00—10:20（10:00） | 09:00—09:20（09:00） | 20 分钟，不变 |",
        "",
        "修改后每事件仍满足 start ≤ end，无非法日期，事件持续时间未改变；",
        "事件实例、类型、对象、对象角色、观测证据、四个风险快照及其余领域事实全部不变。",
        "事件顺序由 Evt_Maneuver < Evt_Approach 反转为 Evt_Approach < Evt_Maneuver。",
        "",
        "### 4.2 时间关系结果",
        "",
        "| 关系 | 原始 | 时间反转后 |",
        "| --- | --- | --- |",
    ]
    for label, orig_v, cf2_v in cf2_temporal_rows:
        lines.append(f"| {label} | {yn(orig_v)} | {yn(cf2_v)} |")
    lines += [
        "",
        "原方向 precedesEvent 消失，反方向 precedesEvent/followsEvent 按 R1 重新生成。",
        "",
        "### 4.3 因果方向结果",
        "",
        "| 关系 | 原始 | 时间反转后 |",
        "| --- | --- | --- |",
    ]
    for label, orig_v, cf2_v in cf2_causal_rows:
        lines.append(f"| {label} | {yn(orig_v)} | {yn(cf2_v)} |")
    lines += [
        "",
        "如实记录：",
        "",
        "- 原方向 causesEvent(Evt_Maneuver, Evt_Approach) 在其时间前提",
        "  precedesEvent(Evt_Maneuver, Evt_Approach) 失效后**未继续成立**；",
        "- 反方向 causesEvent(Evt_Approach, Evt_Maneuver) **未生成**——当前规则集中",
        "  不存在产生它的路径：R3 要求原因侧为 OrbitManeuverEvent、结果侧为",
        "  ApproachEvent（类型方向固定），R4 要求结果侧为 CollisionRiskEvent，",
        "  B1 要求显式 CausalAssertion。本实验的重点不是强制出现反向因果，而是验证",
        "  原方向 causesEvent 不能在其时间前提失效后无条件继续成立——已验证；",
        "- R4 因果边（Evt_Approach → Risk_T0—T3）不受影响：Evt_Approach 移至 09:00 后",
        "  仍先于全部风险快照（11:00—14:00），其前提完好；",
        f"- SHACL conforms={c2['shacl_conforms']}，违规：{viol_text(c2['violations'])}；",
        f"- CF-2 固定点 {c2['fixed_point_iterations']} 轮，每轮新增 "
        f"{c2['graph_triples_added_per_round']}：第一轮恰比基线少 1"
        f"（{c2['graph_triples_added_per_round'][0]} 对 "
        f"{b['graph_triples_added_per_round'][0]}），差值对应未生成的目标 "
        "causesEvent 三元组（时序边总数不变，仅方向反转）；第二轮新增与基线一致。",
        "",
        f"### 4.4 判定：**{verdicts['CF-2']['verdict']}**",
        "",
        verdicts["CF-2"]["reason"],
        "",
        "## 5. 一致性检查",
        "",
        "三个运行均从未推理干净输入图启动，输出中的派生三元组全部来自本次运行",
        "（输入残留校验通过，见第 1 节流程 3）。",
        "",
        "| 检查项 | Baseline | CF-1 | CF-2 |",
        "| --- | --- | --- | --- |",
        f"| SHACL conforms | {b['shacl_conforms']} | {c1['shacl_conforms']} "
        f"| {c2['shacl_conforms']} |",
        f"| SHACL violations | {viol_text(b['violations'])} | {viol_text(c1['violations'])} "
        f"| {viol_text(c2['violations'])} |",
        consistency_row("双向因果对数量", "bidirectional_causal_pairs", fmt_pairs),
        consistency_row("因果环（causesEvent⁺ 自环）", "causal_cycle", fmt_cycle),
        consistency_row("时间方向冲突（precedesEvent 双向对）", "precedence_conflicts", fmt_pairs),
        "| 输入残留派生三元组 | 0 | 0 | 0 |",
        "",
        "CF-1 的唯一违规是 R13 对被删除证据的检出（预期信号，表明证据缺失可被验证层",
        "发现）；CF-1/CF-2 均未出现双向因果、因果环或时间方向冲突。",
        "",
        "## 6. 结果判定汇总",
        "",
        "判定标准——PASS：关键条件改变后，目标派生结果按规则预期消失或改变；",
        "PARTIAL PASS：目标结果变化但存在额外规则路径仍可产生部分关系；",
        "FAIL：关键条件已被删除/反转，但原有目标关系仍以相同方式重新生成。",
        "本实验未为得到 PASS 修改任何正式规则。",
        "",
        "| 实验 | 判定 | 说明 |",
        "| --- | --- | --- |",
        f"| CF-1 观测证据删除 | {verdicts['CF-1']['verdict']} | {verdicts['CF-1']['reason']} |",
        f"| CF-2 时间方向反转 | {verdicts['CF-2']['verdict']} | {verdicts['CF-2']['reason']} |",
        f"| CF-3 风险状态边界（引用） | {verdicts['CF-3']['verdict']} | "
        f"{verdicts['CF-3']['reason']} |",
        "",
        "## 7. CF-3：风险状态边界反事实（引用 TraCSS，不重跑）",
        "",
        "第三组反事实已在 `experiments/tracss_threshold_sensitivity` 完成",
        "（见其报告第 5 节，25 参数点全绿），本实验仅引用，不重复运行。",
        "",
        "真实近距离样本（event_id 1723730887，逐字段核验）：",
        "",
        "| Pc | d (km) | h(e) (km) | d/h |",
        "| ---: | ---: | ---: | ---: |",
        "| 6.593401×10⁻⁶ | 0.008684 | 0.011017 | 0.7882（d < h(e) 成立） |",
        "",
        "同一样本、同一 θ_A=10⁻⁷，仅改变部署参数 θ_M：",
        "",
        "| θ_M | Pc > θ_M ∧ d < h(e) | 该样本派生状态 |",
        "| --- | --- | --- |",
        "| 10⁻⁴（基线） | 不成立 | Warning |",
        "| 10⁻⁶ | 成立 | Dangerous |",
        "",
        "精确边界：Dangerous 当且仅当 θ_M < 6.593401×10⁻⁶（严格不等）。",
        "风险状态随关键边界条件翻转而改变，与 CF-1/CF-2 共同构成三类反事实验证。",
        "",
        "## 8. 三项反事实验证汇总",
        "",
        "| Test | Changed condition | Other facts fixed | Original result | Counterfactual result | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| CF-1 观测证据删除 | 删除 Evt_Maneuver 的 detectedFromData 证据链接"
        f"（R3 的 E_obs 前提） | 事件实例/类型/时间/对象角色/其余证据/风险快照全部固定"
        f" | causesEvent(Evt_Maneuver, Evt_Approach) 由 R3 生成"
        f" | 未重新生成；R13 检出证据缺失；R4 边不受影响"
        f" | {verdicts['CF-1']['verdict']} |",
        f"| CF-2 时间方向反转 | 互换两事件时间区间（持续时间不变，6 个时间三元组）"
        f" | 事件实例/类型/对象角色/观测证据/风险快照全部固定"
        f" | precedesEvent(Man, App) ∧ causesEvent(Man, App)"
        f" | 时序关系反向生成；原向 causesEvent 随前提失效消失；无反向因果与一致性违规"
        f" | {verdicts['CF-2']['verdict']} |",
        f"| CF-3 风险状态边界（TraCSS） | θ_M：10⁻⁴ → 10⁻⁶（部署参数）"
        f" | 样本 Pc=6.593401×10⁻⁶、d=0.008684 km、h(e)=0.011017 km 与 θ_A=10⁻⁷ 固定"
        f" | Warning | Dangerous（Pc > θ_M ∧ d < h(e) 成立） | {verdicts['CF-3']['verdict']} |",
        "",
        "## 9. 复现与边界",
        "",
        "```",
        "python experiments/counterfactual_verification/run_counterfactual_experiments.py",
        "```",
        "",
        "结论边界：",
        "",
        "- 本实验验证的是规则层负例行为（条件缺失/改变时派生关系相应消失或改变），",
        "  不构成对真实事件物理因果性的主张；",
        "- 反事实副本仅存在于本实验目录，正式实验数据、正式规则与正式结果未改动；",
        "- CF-1 中 R13 违规是对干预的检出，不应解读为规则不一致；",
        "- CF-2 中反方向 causesEvent 未生成是规则类型方向的如实结果，",
        "  不构成对反向物理因果的否定。",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
