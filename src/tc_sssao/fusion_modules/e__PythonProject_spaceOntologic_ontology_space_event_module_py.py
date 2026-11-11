"""太空安全态势感知本体 — 空间事件模块

定义以 SpaceEvent 为顶层的完整事件分类体系,支持多重继承。
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction


# ============================================================
# Data Properties (SpaceEvent branch)
# ============================================================

PROP_HAS_EVENT_ID = OntologyProperty(
    name="hasEventID",
    datatype="string",
    name_zh="事件编号",
    description="事件唯一标识。",
    domain="SpaceEvent",
)

# P1-1 fix: hasEncounterID for B3 cross-encounter isolation
# ESA event_id is the official encounter-level identifier ("unique id per collision event").
# All CDM snapshots for the same physical orbital encounter share one event_id.
PROP_HAS_ENCOUNTER_ID = OntologyProperty(
    name="hasEncounterID",
    datatype="string",
    name_zh="交会编号",
    description=(
        "交会事件编号，标识同一物理交会事件的所有风险评估快照。"
        "ESA数据中对应event_id字段，同一物理交会的所有CDM共享同一event_id。"
        "B3规则使用此属性实现跨交会隔离。"
    ),
    domain="SpaceEvent",
)

PROP_HAS_EVENT_TYPE = OntologyProperty(
    name="hasEventType",
    datatype="string",
    name_zh="事件类型",
    description="轨道机动、接近、碰撞风险等。",
    domain="SpaceEvent",
)

PROP_HAS_EVENT_LEVEL = OntologyProperty(
    name="hasEventLevel",
    datatype="string",
    name_zh="事件等级",
    description="一般、重要、严重等。",
    domain="SpaceEvent",
)

PROP_HAS_EVENT_DESCRIPTION = OntologyProperty(
    name="hasEventDescription",
    datatype="string",
    name_zh="事件描述",
    description="事件文字说明。",
    domain="SpaceEvent",
)

PROP_HAS_DURATION = OntologyProperty(
    name="hasDuration",
    datatype="string",
    name_zh="持续时间",
    description="事件持续时间（ISO 8601 时长字符串,如 PT1H30M）。",
    domain="SpaceEvent",
)

PROP_HAS_OCCURRENCE_TIME = OntologyProperty(
    name="hasOccurrenceTime",
    datatype="dateTime",
    name_zh="发生时间",
    description="事件发生时间。",
    domain="SpaceEvent",
)

PROP_HAS_START_TIME = OntologyProperty(
    name="hasStartTime",
    datatype="dateTime",
    name_zh="开始时间",
    description="事件开始时间。",
    domain="SpaceEvent",
)

PROP_HAS_END_TIME = OntologyProperty(
    name="hasEndTime",
    datatype="dateTime",
    name_zh="结束时间",
    description="事件结束时间。",
    domain="SpaceEvent",
)

PROP_HAS_EVENT_CONFIDENCE = OntologyProperty(
    name="hasEventConfidence",
    datatype="float",
    name_zh="事件置信度",
    description="事件判断可信程度。",
    domain="SpaceEvent",
)

PROP_HAS_RELATIVE_DISTANCE = OntologyProperty(
    name="hasRelativeDistance",
    datatype="float",
    name_zh="相对距离",
    description="两目标之间距离。",
    domain="SpatialRelationEvent",
)

PROP_HAS_COLLISION_PROBABILITY = OntologyProperty(
    name="hasCollisionProbability",
    datatype="float",
    name_zh="碰撞概率",
    description="碰撞风险概率。",
    domain="CollisionRiskEvent",
)

PROP_HAS_PREDICTED_MISS_DISTANCE = OntologyProperty(
    name="hasPredictedMissDistance",
    datatype="float",
    name_zh="预测最近交会距离",
    description="碰撞风险事件预测最近交会距离。",
    domain="CollisionRiskEvent",
)

PROP_HAS_COMBINED_HARD_BODY_RADIUS = OntologyProperty(
    name="hasCombinedHardBodyRadius",
    datatype="float",
    name_zh="组合硬体半径",
    description="当前交会风险评估中两个目标的组合硬体半径（combined hard-body radius），即两目标外接球半径之和；由外部交会评估给出，随评估事件变化，不作为全局部署常数。",
    domain="CollisionRiskEvent",
)

PROP_HAS_RISK_VALUE = OntologyProperty(
    name="hasRiskValue",
    datatype="float",
    name_zh="风险值",
    description="由外部风险评估模型、任务系统或应用层给出的可选综合风险评分，其计算方法与取值尺度由外部系统规定，不由本体规定；承载外部评估结果，不等同于碰撞概率 hasCollisionProbability；碰撞风险态势规则（R5—R8）不再以该属性为判定条件。",
    domain="RiskEvent",
)


# ============================================================
# Classes
# ============================================================

SPACE_EVENT_PROPERTIES = [PROP_HAS_EVENT_ID, PROP_HAS_ENCOUNTER_ID, PROP_HAS_EVENT_TYPE, PROP_HAS_EVENT_LEVEL, PROP_HAS_EVENT_DESCRIPTION, PROP_HAS_DURATION, PROP_HAS_OCCURRENCE_TIME, PROP_HAS_START_TIME, PROP_HAS_END_TIME, PROP_HAS_EVENT_CONFIDENCE]

CLS_SPACE_EVENT = OntologyClass(
    name_en="SpaceEvent",
    name_zh="空间事件",
    description="描述引起态势变化的空间事件。",
    namespace="domain",
    properties=SPACE_EVENT_PROPERTIES,
    restrictions=[
        OntologyRestriction("hasEventID", "string"),
        OntologyRestriction("hasEventType", "string"),
        OntologyRestriction("hasEventLevel", "string"),
        OntologyRestriction("hasOccurrenceTime", "dateTime"),
        OntologyRestriction("hasStartTime", "dateTime"),
        OntologyRestriction("hasEndTime", "dateTime"),
        OntologyRestriction("hasEventConfidence", "float"),
        OntologyRestriction("involvesObject", "SpaceObject"),
        OntologyRestriction("occursInOrbit", "Orbit"),
    ],
)

CLS_ORBITAL_EVENT = OntologyClass(
    name_en="OrbitalEvent",
    name_zh="轨道事件",
    parents=["SpaceEvent"],
    description="发生在轨道环境中、由轨道运动直接引发的轨道事件。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("occursInOrbit", "Orbit"),
        OntologyRestriction("involvesObject", "SpaceObject"),
    ],
)

CLS_FRAGMENTATION_EVENT = OntologyClass(
    name_en="FragmentationEvent",
    name_zh="解体事件",
    parents=["OrbitalEvent"],
    description="空间目标发生碎裂或解体的事件。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("involvesObject", "SpaceObject"),
    ],
)

CLS_ORBIT_MANEUVER_EVENT = OntologyClass(
    name_en="OrbitManeuverEvent",
    name_zh="轨道机动事件",
    parents=["OrbitalEvent", "ObjectBehaviorEvent"],
    description="空间目标改变轨道的机动事件。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("involvesObject", "ArtificialSpaceObject"),
        OntologyRestriction("changesOrbit", "Orbit"),
    ],
)

CLS_OBJECT_BEHAVIOR_EVENT = OntologyClass(
    name_en="ObjectBehaviorEvent",
    name_zh="目标行为事件",
    parents=["SpaceEvent"],
    description="由空间目标自身行为引发的事件。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("involvesObject", "SpaceObject"),
        OntologyRestriction("affectsOrbit", "Orbit"),
    ],
)

CLS_OBSERVATION_EVENT = OntologyClass(
    name_en="ObservationEvent",
    name_zh="观测事件",
    parents=["SpaceEvent"],
    description="由观测活动产生的事件。",
    namespace="domain",
    restrictions=[
        OntologyRestriction("detectedFromData", "ObservationData"),
    ],
)

CLS_DETECTION_EVENT = OntologyClass(
    name_en="DetectionEvent",
    name_zh="探测事件",
    parents=["ObservationEvent"],
    description="探测到空间目标的事件。",
    namespace="domain",
)

CLS_TRACKING_EVENT = OntologyClass(
    name_en="TrackingEvent",
    name_zh="跟踪事件",
    parents=["ObservationEvent"],
    description="对空间目标进行跟踪的事件。",
    namespace="domain",
)

CLS_SPATIAL_RELATION_EVENT = OntologyClass(
    name_en="SpatialRelationEvent",
    name_zh="空间关系事件",
    parents=["SpaceEvent"],
    description="描述多个空间目标之间空间关系的事件。",
    namespace="domain",
    properties=[PROP_HAS_RELATIVE_DISTANCE],
    restrictions=[
        OntologyRestriction("hasPrimaryObject", "SpaceObject"),
        OntologyRestriction("hasSecondaryObject", "SpaceObject"),
    ],
)

CLS_APPROACH_EVENT = OntologyClass(
    name_en="ApproachEvent",
    name_zh="接近事件",
    parents=["SpatialRelationEvent"],
    description="两个空间目标相互接近的事件。",
    namespace="domain",
)

CLS_RISK_EVENT = OntologyClass(
    name_en="RiskEvent",
    name_zh="风险事件",
    parents=["SpaceEvent"],
    description="描述空间安全风险的事件。",
    namespace="domain",
    properties=[PROP_HAS_RISK_VALUE],
)

CLS_COLLISION_RISK_EVENT = OntologyClass(
    name_en="CollisionRiskEvent",
    name_zh="碰撞风险事件",
    parents=["RiskEvent", "SpatialRelationEvent"],
    description="空间目标之间存在碰撞风险的事件。作为空间关系事件，通过 hasPrimaryObject/hasSecondaryObject 显式表示交会目标角色。",
    namespace="domain",
    properties=[PROP_HAS_COLLISION_PROBABILITY, PROP_HAS_PREDICTED_MISS_DISTANCE,
                PROP_HAS_COMBINED_HARD_BODY_RADIUS],
    restrictions=[
        OntologyRestriction("hasEncounterID", "string"),
        OntologyRestriction("hasCollisionProbability", "float"),
        OntologyRestriction("hasPredictedMissDistance", "float"),
    ],
)

CLS_DEBRIS_RISK_EVENT = OntologyClass(
    name_en="DebrisRiskEvent",
    name_zh="碎片风险事件",
    parents=["RiskEvent"],
    description="由空间碎片引发的风险事件。",
    namespace="domain",
)


# ============================================================
# Object Properties / Relations
# ============================================================

REL_INVOLVES_OBJECT = OntologyRelation(
    name="involvesObject",
    name_zh="涉及目标",
    domain="SpaceEvent",
    range="SpaceObject",
    description="空间事件涉及空间目标。",
)

REL_IS_INVOLVED_IN_EVENT = OntologyRelation(
    name="isInvolvedInEvent",
    name_zh="参与事件",
    domain="SpaceObject",
    range="SpaceEvent",
    description="空间目标参与空间事件。",
    inverse_of="involvesObject",
)

REL_HAS_PRIMARY_OBJECT = OntologyRelation(
    name="hasPrimaryObject",
    name_zh="具有主目标",
    domain="SpatialRelationEvent",
    range="SpaceObject",
    description="空间关系事件中交会对象对的主要目标，用于显式表示目标角色。",
)

REL_HAS_SECONDARY_OBJECT = OntologyRelation(
    name="hasSecondaryObject",
    name_zh="具有次目标",
    domain="SpatialRelationEvent",
    range="SpaceObject",
    description="空间关系事件中交会对象对的次要目标，用于显式表示目标角色。",
)

REL_OCCURS_IN_ORBIT = OntologyRelation(
    name="occursInOrbit",
    name_zh="发生于轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件发生于某轨道。",
)

REL_AFFECTS_OBJECT = OntologyRelation(
    name="affectsObject",
    name_zh="影响目标",
    domain="SpaceEvent",
    range="SpaceObject",
    description="空间事件影响空间目标。",
)

REL_AFFECTS_ORBIT = OntologyRelation(
    name="affectsOrbit",
    name_zh="影响轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件影响轨道。",
)

REL_CHANGES_ORBIT = OntologyRelation(
    name="changesOrbit",
    name_zh="改变轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件改变轨道。",
)

REL_PRECEDES_EVENT = OntologyRelation(
    name="precedesEvent",
    name_zh="先于事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件在时间上先于另一事件。",
    transitive=True,
)

REL_FOLLOWS_EVENT = OntologyRelation(
    name="followsEvent",
    name_zh="后于事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件在时间上后于另一事件。",
    inverse_of="precedesEvent",
    transitive=True,
)

REL_OVERLAPS_WITH_EVENT = OntologyRelation(
    name="overlapsWithEvent",
    name_zh="与事件时间重叠",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="两个事件在时间上重叠。",
    symmetric=True,
)

REL_OCCURS_DURING_EVENT = OntologyRelation(
    name="occursDuringEvent",
    name_zh="发生于另一事件期间",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件发生于另一事件期间。",
)

REL_CONTAINS_EVENT = OntologyRelation(
    name="containsEvent",
    name_zh="包含事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件包含另一事件。",
    inverse_of="occursDuringEvent",
)

REL_MEETS_EVENT = OntologyRelation(
    name="meetsEvent",
    name_zh="邻接事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="一个事件结束时间等于另一个事件开始时间。",
)

SPACE_EVENT_RELATIONS: tuple[OntologyRelation, ...] = (REL_INVOLVES_OBJECT, REL_IS_INVOLVED_IN_EVENT, REL_HAS_PRIMARY_OBJECT, REL_HAS_SECONDARY_OBJECT, REL_OCCURS_IN_ORBIT, REL_AFFECTS_OBJECT, REL_AFFECTS_ORBIT, REL_CHANGES_ORBIT, REL_PRECEDES_EVENT, REL_FOLLOWS_EVENT, REL_OVERLAPS_WITH_EVENT, REL_OCCURS_DURING_EVENT, REL_CONTAINS_EVENT, REL_MEETS_EVENT)


# ============================================================
# Aggregations
# ============================================================

SPACE_EVENT_CLASSES: tuple[OntologyClass, ...] = (CLS_SPACE_EVENT, CLS_ORBITAL_EVENT, CLS_FRAGMENTATION_EVENT, CLS_ORBIT_MANEUVER_EVENT, CLS_OBJECT_BEHAVIOR_EVENT, CLS_OBSERVATION_EVENT, CLS_DETECTION_EVENT, CLS_TRACKING_EVENT, CLS_SPATIAL_RELATION_EVENT, CLS_APPROACH_EVENT, CLS_RISK_EVENT, CLS_COLLISION_RISK_EVENT, CLS_DEBRIS_RISK_EVENT)

SPACE_EVENT_PROPERTIES_LIST: tuple[OntologyProperty, ...] = (PROP_HAS_EVENT_ID, PROP_HAS_ENCOUNTER_ID, PROP_HAS_EVENT_TYPE, PROP_HAS_EVENT_LEVEL, PROP_HAS_EVENT_DESCRIPTION, PROP_HAS_DURATION, PROP_HAS_OCCURRENCE_TIME, PROP_HAS_START_TIME, PROP_HAS_END_TIME, PROP_HAS_EVENT_CONFIDENCE, PROP_HAS_RELATIVE_DISTANCE, PROP_HAS_COLLISION_PROBABILITY, PROP_HAS_PREDICTED_MISS_DISTANCE, PROP_HAS_RISK_VALUE)
