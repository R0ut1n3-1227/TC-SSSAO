"""TC-SSSAO 安全威胁、安全风险与响应措施模块

本模块定义：
- 安全威胁（SecurityThreat）层级
- 安全风险（SecurityRisk）层级
- 响应措施（ResponseMeasure）层级及对应机动事件
"""

from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction


# ============================================================
# Data Properties
# ============================================================

PROP_HAS_THREAT_ID = OntologyProperty(
    name="hasThreatID",
    datatype="string",
    name_zh="威胁编号",
    description="安全威胁唯一标识。",
    domain="SecurityThreat",
)

PROP_HAS_THREAT_TYPE = OntologyProperty(
    name="hasThreatType",
    datatype="string",
    name_zh="威胁类型",
    description="威胁类型，如物理、网络、电磁、环境、运行等。",
    domain="SecurityThreat",
)

PROP_HAS_THREAT_SOURCE = OntologyProperty(
    name="hasThreatSource",
    datatype="string",
    name_zh="威胁来源",
    description="威胁来源，如碎片、目标、环境、网络等。",
    domain="SecurityThreat",
)

PROP_HAS_IMPACT_SCOPE = OntologyProperty(
    name="hasImpactScope",
    datatype="string",
    name_zh="影响范围",
    description="威胁影响范围，如目标、轨道区域、任务系统等。",
    domain="SecurityThreat",
)

# 注：hasRiskValue 的权威定义见 space_event 模块（domain=RiskEvent，
# 可选外部综合风险评分，R5—R8 不再使用）；本重复定义在融合时按“先见优先”被去重。
PROP_HAS_RISK_VALUE = OntologyProperty(
    name="hasRiskValue",
    datatype="float",
    name_zh="风险值",
    description="由外部风险评估模型、任务系统或应用层给出的可选综合风险评分，其计算方法与取值尺度由外部系统规定，不由本体规定；承载外部评估结果，不等同于碰撞概率 hasCollisionProbability；碰撞风险态势规则（R5—R8）不再以该属性为判定条件。",
    domain="RiskEvent",
)

PROP_HAS_MEASURE_ID = OntologyProperty(
    name="hasMeasureID",
    datatype="string",
    name_zh="措施编号",
    description="响应措施唯一标识。",
    domain="ResponseMeasure",
)

PROP_HAS_MEASURE_DESCRIPTION = OntologyProperty(
    name="hasMeasureDescription",
    datatype="string",
    name_zh="措施描述",
    description="响应措施描述。",
    domain="ResponseMeasure",
)

PROP_HAS_MEASURE_TYPE = OntologyProperty(
    name="hasMeasureType",
    datatype="string",
    name_zh="措施类型",
    description="措施类型，如规避、应急、缓解、预警等。",
    domain="ResponseMeasure",
)

PROP_HAS_MEASURE_LEVEL = OntologyProperty(
    name="hasMeasureLevel",
    datatype="string",
    name_zh="措施等级",
    description="措施等级，如一般、重要、紧急。",
    domain="ResponseMeasure",
)


# ============================================================
# Classes
# ============================================================

# ---------- SecurityThreat ----------
CLS_SECURITY_THREAT = OntologyClass(
    name_en="SecurityThreat",
    name_zh="安全威胁",
    description="可能对太空资产、轨道环境或任务系统造成危害的威胁类型。",
    namespace="domain",
    properties=[
        PROP_HAS_THREAT_ID,
        PROP_HAS_THREAT_TYPE,
        PROP_HAS_THREAT_SOURCE,
        PROP_HAS_IMPACT_SCOPE,
    ],
    restrictions=[
        OntologyRestriction("mayManifestAsEvent", "SpaceEvent"),
        OntologyRestriction("producesRisk", "SecurityRisk"),
        OntologyRestriction("requiresResponseMeasure", "ResponseMeasure"),
        OntologyRestriction("mitigatedBy", "ResponseMeasure"),
    ],
)

CLS_PHYSICAL_THREAT = OntologyClass(
    name_en="PhysicalThreat",
    name_zh="物理威胁",
    parents=["SecurityThreat"],
    description="由物理接近或碰撞等物理作用导致的威胁。",
    namespace="domain",
)

CLS_ENVIRONMENTAL_THREAT = OntologyClass(
    name_en="EnvironmentalThreat",
    name_zh="环境威胁",
    parents=["SecurityThreat"],
    description="由空间环境异常导致的威胁。",
    namespace="domain",
)


# ---------- SecurityRisk ----------
CLS_SECURITY_RISK = OntologyClass(
    name_en="SecurityRisk",
    name_zh="安全风险",
    description="空间系统或任务面临损失的潜在可能性。",
    namespace="domain",
    properties=[PROP_HAS_RISK_VALUE],
    restrictions=[
        OntologyRestriction("mitigatedBy", "ResponseMeasure"),
        OntologyRestriction("leadsToState", "SituationState"),
    ],
)

CLS_COLLISION_RISK = OntologyClass(
    name_en="CollisionRisk",
    name_zh="碰撞风险",
    parents=["SecurityRisk"],
    description="空间目标碰撞导致的风险。",
    namespace="domain",
)

CLS_DEBRIS_RISK = OntologyClass(
    name_en="DebrisRisk",
    name_zh="碎片风险",
    parents=["SecurityRisk"],
    description="空间碎片导致的风险。",
    namespace="domain",
)


# ---------- ResponseMeasure ----------
CLS_RESPONSE_MEASURE = OntologyClass(
    name_en="ResponseMeasure",
    name_zh="响应措施",
    description="为应对安全威胁或安全风险采取的措施。",
    namespace="domain",
    properties=[PROP_HAS_MEASURE_ID, PROP_HAS_MEASURE_TYPE, PROP_HAS_MEASURE_LEVEL, PROP_HAS_MEASURE_DESCRIPTION],
    restrictions=[
        OntologyRestriction("respondsToThreat", "SecurityThreat"),
        OntologyRestriction("respondsToEvent", "SpaceEvent"),
        OntologyRestriction("mitigatesRisk", "SecurityRisk"),
        OntologyRestriction("isImplementedByEvent", "SpaceEvent"),
    ],
)

CLS_AVOIDANCE_MEASURE = OntologyClass(
    name_en="AvoidanceMeasure",
    name_zh="规避措施",
    parents=["ResponseMeasure"],
    description="通过规避动作降低威胁或风险的措施。",
    namespace="domain",
)


# ---------- Maneuver events ----------

# ============================================================
# Object Properties / Relations
# ============================================================

REL_PRODUCES_RISK = OntologyRelation(
    name="producesRisk",
    name_zh="产生风险",
    domain="SecurityThreat",
    range="SecurityRisk",
    description="安全威胁产生安全风险。",
)

REL_MAY_MANIFEST_AS_EVENT = OntologyRelation(
    name="mayManifestAsEvent",
    name_zh="可能表现为事件",
    domain="SecurityThreat",
    range="SpaceEvent",
    description="安全威胁可能表现为空间事件。",
)

REL_LEADS_TO_STATE = OntologyRelation(
    name="leadsToState",
    name_zh="导致状态",
    domain="SpaceEvent",
    range="SituationState",
    description="事件导致态势状态。",
)

REL_STATE_CAUSED_BY_EVENT = OntologyRelation(
    name="stateCausedByEvent",
    name_zh="状态由事件导致",
    domain="SituationState",
    range="SpaceEvent",
    description="态势状态由事件导致。",
    inverse_of="leadsToState",
)

REL_TRIGGERS_STATE = OntologyRelation(
    name="triggersState",
    name_zh="触发状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件触发态势状态。",
)

REL_AFFECTS_STATE = OntologyRelation(
    name="affectsState",
    name_zh="影响状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件影响态势状态。",
)

REL_UPDATES_STATE = OntologyRelation(
    name="updatesState",
    name_zh="更新状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件更新态势状态。",
)

REL_REQUIRES_RESPONSE_MEASURE = OntologyRelation(
    name="requiresResponseMeasure",
    name_zh="需要响应措施",
    domain="SecurityThreat",
    range="ResponseMeasure",
    description="安全威胁需要响应措施。",
    inverse_of="respondsToThreat",
)

REL_RESPONDS_TO_EVENT = OntologyRelation(
    name="respondsToEvent",
    name_zh="响应事件",
    domain="ResponseMeasure",
    range="SpaceEvent",
    description="响应措施响应空间事件。",
)

REL_RESPONDS_TO_THREAT = OntologyRelation(
    name="respondsToThreat",
    name_zh="响应威胁",
    domain="ResponseMeasure",
    range="SecurityThreat",
    description="响应措施响应安全威胁。",
    inverse_of="requiresResponseMeasure",
)

REL_MITIGATES_RISK = OntologyRelation(
    name="mitigatesRisk",
    name_zh="缓解风险",
    domain="ResponseMeasure",
    range="SecurityRisk",
    description="响应措施缓解安全风险。",
)

REL_MITIGATED_BY = OntologyRelation(
    name="mitigatedBy",
    name_zh="被缓解",
    domain="SecurityRisk",
    range="ResponseMeasure",
    description="安全风险被响应措施缓解。",
    inverse_of="mitigatesRisk",
)

REL_IMPLEMENTS_MEASURE = OntologyRelation(
    name="implementsMeasure",
    name_zh="实施措施",
    domain="SpaceEvent",
    range="ResponseMeasure",
    description="空间事件实施响应措施。",
)

REL_IS_IMPLEMENTED_BY_EVENT = OntologyRelation(
    name="isImplementedByEvent",
    name_zh="由事件实施",
    domain="ResponseMeasure",
    range="SpaceEvent",
    description="响应措施由空间事件实施。",
    inverse_of="implementsMeasure",
)

REL_CHANGES_ORBIT = OntologyRelation(
    name="changesOrbit",
    name_zh="改变轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件改变轨道。",
)


# ============================================================
# Aggregation
# ============================================================

THREAT_CLASSES: tuple[OntologyClass, ...] = (CLS_SECURITY_THREAT, CLS_PHYSICAL_THREAT, CLS_ENVIRONMENTAL_THREAT)

RISK_CLASSES: tuple[OntologyClass, ...] = (CLS_SECURITY_RISK, CLS_COLLISION_RISK, CLS_DEBRIS_RISK)

MEASURE_CLASSES: tuple[OntologyClass, ...] = (CLS_RESPONSE_MEASURE, CLS_AVOIDANCE_MEASURE)

MANEUVER_EVENT_CLASSES: tuple[OntologyClass, ...] = ()

ALL_CLASSES: tuple[OntologyClass, ...] = (
    *THREAT_CLASSES,
    *RISK_CLASSES,
    *MEASURE_CLASSES,
    *MANEUVER_EVENT_CLASSES,
)

ALL_PROPERTIES: tuple[OntologyProperty, ...] = (PROP_HAS_THREAT_ID, PROP_HAS_THREAT_TYPE, PROP_HAS_THREAT_SOURCE, PROP_HAS_IMPACT_SCOPE, PROP_HAS_RISK_VALUE, PROP_HAS_MEASURE_ID, PROP_HAS_MEASURE_DESCRIPTION, PROP_HAS_MEASURE_TYPE, PROP_HAS_MEASURE_LEVEL)

ALL_RELATIONS: tuple[OntologyRelation, ...] = (REL_PRODUCES_RISK, REL_MAY_MANIFEST_AS_EVENT, REL_LEADS_TO_STATE, REL_STATE_CAUSED_BY_EVENT, REL_TRIGGERS_STATE, REL_AFFECTS_STATE, REL_UPDATES_STATE, REL_REQUIRES_RESPONSE_MEASURE, REL_RESPONDS_TO_EVENT, REL_RESPONDS_TO_THREAT, REL_MITIGATES_RISK, REL_MITIGATED_BY, REL_IMPLEMENTS_MEASURE, REL_IS_IMPLEMENTED_BY_EVENT, REL_CHANGES_ORBIT)