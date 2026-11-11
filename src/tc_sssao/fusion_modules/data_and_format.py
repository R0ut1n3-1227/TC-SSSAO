"""TC-SSSAO 数据模块

定义 SSAData 数据层级（观测/跟踪/评估/预测数据）。
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation


# ============================================================
# Data Properties (common to SSAData)
# ============================================================

PROP_HAS_DATA_ID = OntologyProperty(
    name="hasDataID",
    datatype="string",
    name_zh="数据编号",
    description="SSA 数据唯一标识。",
    domain="SSAData",
)

PROP_HAS_DATA_TYPE = OntologyProperty(
    name="hasDataType",
    datatype="string",
    name_zh="数据类型",
    description="数据类型说明。",
    domain="SSAData",
)

PROP_HAS_DATA_SOURCE = OntologyProperty(
    name="hasDataSource",
    datatype="string",
    name_zh="数据来源",
    description="数据来源说明。",
    domain="SSAData",
)

PROP_HAS_ERROR_VALUE = OntologyProperty(
    name="hasErrorValue",
    datatype="float",
    name_zh="误差值",
    description="数据误差值。",
    domain="SSAData",
)

PROP_HAS_DATA_CONFIDENCE = OntologyProperty(
    name="hasDataConfidence",
    datatype="float",
    name_zh="数据置信度",
    description="数据可信程度。",
    domain="SSAData",
)


# ============================================================
# SSAData classes
# ============================================================

CLS_SSA_DATA = OntologyClass(
    name_en="SSAData",
    name_zh="太空态势感知数据",
    description="太空态势感知领域的各类数据抽象。",
    namespace="domain",
    properties=[PROP_HAS_DATA_ID, PROP_HAS_DATA_TYPE, PROP_HAS_DATA_SOURCE, PROP_HAS_ERROR_VALUE, PROP_HAS_DATA_CONFIDENCE],
)

CLS_OBSERVATION_DATA = OntologyClass(
    name_en="ObservationData",
    name_zh="观测数据",
    parents=["SSAData"],
    description="通过观测系统获取的数据。",
    namespace="domain",
)

CLS_SENSOR_OBSERVATION_DATA = OntologyClass(
    name_en="SensorObservationData",
    name_zh="传感器观测数据",
    parents=["ObservationData"],
    description="传感器产生的观测数据。",
    namespace="domain",
)

CLS_RADAR_OBSERVATION_DATA = OntologyClass(
    name_en="RadarObservationData",
    name_zh="雷达观测数据",
    parents=["SensorObservationData"],
    description="雷达传感器产生的观测数据。",
    namespace="domain",
)

CLS_TRACKING_DATA = OntologyClass(
    name_en="TrackingData",
    name_zh="跟踪数据",
    parents=["SSAData"],
    description="跟踪数据。",
    namespace="domain",
)

CLS_PREDICTION_DATA = OntologyClass(
    name_en="PredictionData",
    name_zh="预测数据",
    parents=["SSAData"],
    description="预测数据。",
    namespace="domain",
)

CLS_ASSESSMENT_DATA = OntologyClass(
    name_en="AssessmentData",
    name_zh="评估数据",
    parents=["SSAData"],
    description="评估数据。",
    namespace="domain",
)

CLS_SITUATION_ASSESSMENT_DATA = OntologyClass(
    name_en="SituationAssessmentData",
    name_zh="态势评估数据",
    parents=["AssessmentData"],
    description="态势评估数据。",
    namespace="domain",
)

CLS_RISK_ASSESSMENT_DATA = OntologyClass(
    name_en="RiskAssessmentData",
    name_zh="风险评估数据",
    parents=["SituationAssessmentData"],
    description="风险评估数据。",
    namespace="domain",
)


# ============================================================
# Object properties
# ============================================================

REL_DESCRIBES_OBJECT = OntologyRelation(
    name="describesObject",
    name_zh="描述目标",
    domain="SSAData",
    range="SpaceObject",
    description="SSA 数据描述空间目标。",
)

REL_DETECTED_FROM_DATA = OntologyRelation(
    name="detectedFromData",
    name_zh="由数据发现",
    domain="SpaceEvent",
    range="SSAData",
    description="空间事件由 SSA 数据发现。",
)

REL_HAS_OBSERVATION_RESULT = OntologyRelation(
    name="hasObservationResult",
    name_zh="具有观测结果",
    domain="ObservationData",
    range="SpaceObject",
    description="观测数据具有观测结果目标。",
)

REL_HAS_FEATURE_OF_INTEREST = OntologyRelation(
    name="hasFeatureOfInterest",
    name_zh="具有关注目标",
    domain="SSAData",
    range="SpaceObject",
    description="SSA 数据所关注的空间目标。",
)

REL_GENERATED_BY = OntologyRelation(
    name="generatedBy",
    name_zh="由……生成",
    domain="ObservationData",
    range="ObservationSystem",
    description="观测数据由观测系统生成。",
)

REL_GENERATED_BY_ACTIVITY = OntologyRelation(
    name="generatedByActivity",
    name_zh="由活动生成",
    domain="SSAData",
    range="ObservationEvent",
    description="SSA 数据由观测活动事件生成。",
)


# ============================================================
# Aggregations
# ============================================================

ALL_CLASSES: tuple[OntologyClass, ...] = (CLS_SSA_DATA, CLS_OBSERVATION_DATA, CLS_SENSOR_OBSERVATION_DATA, CLS_RADAR_OBSERVATION_DATA, CLS_TRACKING_DATA, CLS_PREDICTION_DATA, CLS_ASSESSMENT_DATA, CLS_SITUATION_ASSESSMENT_DATA, CLS_RISK_ASSESSMENT_DATA)

ALL_RELATIONS: tuple[OntologyRelation, ...] = (REL_DESCRIBES_OBJECT, REL_DETECTED_FROM_DATA, REL_HAS_OBSERVATION_RESULT, REL_HAS_FEATURE_OF_INTEREST, REL_GENERATED_BY, REL_GENERATED_BY_ACTIVITY)
