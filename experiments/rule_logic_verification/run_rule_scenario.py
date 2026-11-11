"""运行通用规则逻辑验证场景（人工构造数据，非真实历史事件）。

验证通用规则 R1、R3--R8 与桥接规则 B3 在给定条件下的推导行为：
- 推理前不声明 precedesEvent / causesEvent / leadsToState / transitsTo / degradesTo；
- 仅使用主规则文件 rules/tc_sssao_rules.ttl（不含任何案例专属规则）；
- M2 第二阶段：场景含同一交会目标对的四个连续风险评估快照（Risk_T0--T3），
  R5--R8 对每次快照各生成一个态势状态（含 hasSeverityRank 0--3），
  B3 在相邻快照的派生状态之间建立 transitsTo（2→3 级时同时 degradesTo）。

统计口径（场景ABox三元组）：
- 场景节点 = rule-scenario# 命名空间内的输入实例
           ∪ 由场景中 CollisionRiskEvent 经场景键派生的 onto:derived_* 状态实例；
- 场景ABox三元组 = 主语或宾语属于场景节点的全部三元组，
  因此包含派生状态实例的类型断言以及 Normal→Attention、Attention→Warning、
  Warning→Dangerous 等状态关系三元组。

固定点判断：比较一轮规则执行前后**完整数据图**的差集，
确保仅涉及 onto# 命名空间派生节点的新三元组也能被检测。
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


def find_project_root(start: Path) -> Path:
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / "ontology" / "tc_sssao.owl").exists():
            return p
    raise RuntimeError("未找到TC-SSSAO工程根目录。")


BASE = find_project_root(Path(__file__).parent)
EXP = Path(__file__).resolve().parent
OUT = EXP / "outputs"
OWL = BASE / "ontology" / "tc_sssao.owl"
MAIN_RULES = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG = BASE / "rules" / "tc_sssao_rule_config.ttl"
FACTS = EXP / "data" / "scenario_facts.ttl"

ONTO = Namespace("https://w3id.org/tc-sssao#")
RS = Namespace("https://w3id.org/tc-sssao/data/rule-scenario#")
RS_PREFIX = str(RS)
STATE_KINDS = ("normal", "attention", "warning", "dangerous")


def derived_state(kind: str, event: URIRef) -> URIRef:
    """与规则一致的派生状态IRI：onto:derived_<kind>_state_<LCASE(SHA256(STR(e)))>。"""
    digest = hashlib.sha256(str(event).encode("utf-8")).hexdigest().lower()
    return URIRef(f"https://w3id.org/tc-sssao#derived_{kind}_state_{digest}")


def scenario_nodes(graph: Graph) -> set[URIRef]:
    """场景节点：输入实例（rs#）＋由场景碰撞风险事件派生的状态实例（onto:derived_*）。"""
    nodes = {u for u in set(graph.subjects()) | set(graph.objects())
             if isinstance(u, URIRef) and str(u).startswith(RS_PREFIX)}
    for event in set(graph.subjects(RDF.type, ONTO.CollisionRiskEvent)):
        if str(event).startswith(RS_PREFIX):
            for kind in STATE_KINDS:
                nodes.add(derived_state(kind, event))
    return nodes


def scenario_abox(graph: Graph, nodes: set[URIRef]) -> set[tuple]:
    """场景ABox三元组：主语或宾语属于场景节点的三元组。"""
    return {t for t in graph if t[0] in nodes or (isinstance(t[2], URIRef) and t[2] in nodes)}


def local_name(value) -> str:
    text = str(value)
    name = text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    for kind in STATE_KINDS:
        prefix = f"derived_{kind}_state_"
        if name.startswith(prefix):
            return f"derived_{kind}_state_{name[len(prefix):][:8]}"
    return name


def is_derived_state(node) -> bool:
    return isinstance(node, URIRef) and str(node).startswith(str(ONTO) + "derived_")


# 推理前显式输入关系（黑色实线）
EXPLICIT_PROPS = (
    ONTO.hasOrbit, ONTO.involvesObject, ONTO.hasPrimaryObject,
    ONTO.hasSecondaryObject, ONTO.affectsObject, ONTO.generatesData,
    ONTO.detectedFromData, ONTO.supportedByData,
)
# 推理新增关系（红色虚线）
INFERRED_PROPS = (
    ONTO.precedesEvent, ONTO.followsEvent, ONTO.causesEvent,
    ONTO.leadsToState, ONTO.transitsTo, ONTO.degradesTo,
    ONTO.recoversTo,
)
# 写入节点标签的关键数据属性（不展开为数据属性边）
LABEL_PROPS = (
    (ONTO.hasOccurrenceTime, "发生时间", lambda v: str(v)[11:16]),
    (ONTO.hasRelativeDistance, "相对距离", lambda v: f"{float(v):g} km"),
    (ONTO.hasCollisionProbability, "碰撞概率", lambda v: f"{float(v):g}"),
    (ONTO.hasPredictedMissDistance, "预测最近交会距离", lambda v: f"{float(v):g} km"),
    (ONTO.hasCombinedHardBodyRadius, "组合硬体半径", lambda v: f"{float(v):g} km"),
)
DERIVED_STATE_TYPES = (
    ONTO.NormalSituationState, ONTO.AttentionSituationState,
    ONTO.WarningSituationState, ONTO.DangerousSituationState,
)


def node_label(g_in: Graph, g_full: Graph, node: URIRef) -> str:
    """节点标签：实例名 + 直接类型 + 关键数据属性值（时间/距离/风险参数）。"""
    lines = [local_name(node)]
    types = [t for t in g_in.objects(node, RDF.type)
             if isinstance(t, URIRef) and str(t).startswith(str(ONTO))]
    if not types and is_derived_state(node):
        types = [t for t in DERIVED_STATE_TYPES if (node, RDF.type, t) in g_full]
    if types:
        lines.append(f"({local_name(types[0])})")
    for prop, title, fmt in LABEL_PROPS:
        for val in g_in.objects(node, prop):
            try:
                lines.append(f"{title} {fmt(val)}")
            except (ValueError, TypeError):
                lines.append(f"{title} {val}")
    return "\\n".join(lines)


def write_dot(path: Path, g_in: Graph, g_full: Graph,
              explicit: set[tuple], inferred: set[tuple]) -> None:
    """生成图4-3的DOT：黑色实线=推理前显式关系，红色虚线=推理新增关系，
    浅黄色填充=规则生成的派生状态实例；时间/距离/风险参数写入节点标签。"""
    edges = []
    nodes: set[URIRef] = set()
    for s, p, o in sorted(explicit, key=lambda x: tuple(map(str, x))):
        if p in EXPLICIT_PROPS and isinstance(o, URIRef):
            edges.append((s, p, o, False))
            nodes.add(s); nodes.add(o)
    for s, p, o in sorted(inferred, key=lambda x: tuple(map(str, x))):
        if p in INFERRED_PROPS and isinstance(o, URIRef):
            edges.append((s, p, o, True))
            nodes.add(s); nodes.add(o)
    lines = ["digraph G {", '  rankdir="LR";',
             '  node [shape=box, fontname="SimHei"];',
             '  edge [fontname="SimHei"];']
    for n in sorted(nodes, key=str):
        label = node_label(g_in, g_full, n)
        if is_derived_state(n):
            lines.append(f'  "{local_name(n)}" [label="{label}", style="filled", fillcolor="lightyellow"];')
        else:
            lines.append(f'  "{local_name(n)}" [label="{label}"];')
    for s, p, o, inferred_flag in edges:
        style = 'color="red", style="dashed"' if inferred_flag else 'color="black", style="solid"'
        lines.append(f'  "{local_name(s)}" -> "{local_name(o)}" [label="{local_name(p)}", {style}];')
    lines.append("}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        from pyshacl import validate
    except ImportError:
        print("缺少pyshacl。请先执行：python -m pip install -r requirements.txt", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    input_graph = Graph()
    input_graph.parse(FACTS, format="turtle")
    input_nodes = scenario_nodes(input_graph)
    explicit_abox = scenario_abox(input_graph, input_nodes)
    input_graph.serialize(OUT / "graph_before.ttl", format="turtle")

    ontology = Graph(); ontology.parse(OWL, format="xml")
    rules = Graph(); rules.parse(MAIN_RULES, format="turtle")
    # 规则部署配置（θ参数）必须并入数据图：pySHACL 的 SPARQL 规则仅对数据图求值。
    config = Graph(); config.parse(RULE_CONFIG, format="turtle")
    sys.path.insert(0, str(BASE))
    from scripts.validate.check_rule_input_preflight import require_formal_input
    require_formal_input(input_graph, config, ontology)
    data = input_graph + ontology + config

    abox_additions: list[int] = []
    graph_additions: list[int] = []
    max_iter = 10
    conforms = False
    report_graph = Graph()
    report_text = ""

    for iteration in range(1, max_iter + 1):
        before_graph = set(data)
        before_abox = scenario_abox(data, scenario_nodes(data))
        conforms, report_graph, report_text = validate(
            data_graph=data,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        after_graph = set(data)
        after_abox = scenario_abox(data, scenario_nodes(data))
        graph_added = len(after_graph - before_graph)
        abox_added = len(after_abox - before_abox)
        graph_additions.append(graph_added)
        abox_additions.append(abox_added)
        print(f"第{iteration}轮新增：完整数据图{graph_added}，场景ABox{abox_added}")
        if graph_added == 0:
            break
    else:
        raise RuntimeError(f"规则在{max_iter}轮内未收敛：{graph_additions}")

    # pyshacl的RDFS闭包会为每个字面量生成"字面量 a rdfs:Resource"等公理化三元组。
    # 字面量作主语不是合法RDF，Protégé/Jena等严格解析器会拒绝整个文件，需清除。
    invalid_subjects = [t for t in data if isinstance(t[0], Literal)]
    for t in invalid_subjects:
        data.remove(t)
    if invalid_subjects:
        print(f"清理RDFS闭包产生的非法字面量主语三元组：{len(invalid_subjects)}")

    final_nodes = scenario_nodes(data)
    final_abox = scenario_abox(data, final_nodes)
    inferred_abox = final_abox - explicit_abox

    data.serialize(OUT / "graph_after_full.ttl", format="turtle")
    report_graph.serialize(OUT / "shacl_report.ttl", format="turtle")
    (OUT / "shacl_report.txt").write_text(report_text, encoding="utf-8")

    risk0 = RS.Risk_T0
    risk1 = RS.Risk_T1
    risk2 = RS.Risk_T2
    risk3 = RS.Risk_T3
    risk4 = RS.Risk_T4
    normal0 = derived_state("normal", risk0)
    attention1 = derived_state("attention", risk1)
    warning2 = derived_state("warning", risk2)
    dangerous3 = derived_state("dangerous", risk3)
    normal4 = derived_state("normal", risk4)
    int0 = Literal(0); int1 = Literal(1); int2 = Literal(2); int3 = Literal(3); int0b = Literal(0)

    expected = {
        "R1_机动先于接近": (RS.Evt_Maneuver, ONTO.precedesEvent, RS.Evt_Approach),
        "R1_接近先于首个风险评估": (RS.Evt_Approach, ONTO.precedesEvent, risk0),
        "R1_风险快照时序链": (risk0, ONTO.precedesEvent, risk1),
        "R1_风险快照时序链2": (risk2, ONTO.precedesEvent, risk3),
        "R1_风险快照时序链3": (risk3, ONTO.precedesEvent, risk4),
        "R1_逆向关系": (risk0, ONTO.followsEvent, RS.Evt_Approach),
        "R3_机动导致接近": (RS.Evt_Maneuver, ONTO.causesEvent, RS.Evt_Approach),
        "R4_接近导致风险T0": (RS.Evt_Approach, ONTO.causesEvent, risk0),
        "R4_接近导致风险T1": (RS.Evt_Approach, ONTO.causesEvent, risk1),
        "R4_接近导致风险T2": (RS.Evt_Approach, ONTO.causesEvent, risk2),
        "R4_接近导致风险T3": (RS.Evt_Approach, ONTO.causesEvent, risk3),
        "R4_接近导致风险T4": (RS.Evt_Approach, ONTO.causesEvent, risk4),
        "R5_T0正常态势": (risk0, ONTO.leadsToState, normal0),
        "R5_正常状态类型": (normal0, RDF.type, ONTO.NormalSituationState),
        "R5_正常状态级别0": (normal0, ONTO.hasSeverityRank, int0),
        "R6_T1关注态势": (risk1, ONTO.leadsToState, attention1),
        "R6_关注状态级别1": (attention1, ONTO.hasSeverityRank, int1),
        "R7_T2预警态势": (risk2, ONTO.leadsToState, warning2),
        "R7_预警状态级别2": (warning2, ONTO.hasSeverityRank, int2),
        "R8_T3危险态势": (risk3, ONTO.leadsToState, dangerous3),
        "R8_危险状态级别3": (dangerous3, ONTO.hasSeverityRank, int3),
        "R5_T4恢复态势": (risk4, ONTO.leadsToState, normal4),
        "R5_T4正常状态类型": (normal4, RDF.type, ONTO.NormalSituationState),
        "R5_T4正常状态级别0": (normal4, ONTO.hasSeverityRank, int0b),
        "B3_正常演化到关注": (normal0, ONTO.transitsTo, attention1),
        "B3_关注演化到预警": (attention1, ONTO.transitsTo, warning2),
        "B3_预警演化到危险": (warning2, ONTO.transitsTo, dangerous3),
        "B3_预警恶化为危险": (warning2, ONTO.degradesTo, dangerous3),
        "B3_危险恢复到正常": (dangerous3, ONTO.transitsTo, normal4),
        "B3_危险恢复到正常_recoversTo": (dangerous3, ONTO.recoversTo, normal4),
    }
    checks = {name: triple in data for name, triple in expected.items()}

    # 互斥性：每个风险事件只能关联一个四级状态（其他级别的派生态势不得存在）
    mutually_exclusive_absent = []
    for ev, expected_kind in ((risk0, "normal"), (risk1, "attention"),
                              (risk2, "warning"), (risk3, "dangerous"),
                              (risk4, "normal")):
        for kind in STATE_KINDS:
            if kind == expected_kind:
                continue
            mutually_exclusive_absent.append(
                (ev, ONTO.leadsToState, derived_state(kind, ev)))
    absent_checks = {f"互斥_无{local_name(o)}": triple not in data
                     for triple in mutually_exclusive_absent
                     for o in [triple[2]]}
    # B3 相邻性：T0 与 T2 之间存在 T1，不得直接建立跨快照转移
    warning_of_t2 = derived_state("warning", risk2)
    absent_checks["B3_不跨快照_N0直达W2"] = (normal0, ONTO.transitsTo, warning_of_t2) not in data
    absent_checks["B3_不跨快照_N0直达D3"] = (normal0, ONTO.transitsTo, dangerous3) not in data

    write_dot(OUT / "scenario_reasoning_graph.dot", input_graph, data,
              explicit_abox, inferred_abox)

    elapsed = time.perf_counter() - t_start

    summary = {
        "experiment": "TC-SSSAO generic rule logic verification scenario (synthetic)",
        "note": "人工构造数据，仅使用通用规则R1--R18与桥接规则B1--B3，不对应真实历史事件；"
                "五个连续风险评估快照 Risk_T0--T4（含危险到正常恢复），R5--R8 单快照单状态，B3 跨快照演化",
        "counting": "场景ABox三元组：主语或宾语属于场景节点（rs#输入实例 ∪ onto:derived_*派生状态实例）的三元组",
        "fixed_point_criterion": "完整数据图一轮前后差集为空",
        "fixed_point_iterations": len(graph_additions),
        "graph_triples_added_per_round": graph_additions,
        "scenario_abox_added_per_round": abox_additions,
        "shacl_conforms": bool(conforms),
        "explicit_scenario_abox_triples": len(explicit_abox),
        "final_scenario_abox_triples": len(final_abox),
        "inferred_scenario_abox_triples": len(inferred_abox),
        "elapsed_seconds": round(elapsed, 3),
        "checks": checks,
        "absent_checks": absent_checks,
        "all_expected_results_present": all(checks.values()),
        "all_absent_conditions_hold": all(absent_checks.values()),
    }
    (OUT / "scenario_reasoning_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 通用规则逻辑验证场景实验报告（人工构造数据）",
        "",
        "本场景为规则逻辑验证而人工构造，不对应任何真实历史事件。",
        "仅使用通用规则文件 rules/tc_sssao_rules.ttl（R1--R18），不含案例专属规则。",
        "",
        "统计口径：场景ABox三元组 = 主语或宾语属于场景节点的三元组；",
        "场景节点 = rs#输入实例 ∪ onto:derived_*派生状态实例。",
        "固定点判断：完整数据图一轮前后差集为空。",
        "",
        f"- 固定点迭代轮数：{len(graph_additions)}",
        f"- 每轮新增完整数据图三元组：{graph_additions}",
        f"- 每轮新增场景ABox三元组：{abox_additions}",
        f"- 推理前场景ABox三元组：{len(explicit_abox)}",
        f"- 推理后场景ABox三元组：{len(final_abox)}",
        f"- 新增场景ABox三元组：{len(inferred_abox)}",
        f"- 总运行时间（含本体解析）：{elapsed:.2f} s",
        f"- SHACL conforms：{conforms}",
        "",
        "## 预期结果检查",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'通过' if ok else '失败'}：{name}")
    lines.append("")
    lines.append("## 互斥与相邻性检查（预期不存在的三元组）")
    for name, ok in absent_checks.items():
        lines.append(f"- {'通过' if ok else '失败'}：{name}")
    lines += [
        "",
        "## 结论边界",
        "本场景验证通用规则在给定条件下的推导行为；",
        "不构成对真实事件的预测验证；R5—R8 对每次风险评估快照各关联一个态势状态，",
        "B3 描述同一交会目标对在连续评估之间的态势演化，派生状态关联不构成严格连续状态机。",
    ]
    (OUT / "scenario_reasoning_report.md").write_text("\n".join(lines), encoding="utf-8")

    all_ok = all(checks.values()) and all(absent_checks.values())
    print(f"SHACL conforms：{conforms}")
    print(f"预期推理结果全部存在：{all(checks.values())}")
    print(f"互斥与相邻性条件全部成立：{all(absent_checks.values())}")
    print(f"总运行时间：{elapsed:.2f} s")
    print(f"结果目录：{OUT}")
    return 0 if (all_ok and conforms) else 1


if __name__ == "__main__":
    raise SystemExit(main())
