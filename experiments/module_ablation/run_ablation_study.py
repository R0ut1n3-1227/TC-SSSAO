#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TC-SSSAO 模块消融、因果一致性故障注入与证据反事实实验。

回答的审稿问题：现有实验是否只是验证规则按定义运行？时序、因果、态势和
一致性模块分别对系统能力产生什么实际作用？

设计原则：
- 所有消融 variant 从同一份本体、同一份输入数据、同一份主规则库出发，
  仅通过在内存中禁用指定 onto:ruleModule 的规则 Shape 获得；
- 不修改任何规则的 WHERE/CONSTRUCT（NO_EVIDENCE_CONSTRAINT 除外：它是
  独立的证据反事实变体，仅在内存中复制 R3/R4 并删除证据图模式，
  主规则文件 rules/tc_sssao_rules.ttl 不被修改）；
- CQ 判定规则在脚本内固定（见 cq_verdict），不手工填写结果。

输入（全部 variant 共享，禁止按 variant 修改）：
- 四风险快照通用场景：rule_logic_verification/data/scenario_facts.ttl
- B1/B2 独立桥接夹具 + 时序重叠夹具：data/bridge_fixtures.ttl
主消融数据图 = 上述两项 + 本体 + 部署配置。

因果一致性故障注入（独立于主消融数据图，三个故障文件各自单独成图
运行，避免不同故障的焦点节点混入同一次检出结果）：
- data/causal_fault_F1.ttl：时间逆序因果（主检测器 R9）
- data/causal_fault_F2.ttl：双向互指（主检测器 R10；互指结构同时构成
  (causesEvent)+ 意义下长度为 2 的闭环，R11 为附加检测器）
- data/causal_fault_F3.ttl：三事件因果环（主检测器 R11）

证据反事实：data/evidence_counterfactual.ttl（E1/E2，单独成图运行；
E1 缺 R3 所需 ObservationData 证据，E2 缺 R4 所需 ObservationData 证据）。

输出：outputs/ 下 ablation_results.csv/.json、consistency_fault_results.csv、
evidence_counterfactual_results.csv、robustness_results.csv、
ablation_table.tex、robustness_table.tex、ablation_summary.json。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import SH

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parents[1].parent
EXP = BASE / "experiments" / "module_ablation"
DATA = EXP / "data"
OUT = EXP / "outputs"

OWL = BASE / "ontology" / "tc_sssao.owl"
RULES = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG = BASE / "rules" / "tc_sssao_rule_config.ttl"
SCENARIO_FACTS = BASE / "experiments" / "rule_logic_verification" / "data" / "scenario_facts.ttl"

ONTO = Namespace("https://w3id.org/tc-sssao#")
RS = Namespace("https://w3id.org/tc-sssao/data/rule-scenario#")
ABL = Namespace("https://w3id.org/tc-sssao/data/module-ablation#")
FLT = Namespace("https://w3id.org/tc-sssao/data/causal-fault-test#")
ECF = Namespace("https://w3id.org/tc-sssao/data/evidence-counterfactual#")

STATE_KINDS = ("normal", "attention", "warning", "dangerous")
STATE_TYPES = {
    "normal": ONTO.NormalSituationState,
    "attention": ONTO.AttentionSituationState,
    "warning": ONTO.WarningSituationState,
    "dangerous": ONTO.DangerousSituationState,
}

# 消融 variant → 禁用的模块标签（模块标签来自规则 Shape 上的 onto:ruleModule）
VARIANTS = {
    "FULL": (),
    "NO_TEMPORAL": ("Temporal",),
    "NO_CAUSAL": ("Causal",),
    "NO_SITUATION": ("Situation",),
    "NO_CONSISTENCY": ("Consistency",),
}

R3_SHAPE = ONTO.OrbitManeuverCausesApproachRuleShape
R4_SHAPE = ONTO.ApproachCausesCollisionRiskRuleShape
CONSISTENCY_SHAPES = (ONTO.CauseBeforeEffectShape, ONTO.CausalDirectionShape, ONTO.CausalCycleShape)


def derived_state_iri(event: URIRef, kind: str) -> URIRef:
    digest = hashlib.sha256(str(event).encode("utf-8")).hexdigest().lower()
    return URIRef(f"{ONTO}derived_{kind}_state_{digest}")


# ----------------------------------------------------------------------
# 规则图变体构造
# ----------------------------------------------------------------------

def _subject_closure(g: Graph, root: URIRef) -> set:
    """收集 root 及其经匿名节点可达的全部主语（用于整体摘除一个 Shape）。"""
    seen = {root}
    frontier = [root]
    while frontier:
        node = frontier.pop()
        for _, _, o in g.triples((node, None, None)):
            if isinstance(o, URIRef) and o not in seen and str(o).startswith(str(ONTO)):
                # Shape 内部不引用其他 onto: 资源作为主语，无需下钻 URIRef
                continue
            if not isinstance(o, URIRef) and not isinstance(o, Literal) and o not in seen:
                seen.add(o)
                frontier.append(o)
    return seen


def load_full_rules() -> Graph:
    g = Graph()
    g.parse(RULES, format="turtle")
    return g


def module_map(rules: Graph) -> dict[str, list[URIRef]]:
    """从规则图动态读取 模块标签 → Shape IRI 列表（onto:ruleModule）。"""
    mapping: dict[str, list[URIRef]] = {}
    for s, o in rules.subject_objects(ONTO.ruleModule):
        if isinstance(s, URIRef):
            mapping.setdefault(str(o), []).append(s)
    return {k: sorted(v, key=str) for k, v in sorted(mapping.items())}


def strip_modules(rules: Graph, modules: tuple[str, ...]) -> Graph:
    """在内存中删除指定模块的全部 Shape（含其匿名子结构），返回新图。"""
    g = Graph()
    for triple in rules:
        g.add(triple)
    mapping = module_map(g)
    for module in modules:
        shapes = mapping.get(module, [])
        if not shapes:
            raise RuntimeError(f"模块 {module} 在规则库中不存在")
        for shape in shapes:
            for subj in _subject_closure(g, shape):
                g.remove((subj, None, None))
    return g


# R3/R4 证据图模式（两行一组 × 2：UNION 证据模式 + 证据类型断言）
_EVIDENCE_LINE_PATTERNS = (
    re.compile(r"\{\s*\?e1 onto:supportedByData \?d1 \.\s*\}\s*UNION\s*\{\s*\?e1 onto:detectedFromData \?d1 \.\s*\}"),
    re.compile(r"\?d1 a onto:ObservationData \."),
    re.compile(r"\{\s*\?e2 onto:supportedByData \?d2 \.\s*\}\s*UNION\s*\{\s*\?e2 onto:detectedFromData \?d2 \.\s*\}"),
    re.compile(r"\?d2 a onto:ObservationData \."),
)


def make_no_evidence_rules(rules: Graph) -> Graph:
    """NO_EVIDENCE_CONSTRAINT：内存中复制完整规则图，仅摘除 R3/R4 的
    证据图模式（每条规则 4 行），其余文本保持逐字节一致。"""
    g = Graph()
    for triple in rules:
        g.add(triple)
    for shape in (R3_SHAPE, R4_SHAPE):
        rule_nodes = list(g.objects(shape, SH.rule))
        assert len(rule_nodes) == 1, f"{shape} 应恰有一条 sh:rule"
        constructs = list(g.objects(rule_nodes[0], SH.construct))
        assert len(constructs) == 1, f"{shape} 应恰有一条 sh:construct"
        original = str(constructs[0])
        modified = original
        for pat in _EVIDENCE_LINE_PATTERNS:
            modified, n = pat.subn("", modified)
            assert n == 1, f"{shape} 证据模式未精确匹配一次: {pat.pattern}"
        assert "supportedByData" not in modified and "detectedFromData" not in modified
        g.remove((rule_nodes[0], SH.construct, constructs[0]))
        g.add((rule_nodes[0], SH.construct, Literal(modified)))
    return g


# ----------------------------------------------------------------------
# 推理执行（与 rule_logic_verification/run_rule_scenario.py 相同的固定点协议）
# ----------------------------------------------------------------------

def run_to_fixed_point(data: Graph, rules: Graph, max_iter: int = 10):
    """Formal module deployment; mandatory current-input preflight."""
    import sys
    sys.path.insert(0, str(BASE))
    from scripts.validate.check_rule_input_preflight import require_formal_input
    require_formal_input(data, Graph(), Graph())
    return run_diagnostic_to_fixed_point(data, rules, max_iter)


def run_diagnostic_to_fixed_point(data: Graph, rules: Graph, max_iter: int = 10):
    """外部固定点包装器：重复执行 pySHACL（RDFS + advanced）直至完整数据图
    差集为零。返回 (conforms, report_graph, report_text, 每轮新增)。"""
    from pyshacl import validate

    conforms, report_graph, report_text = False, Graph(), ""
    additions: list[int] = []
    for _ in range(1, max_iter + 1):
        before = set(data)
        conforms, report_graph, report_text = validate(
            data_graph=data, shacl_graph=rules, ont_graph=None,
            inference="rdfs", advanced=True, inplace=True, debug=False,
        )
        added = len(set(data) - before)
        additions.append(added)
        if added == 0:
            break
    else:
        raise RuntimeError(f"规则在{max_iter}轮内未收敛：{additions}")
    # 清理 RDFS 闭包产生的非法字面量主语三元组
    invalid = [t for t in data if isinstance(t[0], Literal)]
    for t in invalid:
        data.remove(t)
    return conforms, report_graph, report_text, additions


def load_graph(path: Path, fmt: str = "turtle") -> Graph:
    g = Graph()
    g.parse(path, format=fmt)
    return g


def build_main_data() -> Graph:
    """主消融数据图：M2 场景 + 桥接/重叠夹具 + 本体 + 部署配置。
    故障夹具不在此合并——F1—F3 各自独立成图运行（run_fault_injection）。"""
    data = Graph()
    for path in (SCENARIO_FACTS, DATA / "bridge_fixtures.ttl"):
        data += load_graph(path)
    data += load_graph(OWL, "xml")
    data += load_graph(RULE_CONFIG)
    return data


# ----------------------------------------------------------------------
# 探针（每 variant 固定检查清单）
# ----------------------------------------------------------------------

def probe_variant(data: Graph) -> dict:
    """对收敛后的数据图执行固定探针，返回模块能力与 CQ 子项的布尔结果。"""
    has = lambda s, p, o: (s, p, o) in data

    # Temporal：R1 事件先后（场景链）+ R2 重叠（夹具）
    precedence_ok = all([
        has(RS.Evt_Maneuver, ONTO.precedesEvent, RS.Evt_Approach),
        has(RS.Evt_Approach, ONTO.precedesEvent, RS.Risk_T0),
        has(RS.Risk_T0, ONTO.precedesEvent, RS.Risk_T1),
        has(RS.Risk_T1, ONTO.precedesEvent, RS.Risk_T2),
        has(RS.Risk_T2, ONTO.precedesEvent, RS.Risk_T3),
        has(RS.Evt_Approach, ONTO.followsEvent, RS.Evt_Maneuver),
    ])
    overlap_ok = all([
        has(ABL.EvtOverlapA, ONTO.overlapsWithEvent, ABL.EvtOverlapB),
        has(ABL.EvtOverlapB, ONTO.overlapsWithEvent, ABL.EvtOverlapA),
    ])

    # Causal：R3 机动→接近；R4 接近→四个风险快照
    causal_ok = all([
        has(RS.Evt_Maneuver, ONTO.causesEvent, RS.Evt_Approach),
        has(RS.Evt_Approach, ONTO.causesEvent, RS.Risk_T0),
        has(RS.Evt_Approach, ONTO.causesEvent, RS.Risk_T1),
        has(RS.Evt_Approach, ONTO.causesEvent, RS.Risk_T2),
        has(RS.Evt_Approach, ONTO.causesEvent, RS.Risk_T3),
    ])

    # Situation：R5—R8 四快照 → 四级状态（类型 + 严重度 + leadsToState）
    risk_events = {"normal": RS.Risk_T0, "attention": RS.Risk_T1,
                   "warning": RS.Risk_T2, "dangerous": RS.Risk_T3}
    states_ok = True
    for rank, (kind, evt) in enumerate(risk_events.items()):
        st = derived_state_iri(evt, kind)
        states_ok &= all([
            has(evt, ONTO.leadsToState, st),
            has(st, RDF.type, STATE_TYPES[kind]),
            has(st, ONTO.hasSeverityRank, Literal(rank)),
        ])

    # Evolution：B3 相邻演化 transitsTo ×3 + 预警→危险 degradesTo ×1
    evolution_ok = all([
        has(derived_state_iri(RS.Risk_T0, "normal"), ONTO.transitsTo,
            derived_state_iri(RS.Risk_T1, "attention")),
        has(derived_state_iri(RS.Risk_T1, "attention"), ONTO.transitsTo,
            derived_state_iri(RS.Risk_T2, "warning")),
        has(derived_state_iri(RS.Risk_T2, "warning"), ONTO.transitsTo,
            derived_state_iri(RS.Risk_T3, "dangerous")),
        has(derived_state_iri(RS.Risk_T2, "warning"), ONTO.degradesTo,
            derived_state_iri(RS.Risk_T3, "dangerous")),
    ])

    # B1 / B2 桥接
    b1_ok = has(ABL.EvtCauseA, ONTO.causesEvent, ABL.EvtEffectB)
    b2_ok = has(ABL.StateX2, ONTO.transitsTo, ABL.StateY2)

    return {
        "precedence_ok": precedence_ok,
        "overlap_ok": overlap_ok,
        "temporal_ok": precedence_ok and overlap_ok,
        "causal_ok": causal_ok,
        "situation_states_ok": states_ok,
        "state_evolution_ok": evolution_ok,
        "b1_bridge_ok": b1_ok,
        "b2_bridge_ok": b2_ok,
    }


FAULTS = {
    "F1_time_reversed_causation": {
        "path": DATA / "causal_fault_F1.ttl",
        "primary": ONTO.CauseBeforeEffectShape,   # R9
        "primary_foci": {FLT.EvtLate},
    },
    "F2_reciprocal_causation": {
        "path": DATA / "causal_fault_F2.ttl",
        "primary": ONTO.CausalDirectionShape,      # R10
        "primary_foci": {FLT.EvtPairA, FLT.EvtPairB},
    },
    "F3_causal_cycle": {
        "path": DATA / "causal_fault_F3.ttl",
        "primary": ONTO.CausalCycleShape,          # R11
        "primary_foci": {FLT.EvtCycle1, FLT.EvtCycle2, FLT.EvtCycle3},
    },
}
SHAPE_LABEL = {
    ONTO.CauseBeforeEffectShape: "R9",
    ONTO.CausalDirectionShape: "R10",
    ONTO.CausalCycleShape: "R11",
}


def fault_detections(report_graph: Graph) -> dict:
    """报告图 → {一致性 Shape IRI: 焦点节点集合}（仅 R9/R10/R11）。"""
    out = {s: set() for s in CONSISTENCY_SHAPES}
    for r in report_graph.subjects(RDF.type, SH.ValidationResult):
        for shape in CONSISTENCY_SHAPES:
            if (r, SH.sourceShape, shape) in report_graph:
                out[shape].update(report_graph.objects(r, SH.focusNode))
    return out


def run_fault_injection(rules: Graph) -> dict:
    """三个故障文件各自独立成图运行，返回每个故障的检出明细。
    每个故障的唯一输入是其自身文件 + 本体 + 部署配置。"""
    results = {}
    for fault, fspec in FAULTS.items():
        data = load_graph(fspec["path"])
        data += load_graph(OWL, "xml")
        data += load_graph(RULE_CONFIG)
        _, report_graph, _, _ = run_diagnostic_to_fixed_point(data, rules)
        det = fault_detections(report_graph)
        primary = fspec["primary"]
        additional = {SHAPE_LABEL[s]: sorted(str(f) for f in foci)
                      for s, foci in det.items() if s != primary and foci}
        results[fault] = {
            "primary_detector": SHAPE_LABEL[primary],
            "primary_shape": f"onto:{str(primary).rsplit('#', 1)[-1]}",
            "expected_foci": sorted(str(f) for f in fspec["primary_foci"]),
            "detected_primary_foci": sorted(str(f) for f in det[primary]),
            "primary_detected": fspec["primary_foci"] <= det[primary],
            "any_consistency_detection": any(det.values()),
            "additional_detectors": additional,
        }
    return results


def clean_part_conforms(report_graph: Graph) -> bool:
    """干净部分（rs:/abl: 命名空间）不得有任何 violation——故障检测之外
    不应出现附带违规。"""
    for r in report_graph.subjects(RDF.type, SH.ValidationResult):
        for f in report_graph.objects(r, SH.focusNode):
            fs = str(f)
            if fs.startswith(str(RS)) or fs.startswith(str(ABL)):
                return False
    return True


# ----------------------------------------------------------------------
# CQ 判定（规则固定，不得手工改表）
# ----------------------------------------------------------------------

def cq_verdicts(probe: dict, consistency_ok: bool) -> dict[str, str]:
    """按 spec 第十二节的固定规则判定 CQ2—CQ6。"""
    v = {}
    # CQ2：事件先后 + overlap；全存在 PASS，部分 PARTIAL，均缺 FAIL
    if probe["precedence_ok"] and probe["overlap_ok"]:
        v["CQ2"] = "PASS"
    elif probe["precedence_ok"] or probe["overlap_ok"]:
        v["CQ2"] = "PARTIAL"
    else:
        v["CQ2"] = "FAIL"
    # CQ3：R3/R4 causesEvent + 一致性检测能力；因果在但一致性不可用 → PARTIAL
    if probe["causal_ok"] and consistency_ok:
        v["CQ3"] = "PASS"
    elif probe["causal_ok"]:
        v["CQ3"] = "PARTIAL"
    else:
        v["CQ3"] = "FAIL"
    # CQ4：B1 桥接
    v["CQ4"] = "PASS" if probe["b1_bridge_ok"] else "FAIL"
    # CQ5：四级状态 + B3 演化；只有状态 → PARTIAL；全缺 → FAIL
    if probe["situation_states_ok"] and probe["state_evolution_ok"]:
        v["CQ5"] = "PASS"
    elif probe["situation_states_ok"]:
        v["CQ5"] = "PARTIAL"
    else:
        v["CQ5"] = "FAIL"
    # CQ6：B2 桥接
    v["CQ6"] = "PASS" if probe["b2_bridge_ok"] else "FAIL"
    return v


def missing_capabilities(variant: str, probe: dict, consistency_ok: bool) -> str:
    if variant == "FULL":
        return "—"
    missing = []
    if not probe["temporal_ok"]:
        missing.append("事件时序关系")
    if not probe["causal_ok"]:
        missing.append("事件因果链")
    if not probe["situation_states_ok"]:
        missing.append("分级态势状态")
    if not probe["state_evolution_ok"]:
        missing.append("跨快照态势演化")
    if not probe["b1_bridge_ok"]:
        missing.append("B1因果桥接")
    if not probe["b2_bridge_ok"]:
        missing.append("B2状态转移桥接")
    if not consistency_ok:
        missing.append("因果一致性检测")
    return "、".join(missing) if missing else "—"


# ----------------------------------------------------------------------
# 证据反事实
# ----------------------------------------------------------------------

def run_evidence_counterfactual(full_rules: Graph) -> dict:
    no_evidence_rules = make_no_evidence_rules(full_rules)

    def run_once(rules: Graph) -> tuple[Graph, Graph]:
        data = load_graph(DATA / "evidence_counterfactual.ttl")
        data += load_graph(OWL, "xml")
        data += load_graph(RULE_CONFIG)
        _, report_graph, _, _ = run_to_fixed_point(data, rules)
        return data, report_graph

    data_full, report_full = run_once(full_rules)
    data_noev, _ = run_once(no_evidence_rules)

    def ecf_causal_edges(data: Graph) -> list[tuple[str, str]]:
        edges = []
        for s, o in data.subject_objects(ONTO.causesEvent):
            if str(s).startswith(str(ECF)) and str(o).startswith(str(ECF)):
                edges.append((str(s), str(o)))
        return sorted(edges)

    def has_obs_evidence(data: Graph, event: URIRef) -> bool:
        """事件是否具有 ObservationData 类型的 detectedFromData/supportedByData
        证据（与 R3/R4 证据前件同口径）。"""
        for prop in (ONTO.supportedByData, ONTO.detectedFromData):
            for d in data.objects(event, prop):
                if (d, RDF.type, ONTO.ObservationData) in data:
                    return True
        return False

    def spurious_edges(data: Graph) -> list[tuple[str, str]]:
        """无证据因果边：至少一端缺少 ObservationData 证据的 causesEvent 边。
        E1/E2 已用独立目标对隔离，本套件中不存在跨场景附带边。"""
        return [(s, o) for s, o in ecf_causal_edges(data)
                if not (has_obs_evidence(data, URIRef(s)) and has_obs_evidence(data, URIRef(o)))]

    edges_full = ecf_causal_edges(data_full)
    edges_noev = ecf_causal_edges(data_noev)
    spurious_full = spurious_edges(data_full)
    spurious_noev = spurious_edges(data_noev)

    e1 = {
        "scenario": "E1_missing_approach_observation",
        "rule": "R3",
        "edge": f"{ECF}E1_Maneuver causesEvent {ECF}E1_Approach",
        "full_edge": (ECF.E1_Maneuver, ONTO.causesEvent, ECF.E1_Approach) in data_full,
        "no_evidence_edge": (ECF.E1_Maneuver, ONTO.causesEvent, ECF.E1_Approach) in data_noev,
    }
    e2 = {
        "scenario": "E2_missing_risk_observation_evidence",
        "rule": "R4",
        "edge": f"{ECF}E2_Approach causesEvent {ECF}E2_Risk",
        "full_edge": (ECF.E2_Approach, ONTO.causesEvent, ECF.E2_Risk) in data_full,
        "no_evidence_edge": (ECF.E2_Approach, ONTO.causesEvent, ECF.E2_Risk) in data_noev,
    }
    # R13 应标记两个缺证据事件（验证层对证据缺失的对应表现）
    r13_flagged = set()
    for r in report_full.subjects(RDF.type, SH.ValidationResult):
        if (r, SH.sourceShape, ONTO.EventDataEvidenceShape) in report_full:
            r13_flagged.update(str(f) for f in report_full.objects(r, SH.focusNode))
    return {
        "cases": [e1, e2],
        "causal_edges_full": edges_full,
        "causal_edges_no_evidence": edges_noev,
        "spurious_causal_edges_full": len(spurious_full),
        "spurious_causal_edges_no_evidence": len(spurious_noev),
        "spurious_causal_edges_no_evidence_list": [f"{s} causesEvent {o}" for s, o in spurious_noev],
        "r13_flagged_missing_evidence_events": sorted(r13_flagged),
    }


# ----------------------------------------------------------------------
# LaTeX 表片段生成（论文 4.2.5 直接 \input，数值不手工转写）
# ----------------------------------------------------------------------

def write_ablation_tex(rows: list[dict], path: Path) -> None:
    verdict_zh = {"PASS": "PASS", "PARTIAL": "PARTIAL", "FAIL": "FAIL"}
    lines = [
        "% 本文件由 run_ablation_study.py 自动生成，禁止手工编辑数值。",
        "\\begin{longtable}{|p{0.14\\textwidth}|p{0.085\\textwidth}|p{0.085\\textwidth}|p{0.085\\textwidth}|p{0.085\\textwidth}|p{0.085\\textwidth}|p{0.26\\textwidth}|}",
        "\\caption{TC-SSSAO模块消融对能力问题的影响}\\label{tab:ablation-cq}\\\\",
        "\\hline",
        "\\textbf{变体} & \\textbf{CQ2} & \\textbf{CQ3} & \\textbf{CQ4} & \\textbf{CQ5} & \\textbf{CQ6} & \\textbf{主要缺失能力} \\\\",
        "\\hline",
        "\\endfirsthead",
        "\\multicolumn{7}{c}{续表~\\thetable}\\\\",
        "\\hline",
        "\\textbf{变体} & \\textbf{CQ2} & \\textbf{CQ3} & \\textbf{CQ4} & \\textbf{CQ5} & \\textbf{CQ6} & \\textbf{主要缺失能力} \\\\",
        "\\hline",
        "\\endhead",
    ]
    name_zh = {
        "FULL": "Full（完整规则库）",
        "NO_TEMPORAL": "w/o Temporal（R1、R2）",
        "NO_CAUSAL": "w/o Causal（R3、R4、B1）",
        "NO_SITUATION": "w/o Situation（R5—R8、B2、B3）",
        "NO_CONSISTENCY": "w/o Consistency（R9—R11）",
    }
    for r in rows:
        cqs = " & ".join(verdict_zh[r["cq"][cq]] for cq in ("CQ2", "CQ3", "CQ4", "CQ5", "CQ6"))
        lines.append(f"{name_zh[r['variant']]} & {cqs} & {r['main_missing']} \\\\")
        lines.append("\\hline")
    lines.append("\\end{longtable}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_robustness_tex(rows: list[dict], path: Path) -> None:
    lines = [
        "% 本文件由 run_ablation_study.py 自动生成，禁止手工编辑数值。",
        "\\begin{longtable}{|p{0.17\\textwidth}|p{0.065\\textwidth}|p{0.075\\textwidth}|p{0.135\\textwidth}|p{0.155\\textwidth}|p{0.27\\textwidth}|}",
        "\\caption{一致性故障与证据反事实测试结果}\\label{tab:robustness}\\\\",
        "\\hline",
        "\\textbf{测试} & \\textbf{主检测器} & \\textbf{附加检测器} & \\textbf{Full} & \\textbf{消融变体} & \\textbf{结果解释} \\\\",
        "\\hline",
        "\\endfirsthead",
        "\\multicolumn{6}{c}{续表~\\thetable}\\\\",
        "\\hline",
        "\\textbf{测试} & \\textbf{主检测器} & \\textbf{附加检测器} & \\textbf{Full} & \\textbf{消融变体} & \\textbf{结果解释} \\\\",
        "\\hline",
        "\\endhead",
    ]
    for r in rows:
        lines.append(f"{r['test_zh']} & {r['primary']} & {r['additional']} & {r['full']} & {r['ablated']} & {r['interpretation']} \\\\")
        lines.append("\\hline")
    lines.append("\\end{longtable}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    full_rules = load_full_rules()
    mapping = module_map(full_rules)
    expected_modules = {"Temporal", "Causal", "Situation", "Consistency",
                        "SemanticProjection", "DataValidation"}
    if set(mapping) != expected_modules:
        raise RuntimeError(f"模块标签不完整：{sorted(mapping)}")
    print("模块映射（从规则图动态读取）：")
    for module, shapes in mapping.items():
        print(f"  {module}: {len(shapes)} 个 Shape")

    # ---------------- 主消融（5 variants，同一输入数据） ----------------
    # 每个 variant 同时独立运行 F1—F3 故障注入（逐故障单独成图），
    # 一致性检测能力以三个故障的主检测器全部命中为准。
    rows = []
    fault_matrix: dict[str, dict] = {}
    full_clean_inferred: set | None = None
    full_final_graph: Graph | None = None
    for variant, modules in VARIANTS.items():
        rules = strip_modules(full_rules, modules) if modules else full_rules
        data = build_main_data()
        before = set(data)
        conforms, report_graph, _, additions = run_to_fixed_point(data, rules)
        probe = probe_variant(data)
        faults = run_fault_injection(rules)
        fault_matrix[variant] = faults
        consistency_ok = all(f["primary_detected"] for f in faults.values())
        clean_ok = clean_part_conforms(report_graph)
        cq = cq_verdicts(probe, consistency_ok)

        # NO_CONSISTENCY 知识生成等价性：R9—R11 是纯验证器（不 CONSTRUCT），
        # 因此移除一致性模块后推理所得知识应与 FULL 完全一致。判定用两重口径：
        # (a) 不含匿名节点的推理新增三元组集合相等（规则的 CONSTRUCT 只产生
        #     IRI 节点，匿名节点新增三元组是 RDFS 闭包在 OWL 限制节点上的
        #     公理化产物，其 bnode id 跨进程不稳定、无语义差异）；
        # (b) 收敛后完整数据图同构（rdflib.compare.isomorphic，处理 bnode 重标号）。
        inferred = set(data) - before
        inferred_iri_only = {t for t in inferred
                             if not isinstance(t[0], BNode) and not isinstance(t[2], BNode)}
        if variant == "FULL":
            full_clean_inferred = inferred_iri_only
            full_final_graph = data
        knowledge_delta_empty = (inferred_iri_only == full_clean_inferred)
        knowledge_isomorphic = isomorphic(data, full_final_graph)
        if variant == "NO_CONSISTENCY" and not (knowledge_delta_empty and knowledge_isomorphic):
            print(f"  警告：NO_CONSISTENCY 与 FULL 知识生成不一致 "
                  f"(IRI差集相等={knowledge_delta_empty}, 图同构={knowledge_isomorphic})")

        row = {
            "variant": variant,
            "disabled_modules": list(modules),
            "fixed_point_rounds": len(additions),
            "graph_additions_per_round": additions,
            **probe,
            "main_run_conforms": bool(conforms),
            "consistency_fault_detection_ok": consistency_ok,
            "fault_injection": faults,
            "clean_part_violation_free": clean_ok,
            "knowledge_identical_to_full": knowledge_delta_empty and knowledge_isomorphic,
            "knowledge_iri_delta_empty": knowledge_delta_empty,
            "knowledge_graph_isomorphic": knowledge_isomorphic,
            "cq": cq,
            "main_missing": missing_capabilities(variant, probe, consistency_ok),
        }
        rows.append(row)
        print(f"[{variant}] 轮数={len(additions)} conforms={conforms} CQ={cq} "
              f"故障主检出={consistency_ok} 干净部分零违规={clean_ok} "
              f"知识与FULL一致={row['knowledge_identical_to_full']}")

    # ---------------- 证据反事实 ----------------
    print("\n证据反事实（NO_EVIDENCE_CONSTRAINT 为内存变体，主规则文件不修改）")
    ecf = run_evidence_counterfactual(full_rules)
    for case in ecf["cases"]:
        print(f"  {case['scenario']}: FULL生成={case['full_edge']} "
              f"去证据后生成={case['no_evidence_edge']}")
    print(f"  因果边总数： FULL={len(ecf['causal_edges_full'])} "
          f"NO_EVIDENCE={len(ecf['causal_edges_no_evidence'])}")
    print(f"  无证据因果边： FULL={ecf['spurious_causal_edges_full']} "
          f"NO_EVIDENCE={ecf['spurious_causal_edges_no_evidence']}")

    # ---------------- 输出 ----------------
    # ablation_results.csv
    with open(OUT / "ablation_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Variant", "Temporal", "Causal", "Situation", "Evolution",
                    "B1", "B2", "CQ2", "CQ3", "CQ4", "CQ5", "CQ6"])
        for r in rows:
            yn = lambda b: "Y" if b else "N"
            w.writerow([r["variant"], yn(r["temporal_ok"]), yn(r["causal_ok"]),
                        yn(r["situation_states_ok"]), yn(r["state_evolution_ok"]),
                        yn(r["b1_bridge_ok"]), yn(r["b2_bridge_ok"]),
                        r["cq"]["CQ2"], r["cq"]["CQ3"], r["cq"]["CQ4"],
                        r["cq"]["CQ5"], r["cq"]["CQ6"]])

    # ablation_results.json（完整探针明细）
    (OUT / "ablation_results.json").write_text(
        json.dumps({"variants": rows,
                    "module_map": {k: [str(s) for s in v] for k, v in mapping.items()},
                    "cq_rule": "见 run_ablation_study.py cq_verdicts()（固定判定规则）"},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # consistency_fault_results.csv（逐故障独立成图运行；主/附加检测器分列，
    # 另给出其余消融变体下主检测器是否仍命中——证明故障检测不依赖被消融模块之外的模块）
    with open(OUT / "consistency_fault_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["fault_type", "primary_detector", "additional_detector",
                    "shape", "focus_node", "full_detected", "no_consistency_detected",
                    "no_temporal_detected", "no_causal_detected", "no_situation_detected"])
        for fault in FAULTS:
            full = fault_matrix["FULL"][fault]
            add = full["additional_detectors"]
            w.writerow([
                fault, full["primary_detector"],
                ";".join(add) if add else "—",
                full["primary_shape"],
                ";".join(full["detected_primary_foci"]) if full["detected_primary_foci"] else "—",
                full["primary_detected"],
                fault_matrix["NO_CONSISTENCY"][fault]["any_consistency_detection"],
                fault_matrix["NO_TEMPORAL"][fault]["primary_detected"],
                fault_matrix["NO_CAUSAL"][fault]["primary_detected"],
                fault_matrix["NO_SITUATION"][fault]["primary_detected"],
            ])

    # evidence_counterfactual_results.csv
    with open(OUT / "evidence_counterfactual_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "rule", "edge", "full_generates",
                    "no_evidence_constraint_generates"])
        for case in ecf["cases"]:
            w.writerow([case["scenario"], case["rule"], case["edge"],
                        case["full_edge"], case["no_evidence_edge"]])
        w.writerow(["TOTAL", "R3+R4", "spurious_causal_edges",
                    ecf["spurious_causal_edges_full"],
                    ecf["spurious_causal_edges_no_evidence"]])

    # robustness_results.csv（数值与判定全部来自 fault_matrix / ecf 实测结果）
    FAULT_ZH = {
        "F1_time_reversed_causation": ("因果时序逆序（F1）", "causal_direction_violation(F1)",
            "一致性模块识别发生时间晚于结果事件的因果方向错误"),
        "F2_reciprocal_causation": ("双向直接因果冲突（F2）", "reciprocal_causal_conflict(F2)",
            "R10直接识别同一对事件的双向因果冲突；该互指结构同时构成长度为2的因果闭环，由R11一并标记"),
        "F3_causal_cycle": ("因果闭环（F3）", "causal_cycle(F3)",
            "一致性模块经传递路径识别三事件因果闭环"),
    }

    def fault_full_cell(fault: str) -> str:
        det = fault_matrix["FULL"][fault]
        if not det["primary_detected"]:
            return "未检出"
        cell = f"检出（{det['primary_detector']}）"
        if det["additional_detectors"]:
            cell = (f"检出（{det['primary_detector']}；"
                    f"{'、'.join(det['additional_detectors'])}一并标记）")
        return cell

    def fault_ablated_cell(fault: str) -> str:
        det = fault_matrix["NO_CONSISTENCY"][fault]
        return "w/o Consistency：检出" if det["any_consistency_detection"] else "w/o Consistency：未检出"

    robustness_rows = []
    for fault, (zh, test_id, interp) in FAULT_ZH.items():
        full = fault_matrix["FULL"][fault]
        robustness_rows.append({
            "test": test_id, "test_zh": zh,
            "primary": full["primary_detector"],
            "additional": "、".join(full["additional_detectors"]) if full["additional_detectors"] else "—",
            "full": fault_full_cell(fault),
            "ablated": fault_ablated_cell(fault),
            "interpretation": interp,
        })
    robustness_rows += [
        {"test": "missing_evidence_R3(E1)", "test_zh": "缺观测证据的机动→接近（E1）",
         "primary": "—", "additional": "—",
         "full": "不生成 causesEvent" if not ecf["cases"][0]["full_edge"] else "生成 causesEvent",
         "ablated": "去证据约束：生成" if ecf["cases"][0]["no_evidence_edge"] else "去证据约束：不生成",
         "interpretation": "R3的ObservationData证据前件抑制仅凭类型、对象角色与时间先后的无证据因果关联"},
        {"test": "missing_evidence_R4(E2)", "test_zh": "缺观测证据的接近→碰撞风险（E2）",
         "primary": "—", "additional": "—",
         "full": "不生成 causesEvent" if not ecf["cases"][1]["full_edge"] else "生成 causesEvent",
         "ablated": "去证据约束：生成" if ecf["cases"][1]["no_evidence_edge"] else "去证据约束：不生成",
         "interpretation": "R4的ObservationData证据前件抑制仅依据目标角色和时间关系建立的无观测证据接近—碰撞风险因果关联"},
    ]
    with open(OUT / "robustness_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Test", "PrimaryDetector", "AdditionalDetector", "FULL",
                    "AblatedVariant", "Interpretation"])
        for r in robustness_rows:
            w.writerow([r["test"], r["primary"], r["additional"],
                        r["full"], r["ablated"], r["interpretation"]])

    # LaTeX 表片段（论文 4.2.5 直接 \input）
    write_ablation_tex(rows, OUT / "ablation_table.tex")
    write_robustness_tex(robustness_rows, OUT / "robustness_table.tex")

    summary = {
        "experiment": "TC-SSSAO module ablation / fault injection / evidence counterfactual",
        "variants": list(VARIANTS),
        "evidence_variant": "NO_EVIDENCE_CONSTRAINT（内存中摘除 R3/R4 证据图模式，主规则文件不修改）",
        "elapsed_seconds": round(time.perf_counter() - t_start, 2),
        "ablation": [{"variant": r["variant"], "cq": r["cq"],
                      "main_missing": r["main_missing"],
                      "knowledge_identical_to_full": r["knowledge_identical_to_full"],
                      "clean_part_violation_free": r["clean_part_violation_free"]}
                     for r in rows],
        "consistency_faults": {v: {f: {"primary_detected": d["primary_detected"],
                                       "primary_detector": d["primary_detector"],
                                       "additional_detectors": d["additional_detectors"],
                                       "detected_primary_foci": d["detected_primary_foci"]}
                                   for f, d in det.items()}
                               for v, det in fault_matrix.items()},
        "evidence_counterfactual": ecf,
    }
    (OUT / "ablation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n输出目录：{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
