"""运行 CZ-6A 2022-151B 单案例表示与推理实验（M3 第一阶段，证据化重构版）。

案例定位：公开来源（NASA ODQN、Wacker et al. 2025）负责给出解体事实与碎片
环境风险评估结论；TC-SSSAO 负责对这些来源支撑的知识进行语义组织，并通过
**主规则文件中的通用规则**完成关系桥接与安全语义投影：

- R1：事件时间关系（precedesEvent/followsEvent）；
- B1：显式 DirectCausalAssertion → 直接 causesEvent；
- B4：DebrisRiskEvent + RiskAssessmentData → 派生 PhysicalThreat/DebrisRisk
      及 indicatesThreat/mayManifestAsEvent/producesRisk（SHA256 稳定派生 IRI）；
- B5：显式 ResponseMeasure(respondsToEvent) → requiresResponseMeasure/
      respondsToThreat/threatMitigatedBy/mitigatesRisk/mitigatedBy。

本案例不加载任何 CZ-6A 专属 SHACL-SPARQL 推理规则（原
CZ6ALongTermDebrisReasoningShape 已于 M3 第一阶段删除，历史快照
仅存于项目外备份，不在活动树）。

固定点判断：比较一轮规则执行前后**完整数据图**的差集（派生威胁/风险实例
位于 onto: 命名空间，仅统计案例命名空间三元组可能漏检）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


def serialize_deterministic(g: Graph, path: Path) -> None:
    """字节级确定性 Turtle 序列化（2026-09-05 M5 Phase 1 修订）。

    pySHACL 定点迭代与 RDFS 闭包会向数据图引入运行间随机的 bnode 标识
    与插入顺序，导致同一内容每次序列化字节不同（图4-4/4-5 哈希钉两次
    观测到漂移：715bf565 -> d3e2c489 -> 90c3f9e7，三元组计数与语义
    回归 47/47 均不变）。本函数先用 rdflib.compare.to_canonical_graph
    规范化 bnode 标签，再按字符串序把三元组重插入新图，使同构图每次
    输出字节一致。仅稳定序列化形式，不改变任何语义内容（同构）。
    """
    from rdflib.compare import to_canonical_graph
    canon = to_canonical_graph(g)
    out = Graph()
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns)
    for t in sorted(canon, key=lambda x: (str(x[0]), str(x[1]), str(x[2]))):
        out.add(t)
    out.serialize(path, format="turtle")


def find_project_root(start: Path) -> Path:
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / "ontology" / "tc_sssao.owl").exists():
            return p
    raise RuntimeError("未找到TC-SSSAO工程根目录。请把本实验目录放到工程的experiments目录下。")


BASE = find_project_root(Path(__file__).parent)
EXP = Path(__file__).resolve().parent
OUT = EXP / "outputs"
OWL = BASE / "ontology" / "tc_sssao.owl"
MAIN_RULES = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG = BASE / "rules" / "tc_sssao_rule_config.ttl"
SCHEMA = EXP / "data" / "case_schema.ttl"
FACTS = EXP / "data" / "case_facts.ttl"

ONTO = Namespace("https://w3id.org/tc-sssao#")
CASE = Namespace("https://w3id.org/tc-sssao/data/cz6a-case#")
CASE_PREFIX = str(CASE)


def is_case_uri(value) -> bool:
    return isinstance(value, URIRef) and str(value).startswith(CASE_PREFIX)


def case_triples(graph: Graph) -> set[tuple]:
    return {t for t in graph if is_case_uri(t[0]) or is_case_uri(t[2])}


def derived_iri(kind: str, event: URIRef) -> URIRef:
    """与 B4 规则一致的派生实例 IRI：onto:derived_<kind>_<LCASE(SHA256(STR(e)))>。"""
    digest = hashlib.sha256(str(event).encode("utf-8")).hexdigest().lower()
    return URIRef(f"https://w3id.org/tc-sssao#derived_{kind}_{digest}")


def local_name(value) -> str:
    text = str(value)
    name = text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    for prefix in ("derived_physical_threat_", "derived_debris_risk_"):
        if name.startswith(prefix):
            return f"{prefix}{name[len(prefix):][:8]}"
    return name


def run_query(graph: Graph, path: Path) -> list[dict[str, str]]:
    rows = []
    result = graph.query(path.read_text(encoding="utf-8"))
    for row in result:
        rows.append({str(var): (str(val) if val is not None else "") for var, val in zip(result.vars, row)})
    return rows


def write_dot(path: Path, explicit: set[tuple], inferred: set[tuple]) -> None:
    wanted = {
        ONTO.precedesEvent, ONTO.followsEvent, ONTO.causesEvent,
        ONTO.indicatesThreat, ONTO.mayManifestAsEvent, ONTO.producesRisk,
        ONTO.requiresResponseMeasure, ONTO.respondsToEvent,
        ONTO.respondsToThreat, ONTO.threatMitigatedBy,
        ONTO.mitigatesRisk, ONTO.mitigatedBy,
        ONTO.leadsToState, ONTO.transitsTo,
    }
    lines = ["digraph G {", '  rankdir="LR";', '  node [shape=box, fontname="SimHei"];']
    for triples, inferred_flag in ((explicit, False), (inferred, True)):
        for s, p, o in sorted(triples, key=lambda x: tuple(map(str, x))):
            if p not in wanted or not isinstance(o, URIRef):
                continue
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
    input_graph.parse(SCHEMA, format="turtle")
    input_graph.parse(FACTS, format="turtle")
    explicit_case = case_triples(input_graph)
    input_graph.serialize(OUT / "graph_before.ttl", format="turtle")

    ontology = Graph(); ontology.parse(OWL, format="xml")
    # 只加载主通用规则文件：本案例不使用任何 CZ-6A 专属推理规则
    rules = Graph(); rules.parse(MAIN_RULES, format="turtle")
    # 规则部署配置（R5—R8 的 θAttentionPc/θMitigationPc 参数）必须并入数据图：
    # pySHACL 规则仅对数据图求值。本案例无 CollisionRiskEvent，R5—R8 不触发，
    # 并入配置保持规则求值路径一致。
    config = Graph(); config.parse(RULE_CONFIG, format="turtle")
    sys.path.insert(0, str(BASE))
    from scripts.validate.check_rule_input_preflight import require_formal_input
    require_formal_input(input_graph, config, ontology)
    data = input_graph + ontology + config

    additions: list[int] = []
    case_additions: list[int] = []
    max_iter = 10
    conforms = False
    report_graph = Graph()
    report_text = ""

    for iteration in range(1, max_iter + 1):
        before_graph = set(data)
        before_case = case_triples(data)
        conforms, report_graph, report_text = validate(
            data_graph=data,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        added = len(set(data) - before_graph)
        case_added = len(case_triples(data) - before_case)
        additions.append(added)
        case_additions.append(case_added)
        print(f"第{iteration}轮新增：完整数据图{added}，案例三元组{case_added}")
        if added == 0:
            break
    else:
        raise RuntimeError(f"规则在{max_iter}轮内未收敛：{additions}")

    # pyshacl的RDFS闭包会为每个字面量生成"字面量 a rdfs:Resource"等公理化三元组。
    # 字面量作主语不是合法RDF，Protégé/Jena等严格解析器会拒绝整个文件，需清除。
    invalid_subjects = [t for t in data if isinstance(t[0], Literal)]
    for t in invalid_subjects:
        data.remove(t)
    if invalid_subjects:
        print(f"清理RDFS闭包产生的非法字面量主语三元组：{len(invalid_subjects)}")

    final_case = case_triples(data)
    inferred_case = final_case - explicit_case

    full_graph_path = OUT / "graph_after_full.ttl"
    serialize_deterministic(data, full_graph_path)

    abox = Graph()
    for prefix, ns in input_graph.namespaces():
        abox.bind(prefix, ns)
    for triple in final_case:
        abox.add(triple)
    serialize_deterministic(abox, OUT / "case_abox_after.ttl")

    serialize_deterministic(report_graph, OUT / "shacl_report.ttl")
    (OUT / "shacl_report.txt").write_text(report_text, encoding="utf-8")

    with (OUT / "inferred_triples.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["subject", "predicate", "object"])
        for s, p, o in sorted(inferred_case, key=lambda x: tuple(map(str, x))):
            writer.writerow([str(s), str(p), str(o)])

    query_rows = []
    for query_path in sorted((EXP / "queries").glob("*.rq")):
        rows = run_query(data, query_path)
        for row in rows:
            query_rows.append({"query": query_path.stem, "result": json.dumps(row, ensure_ascii=False)})
    with (OUT / "query_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "result"])
        writer.writeheader(); writer.writerows(query_rows)

    frag = CASE.CZ6A_Fragmentation_2022
    risk = CASE.CZ6A_DebrisRiskEvent
    track = CASE.CZ6A_TrackingEvent_2023
    assess = CASE.CZ6A_DebrisRiskAssessment
    assertion = CASE.CZ6A_FragmentationRiskAssertion
    measure = CASE.ContinuousTrackingMeasure
    threat = derived_iri("physical_threat", risk)
    drisk = derived_iri("debris_risk", risk)

    # 通用规则预期输出：R1 时序、B1 因果桥接、B4 安全语义投影、B5 响应投影
    expected = {
        "R1_解体先于跟踪": (frag, ONTO.precedesEvent, track),
        "R1_跟踪跟随解体": (track, ONTO.followsEvent, frag),
        "B1_直接因果边": (frag, ONTO.causesEvent, risk),
        "B4_派生物理威胁": (threat, RDF.type, ONTO.PhysicalThreat),
        "B4_派生碎片风险": (drisk, RDF.type, ONTO.DebrisRisk),
        "B4_事件指示威胁": (risk, ONTO.indicatesThreat, threat),
        "B4_威胁表现为事件": (threat, ONTO.mayManifestAsEvent, risk),
        "B4_威胁产生风险": (threat, ONTO.producesRisk, drisk),
        "B5_威胁需要响应措施": (threat, ONTO.requiresResponseMeasure, measure),
        "B5_措施响应威胁": (measure, ONTO.respondsToThreat, threat),
        "B5_威胁被措施缓解": (threat, ONTO.threatMitigatedBy, measure),
        "B5_措施缓解风险": (measure, ONTO.mitigatesRisk, drisk),
        "B5_风险被措施缓解": (drisk, ONTO.mitigatedBy, measure),
    }
    checks = {name: triple in data for name, triple in expected.items()}

    # 显式输入检查：来源支撑知识必须在推理前已经存在
    explicit_checks = {
        "显式_风险评估数据": (assess, RDF.type, ONTO.RiskAssessmentData) in input_graph,
        "显式_碎片风险事件": (risk, RDF.type, ONTO.DebrisRiskEvent) in input_graph,
        "显式_因果断言": (assertion, RDF.type, ONTO.DirectCausalAssertion) in input_graph,
        "显式_响应措施关联事件": (measure, ONTO.respondsToEvent, risk) in input_graph,
    }

    # 反向检查：M3 第一阶段移除的内容不得再出现
    absent = {
        "无_案例专属规则Shape": (CASE.CZ6ALongTermDebrisReasoningShape, RDF.type, None) not in data
            and (None, None, CASE.CZ6ALongTermDebrisReasoningShape) not in data,
        "无_关注态势实例": not any(data.subjects(RDF.type, ONTO.AttentionSituationState)),
        "无_状态转移实例": not any(data.subjects(RDF.type, ONTO.StateTransition)),
        "无_风险事件leadsToState": not any(data.triples((risk, ONTO.leadsToState, None))),
        "无_风险事件hasRiskValue": not any(data.triples((risk, ONTO.hasRiskValue, None))),
        "无_因果断言置信度": not any(data.triples((assertion, ONTO.hasCausalConfidence, None))),
        "无_正常态势实例": not any(data.subjects(RDF.type, ONTO.NormalSituationState)),
    }
    checks.update(explicit_checks)
    checks.update(absent)

    write_dot(OUT / "case_reasoning_graph.dot", explicit_case, inferred_case)

    elapsed = time.perf_counter() - t_start

    summary = {
        "experiment": "CZ-6A 2022-151B case representation and reasoning (M3 phase 1, evidence-based)",
        "note": "解体事实与碎片环境风险评估来自公开来源（NASA ODQN、Wacker et al. 2025）；"
                "案例只加载主通用规则文件 rules/tc_sssao_rules.ttl，"
                "不含任何 CZ-6A 专属推理规则；统计口径为案例命名空间三元组。",
        "fixed_point_criterion": "完整数据图一轮前后差集为空",
        "fixed_point_iterations": len(additions),
        "graph_triples_added_per_round": additions,
        "case_triples_added_per_round": case_additions,
        "shacl_conforms": bool(conforms),
        "explicit_case_triples": len(explicit_case),
        "final_case_triples": len(final_case),
        "inferred_case_triples": len(inferred_case),
        "elapsed_seconds": round(elapsed, 3),
        "checks": checks,
        "all_expected_results_present": all(checks.values()),
    }
    (OUT / "case_reasoning_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# CZ-6A 2022-151B 单案例表示与推理实验报告（M3 第一阶段）",
        "",
        "案例定位：公开来源给出解体事实与碎片环境风险评估结论；TC-SSSAO 对来源支撑的",
        "显式知识进行语义组织，并由主规则文件中的通用规则（R1、B1、B4、B5）生成关系知识。",
        "本案例不加载任何 CZ-6A 专属 SHACL-SPARQL 推理规则。",
        "",
        f"- 固定点迭代轮数：{len(additions)}",
        f"- 每轮新增完整数据图三元组：{additions}",
        f"- 每轮新增案例三元组：{case_additions}",
        f"- 推理前案例三元组：{len(explicit_case)}",
        f"- 推理后案例三元组：{len(final_case)}",
        f"- 新增案例三元组：{len(inferred_case)}",
        f"- 总运行时间（含本体解析）：{elapsed:.2f} s",
        f"- SHACL conforms：{conforms}",
        "",
        "## 预期结果检查（通用规则输出、显式输入与移除项）",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'通过' if ok else '失败'}：{name}")
    lines += [
        "",
        "## 结论边界",
        "本实验验证真实来源知识在 TC-SSSAO 中的证据化表示与通用关系规则的执行结果；",
        "不用于证明 TC-SSSAO 能够从碎片数量和轨道高度独立发现长期碎片风险，",
        "也不用于证明具体碰撞预测准确率。",
    ]
    (OUT / "case_reasoning_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"SHACL conforms：{conforms}")
    print(f"预期推理结果全部存在：{all(checks.values())}")
    print(f"总运行时间：{elapsed:.2f} s")
    print(f"结果目录：{OUT}")
    return 0 if (all(checks.values()) and conforms) else 1


if __name__ == "__main__":
    raise SystemExit(main())
