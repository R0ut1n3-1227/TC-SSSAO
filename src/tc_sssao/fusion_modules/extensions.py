"""TC-SSSAO 扩展词汇（Extension Vocabulary）

本模块定义不属于论文核心模型但在完整本体中保留的扩展类。
这些类仍参与 OWL 推理（子类闭包、属性 domain/range 等），
但不在论文图 3-1 核心概念图中展示。

标注方式：导出时所有本模块类会标记 onto:modelLayer "extension"。

用户指定的 Extension 类：
- DirectCausalAssertion / IndirectCausalAssertion /
  PromotingCausalAssertion / InhibitingCausalAssertion
- RiskEscalationTransition / RiskReductionTransition /
  ThreatEscalationTransition / RecoveryTransition
- CyberThreat / CyberSecurityRisk
- TrackingSystem / SurveillanceSystem
- MitigationMeasure / WarningMeasure
"""
from __future__ import annotations

from .meta_schema import OntologyClass


# ============================================================
# Extension: Causal Assertion Subtypes
# ============================================================

CLS_DIRECT_CAUSAL_ASSERTION = OntologyClass(
    name_en="DirectCausalAssertion",
    name_zh="直接因果断言",
    parents=["CausalAssertion"],
    description="原因事件直接导致结果事件的因果断言。",
    namespace="causal",
)

CLS_INDIRECT_CAUSAL_ASSERTION = OntologyClass(
    name_en="IndirectCausalAssertion",
    name_zh="间接因果断言",
    parents=["CausalAssertion"],
    description="原因事件通过中间环节导致结果事件的因果断言。",
    namespace="causal",
)

CLS_PROMOTING_CAUSAL_ASSERTION = OntologyClass(
    name_en="PromotingCausalAssertion",
    name_zh="促进型因果断言",
    parents=["CausalAssertion"],
    description="原因事件促进但非必然导致结果事件的因果断言。",
    namespace="causal",
)

CLS_INHIBITING_CAUSAL_ASSERTION = OntologyClass(
    name_en="InhibitingCausalAssertion",
    name_zh="抑制型因果断言",
    parents=["CausalAssertion"],
    description="原因事件抑制或削弱结果事件的因果断言。",
    namespace="causal",
)


# ============================================================
# Extension: StateTransition Subtypes
# ============================================================

CLS_RISK_ESCALATION_TRANSITION = OntologyClass(
    name_en="RiskEscalationTransition",
    name_zh="风险升级转移",
    parents=["StateTransition"],
    description="风险等级上升的状态转移。",
    namespace="domain",
)

CLS_RISK_REDUCTION_TRANSITION = OntologyClass(
    name_en="RiskReductionTransition",
    name_zh="风险降级转移",
    parents=["StateTransition"],
    description="风险等级下降的状态转移。",
    namespace="domain",
)

CLS_THREAT_ESCALATION_TRANSITION = OntologyClass(
    name_en="ThreatEscalationTransition",
    name_zh="威胁升级转移",
    parents=["StateTransition"],
    description="威胁等级上升的状态转移。",
    namespace="domain",
)

CLS_RECOVERY_TRANSITION = OntologyClass(
    name_en="RecoveryTransition",
    name_zh="恢复转移",
    parents=["StateTransition"],
    description="态势从异常/危险向正常恢复的转移。",
    namespace="domain",
)


# ============================================================
# Extension: Cyber / Security Extension
# ============================================================

CLS_CYBER_THREAT = OntologyClass(
    name_en="CyberThreat",
    name_zh="网络威胁",
    parents=["SecurityThreat"],
    description="通过网络手段对空间系统造成的威胁。",
    namespace="domain",
)

CLS_CYBER_SECURITY_RISK = OntologyClass(
    name_en="CyberSecurityRisk",
    name_zh="网络安全风险",
    parents=["SecurityRisk"],
    description="网络攻击导致的风险。",
    namespace="domain",
)


# ============================================================
# Extension: Observation System Subtypes
# ============================================================

CLS_TRACKING_SYSTEM = OntologyClass(
    name_en="TrackingSystem",
    name_zh="跟踪系统",
    parents=["ObservationSystem"],
    description="用于持续跟踪空间目标的系统。",
    namespace="domain",
)

CLS_SURVEILLANCE_SYSTEM = OntologyClass(
    name_en="SurveillanceSystem",
    name_zh="监视系统",
    parents=["ObservationSystem"],
    description="用于监视空间区域的系统。",
    namespace="domain",
)


# ============================================================
# Extension: Response Measure Subtypes
# ============================================================

CLS_MITIGATION_MEASURE = OntologyClass(
    name_en="MitigationMeasure",
    name_zh="缓解措施",
    parents=["ResponseMeasure"],
    description="减轻威胁或风险后果的措施。",
    namespace="domain",
)

CLS_WARNING_MEASURE = OntologyClass(
    name_en="WarningMeasure",
    name_zh="预警措施",
    parents=["ResponseMeasure"],
    description="提前发出预警的响应措施。",
    namespace="domain",
)


# ============================================================
# Aggregation tuples
# ============================================================

EXTENSION_CLASSES: tuple[OntologyClass, ...] = (
    # Causal subtypes
    CLS_DIRECT_CAUSAL_ASSERTION,
    CLS_INDIRECT_CAUSAL_ASSERTION,
    CLS_PROMOTING_CAUSAL_ASSERTION,
    CLS_INHIBITING_CAUSAL_ASSERTION,
    # StateTransition subtypes
    CLS_RISK_ESCALATION_TRANSITION,
    CLS_RISK_REDUCTION_TRANSITION,
    CLS_THREAT_ESCALATION_TRANSITION,
    CLS_RECOVERY_TRANSITION,
    # Cyber extension
    CLS_CYBER_THREAT,
    CLS_CYBER_SECURITY_RISK,
    # Observation system subtypes
    CLS_TRACKING_SYSTEM,
    CLS_SURVEILLANCE_SYSTEM,
    # Response measure subtypes
    CLS_MITIGATION_MEASURE,
    CLS_WARNING_MEASURE,
)
