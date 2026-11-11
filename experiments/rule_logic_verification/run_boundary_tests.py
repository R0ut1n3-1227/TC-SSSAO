# Controlled rule-contract diagnostics: intentional invalid/incomplete fixtures; not formal instance ingestion.
"""R3/R4/R5/R6/R7/R8/B2/B3 正负例及边界测试。

每个测试构造最小数据图，仅使用通用规则 rules/tc_sssao_rules.ttl 执行推理，
检查目标关系是否按预期生成或抑制。所有测试均为人工构造的规则边界数据，
不对应真实事件，也不构成机器学习意义上的敏感性分析。

M2 规则语义（与论文第3章一致）：
- R3：OrbitManeuverEvent affectsObject(o1)，ApproachEvent hasPrimaryObject(o1)/
  hasSecondaryObject(o2)，o1≠o2，机动先于接近，两事件均具 ObservationData 证据
  → causesEvent。（M2 第一阶段定稿，本阶段保持不变。）
- R4：ApproachEvent 与 CollisionRiskEvent 具有相同主要/次要目标（同一交会
  目标对），接近先于碰撞风险，两事件均具 ObservationData 证据 → causesEvent。
- R5—R8（M2 第二阶段重构）：以 RuleDeploymentConfiguration 实例中的两个
  部署参数 θ_A（attentionPcThreshold）与 θ_M（mitigationPcThreshold）为判据，
  并结合事件级组合硬体半径 hasCombinedHardBodyRadius，对单次风险评估快照
  生成唯一态势状态（hasSeverityRank 0—3）；要求 Ev_assess 证据
  （AssessmentData 或 PredictionData），普通 ObservationData 不再单独作为依据。
  配置实例来自 rules/tc_sssao_rule_config.ttl，必须并入数据图
  （pySHACL 规则仅对数据图求值）。实验参考值 θ_A=1E-7、θ_M=1E-4。
- B2：显式 StateTransition 的 hasSourceState/hasTargetState → transitsTo。
- B3（2026-09-14 确立上升/恶化语义；2026-10-10 扩展恢复语义）：
  同一交会目标对相邻两次快照、时间先后且严重度级别升高 → 直接建立 transitsTo；
  级别 2→3 时同时建立 degradesTo；严重度下降（r1>r2）时同时建立
  transitsTo 和 recoversTo；B3 不创建 StateTransition；等级相同时不生成
  transitsTo；存在中间快照、不同目标对或时间顺序不成立时均不生成 transitsTo。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef

ONTO = Namespace("https://w3id.org/tc-sssao#")
BT = Namespace("https://w3id.org/tc-sssao/data/boundary-test#")

HEADER = """@prefix onto: <https://w3id.org/tc-sssao#> .
@prefix bt: <https://w3id.org/tc-sssao/data/boundary-test#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

# 每个事件一个专属观测数据实例，避免证据共享造成混淆
OBS = "bt:Obs_{name} a onto:RadarObservationData .\n"
ASSESS = "bt:Assess_{name} a onto:AssessmentData .\n"

STATE_KINDS = ("normal", "attention", "warning", "dangerous")


def derived_state(kind: str, event_iri: str) -> URIRef:
    digest = hashlib.sha256(event_iri.encode("utf-8")).hexdigest().lower()
    return URIRef(f"https://w3id.org/tc-sssao#derived_{kind}_state_{digest}")


def st(kind: str, name: str) -> URIRef:
    """bt:<name> 事件对应的派生状态 IRI。"""
    return derived_state(kind, str(BT[name]))


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


def r3_fixture(t_man: str, t_app: str, affected: str = "SatA",
               man_evidence: bool = True, app_evidence: bool = True) -> str:
    """R3 夹具：机动事件 affectsObject + 接近事件主要/次要目标 + 双事件观测证据。"""
    man_ev = 'onto:detectedFromData bt:Obs_Man ;' if man_evidence else ''
    app_ev = 'onto:supportedByData bt:Obs_App ;' if app_evidence else ''
    obs = OBS.format(name="Man") if man_evidence else ""
    obs += OBS.format(name="App") if app_evidence else ""
    return f"""
bt:SatA a onto:Spacecraft .
bt:SatB a onto:Spacecraft .
bt:SatC a onto:Spacecraft .
{obs}
bt:Man a onto:OrbitManeuverEvent ;
    onto:hasOccurrenceTime "{t_man}"^^xsd:dateTime ;
    onto:affectsObject bt:{affected} ;
    {man_ev}
    onto:involvesObject bt:{affected} .
bt:App a onto:ApproachEvent ;
    onto:hasOccurrenceTime "{t_app}"^^xsd:dateTime ;
    onto:hasRelativeDistance "0.8"^^xsd:float ;
    onto:hasPrimaryObject bt:SatA ;
    onto:hasSecondaryObject bt:SatB ;
    {app_ev}
    onto:involvesObject bt:SatA , bt:SatB .
"""


def r4_fixture(t_app: str, t_risk: str, risk_primary: str = "SatA",
               risk_secondary: str = "SatB",
               app_evidence: bool = True, risk_evidence: bool = True) -> str:
    """R4 夹具：接近事件与碰撞风险事件的交会目标对角色 + 双事件观测证据。"""
    app_ev = 'onto:detectedFromData bt:Obs_App ;' if app_evidence else ''
    risk_ev = 'onto:supportedByData bt:Obs_Risk ;' if risk_evidence else ''
    obs = OBS.format(name="App") if app_evidence else ""
    obs += OBS.format(name="Risk") if risk_evidence else ""
    return f"""
bt:SatA a onto:Spacecraft .
bt:SatB a onto:Spacecraft .
bt:SatC a onto:Spacecraft .
{obs}
bt:App a onto:ApproachEvent ;
    onto:hasOccurrenceTime "{t_app}"^^xsd:dateTime ;
    onto:hasRelativeDistance "0.8"^^xsd:float ;
    onto:hasPrimaryObject bt:SatA ;
    onto:hasSecondaryObject bt:SatB ;
    {app_ev}
    onto:involvesObject bt:SatA , bt:SatB .
bt:Risk a onto:CollisionRiskEvent ;
    onto:hasOccurrenceTime "{t_risk}"^^xsd:dateTime ;
    onto:hasPrimaryObject bt:{risk_primary} ;
    onto:hasSecondaryObject bt:{risk_secondary} ;
    {risk_ev}
    onto:involvesObject bt:SatA , bt:SatB .
"""


def risk_event(name: str, pc=None, miss=None, hbr=None,
               time: str = "2026-08-01T11:00:00Z",
               evidence: str = "assessment",
               primary: str = None, secondary: str = None,
               encounter_id: str = None) -> str:
    """R5—R8/B3 夹具：碰撞风险事件 + Pc/miss/HBR + 指定类型证据。

    evidence: 'assessment' | 'prediction' | 'observation' | 'none'
      assessment/prediction 满足 Ev_assess；observation 为普通观测数据
      （M2 第二阶段起不再单独作为态势规则依据）；none 表示无证据。
    """
    props = []
    if pc is not None:
        props.append(f'onto:hasCollisionProbability "{pc}"^^xsd:float ;')
    if miss is not None:
        props.append(f'onto:hasPredictedMissDistance "{miss}"^^xsd:float ;')
    if hbr is not None:
        props.append(f'onto:hasCombinedHardBodyRadius "{hbr}"^^xsd:float ;')
    if primary is not None:
        props.append(f'onto:hasPrimaryObject bt:{primary} ;')
    if secondary is not None:
        props.append(f'onto:hasSecondaryObject bt:{secondary} ;')
    if encounter_id is not None:
        props.append(f'onto:hasEncounterID "{encounter_id}"^^xsd:string ;')
    elif primary is not None or secondary is not None:
        # Default encounter ID for B3 boundary tests (all same-encounter pairs)
        props.append('onto:hasEncounterID "BT-ENC-01"^^xsd:string ;')
    data_decl = ""
    if evidence == "assessment":
        data_decl = ASSESS.format(name=name)
        props.append(f'onto:supportedByData bt:Assess_{name} ;')
    elif evidence == "prediction":
        data_decl = f"bt:Pred_{name} a onto:PredictionData .\n"
        props.append(f'onto:supportedByData bt:Pred_{name} ;')
    elif evidence == "observation":
        data_decl = OBS.format(name=name)
        props.append(f'onto:detectedFromData bt:Obs_{name} ;')
    sats = ""
    if primary or secondary:
        sats = ("bt:SatA a onto:Spacecraft .\n"
                "bt:SatB a onto:Spacecraft .\n"
                "bt:SatC a onto:Spacecraft .\n")
    return f"""
{sats}{data_decl}bt:{name} a onto:CollisionRiskEvent ;
    onto:hasOccurrenceTime "{time}"^^xsd:dateTime ;
    {' '.join(props)}
    onto:hasEventID "BT-{name}"^^xsd:string .
"""


def b2_fixture(with_target: bool = True) -> str:
    """B2 独立夹具：只提供显式 StateTransition，不依赖 B3 风险快照。"""
    transition_props = (
        "onto:hasSourceState bt:B2Source ;\n"
        "    onto:hasTargetState bt:B2Target"
        if with_target else "onto:hasSourceState bt:B2Source"
    )
    return f"""
bt:B2Source a onto:NormalSituationState ;
    onto:hasSeverityRank "0"^^xsd:integer .
bt:B2Target a onto:WarningSituationState ;
    onto:hasSeverityRank "2"^^xsd:integer .
bt:B2Transition a onto:StateTransition ;
    {transition_props} .
"""


def main() -> int:
    only_b2_b3 = "--only-b2-b3" in sys.argv
    rules = Graph()
    base = Path(__file__).resolve().parent
    root = base
    for p in [base, *base.parents]:
        if (p / "rules" / "tc_sssao_rules.ttl").exists():
            root = p
            break
    rules.parse(root / "rules" / "tc_sssao_rules.ttl", format="turtle")
    # 规则前件中的 onto:SpaceEvent / onto:SpaceObject 类型依赖本体的子类闭包，
    # 因此测试数据图需包含主本体（与主实验一致）。
    ontology = Graph()
    ontology.parse(root / "ontology" / "tc_sssao.owl", format="xml")
    # R5—R8 的部署参数 θ_A/θ_M 必须并入数据图（pySHACL 规则仅对数据图求值）。
    config = Graph()
    config.parse(root / "rules" / "tc_sssao_rule_config.ttl", format="turtle")
    if len(config) == 0:
        print("规则部署配置为空，R5—R8 无法求值。", file=sys.stderr)
        return 2

    RISK_IRI = str(BT.Risk)
    normal = derived_state("normal", RISK_IRI)
    warning = derived_state("warning", RISK_IRI)
    attention = derived_state("attention", RISK_IRI)
    dangerous = derived_state("dangerous", RISK_IRI)

    # 单事件缺态检查：四种派生状态全部不存在的三元组列表
    def no_states(name: str):
        return [(BT[name], ONTO.leadsToState, st(k, name)) for k in STATE_KINDS]

    tests = [
        # (编号, 说明, 数据, 目标三元组函数, 预期是否生成)
        # ---- R3：机动→接近（对象角色 + 时序 + 观测证据）----
        ("R3-正例", "affectsObject=接近主要目标，机动早于接近，双事件具观测证据",
         r3_fixture("2026-08-01T09:00:00Z", "2026-08-01T10:00:00Z"),
         (BT.Man, ONTO.causesEvent, BT.App), True),
        ("R3-反例-作用对象不符", "机动作用对象为SatC，非接近主要目标SatA",
         r3_fixture("2026-08-01T09:00:00Z", "2026-08-01T10:00:00Z", affected="SatC"),
         (BT.Man, ONTO.causesEvent, BT.App), False),
        ("R3-反例-缺证据", "接近事件缺少观测数据证据",
         r3_fixture("2026-08-01T09:00:00Z", "2026-08-01T10:00:00Z", app_evidence=False),
         (BT.Man, ONTO.causesEvent, BT.App), False),
        ("R3-反例-时序不满足", "机动晚于接近",
         r3_fixture("2026-08-01T10:00:00Z", "2026-08-01T09:00:00Z"),
         (BT.Man, ONTO.causesEvent, BT.App), False),
        # ---- R4：接近→碰撞风险（同一交会目标对 + 时序 + 观测证据）----
        ("R4-正例", "接近与碰撞风险具相同主要/次要目标，接近在先，双事件具观测证据",
         r4_fixture("2026-08-01T10:00:00Z", "2026-08-01T11:00:00Z"),
         (BT.App, ONTO.causesEvent, BT.Risk), True),
        ("R4-反例-primary不一致", "碰撞风险主要目标为SatC，与接近事件不一致",
         r4_fixture("2026-08-01T10:00:00Z", "2026-08-01T11:00:00Z", risk_primary="SatC"),
         (BT.App, ONTO.causesEvent, BT.Risk), False),
        ("R4-反例-secondary不一致", "碰撞风险次要目标为SatC，与接近事件不一致",
         r4_fixture("2026-08-01T10:00:00Z", "2026-08-01T11:00:00Z", risk_secondary="SatC"),
         (BT.App, ONTO.causesEvent, BT.Risk), False),
        ("R4-反例-缺证据", "碰撞风险事件缺少观测数据证据",
         r4_fixture("2026-08-01T10:00:00Z", "2026-08-01T11:00:00Z", risk_evidence=False),
         (BT.App, ONTO.causesEvent, BT.Risk), False),
        ("R4-反例-时序不满足", "碰撞风险事件早于接近事件",
         r4_fixture("2026-08-01T11:00:00Z", "2026-08-01T10:00:00Z"),
         (BT.App, ONTO.causesEvent, BT.Risk), False),
        # ---- R5：Pc ≤ θ_A 且 miss ≥ HBR → Normal（θ_A=1E-7）----
        ("R5-正例", "Pc=5E-8≤θ_A 且 miss=0.5≥HBR=0.01，具评估证据，应生成 Normal",
         risk_event("Risk", pc="5.0E-8", miss="0.5", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, normal), True),
        ("R5-反例-Pc>θ_A", "Pc=2E-7>θ_A，miss≥HBR，不应生成 Normal",
         risk_event("Risk", pc="2.0E-7", miss="0.5", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, normal), False),
        # ---- R6：θ_A < Pc ≤ θ_M 且 miss ≥ HBR → Attention ----
        ("R6-反例-Pc=θ_A", "Pc=1E-7=θ_A，不满足 Pc>θ_A，不应生成 Attention",
         risk_event("Risk", pc="1.0E-7", miss="0.5", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, attention), False),
        ("R6-反例-Pc=θ_A伴随Normal", "Pc=1E-7=θ_A 且 miss≥HBR，应生成 Normal（互斥佐证）",
         risk_event("Risk", pc="1.0E-7", miss="0.5", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, normal), True),
        ("R6-正例", "θ_A<Pc=5E-6≤θ_M 且 miss≥HBR，具评估证据，应生成 Attention",
         risk_event("Risk", pc="5.0E-6", miss="0.3", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, attention), True),
        ("R6-反例-Pc>θ_M", "Pc=2E-4>θ_M，miss≥HBR，不应生成 Attention",
         risk_event("Risk", pc="2.0E-4", miss="0.05", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, attention), False),
        ("R6-反例-Pc>θ_M伴随Warning", "Pc=2E-4>θ_M 且 miss≥HBR，应生成 Warning（互斥佐证）",
         risk_event("Risk", pc="2.0E-4", miss="0.05", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), True),
        # ---- R7：(Pc>θ_M 且 miss≥HBR) 或 (Pc≤θ_M 且 miss<HBR) → Warning ----
        ("R7-正例-高Pc", "Pc=2E-4>θ_M 且 miss=0.05≥HBR，应生成 Warning",
         risk_event("Risk", pc="2.0E-4", miss="0.05", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), True),
        ("R7-正例-低Pc近距", "Pc=5E-8≤θ_M 且 miss=0.005<HBR，应生成 Warning（第二析取支）",
         risk_event("Risk", pc="5.0E-8", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), True),
        # ---- R8：Pc > θ_M 且 miss < HBR → Dangerous ----
        ("R8-正例", "Pc=2E-4>θ_M 且 miss=0.005<HBR=0.01，具评估证据，应生成 Dangerous",
         risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, dangerous), True),
        ("R8-反例-Pc=θ_M", "Pc=1E-4=θ_M，不满足 Pc>θ_M，不应生成 Dangerous",
         risk_event("Risk", pc="1.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, dangerous), False),
        ("R8-反例-Pc=θ_M伴随Warning", "Pc=1E-4≤θ_M 且 miss<HBR，应生成 Warning（互斥佐证）",
         risk_event("Risk", pc="1.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), True),
        ("R8-反例-miss=HBR", "miss=0.01=HBR，不满足 miss<HBR，不应生成 Dangerous",
         risk_event("Risk", pc="2.0E-4", miss="0.01", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, dangerous), False),
        ("R8-反例-miss=HBR伴随Warning", "Pc>θ_M 且 miss=HBR，应生成 Warning（互斥佐证）",
         risk_event("Risk", pc="2.0E-4", miss="0.01", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), True),
        # ---- 状态互斥：单个危险级输入只能关联 Dangerous 一个状态 ----
        ("互斥-Dangerous存在", "Dangerous 输入（Pc=2E-4, miss=0.005<HBR）应生成 Dangerous",
         risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, dangerous), True),
        ("互斥-无Normal", "同一事件不应同时生成 Normal",
         risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, normal), False),
        ("互斥-无Attention", "同一事件不应同时生成 Attention",
         risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, attention), False),
        ("互斥-无Warning", "同一事件不应同时生成 Warning",
         risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01"),
         (BT.Risk, ONTO.leadsToState, warning), False),
        # ---- 证据收紧：仅 ObservationData / 无证据 / 缺 HBR → 不生成任何态势状态 ----
        *[("证据收紧-仅观测数据-无" + k.capitalize(),
           "风险事件仅具 ObservationData 证据（不满足 Ev_assess），不应生成任何态势状态",
           risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01", evidence="observation"),
           triple, False)
          for k, triple in zip(STATE_KINDS, no_states("Risk"))],
        *[("证据收紧-无证据-无" + k.capitalize(),
           "风险事件无任何数据证据，不应生成任何态势状态",
           risk_event("Risk", pc="2.0E-4", miss="0.005", hbr="0.01", evidence="none"),
           triple, False)
          for k, triple in zip(STATE_KINDS, no_states("Risk"))],
        *[("证据收紧-缺HBR-无" + k.capitalize(),
           "风险事件缺少 hasCombinedHardBodyRadius，不应生成任何态势状态",
           risk_event("Risk", pc="2.0E-4", miss="0.005", hbr=None),
           triple, False)
          for k, triple in zip(STATE_KINDS, no_states("Risk"))],
        # ---- B3：相邻快照等级升高 → transitsTo / degradesTo ----
        ("B3-正例-升级", "同一目标对相邻快照 Normal(11:00)→Attention(12:00)，应生成 transitsTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("attention", "RiskB")), True),
        ("B3-正例-升级无degradesTo", "级别 0→1 非 2→3，不应生成 degradesTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.degradesTo, st("attention", "RiskB")), False),
        ("B3-正例-恶化", "同一目标对相邻快照 Warning(11:00)→Dangerous(12:00)，应生成 transitsTo+degradesTo，不生成 recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.05", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.005", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("warning", "RiskA"), ONTO.transitsTo, st("dangerous", "RiskB")), True,
         (st("warning", "RiskA"), ONTO.degradesTo, st("dangerous", "RiskB"), True, "degradesTo存在"),
         (st("warning", "RiskA"), ONTO.recoversTo, st("dangerous", "RiskB"), False, "recoversTo不存在"),
        ),
        ("B3-反例-中间快照不跨越", "Normal(11:00)→Attention(12:00)→Warning(13:00)，"
         "存在中间快照，不应跨越生成 Normal→Warning",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskMid", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskC", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T13:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("warning", "RiskC")), False),
        ("B3-反例-中间快照-相邻段1存在", "同一三快照序列，相邻段 Normal→Attention 应生成",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskMid", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskC", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T13:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("attention", "RiskMid")), True),
        ("B3-反例-中间快照-相邻段2存在", "同一三快照序列，相邻段 Attention→Warning 应生成",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskMid", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskC", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T13:00:00Z", primary="SatA", secondary="SatB"),
         (st("attention", "RiskMid"), ONTO.transitsTo, st("warning", "RiskC")), True),
        ("B3-反例-primary不同", "RiskA(SatA/SatB) Normal → RiskX(SatC/SatB) Warning，"
         "主要目标不同，不应生成 transitsTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskX", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatC", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("warning", "RiskX")), False),
        ("B3-反例-secondary不同", "RiskA(SatA/SatB) Normal → RiskX(SatA/SatC) Warning，"
         "次要目标不同，不应生成 transitsTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskX", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatC"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("warning", "RiskX")), False),
        ("B3-反例-等级相同", "Normal(11:00)→Normal(12:00) 级别相同，不应生成 transitsTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-8", miss="0.5", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("normal", "RiskB")), False),
        ("B3-正例-恢复 Dangerous→Warning", "Dangerous(11:00)→Warning(12:00) 级别下降，应生成 transitsTo+recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("dangerous", "RiskA"), ONTO.transitsTo, st("warning", "RiskB")), True,
         (st("dangerous", "RiskA"), ONTO.recoversTo, st("warning", "RiskB"), True, "recoversTo存在"),
         (st("dangerous", "RiskA"), ONTO.degradesTo, st("warning", "RiskB"), False, "degradesTo不存在"),
        ),
        ("B3-正例-恢复 Warning→Attention", "Warning(11:00)→Attention(12:00) 级别下降，应生成 transitsTo+recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.05", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("warning", "RiskA"), ONTO.transitsTo, st("attention", "RiskB")), True,
         (st("warning", "RiskA"), ONTO.recoversTo, st("attention", "RiskB"), True, "recoversTo存在"),
         (st("warning", "RiskA"), ONTO.degradesTo, st("attention", "RiskB"), False, "degradesTo不存在"),
        ),
        ("B3-正例-恢复 Attention→Normal", "Attention(11:00)→Normal(12:00) 级别下降，应生成 transitsTo+recoversTo",
         risk_event("RiskA", pc="5.0E-6", miss="0.3", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-8", miss="0.5", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("attention", "RiskA"), ONTO.transitsTo, st("normal", "RiskB")), True,
         (st("attention", "RiskA"), ONTO.recoversTo, st("normal", "RiskB"), True, "recoversTo存在"),
         (st("attention", "RiskA"), ONTO.degradesTo, st("normal", "RiskB"), False, "degradesTo不存在"),
        ),
        ("B3-正例-恢复 Dangerous→Normal (跨2级)", "Dangerous(11:00)→Normal(12:00) 级别大幅下降，应生成 transitsTo+recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-8", miss="0.5", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("dangerous", "RiskA"), ONTO.transitsTo, st("normal", "RiskB")), True,
         (st("dangerous", "RiskA"), ONTO.recoversTo, st("normal", "RiskB"), True, "recoversTo存在"),
         (st("dangerous", "RiskA"), ONTO.degradesTo, st("normal", "RiskB"), False, "degradesTo不存在"),
        ),
        ("B3-反例-恢复不生成 degradesTo", "Dangerous→Warning 下降不应生成 degradesTo（那是上升恶化专属）",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("dangerous", "RiskA"), ONTO.degradesTo, st("warning", "RiskB")), False),
        ("B3-反例-上升不生成 recoversTo", "Normal→Attention 上升不应生成 recoversTo（那是下降专属）",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.recoversTo, st("attention", "RiskB")), False),
        ("B3-反例-时间顺序不成立", "Normal(12:00) 与 Warning(11:00) 不满足前者先于后者，"
         "不应生成 Normal→Warning transitsTo",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("warning", "RiskB")), False),
        # ---- B3 跨交会边界测试：encounter_id 必须一致 ----
        ("B3-跨交会-正例同键", "同一 encounter ID 相邻快照严重度升高 → transitsTo 应生成",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB",
                    encounter_id="CROSS-ENC-01")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-01"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("attention", "RiskB")), True),
        ("B3-跨交会-反例不同键误连", "不同 encounter ID 相同目标对相邻快照 → transitsTo 不应生成",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB",
                    encounter_id="CROSS-ENC-A")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-B"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("attention", "RiskB")), False),
        ("B3-跨交会-验证中间快照不同键不阻塞", "三快照 RiskA(enc=X)→RiskMid(enc=Y)→RiskC(enc=X)，"
         "RiskMid enc≠X 不匹配 NOT EXISTS ?enc=X，故不阻塞 RiskA→RiskC 直接生成",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB",
                    encounter_id="CROSS-ENC-X")
         + risk_event("RiskMid", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-Y")
         + risk_event("RiskC", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T13:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-X"),
         (st("normal", "RiskA"), ONTO.transitsTo, st("warning", "RiskC")), True),
        ("B3-跨交会-恢复同键", "Dangerous(enc=X)→Normal(enc=X) 同 encounter 级别下降，"
         "应生成 transitsTo+recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB",
                    encounter_id="CROSS-ENC-01")
         + risk_event("RiskB", pc="5.0E-8", miss="0.5", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-01"),
         (st("dangerous", "RiskA"), ONTO.transitsTo, st("normal", "RiskB")), True,
         (st("dangerous", "RiskA"), ONTO.recoversTo, st("normal", "RiskB"), True, "recoversTo存在"),
         (st("dangerous", "RiskA"), ONTO.degradesTo, st("normal", "RiskB"), False, "degradesTo不存在"),
        ),
        ("B3-跨交会-恢复不同键", "Dangerous(enc=X)→Normal(enc=Y) 不同 encounter 级别下降，"
         "不应生成 transitsTo 或 recoversTo",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB",
                    encounter_id="CROSS-ENC-X")
         + risk_event("RiskB", pc="5.0E-8", miss="0.5", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB",
                      encounter_id="CROSS-ENC-Y"),
         (st("dangerous", "RiskA"), ONTO.transitsTo, st("normal", "RiskB")), False,
         (st("dangerous", "RiskA"), ONTO.recoversTo, st("normal", "RiskB"), False, "recoversTo不存在"),
        ),
    ]

    if only_b2_b3:
        tests = [test for test in tests if test[0].startswith("B3-")]

    results = []
    all_ok = True

    # ---- B2：显式 StateTransition 独立投影，不依赖 B3 ----
    b2_tests = [
        ("B2-正例-显式转换投影", "显式转换具 source/target，应投影 source transitsTo target",
         b2_fixture(), (BT.B2Source, ONTO.transitsTo, BT.B2Target), True),
        ("B2-反例-缺目标状态", "显式转换缺少 target，不应产生 transitsTo",
         b2_fixture(with_target=False), (BT.B2Source, ONTO.transitsTo, BT.B2Target), False),
    ]
    for tid, desc, body, triple, expect in b2_tests:
        data = build_graph(body) + ontology + config
        run_rules_to_fixed_point(data, rules)
        present = triple in data
        ok = present == expect
        all_ok = all_ok and ok
        print(f"{tid}: 预期{'生成' if expect else '不生成'}，实际{'生成' if present else '未生成'} → "
              f"{'符合预期' if ok else '与预期不符'}")
        results.append({
            "id": tid, "description": desc,
            "expected": expect, "actual": present, "pass": ok,
        })

    for tid, desc, body, triple, expect, *extra_assertions in tests:
        data = build_graph(body) + ontology + config
        run_rules_to_fixed_point(data, rules)
        present = triple in data
        ok = present == expect
        # Handle additional assertions per test: each extra item is (subject, predicate, object, expect, label)
        extra_results = []
        for extra_item in extra_assertions:
            extra_s, extra_p, extra_o, extra_expect, extra_label = extra_item
            extra_triple = (extra_s, extra_p, extra_o)
            extra_present = extra_triple in data
            extra_ok = extra_present == extra_expect
            ok = ok and extra_ok
            status = "符合预期" if extra_ok else "与预期不符"
            print(f"  [{extra_label}] 预期{'生成' if extra_expect else '不生成'}，实际{'生成' if extra_present else '未生成'} → {status}")
            extra_results.append({"label": extra_label, "expected": extra_expect, "actual": extra_present, "pass": extra_ok})
        all_ok = all_ok and ok
        status = "符合预期" if ok else "与预期不符"
        print(f"{tid}: 预期{'生成' if expect else '不生成'}，实际{'生成' if present else '未生成'} → {status}")
        results.append({
            "id": tid, "description": desc,
            "expected": expect, "actual": present, "pass": ok,
            "extra_assertions": extra_results,
        })

    # ---- B3 不创建 StateTransition ----
    b3_no_transition_tests = [
        ("B3-正例-升级-不创建StateTransition",
         risk_event("RiskA", pc="5.0E-8", miss="0.5", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="5.0E-6", miss="0.3", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         "RiskA", "RiskB", "normal", "attention"),
        ("B3-正例-恶化-不创建StateTransition",
         risk_event("RiskA", pc="2.0E-4", miss="0.05", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.005", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         "RiskA", "RiskB", "warning", "dangerous"),
        ("B3-正例-恢复-不创建StateTransition",
         risk_event("RiskA", pc="2.0E-4", miss="0.005", hbr="0.01",
                    time="2026-08-01T11:00:00Z", primary="SatA", secondary="SatB")
         + risk_event("RiskB", pc="2.0E-4", miss="0.05", hbr="0.01",
                      time="2026-08-01T12:00:00Z", primary="SatA", secondary="SatB"),
         "RiskA", "RiskB", "dangerous", "warning"),
    ]
    for label, body, e1, e2, s1_kind, s2_kind in b3_no_transition_tests:
        data = build_graph(body) + ontology + config
        before = set(data.subjects(RDF.type, ONTO.StateTransition))
        run_rules_to_fixed_point(data, rules)
        s1 = st(s1_kind, e1)
        s2 = st(s2_kind, e2)
        after = set(data.subjects(RDF.type, ONTO.StateTransition))
        new_transitions = after - before
        direct_relation = (s1, ONTO.transitsTo, s2) in data
        ok = direct_relation and not new_transitions
        all_ok = all_ok and ok
        detail = f"transitsTo={'Y' if direct_relation else 'N'}, 新StateTransition={len(new_transitions)}"
        print(f"{label}: {'PASS' if ok else 'FAIL'} [{detail}]")
        results.append({
            "id": label,
            "description": f"B3 直接建立{s1_kind}→{s2_kind}且不创建 StateTransition",
            "expected": True, "actual": ok, "pass": ok,
            "detail": detail,
        })

    if not only_b2_b3:
        out = Path(__file__).resolve().parent / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        (out / "boundary_test_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n全部{len(results)}项边界测试{'通过' if all_ok else '存在不符项'}")
    if not only_b2_b3:
        print(f"结果文件：{out / 'boundary_test_results.json'}")
    else:
        print("B2/B3 筛选模式：未写入结果文件")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
