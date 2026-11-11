"""时序-因果-态势-转移模块 (TC-SSSAO)

Temporal, causal, situation-state and state-transition building blocks for the
space-security situation-awareness ontology.

Naming conventions:
- Class names: PascalCase
- Data property names: camelCase
- Object property names: camelCase
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction


# ============================================================
# Data Properties
# ============================================================

# ---------- CausalAssertion properties ----------
PROP_HAS_CAUSAL_CONFIDENCE = OntologyProperty(
    name="hasCausalConfidence",
    datatype="float",
    name_zh="因果置信度",
    description="因果断言的可选置信度元数据。当数据来源、专家评估或外部模型提供定量置信信息时记录该值；"
                "来源未给出定量置信度时不强制赋值（M3 第一阶段起由 exactly 1 放宽为 max 1）。",
    domain="CausalAssertion",
)

PROP_HAS_CAUSAL_MECHANISM = OntologyProperty(
    name="hasCausalMechanism",
    datatype="string",
    name_zh="因果机制",
    description="因果断言背后的物理或逻辑机制描述。",
    domain="CausalAssertion",
)

# ---------- SituationState properties ----------
PROP_HAS_STATE_ID = OntologyProperty(
    name="hasStateID",
    datatype="string",
    name_zh="状态编号",
    description="态势状态唯一标识。",
    domain="SituationState",
)

PROP_HAS_STATE_TYPE = OntologyProperty(
    name="hasStateType",
    datatype="string",
    name_zh="状态类型",
    description="运行状态、空间安全状态、威胁状态、综合态势状态等。",
    domain="SituationState",
)

PROP_HAS_STATE_LEVEL = OntologyProperty(
    name="hasStateLevel",
    datatype="string",
    name_zh="状态等级",
    description="正常、关注、异常、预警、危险、恢复等。",
    domain="SituationState",
)

PROP_HAS_STATE_DURATION = OntologyProperty(
    name="hasStateDuration",
    datatype="string",
    name_zh="状态持续时间",
    description="状态持续时间（ISO 8601 时长字符串，如 PT1H30M）。",
    domain="SituationState",
)

PROP_HAS_STATE_DESCRIPTION = OntologyProperty(
    name="hasStateDescription",
    datatype="string",
    name_zh="状态描述",
    description="态势状态的文字说明。",
    domain="SituationState",
)

PROP_HAS_RISK_LEVEL = OntologyProperty(
    name="hasRiskLevel",
    datatype="string",
    name_zh="风险等级",
    description="低、中、高、极高。",
    domain="SituationState",
)

PROP_HAS_STATE_CONFIDENCE = OntologyProperty(
    name="hasStateConfidence",
    datatype="float",
    name_zh="状态置信度",
    description="状态判断的可信程度。",
    domain="SituationState",
)

PROP_HAS_STATE_START_TIME = OntologyProperty(
    name="hasStateStartTime",
    datatype="dateTime",
    name_zh="状态开始时间",
    description="状态开始时间。",
    domain="SituationState",
)

PROP_HAS_STATE_END_TIME = OntologyProperty(
    name="hasStateEndTime",
    datatype="dateTime",
    name_zh="状态结束时间",
    description="状态结束时间。",
    domain="SituationState",
)

PROP_HAS_STATE_UPDATE_TIME = OntologyProperty(
    name="hasStateUpdateTime",
    datatype="dateTime",
    name_zh="态势状态更新时间",
    description="态势状态最近一次更新时间。",
    domain="SituationState",
)

PROP_HAS_SEVERITY_RANK = OntologyProperty(
    name="hasSeverityRank",
    datatype="integer",
    name_zh="严重度级别",
    description="分级风险态势的严重度排序值：正常=0、关注=1、预警=2、危险=3；仅用于支持分级态势之间的排序及跨时间演化规则。",
    domain="SituationState",
)


# ============================================================
# Classes
# ============================================================

# ---------- TemporalEntity ----------
CLS_TEMPORAL_ENTITY = OntologyClass(
    name_en="TemporalEntity",
    name_zh="时序实体",
    description="时间维度的顶层抽象。",
    namespace="temporal",
)

CLS_TIME_INSTANT = OntologyClass(
    name_en="TimeInstant",
    name_zh="时间点",
    parents=["TemporalEntity"],
    description="零长度的时间点。",
    namespace="temporal",
)

CLS_TIME_INTERVAL = OntologyClass(
    name_en="TimeInterval",
    name_zh="时间区间",
    parents=["TemporalEntity"],
    description="具有开始与结束两个端点的时间区间。",
    namespace="temporal",
    restrictions=[
        OntologyRestriction("hasBeginning", "TimeInstant"),
        OntologyRestriction("hasEnd", "TimeInstant"),
    ],
)


# ---------- CausalAssertion ----------
CLS_CAUSAL_ASSERTION = OntologyClass(
    name_en="CausalAssertion",
    name_zh="因果断言",
    description="描述事件之间因果关系的断言。",
    namespace="causal",
    properties=[PROP_HAS_CAUSAL_CONFIDENCE, PROP_HAS_CAUSAL_MECHANISM],
    restrictions=[
        OntologyRestriction("hasCause", "SpaceEvent"),
        OntologyRestriction("hasEffect", "SpaceEvent"),
        OntologyRestriction("hasCausalEvidence", "SSAData"),
    ],
)

CLS_MULTI_CAUSE_ASSERTION = OntologyClass(
    name_en="MultiCauseAssertion",
    name_zh="多因因果断言",
    parents=["CausalAssertion"],
    description="多个原因事件共同导致结果事件的因果断言。",
    namespace="causal",
)


# ---------- SSAData (range for hasCausalEvidence / supportedByData) ----------
CLS_SSA_DATA = OntologyClass(
    name_en="SSAData",
    name_zh="太空态势感知数据",
    description="支撑因果断言与事件判断的太空态势感知数据。",
    namespace="domain",
)


# ---------- SituationState ----------
# 2026-09-06 终审 schema 修复（归因记录）：删除全部状态类上
# transitsTo/transitsFrom/degradesTo/recoversTo 的 someValuesFrom 存在性限制
# （含原 SituationState 级 transitsTo some SituationState 与 Normal/Attention/
# Warning/Dangerous 四类上的 8 条）。这些公理在 OWL 语义下断言“每个状态实例
# 必然存在固定方向的转移/恶化/恢复关系”（如 Dangerous 必然恢复为 Normal），
# 与 B3 的条件式状态演化（同一目标对+相邻快照+时间先后+严重度升高才生成）
# 冲突。状态类不再预设必然转移；实例级状态演化只来自 StateTransition+B2 与
# B3 桥接规则；transitsTo 等属性本身保留 domain/range/inverseOf 定义。
CLS_SITUATION_STATE = OntologyClass(
    name_en="SituationState",
    name_zh="态势状态",
    description="描述某一阶段的安全态势。",
    namespace="domain",
    properties=[
        PROP_HAS_STATE_ID,
        PROP_HAS_STATE_TYPE,
        PROP_HAS_STATE_LEVEL,
        PROP_HAS_RISK_LEVEL,
        PROP_HAS_STATE_CONFIDENCE,
        PROP_HAS_STATE_DESCRIPTION,
        PROP_HAS_STATE_START_TIME,
        PROP_HAS_STATE_END_TIME,
        PROP_HAS_STATE_DURATION,
        PROP_HAS_STATE_UPDATE_TIME,
        PROP_HAS_SEVERITY_RANK,
    ],
    restrictions=[
        OntologyRestriction("stateCausedByEvent", "SpaceEvent"),
        OntologyRestriction("hasStateLevel", "string"),
        OntologyRestriction("hasStateConfidence", "float"),
        OntologyRestriction("hasStateStartTime", "dateTime"),
        OntologyRestriction("hasStateEndTime", "dateTime"),
        OntologyRestriction("hasStateUpdateTime", "dateTime"),
        # 2026-09-14 SituationState 层级简化：hasSeverityRank 最多一个值
        OntologyRestriction("hasSeverityRank", "integer",
                            restriction_type="maxCardinality", max_cardinality=1),
    ],
)

# 2026-09-14 SituationState 层级简化：删除 ComprehensiveSituationState，
# Normal/Attention/Warning/Dangerous 四状态直连 SituationState，
# 以 owl:hasValue 限定各自的严重度级别（0/1/2/3）。

CLS_NORMAL_SITUATION_STATE = OntologyClass(
    name_en="NormalSituationState",
    name_zh="正常态势状态",
    parents=["SituationState"],
    description="整体态势正常。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("hasSeverityRank", "integer",
                            restriction_type="hasValue", has_value="0"),
    ],
)

CLS_ATTENTION_SITUATION_STATE = OntologyClass(
    name_en="AttentionSituationState",
    name_zh="关注态势状态",
    parents=["SituationState"],
    description="整体态势需要关注。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("hasSeverityRank", "integer",
                            restriction_type="hasValue", has_value="1"),
    ],
)

CLS_WARNING_SITUATION_STATE = OntologyClass(
    name_en="WarningSituationState",
    name_zh="预警态势状态",
    parents=["SituationState"],
    description="整体态势达到预警级别。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("hasSeverityRank", "integer",
                            restriction_type="hasValue", has_value="2"),
    ],
)

CLS_DANGEROUS_SITUATION_STATE = OntologyClass(
    name_en="DangerousSituationState",
    name_zh="危险态势状态",
    parents=["SituationState"],
    description="整体态势处于危险级别。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("hasSeverityRank", "integer",
                            restriction_type="hasValue", has_value="3"),
    ],
)

# ---------- StateTransition ----------
CLS_STATE_TRANSITION = OntologyClass(
    name_en="StateTransition",
    name_zh="状态转移",
    description="态势状态之间的转移。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("hasSourceState", "SituationState"),
        OntologyRestriction("hasTargetState", "SituationState"),
        OntologyRestriction("triggeredByEvent", "SpaceEvent"),
    ],
)


# ============================================================
# Object Properties / Relations
# ============================================================

TEMPORAL_CAUSAL_STATE_RELATIONS: tuple[OntologyRelation, ...] = [OntologyRelation(
        name="occursAtTime",
        name_zh="发生于时间点",
        domain="SpaceEvent",
        range="TimeInstant",
        description="事件发生在某一时间点。",
        namespace="temporal",
    ), OntologyRelation(
        name="occursInTimeInterval",
        name_zh="发生于时间区间",
        domain="SpaceEvent",
        range="TimeInterval",
        description="事件发生在某一时间区间内。",
        namespace="temporal",
    ), OntologyRelation(
        name="hasBeginning",
        name_zh="具有开始",
        domain="TimeInterval",
        range="TimeInstant",
        description="时间区间的开始时间点。",
        namespace="temporal",
    ), OntologyRelation(
        name="hasEnd",
        name_zh="具有结束",
        domain="TimeInterval",
        range="TimeInstant",
        description="时间区间的结束时间点。",
        namespace="temporal",
    ), OntologyRelation(
        name="hasCause",
        name_zh="具有原因",
        domain="CausalAssertion",
        range="SpaceEvent",
        description="因果断言中的原因事件。",
        namespace="causal",
    ), OntologyRelation(
        name="hasEffect",
        name_zh="具有结果",
        domain="CausalAssertion",
        range="SpaceEvent",
        description="因果断言中的结果事件。",
        namespace="causal",
    ), OntologyRelation(
        name="hasCausalEvidence",
        name_zh="具有因果证据",
        domain="CausalAssertion",
        range="SSAData",
        description="支撑因果断言的 SSA 数据。",
        namespace="causal",
    ), OntologyRelation(
        name="transitsTo",
        name_zh="转移到",
        domain="SituationState",
        range="SituationState",
        description="态势状态转移到另一状态。",
        namespace="domain",
    ), OntologyRelation(
        name="transitsFrom",
        name_zh="转移自",
        domain="SituationState",
        range="SituationState",
        description="态势状态转移自另一状态。",
        namespace="domain",
        inverse_of="transitsTo",
    ), OntologyRelation(
        name="evolvesTo",
        name_zh="演化为",
        domain="SituationState",
        range="SituationState",
        description="态势状态演化为另一状态。",
        namespace="domain",
    ), OntologyRelation(
        name="degradesTo",
        name_zh="恶化为",
        domain="SituationState",
        range="SituationState",
        description="态势状态恶化为另一状态。",
        namespace="domain",
    ), OntologyRelation(
        name="recoversTo",
        name_zh="恢复为",
        domain="SituationState",
        range="SituationState",
        description="态势状态恢复为另一状态。",
        namespace="domain",
    ), OntologyRelation(
        name="hasSourceState",
        name_zh="具有源状态",
        domain="StateTransition",
        range="SituationState",
        description="状态转移的源状态。",
        namespace="domain",
    ), OntologyRelation(
        name="hasTargetState",
        name_zh="具有目标状态",
        domain="StateTransition",
        range="SituationState",
        description="状态转移的目标状态。",
        namespace="domain",
    ), OntologyRelation(
        name="triggeredByEvent",
        name_zh="由事件触发",
        domain="StateTransition",
        range="SpaceEvent",
        description="触发状态转移的空间事件。",
        namespace="domain",
    ), OntologyRelation(
        name="supportedByData",
        name_zh="由数据支撑",
        domain="SpaceEvent",
        range="SSAData",
        description="空间事件由 SSA 数据支撑。",
        namespace="domain",
    )]


# ============================================================
# Aggregation tuples
# ============================================================

TEMPORAL_CLASSES: tuple[OntologyClass, ...] = (
    CLS_TEMPORAL_ENTITY,
    CLS_TIME_INSTANT,
    CLS_TIME_INTERVAL,
)

CAUSAL_CLASSES: tuple[OntologyClass, ...] = (
    CLS_CAUSAL_ASSERTION,
    CLS_MULTI_CAUSE_ASSERTION,
    CLS_SSA_DATA,
)

SITUATION_STATE_CLASSES: tuple[OntologyClass, ...] = (CLS_SITUATION_STATE, CLS_NORMAL_SITUATION_STATE, CLS_ATTENTION_SITUATION_STATE, CLS_WARNING_SITUATION_STATE, CLS_DANGEROUS_SITUATION_STATE)

STATE_TRANSITION_CLASSES: tuple[OntologyClass, ...] = (
    CLS_STATE_TRANSITION,
)

ALL_TEMPORAL_CAUSAL_STATE_CLASSES: tuple[OntologyClass, ...] = (
    *TEMPORAL_CLASSES,
    *CAUSAL_CLASSES,
    *SITUATION_STATE_CLASSES,
    *STATE_TRANSITION_CLASSES,
)

ALL_TEMPORAL_CAUSAL_STATE_PROPERTIES: tuple[OntologyProperty, ...] = (PROP_HAS_CAUSAL_CONFIDENCE, PROP_HAS_CAUSAL_MECHANISM, PROP_HAS_STATE_ID, PROP_HAS_STATE_TYPE, PROP_HAS_STATE_LEVEL, PROP_HAS_STATE_DURATION, PROP_HAS_STATE_DESCRIPTION, PROP_HAS_RISK_LEVEL, PROP_HAS_STATE_CONFIDENCE, PROP_HAS_STATE_START_TIME, PROP_HAS_STATE_END_TIME, PROP_HAS_STATE_UPDATE_TIME)

ALL_TEMPORAL_CAUSAL_STATE_RELATIONS: tuple[OntologyRelation, ...] = TEMPORAL_CAUSAL_STATE_RELATIONS
