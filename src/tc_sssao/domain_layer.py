"""TC-SSSAO -- 基于时序因果联合建模的太空安全态势感知本体

Top-level branches: SpaceObject, Orbit, GeometricConstruct, SpaceEnvironment,
                   ObservationSystem, SSAActivity, SSAData, SpaceEvent,
                   SecurityThreat, SecurityRisk, SituationState, StateTransition,
                   CausalAssertion, ResponseMeasure, SpaceOrganization,
                   TemporalEntity
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction

# ============================================================
# Data Properties
# ============================================================
PROP_HASARGUMENTOFPERIGEE = OntologyProperty(
    name="hasArgumentOfPerigee", datatype="float",
    name_zh="近地点幅角",
    description="轨道近地点幅角。",
    domain="Orbit",
)

PROP_HASCAUSALCONFIDENCE = OntologyProperty(
    name="hasCausalConfidence", datatype="float",
    name_zh="因果置信度",
    description="因果断言的可选置信度元数据。当数据来源、专家评估或外部模型提供定量置信信息时记录该值；来源未给出定量置信度时不强制赋值（M3 第一阶段起由 exactly 1 放宽为 max 1）。",
    domain="CausalAssertion",
)

PROP_HASCAUSALMECHANISM = OntologyProperty(
    name="hasCausalMechanism", datatype="string",
    name_zh="因果机制",
    description="因果断言背后的物理或逻辑机制描述。",
    domain="CausalAssertion",
)

PROP_HASCOLLISIONPROBABILITY = OntologyProperty(
    name="hasCollisionProbability", datatype="float",
    name_zh="碰撞概率",
    description="碰撞风险概率。",
    domain="CollisionRiskEvent",
)

PROP_HASCOMBINEDHARDBODYRADIUS = OntologyProperty(
    name="hasCombinedHardBodyRadius", datatype="float",
    name_zh="组合硬体半径",
    description="当前交会风险评估中两个目标的组合硬体半径（combined hard-body radius），即两目标外接球半径之和；由外部交会评估给出，随评估事件变化，不作为全局部署常数。",
    domain="CollisionRiskEvent",
)

PROP_HASDATACONFIDENCE = OntologyProperty(
    name="hasDataConfidence", datatype="float",
    name_zh="数据置信度",
    description="数据可信程度。",
    domain="SSAData",
)

PROP_HASDATAID = OntologyProperty(
    name="hasDataID", datatype="string",
    name_zh="数据编号",
    description="SSA 数据唯一标识。",
    domain="SSAData",
)

PROP_HASDATASOURCE = OntologyProperty(
    name="hasDataSource", datatype="string",
    name_zh="数据来源",
    description="数据来源说明。",
    domain="SSAData",
)

PROP_HASDATATYPE = OntologyProperty(
    name="hasDataType", datatype="string",
    name_zh="数据类型",
    description="数据类型说明。",
    domain="SSAData",
)

PROP_HASDURATION = OntologyProperty(
    name="hasDuration", datatype="duration",
    name_zh="持续时间",
    description="事件持续时间（ISO 8601 时长字符串,如 PT1H30M）。",
    domain="SpaceEvent",
)

PROP_HASENCOUNTERID = OntologyProperty(
    name="hasEncounterID", datatype="string",
    name_zh="交会编号",
    description="交会事件编号，标识同一物理交会事件的所有风险评估快照。ESA数据中对应event_id字段，同一物理交会的所有CDM共享同一event_id。B3规则使用此属性实现跨交会隔离。",
    domain="SpaceEvent",
)

PROP_HASENDTIME = OntologyProperty(
    name="hasEndTime", datatype="dateTime",
    name_zh="结束时间",
    description="事件结束时间。",
    domain="SpaceEvent",
)

PROP_HASERRORVALUE = OntologyProperty(
    name="hasErrorValue", datatype="float",
    name_zh="误差值",
    description="观测或计算误差。",
    domain="SSAData",
)

PROP_HASEVENTCONFIDENCE = OntologyProperty(
    name="hasEventConfidence", datatype="float",
    name_zh="事件置信度",
    description="事件判断可信程度。",
    domain="SpaceEvent",
)

PROP_HASEVENTDESCRIPTION = OntologyProperty(
    name="hasEventDescription", datatype="string",
    name_zh="事件描述",
    description="事件文字说明。",
    domain="SpaceEvent",
)

PROP_HASEVENTID = OntologyProperty(
    name="hasEventID", datatype="string",
    name_zh="事件编号",
    description="事件唯一标识。",
    domain="SpaceEvent",
)

PROP_HASEVENTLEVEL = OntologyProperty(
    name="hasEventLevel", datatype="string",
    name_zh="事件等级",
    description="一般、重要、严重等。",
    domain="SpaceEvent",
)

PROP_HASEVENTTYPE = OntologyProperty(
    name="hasEventType", datatype="string",
    name_zh="事件类型",
    description="轨道机动、接近、碰撞风险等。",
    domain="SpaceEvent",
)

PROP_HASGEOMETRICERRORVALUE = OntologyProperty(
    name="hasGeometricErrorValue", datatype="float",
    name_zh="几何误差值",
    description="几何构造的误差值。",
    domain="GeometricConstruct",
)

PROP_HASIMPACTSCOPE = OntologyProperty(
    name="hasImpactScope", datatype="string",
    name_zh="影响范围",
    description="威胁影响范围，如目标、轨道区域、任务系统等。",
    domain="SecurityThreat",
)

PROP_HASLAUNCHCOUNTRY = OntologyProperty(
    name="hasLaunchCountry", datatype="xsd:string",
    name_zh="发射国家",
    description="空间目标的发射国家或责任机构。",
    domain="SpaceObject",
)

PROP_HASLAUNCHDATE = OntologyProperty(
    name="hasLaunchDate", datatype="xsd:dateTime",
    name_zh="发射日期",
    description="空间目标的发射日期与时间。",
    domain="SpaceObject",
)

PROP_HASLOCATION = OntologyProperty(
    name="hasLocation", datatype="string",
    name_zh="部署位置",
    description="观测系统或传感器的部署位置。",
    domain="ObservationSystem",
)

PROP_HASMASS = OntologyProperty(
    name="hasMass", datatype="xsd:float",
    name_zh="质量",
    description="空间目标的质量，通常以千克为单位。",
    domain="SpaceObject",
)

PROP_HASMEANANOMALY = OntologyProperty(
    name="hasMeanAnomaly", datatype="float",
    name_zh="平近点角",
    description="轨道平近点角。",
    domain="Orbit",
)

PROP_HASMEASUREDESCRIPTION = OntologyProperty(
    name="hasMeasureDescription", datatype="string",
    name_zh="措施描述",
    description="响应措施描述。",
    domain="ResponseMeasure",
)

PROP_HASMEASUREID = OntologyProperty(
    name="hasMeasureID", datatype="string",
    name_zh="措施编号",
    description="响应措施唯一标识。",
    domain="ResponseMeasure",
)

PROP_HASMEASURELEVEL = OntologyProperty(
    name="hasMeasureLevel", datatype="string",
    name_zh="措施等级",
    description="措施等级，如一般、重要、紧急。",
    domain="ResponseMeasure",
)

PROP_HASMEASURETYPE = OntologyProperty(
    name="hasMeasureType", datatype="string",
    name_zh="措施类型",
    description="措施类型，如规避、应急、缓解、预警等。",
    domain="ResponseMeasure",
)

PROP_HASMISSIONTYPE = OntologyProperty(
    name="hasMissionType", datatype="xsd:string",
    name_zh="任务类型",
    description="航天器承担的任务类型。",
    domain="Spacecraft",
)

PROP_HASOBJECTID = OntologyProperty(
    name="hasObjectID", datatype="xsd:string",
    name_zh="目标编号",
    description="空间目标的唯一标识编号。",
    domain="SpaceObject",
)

PROP_HASOBJECTNAME = OntologyProperty(
    name="hasObjectName", datatype="xsd:string",
    name_zh="目标名称",
    description="空间目标的名称。",
    domain="SpaceObject",
)

PROP_HASOCCURRENCETIME = OntologyProperty(
    name="hasOccurrenceTime", datatype="dateTime",
    name_zh="发生时间",
    description="事件发生时间。",
    domain="SpaceEvent",
)

PROP_HASOPERATORNAME = OntologyProperty(
    name="hasOperatorName", datatype="xsd:string",
    name_zh="运营方名称",
    description="空间目标当前运营方的名称。",
    domain="SpaceObject",
)

PROP_HASORBITTYPE = OntologyProperty(
    name="hasOrbitType", datatype="string",
    name_zh="轨道类型",
    description="轨道类型，如 LEO、MEO、GEO、HEO 等。",
    domain="Orbit",
)

PROP_HASORBITALPERIOD = OntologyProperty(
    name="hasOrbitalPeriod", datatype="float",
    name_zh="轨道周期",
    description="轨道运行周期。",
    domain="Orbit",
)

PROP_HASPREDICTEDMISSDISTANCE = OntologyProperty(
    name="hasPredictedMissDistance", datatype="float",
    name_zh="预测最近交会距离",
    description="碰撞风险事件预测最近交会距离。",
    domain="CollisionRiskEvent",
)

PROP_HASRAAN = OntologyProperty(
    name="hasRAAN", datatype="float",
    name_zh="升交点赤经",
    description="升交点赤经（Right Ascension of Ascending Node）。",
    domain="Orbit",
)

PROP_HASRELATIVEDISTANCE = OntologyProperty(
    name="hasRelativeDistance", datatype="float",
    name_zh="相对距离",
    description="两目标之间距离。",
    domain="SpatialRelationEvent",
)

PROP_HASRESOLUTION = OntologyProperty(
    name="hasResolution", datatype="float",
    name_zh="分辨率",
    description="传感器探测分辨率。",
    domain="Sensor",
)

PROP_HASRISKLEVEL = OntologyProperty(
    name="hasRiskLevel", datatype="string",
    name_zh="风险等级",
    description="低、中、高、极高。",
    domain="SituationState",
)

PROP_HASRISKVALUE = OntologyProperty(
    name="hasRiskValue", datatype="float",
    name_zh="风险值",
    description="由外部风险评估模型、任务系统或应用层给出的可选综合风险评分，其计算方法与取值尺度由外部系统规定，不由本体规定；承载外部评估结果，不等同于碰撞概率 hasCollisionProbability；碰撞风险态势规则（R5—R8）不再以该属性为判定条件。",
    domain="RiskEvent",
)

PROP_HASSEMIMAJORAXIS = OntologyProperty(
    name="hasSemiMajorAxis", datatype="float",
    name_zh="半长轴",
    description="轨道半长轴。",
    domain="Orbit",
)

PROP_HASSENSORID = OntologyProperty(
    name="hasSensorID", datatype="string",
    name_zh="传感器编号",
    description="传感器唯一标识。",
    domain="Sensor",
)

PROP_HASSEVERITYRANK = OntologyProperty(
    name="hasSeverityRank", datatype="integer",
    name_zh="严重度级别",
    description="分级风险态势的严重度排序值：正常=0、关注=1、预警=2、危险=3；仅用于支持分级态势之间的排序及跨时间演化规则。",
    domain="SituationState",
)

PROP_HASSIZE = OntologyProperty(
    name="hasSize", datatype="xsd:float",
    name_zh="尺寸",
    description="空间目标的特征尺寸。",
    domain="SpaceObject",
)

PROP_HASSTARTTIME = OntologyProperty(
    name="hasStartTime", datatype="dateTime",
    name_zh="开始时间",
    description="事件开始时间。",
    domain="SpaceEvent",
)

PROP_HASSTATECONFIDENCE = OntologyProperty(
    name="hasStateConfidence", datatype="float",
    name_zh="状态置信度",
    description="状态判断的可信程度。",
    domain="SituationState",
)

PROP_HASSTATEDESCRIPTION = OntologyProperty(
    name="hasStateDescription", datatype="string",
    name_zh="状态描述",
    description="态势状态的文字说明。",
    domain="SituationState",
)

PROP_HASSTATEDURATION = OntologyProperty(
    name="hasStateDuration", datatype="duration",
    name_zh="状态持续时间",
    description="状态持续时间（ISO 8601 时长字符串，如 PT1H30M）。",
    domain="SituationState",
)

PROP_HASSTATEENDTIME = OntologyProperty(
    name="hasStateEndTime", datatype="dateTime",
    name_zh="状态结束时间",
    description="状态结束时间。",
    domain="SituationState",
)

PROP_HASSTATEID = OntologyProperty(
    name="hasStateID", datatype="string",
    name_zh="状态编号",
    description="态势状态唯一标识。",
    domain="SituationState",
)

PROP_HASSTATELEVEL = OntologyProperty(
    name="hasStateLevel", datatype="string",
    name_zh="状态等级",
    description="正常、关注、异常、预警、危险、恢复等。",
    domain="SituationState",
)

PROP_HASSTATESTARTTIME = OntologyProperty(
    name="hasStateStartTime", datatype="dateTime",
    name_zh="状态开始时间",
    description="状态开始时间。",
    domain="SituationState",
)

PROP_HASSTATETYPE = OntologyProperty(
    name="hasStateType", datatype="string",
    name_zh="状态类型",
    description="运行状态、空间安全状态、威胁状态、综合态势状态等。",
    domain="SituationState",
)

PROP_HASSTATEUPDATETIME = OntologyProperty(
    name="hasStateUpdateTime", datatype="dateTime",
    name_zh="态势状态更新时间",
    description="态势状态最近一次更新时间。",
    domain="SituationState",
)

PROP_HASTHREATID = OntologyProperty(
    name="hasThreatID", datatype="string",
    name_zh="威胁编号",
    description="安全威胁唯一标识。",
    domain="SecurityThreat",
)

PROP_HASTHREATSOURCE = OntologyProperty(
    name="hasThreatSource", datatype="string",
    name_zh="威胁来源",
    description="威胁来源，如碎片、目标、环境、网络等。",
    domain="SecurityThreat",
)

PROP_HASTHREATTYPE = OntologyProperty(
    name="hasThreatType", datatype="string",
    name_zh="威胁类型",
    description="威胁类型，如物理、网络、电磁、环境、运行等。",
    domain="SecurityThreat",
)

# ============================================================
# Object Properties / Relations
# ============================================================
REL_001_AFFECTSOBJECT = OntologyRelation(
    name="affectsObject",
    name_zh="影响目标",
    domain="SpaceEvent",
    range="SpaceObject",
    description="空间事件影响空间目标。",
)

REL_002_AFFECTSORBIT = OntologyRelation(
    name="affectsOrbit",
    name_zh="影响轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件影响轨道。",
)

REL_003_AFFECTSSTATE = OntologyRelation(
    name="affectsState",
    name_zh="影响状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件影响态势状态。",
)

REL_004_CAUSEDBYEVENT = OntologyRelation(
    name="causedByEvent",
    name_zh="由事件导致",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件由另一事件导致。",
    inverse_of="causesEvent",
)

REL_005_CAUSESEVENT = OntologyRelation(
    name="causesEvent",
    name_zh="导致事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件导致另一事件发生。",
)

REL_006_CHANGESORBIT = OntologyRelation(
    name="changesOrbit",
    name_zh="改变轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件改变轨道。",
)

REL_007_CONTAINSEVENT = OntologyRelation(
    name="containsEvent",
    name_zh="包含事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件包含另一事件。",
    inverse_of="occursDuringEvent",
)

REL_008_DEGRADESTO = OntologyRelation(
    name="degradesTo",
    name_zh="恶化为",
    domain="SituationState",
    range="SituationState",
    description="态势状态恶化为另一状态。",
)

REL_009_DESCRIBESOBJECT = OntologyRelation(
    name="describesObject",
    name_zh="描述目标",
    domain="SSAData",
    range="SpaceObject",
    description="SSA 数据描述空间目标。",
)

REL_010_DETECTEDFROMDATA = OntologyRelation(
    name="detectedFromData",
    name_zh="由数据发现",
    domain="SpaceEvent",
    range="SSAData",
    description="空间事件由 SSA 数据发现。",
)

REL_011_EVOLVESTO = OntologyRelation(
    name="evolvesTo",
    name_zh="演化为",
    domain="SituationState",
    range="SituationState",
    description="态势状态演化为另一状态。",
)

REL_012_FOLLOWSEVENT = OntologyRelation(
    name="followsEvent",
    name_zh="后于事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件在时间上后于另一事件。",
    inverse_of="precedesEvent",
    transitive=True,
)

REL_013_GENERATEDBY = OntologyRelation(
    name="generatedBy",
    name_zh="由……生成",
    domain="ObservationData",
    range="ObservationSystem",
    description="观测数据由观测系统生成。",
    inverse_of="generatesData",
)

REL_014_GENERATEDBYACTIVITY = OntologyRelation(
    name="generatedByActivity",
    name_zh="由活动生成",
    domain="SSAData",
    range="SSAActivity",
    description="SSA 数据由 SSA 活动生成。",
    inverse_of="producesData",
)

REL_015_GENERATESDATA = OntologyRelation(
    name="generatesData",
    name_zh="生成数据",
    domain="ObservationSystem",
    range="ObservationData",
    description="观测系统生成观测数据。",
    inverse_of="generatedBy",
)

REL_016_HASBEGINNING = OntologyRelation(
    name="hasBeginning",
    name_zh="具有开始",
    domain="TimeInterval",
    range="TimeInstant",
    description="时间区间的开始时间点。",
)

REL_017_HASCAUSALEVIDENCE = OntologyRelation(
    name="hasCausalEvidence",
    name_zh="具有因果证据",
    domain="CausalAssertion",
    range="SSAData",
    description="支撑因果断言的 SSA 数据。",
)

REL_018_HASCAUSE = OntologyRelation(
    name="hasCause",
    name_zh="具有原因",
    domain="CausalAssertion",
    range="SpaceEvent",
    description="因果断言中的原因事件。",
)

REL_019_HASEFFECT = OntologyRelation(
    name="hasEffect",
    name_zh="具有结果",
    domain="CausalAssertion",
    range="SpaceEvent",
    description="因果断言中的结果事件。",
)

REL_020_HASEND = OntologyRelation(
    name="hasEnd",
    name_zh="具有结束",
    domain="TimeInterval",
    range="TimeInstant",
    description="时间区间的结束时间点。",
)

REL_021_HASFEATUREOFINTEREST = OntologyRelation(
    name="hasFeatureOfInterest",
    name_zh="具有关注目标",
    domain="SSAData",
    range="SpaceObject",
    description="SSA 数据所关注的空间目标。",
)

REL_022_HASOBSERVATIONRESULT = OntologyRelation(
    name="hasObservationResult",
    name_zh="具有观测结果",
    domain="ObservationData",
    range="SpaceObject",
    description="观测数据具有观测结果目标。",
)

REL_023_HASORBIT = OntologyRelation(
    name="hasOrbit",
    name_zh="具有轨道",
    domain="SpaceObject",
    range="Orbit",
    description="空间目标具有轨道。",
)

REL_024_HASPRIMARYOBJECT = OntologyRelation(
    name="hasPrimaryObject",
    name_zh="具有主目标",
    domain="SpatialRelationEvent",
    range="SpaceObject",
    description="空间关系事件中交会对象对的主要目标，用于显式表示目标角色。",
)

REL_025_HASSECONDARYOBJECT = OntologyRelation(
    name="hasSecondaryObject",
    name_zh="具有次目标",
    domain="SpatialRelationEvent",
    range="SpaceObject",
    description="空间关系事件中交会对象对的次要目标，用于显式表示目标角色。",
)

REL_026_HASSOURCESTATE = OntologyRelation(
    name="hasSourceState",
    name_zh="具有源状态",
    domain="StateTransition",
    range="SituationState",
    description="状态转移的源状态。",
)

REL_027_HASTARGETSTATE = OntologyRelation(
    name="hasTargetState",
    name_zh="具有目标状态",
    domain="StateTransition",
    range="SituationState",
    description="状态转移的目标状态。",
)

REL_028_IMPLEMENTSMEASURE = OntologyRelation(
    name="implementsMeasure",
    name_zh="实施措施",
    domain="SpaceEvent",
    range="ResponseMeasure",
    description="空间事件实施响应措施。",
)

REL_029_INVOLVESOBJECT = OntologyRelation(
    name="involvesObject",
    name_zh="涉及目标",
    domain="SpaceEvent",
    range="SpaceObject",
    description="空间事件涉及空间目标。",
)

REL_030_ISIMPLEMENTEDBYEVENT = OntologyRelation(
    name="isImplementedByEvent",
    name_zh="由事件实施",
    domain="ResponseMeasure",
    range="SpaceEvent",
    description="响应措施由空间事件实施。",
    inverse_of="implementsMeasure",
)

REL_031_ISINVOLVEDINEVENT = OntologyRelation(
    name="isInvolvedInEvent",
    name_zh="参与事件",
    domain="SpaceObject",
    range="SpaceEvent",
    description="空间目标参与空间事件。",
    inverse_of="involvesObject",
)

REL_032_ISORBITOF = OntologyRelation(
    name="isOrbitOf",
    name_zh="是某目标的轨道",
    domain="Orbit",
    range="SpaceObject",
    description="轨道属于空间目标。",
    inverse_of="hasOrbit",
)

REL_033_LEADSTOSTATE = OntologyRelation(
    name="leadsToState",
    name_zh="导致状态",
    domain="SpaceEvent",
    range="SituationState",
    description="事件导致态势状态。",
)

REL_034_MADEBYSENSOR = OntologyRelation(
    name="madeBySensor",
    name_zh="由传感器执行",
    domain="ObservationActivity",
    range="Sensor",
    description="观测活动由传感器执行。",
)

REL_035_MAYMANIFESTASEVENT = OntologyRelation(
    name="mayManifestAsEvent",
    name_zh="可能表现为事件",
    domain="SecurityThreat",
    range="SpaceEvent",
    description="安全威胁可能表现为空间事件。",
)

REL_036_MEETSEVENT = OntologyRelation(
    name="meetsEvent",
    name_zh="邻接事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="一个事件结束时间等于另一个事件开始时间。",
)

REL_037_MITIGATEDBY = OntologyRelation(
    name="mitigatedBy",
    name_zh="被缓解",
    domain="SecurityRisk",
    range="ResponseMeasure",
    description="安全风险被响应措施缓解。",
    inverse_of="mitigatesRisk",
)

REL_038_MITIGATESRISK = OntologyRelation(
    name="mitigatesRisk",
    name_zh="缓解风险",
    domain="ResponseMeasure",
    range="SecurityRisk",
    description="响应措施缓解安全风险。",
)

REL_039_OBSERVEDBYSENSOR = OntologyRelation(
    name="observedBySensor",
    name_zh="由传感器观测",
    domain="ObservationEvent",
    range="Sensor",
    description="观测事件由传感器观测。",
)

REL_040_OCCURSATTIME = OntologyRelation(
    name="occursAtTime",
    name_zh="发生于时间点",
    domain="SpaceEvent",
    range="TimeInstant",
    description="事件发生在某一时间点。",
)

REL_041_OCCURSDURINGEVENT = OntologyRelation(
    name="occursDuringEvent",
    name_zh="发生于另一事件期间",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件发生于另一事件期间。",
)

REL_042_OCCURSINORBIT = OntologyRelation(
    name="occursInOrbit",
    name_zh="发生于轨道",
    domain="SpaceEvent",
    range="Orbit",
    description="空间事件发生于某轨道。",
)

REL_043_OCCURSINTIMEINTERVAL = OntologyRelation(
    name="occursInTimeInterval",
    name_zh="发生于时间区间",
    domain="SpaceEvent",
    range="TimeInterval",
    description="事件发生在某一时间区间内。",
)

REL_044_OVERLAPSWITHEVENT = OntologyRelation(
    name="overlapsWithEvent",
    name_zh="与事件时间重叠",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="两个事件在时间上重叠。",
    symmetric=True,
)

REL_045_PRECEDESEVENT = OntologyRelation(
    name="precedesEvent",
    name_zh="先于事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件在时间上先于另一事件。",
    transitive=True,
)

REL_046_PRODUCESDATA = OntologyRelation(
    name="producesData",
    name_zh="产生活动数据",
    domain="SSAActivity",
    range="SSAData",
    description="SSA 活动产生 SSA 数据。",
    inverse_of="generatedByActivity",
)

REL_047_PRODUCESRISK = OntologyRelation(
    name="producesRisk",
    name_zh="产生风险",
    domain="SecurityThreat",
    range="SecurityRisk",
    description="安全威胁产生安全风险。",
)

REL_048_RECOVERSTO = OntologyRelation(
    name="recoversTo",
    name_zh="恢复为",
    domain="SituationState",
    range="SituationState",
    description="态势状态恢复为另一状态。",
)

REL_049_REQUIRESRESPONSEMEASURE = OntologyRelation(
    name="requiresResponseMeasure",
    name_zh="需要响应措施",
    domain="SecurityThreat",
    range="ResponseMeasure",
    description="安全威胁需要响应措施。",
    inverse_of="respondsToThreat",
)

REL_050_RESPONDSTOEVENT = OntologyRelation(
    name="respondsToEvent",
    name_zh="响应事件",
    domain="ResponseMeasure",
    range="SpaceEvent",
    description="响应措施响应空间事件。",
)

REL_051_RESPONDSTOTHREAT = OntologyRelation(
    name="respondsToThreat",
    name_zh="响应威胁",
    domain="ResponseMeasure",
    range="SecurityThreat",
    description="响应措施响应安全威胁。",
    inverse_of="requiresResponseMeasure",
)

REL_052_RESULTEDFROMEVENT = OntologyRelation(
    name="resultedFromEvent",
    name_zh="由事件产生",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件由另一事件产生。",
    inverse_of="resultsInEvent",
)

REL_053_RESULTSINEVENT = OntologyRelation(
    name="resultsInEvent",
    name_zh="产生事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件产生另一事件。",
)

REL_054_RISKLEADSTOSTATE = OntologyRelation(
    name="riskLeadsToState",
    name_zh="风险导致状态",
    domain="SecurityRisk",
    range="SituationState",
    description="安全风险导致态势状态。",
)

REL_055_STATECAUSEDBYEVENT = OntologyRelation(
    name="stateCausedByEvent",
    name_zh="状态由事件导致",
    domain="SituationState",
    range="SpaceEvent",
    description="态势状态由事件导致。",
    inverse_of="leadsToState",
)

REL_056_SUPPORTEDBYDATA = OntologyRelation(
    name="supportedByData",
    name_zh="由数据支撑",
    domain="SpaceEvent",
    range="SSAData",
    description="空间事件由 SSA 数据支撑。",
)

REL_057_THREATMITIGATEDBY = OntologyRelation(
    name="threatMitigatedBy",
    name_zh="威胁被缓解",
    domain="SecurityThreat",
    range="ResponseMeasure",
    description="安全威胁被响应措施缓解。",
)

REL_058_TRANSITSFROM = OntologyRelation(
    name="transitsFrom",
    name_zh="转移自",
    domain="SituationState",
    range="SituationState",
    description="态势状态转移自另一状态。",
    inverse_of="transitsTo",
)

REL_059_TRANSITSTO = OntologyRelation(
    name="transitsTo",
    name_zh="转移到",
    domain="SituationState",
    range="SituationState",
    description="态势状态转移到另一状态。",
)

REL_060_TRIGGEREDBYEVENT = OntologyRelation(
    name="triggeredByEvent",
    name_zh="由事件触发",
    domain="StateTransition",
    range="SpaceEvent",
    description="触发状态转移的空间事件。",
)

REL_061_TRIGGERSEVENT = OntologyRelation(
    name="triggersEvent",
    name_zh="触发事件",
    domain="SpaceEvent",
    range="SpaceEvent",
    description="某事件触发另一事件发生。",
)

REL_062_TRIGGERSSTATE = OntologyRelation(
    name="triggersState",
    name_zh="触发状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件触发态势状态。",
)

REL_063_UPDATESSTATE = OntologyRelation(
    name="updatesState",
    name_zh="更新状态",
    domain="SpaceEvent",
    range="SituationState",
    description="空间事件更新态势状态。",
)

# ============================================================
# Classes
# ============================================================
CLS_001_SPACEEVENT = OntologyClass(
    name_en="SpaceEvent",
    name_zh="空间事件",
    description="描述引起态势变化的空间事件。",
    namespace="domain",
    properties=[PROP_HASEVENTID, PROP_HASENCOUNTERID, PROP_HASEVENTTYPE, PROP_HASEVENTLEVEL, PROP_HASEVENTDESCRIPTION, PROP_HASDURATION, PROP_HASOCCURRENCETIME, PROP_HASSTARTTIME, PROP_HASENDTIME, PROP_HASEVENTCONFIDENCE],
    restrictions=[OntologyRestriction("hasEventID", "string", "someValuesFrom"), OntologyRestriction("hasEventType", "string", "someValuesFrom"), OntologyRestriction("hasEventLevel", "string", "someValuesFrom"), OntologyRestriction("hasOccurrenceTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasStartTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasEndTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasEventConfidence", "float", "someValuesFrom"), OntologyRestriction("involvesObject", "SpaceObject", "someValuesFrom"), OntologyRestriction("occursInOrbit", "Orbit", "someValuesFrom")],
)

CLS_002_SPATIALRELATIONEVENT = OntologyClass(
    name_en="SpatialRelationEvent",
    name_zh="空间关系事件",
    description="描述多个空间目标之间空间关系的事件。",
    namespace="domain",
    parents=['SpaceEvent'],
    properties=[PROP_HASRELATIVEDISTANCE],
    restrictions=[OntologyRestriction("hasPrimaryObject", "SpaceObject", "someValuesFrom"), OntologyRestriction("hasSecondaryObject", "SpaceObject", "someValuesFrom")],
)

CLS_003_APPROACHEVENT = OntologyClass(
    name_en="ApproachEvent",
    name_zh="接近事件",
    description="两个空间目标相互接近的事件。",
    namespace="domain",
    parents=['SpatialRelationEvent'],
)

CLS_004_SPACEOBJECT = OntologyClass(
    name_en="SpaceObject",
    name_zh="空间目标",
    description="太空安全态势感知中的顶层空间目标概念，涵盖自然空间目标与人造空间目标。",
    namespace="domain",
    properties=[PROP_HASOBJECTID, PROP_HASOBJECTNAME, PROP_HASMASS, PROP_HASSIZE, PROP_HASLAUNCHDATE, PROP_HASLAUNCHCOUNTRY, PROP_HASOPERATORNAME],
    restrictions=[OntologyRestriction("hasOrbit", "Orbit", "someValuesFrom")],
)

CLS_005_ARTIFICIALSPACEOBJECT = OntologyClass(
    name_en="ArtificialSpaceObject",
    name_zh="人造空间目标",
    description="由人类制造并发射至外层空间的目标。",
    namespace="domain",
    parents=['SpaceObject'],
)

CLS_006_SSADATA = OntologyClass(
    name_en="SSAData",
    name_zh="太空态势感知数据",
    description="支撑因果断言与事件判断的太空态势感知数据。",
    namespace="domain",
    properties=[PROP_HASDATAID, PROP_HASDATATYPE, PROP_HASDATASOURCE, PROP_HASERRORVALUE, PROP_HASDATACONFIDENCE],
)

CLS_007_ASSESSMENTDATA = OntologyClass(
    name_en="AssessmentData",
    name_zh="评估数据",
    description="评估数据。",
    namespace="domain",
    parents=['SSAData'],
)

CLS_008_SITUATIONSTATE = OntologyClass(
    name_en="SituationState",
    name_zh="态势状态",
    description="描述某一阶段的安全态势。",
    namespace="domain",
    properties=[PROP_HASSTATEID, PROP_HASSTATETYPE, PROP_HASSTATELEVEL, PROP_HASRISKLEVEL, PROP_HASSTATECONFIDENCE, PROP_HASSTATEDESCRIPTION, PROP_HASSTATESTARTTIME, PROP_HASSTATEENDTIME, PROP_HASSTATEDURATION, PROP_HASSTATEUPDATETIME, PROP_HASSEVERITYRANK],
    restrictions=[OntologyRestriction("stateCausedByEvent", "SpaceEvent", "someValuesFrom"), OntologyRestriction("hasStateLevel", "string", "someValuesFrom"), OntologyRestriction("hasStateConfidence", "float", "someValuesFrom"), OntologyRestriction("hasStateStartTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasStateEndTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasStateUpdateTime", "dateTime", "someValuesFrom"), OntologyRestriction("hasSeverityRank", "integer", "maxCardinality", max_cardinality=1)],
)

CLS_009_ATTENTIONSITUATIONSTATE = OntologyClass(
    name_en="AttentionSituationState",
    name_zh="关注态势状态",
    description="整体态势需要关注。",
    namespace="domain",
    parents=['SituationState'],
    restrictions=[OntologyRestriction("hasSeverityRank", "integer", "hasValue", has_value='1')],
)

CLS_010_RESPONSEMEASURE = OntologyClass(
    name_en="ResponseMeasure",
    name_zh="响应措施",
    description="为应对安全威胁或安全风险采取的措施。",
    namespace="domain",
    properties=[PROP_HASMEASUREID, PROP_HASMEASURETYPE, PROP_HASMEASURELEVEL, PROP_HASMEASUREDESCRIPTION],
    restrictions=[OntologyRestriction("respondsToThreat", "SecurityThreat", "someValuesFrom"), OntologyRestriction("respondsToEvent", "SpaceEvent", "someValuesFrom"), OntologyRestriction("mitigatesRisk", "SecurityRisk", "someValuesFrom"), OntologyRestriction("isImplementedByEvent", "SpaceEvent", "someValuesFrom")],
)

CLS_011_AVOIDANCEMEASURE = OntologyClass(
    name_en="AvoidanceMeasure",
    name_zh="规避措施",
    description="通过规避动作降低威胁或风险的措施。",
    namespace="domain",
    parents=['ResponseMeasure'],
)

CLS_012_CAUSALASSERTION = OntologyClass(
    name_en="CausalAssertion",
    name_zh="因果断言",
    description="描述事件之间因果关系的断言。",
    namespace="causal",
    properties=[PROP_HASCAUSALCONFIDENCE, PROP_HASCAUSALMECHANISM],
    restrictions=[OntologyRestriction("hasCause", "SpaceEvent", "minCardinality", min_cardinality=1), OntologyRestriction("hasEffect", "SpaceEvent", "cardinality", cardinality=1), OntologyRestriction("hasCausalEvidence", "SSAData", "minCardinality", min_cardinality=1), OntologyRestriction("hasCausalConfidence", "float", "maxCardinality", max_cardinality=1)],
)

CLS_013_SECURITYRISK = OntologyClass(
    name_en="SecurityRisk",
    name_zh="安全风险",
    description="空间系统或任务面临损失的潜在可能性。",
    namespace="domain",
    properties=[PROP_HASRISKVALUE],
    restrictions=[OntologyRestriction("mitigatedBy", "ResponseMeasure", "someValuesFrom"), OntologyRestriction("riskLeadsToState", "SituationState", "someValuesFrom")],
)

CLS_014_COLLISIONRISK = OntologyClass(
    name_en="CollisionRisk",
    name_zh="碰撞风险",
    description="空间目标碰撞导致的风险。",
    namespace="domain",
    parents=['SecurityRisk'],
)

CLS_015_RISKEVENT = OntologyClass(
    name_en="RiskEvent",
    name_zh="风险事件",
    description="描述空间安全风险的事件。",
    namespace="domain",
    parents=['SpaceEvent'],
    properties=[PROP_HASRISKVALUE],
)

CLS_016_COLLISIONRISKEVENT = OntologyClass(
    name_en="CollisionRiskEvent",
    name_zh="碰撞风险事件",
    description="空间目标之间存在碰撞风险的事件。作为空间关系事件，通过 hasPrimaryObject/hasSecondaryObject 显式表示交会目标角色。",
    namespace="domain",
    parents=['RiskEvent', 'SpatialRelationEvent'],
    properties=[PROP_HASCOLLISIONPROBABILITY, PROP_HASPREDICTEDMISSDISTANCE, PROP_HASCOMBINEDHARDBODYRADIUS],
    restrictions=[OntologyRestriction("hasEncounterID", "string", "someValuesFrom"), OntologyRestriction("hasCollisionProbability", "float", "someValuesFrom"), OntologyRestriction("hasPredictedMissDistance", "float", "someValuesFrom")],
)

CLS_017_CYBERSECURITYRISK = OntologyClass(
    name_en="CyberSecurityRisk",
    name_zh="网络安全风险",
    description="网络攻击导致的风险。",
    namespace="domain",
    parents=['SecurityRisk'],
)

CLS_018_SECURITYTHREAT = OntologyClass(
    name_en="SecurityThreat",
    name_zh="安全威胁",
    description="可能对太空资产、轨道环境或任务系统造成危害的威胁类型。",
    namespace="domain",
    properties=[PROP_HASTHREATID, PROP_HASTHREATTYPE, PROP_HASTHREATSOURCE, PROP_HASIMPACTSCOPE],
    restrictions=[OntologyRestriction("mayManifestAsEvent", "SpaceEvent", "someValuesFrom"), OntologyRestriction("producesRisk", "SecurityRisk", "someValuesFrom"), OntologyRestriction("requiresResponseMeasure", "ResponseMeasure", "someValuesFrom"), OntologyRestriction("threatMitigatedBy", "ResponseMeasure", "someValuesFrom")],
)

CLS_019_CYBERTHREAT = OntologyClass(
    name_en="CyberThreat",
    name_zh="网络威胁",
    description="通过网络手段对空间系统造成的威胁。",
    namespace="domain",
    parents=['SecurityThreat'],
)

CLS_020_DANGEROUSSITUATIONSTATE = OntologyClass(
    name_en="DangerousSituationState",
    name_zh="危险态势状态",
    description="整体态势处于危险级别。",
    namespace="domain",
    parents=['SituationState'],
    restrictions=[OntologyRestriction("hasSeverityRank", "integer", "hasValue", has_value='3')],
)

CLS_021_SPACEORGANIZATION = OntologyClass(
    name_en="SpaceOrganization",
    name_zh="空间组织",
    description="描述空间相关组织的顶层抽象类。",
    namespace="domain",
)

CLS_022_DATAPROVIDER = OntologyClass(
    name_en="DataProvider",
    name_zh="数据提供方",
    description="提供空间观测或态势数据的组织。",
    namespace="domain",
    parents=['SpaceOrganization'],
)

CLS_023_DEBRISRISK = OntologyClass(
    name_en="DebrisRisk",
    name_zh="碎片风险",
    description="空间碎片导致的风险。",
    namespace="domain",
    parents=['SecurityRisk'],
)

CLS_024_DEBRISRISKEVENT = OntologyClass(
    name_en="DebrisRiskEvent",
    name_zh="碎片风险事件",
    description="由空间碎片引发的风险事件。",
    namespace="domain",
    parents=['RiskEvent'],
)

CLS_025_OBSERVATIONEVENT = OntologyClass(
    name_en="ObservationEvent",
    name_zh="观测事件",
    description="由观测活动产生的事件。",
    namespace="domain",
    parents=['SpaceEvent'],
    restrictions=[OntologyRestriction("detectedFromData", "ObservationData", "someValuesFrom"), OntologyRestriction("observedBySensor", "Sensor", "someValuesFrom")],
)

CLS_026_DETECTIONEVENT = OntologyClass(
    name_en="DetectionEvent",
    name_zh="探测事件",
    description="探测到空间目标的事件。",
    namespace="domain",
    parents=['ObservationEvent'],
)

CLS_027_DIRECTCAUSALASSERTION = OntologyClass(
    name_en="DirectCausalAssertion",
    name_zh="直接因果断言",
    description="原因事件直接导致结果事件的因果断言。",
    namespace="causal",
    parents=['CausalAssertion'],
)

CLS_028_ORBIT = OntologyClass(
    name_en="Orbit",
    name_zh="轨道",
    description="描述空间目标运行轨道。",
    namespace="domain",
    properties=[PROP_HASORBITTYPE, PROP_HASSEMIMAJORAXIS, PROP_HASRAAN, PROP_HASARGUMENTOFPERIGEE, PROP_HASMEANANOMALY, PROP_HASORBITALPERIOD],
)

CLS_029_EARTHORBIT = OntologyClass(
    name_en="EarthOrbit",
    name_zh="地球轨道",
    description="以地球为中心天体的轨道。",
    namespace="domain",
    parents=['Orbit'],
)

CLS_030_SPACEENVIRONMENT = OntologyClass(
    name_en="SpaceEnvironment",
    name_zh="空间环境",
    description="描述空间环境条件。",
    namespace="domain",
)

CLS_031_ELECTROMAGNETICENVIRONMENT = OntologyClass(
    name_en="ElectromagneticEnvironment",
    name_zh="电磁环境",
    description="电磁环境。",
    namespace="domain",
    parents=['SpaceEnvironment'],
)

CLS_032_ENVIRONMENTALTHREAT = OntologyClass(
    name_en="EnvironmentalThreat",
    name_zh="环境威胁",
    description="由空间环境异常导致的威胁。",
    namespace="domain",
    parents=['SecurityThreat'],
)

CLS_033_ORBITALEVENT = OntologyClass(
    name_en="OrbitalEvent",
    name_zh="轨道事件",
    description="发生在轨道环境中、由轨道运动直接引发的轨道事件。",
    namespace="domain",
    parents=['SpaceEvent'],
    restrictions=[OntologyRestriction("occursInOrbit", "Orbit", "someValuesFrom"), OntologyRestriction("involvesObject", "SpaceObject", "someValuesFrom")],
)

CLS_034_FRAGMENTATIONEVENT = OntologyClass(
    name_en="FragmentationEvent",
    name_zh="解体事件",
    description="空间目标发生碎裂或解体的事件。",
    namespace="domain",
    parents=['OrbitalEvent'],
    restrictions=[OntologyRestriction("involvesObject", "SpaceObject", "someValuesFrom")],
)

CLS_035_GEOMETRICCONSTRUCT = OntologyClass(
    name_en="GeometricConstruct",
    name_zh="几何构造",
    description="轨道与空间态势中使用的几何构造抽象。",
    namespace="domain",
    properties=[PROP_HASERRORVALUE, PROP_HASDATACONFIDENCE, PROP_HASGEOMETRICERRORVALUE],
)

CLS_036_OBSERVATIONSYSTEM = OntologyClass(
    name_en="ObservationSystem",
    name_zh="观测系统",
    description="用于探测、监视、跟踪空间目标的观测系统。",
    namespace="domain",
    properties=[PROP_HASLOCATION],
    restrictions=[OntologyRestriction("generatesData", "ObservationData", "someValuesFrom")],
)

CLS_037_SENSOR = OntologyClass(
    name_en="Sensor",
    name_zh="传感器",
    description="能够探测空间目标的传感器。",
    namespace="domain",
    parents=['ObservationSystem'],
    properties=[PROP_HASSENSORID, PROP_HASRESOLUTION],
)

CLS_038_GROUNDBASEDSENSOR = OntologyClass(
    name_en="GroundBasedSensor",
    name_zh="地基传感器",
    description="部署于地面的传感器。",
    namespace="domain",
    parents=['Sensor'],
)

CLS_039_RADARSENSOR = OntologyClass(
    name_en="RadarSensor",
    name_zh="雷达传感器",
    description="以雷达为主要感知机制的传感器。",
    namespace="domain",
    parents=['Sensor'],
)

CLS_040_GROUNDRADARSENSOR = OntologyClass(
    name_en="GroundRadarSensor",
    name_zh="地基雷达传感器",
    description="部署于地面的雷达传感器。",
    namespace="domain",
    parents=['GroundBasedSensor', 'RadarSensor'],
    equivalent_to=['GroundBasedSensor', 'RadarSensor'],
)

CLS_041_GROUNDSTATION = OntologyClass(
    name_en="GroundStation",
    name_zh="地面站",
    description="用于数据接收、指令发送与任务控制的地面站。",
    namespace="domain",
    parents=['ObservationSystem'],
)

CLS_042_INDIRECTCAUSALASSERTION = OntologyClass(
    name_en="IndirectCausalAssertion",
    name_zh="间接因果断言",
    description="原因事件通过中间环节导致结果事件的因果断言。",
    namespace="causal",
    parents=['CausalAssertion'],
)

CLS_043_INFRAREDSENSOR = OntologyClass(
    name_en="InfraredSensor",
    name_zh="红外传感器",
    description="以红外为主要感知机制的传感器。",
    namespace="domain",
    parents=['Sensor'],
)

CLS_044_INHIBITINGCAUSALASSERTION = OntologyClass(
    name_en="InhibitingCausalAssertion",
    name_zh="抑制型因果断言",
    description="原因事件抑制或削弱结果事件的因果断言。",
    namespace="causal",
    parents=['CausalAssertion'],
)

CLS_045_LOWEARTHORBIT = OntologyClass(
    name_en="LowEarthOrbit",
    name_zh="低地球轨道",
    description="低地球轨道（LEO）。",
    namespace="domain",
    parents=['EarthOrbit'],
)

CLS_046_MICROMETEOROIDENVIRONMENT = OntologyClass(
    name_en="MicrometeoroidEnvironment",
    name_zh="微流星体环境",
    description="微流星体环境。",
    namespace="domain",
    parents=['SpaceEnvironment'],
)

CLS_047_MITIGATIONMEASURE = OntologyClass(
    name_en="MitigationMeasure",
    name_zh="缓解措施",
    description="减轻威胁或风险后果的措施。",
    namespace="domain",
    parents=['ResponseMeasure'],
)

CLS_048_MULTICAUSEASSERTION = OntologyClass(
    name_en="MultiCauseAssertion",
    name_zh="多因因果断言",
    description="多个原因事件共同导致结果事件的因果断言。",
    namespace="causal",
    parents=['CausalAssertion'],
    restrictions=[OntologyRestriction("hasCause", "SpaceEvent", "minCardinality", min_cardinality=2)],
)

CLS_049_NORMALSITUATIONSTATE = OntologyClass(
    name_en="NormalSituationState",
    name_zh="正常态势状态",
    description="整体态势正常。",
    namespace="domain",
    parents=['SituationState'],
    restrictions=[OntologyRestriction("hasSeverityRank", "integer", "hasValue", has_value='0')],
)

CLS_050_OBJECTBEHAVIOREVENT = OntologyClass(
    name_en="ObjectBehaviorEvent",
    name_zh="目标行为事件",
    description="由空间目标自身行为引发的事件。",
    namespace="domain",
    parents=['SpaceEvent'],
    restrictions=[OntologyRestriction("involvesObject", "SpaceObject", "someValuesFrom"), OntologyRestriction("affectsOrbit", "Orbit", "someValuesFrom")],
)

CLS_051_SSAACTIVITY = OntologyClass(
    name_en="SSAActivity",
    name_zh="空间态势感知活动",
    description="支撑空间态势感知的各类活动。",
    namespace="domain",
)

CLS_052_OBSERVATIONACTIVITY = OntologyClass(
    name_en="ObservationActivity",
    name_zh="观测活动",
    description="对空间目标进行观测的活动。",
    namespace="domain",
    parents=['SSAActivity'],
)

CLS_053_OBSERVATIONDATA = OntologyClass(
    name_en="ObservationData",
    name_zh="观测数据",
    description="通过观测系统获取的数据。",
    namespace="domain",
    parents=['SSAData'],
)

CLS_054_OPTICALSENSOR = OntologyClass(
    name_en="OpticalSensor",
    name_zh="光学传感器",
    description="以光学为主要感知机制的传感器。",
    namespace="domain",
    parents=['Sensor'],
)

CLS_055_ORBITMANEUVEREVENT = OntologyClass(
    name_en="OrbitManeuverEvent",
    name_zh="轨道机动事件",
    description="空间目标改变轨道的机动事件。",
    namespace="domain",
    parents=['OrbitalEvent', 'ObjectBehaviorEvent'],
    restrictions=[OntologyRestriction("involvesObject", "ArtificialSpaceObject", "someValuesFrom"), OntologyRestriction("changesOrbit", "Orbit", "someValuesFrom")],
)

CLS_056_ORBITALCONGESTIONENVIRONMENT = OntologyClass(
    name_en="OrbitalCongestionEnvironment",
    name_zh="轨道拥堵环境",
    description="轨道拥堵环境。",
    namespace="domain",
    parents=['SpaceEnvironment'],
)

CLS_057_PAYLOAD = OntologyClass(
    name_en="Payload",
    name_zh="有效载荷",
    description="航天器或运载火箭上承载的任务设备或载荷。",
    namespace="domain",
    parents=['ArtificialSpaceObject'],
)

CLS_058_PHYSICALTHREAT = OntologyClass(
    name_en="PhysicalThreat",
    name_zh="物理威胁",
    description="由物理接近或碰撞等物理作用导致的威胁。",
    namespace="domain",
    parents=['SecurityThreat'],
)

CLS_059_PREDICTIONDATA = OntologyClass(
    name_en="PredictionData",
    name_zh="预测数据",
    description="预测数据。",
    namespace="domain",
    parents=['SSAData'],
)

CLS_060_PROMOTINGCAUSALASSERTION = OntologyClass(
    name_en="PromotingCausalAssertion",
    name_zh="促进型因果断言",
    description="原因事件促进但非必然导致结果事件的因果断言。",
    namespace="causal",
    parents=['CausalAssertion'],
)

CLS_061_SENSOROBSERVATIONDATA = OntologyClass(
    name_en="SensorObservationData",
    name_zh="传感器观测数据",
    description="传感器产生的观测数据。",
    namespace="domain",
    parents=['ObservationData'],
)

CLS_062_RADAROBSERVATIONDATA = OntologyClass(
    name_en="RadarObservationData",
    name_zh="雷达观测数据",
    description="雷达传感器产生的观测数据。",
    namespace="domain",
    parents=['SensorObservationData'],
)

CLS_063_RADIATIONENVIRONMENT = OntologyClass(
    name_en="RadiationEnvironment",
    name_zh="辐射环境",
    description="辐射环境。",
    namespace="domain",
    parents=['SpaceEnvironment'],
)

CLS_064_STATETRANSITION = OntologyClass(
    name_en="StateTransition",
    name_zh="状态转移",
    description="态势状态之间的转移。",
    namespace="domain",
    restrictions=[OntologyRestriction("hasSourceState", "SituationState", "cardinality", cardinality=1), OntologyRestriction("hasTargetState", "SituationState", "cardinality", cardinality=1), OntologyRestriction("triggeredByEvent", "SpaceEvent", "minCardinality", min_cardinality=1)],
)

CLS_065_RECOVERYTRANSITION = OntologyClass(
    name_en="RecoveryTransition",
    name_zh="恢复转移",
    description="态势从异常/危险向正常恢复的转移。",
    namespace="domain",
    parents=['StateTransition'],
)

CLS_066_SITUATIONASSESSMENTDATA = OntologyClass(
    name_en="SituationAssessmentData",
    name_zh="态势评估数据",
    description="态势评估数据。",
    namespace="domain",
    parents=['AssessmentData'],
)

CLS_067_RISKASSESSMENTDATA = OntologyClass(
    name_en="RiskAssessmentData",
    name_zh="风险评估数据",
    description="风险评估数据。",
    namespace="domain",
    parents=['SituationAssessmentData'],
)

CLS_068_RISKESCALATIONTRANSITION = OntologyClass(
    name_en="RiskEscalationTransition",
    name_zh="风险升级转移",
    description="风险等级上升的状态转移。",
    namespace="domain",
    parents=['StateTransition'],
)

CLS_069_RISKREDUCTIONTRANSITION = OntologyClass(
    name_en="RiskReductionTransition",
    name_zh="风险降级转移",
    description="风险等级下降的状态转移。",
    namespace="domain",
    parents=['StateTransition'],
)

CLS_070_ROCKETBODY = OntologyClass(
    name_en="RocketBody",
    name_zh="火箭体",
    description="运载火箭的末级、助推器或相关结构体。",
    namespace="domain",
    parents=['ArtificialSpaceObject'],
)

CLS_071_SPACEDEBRIS = OntologyClass(
    name_en="SpaceDebris",
    name_zh="空间碎片",
    description="在地球轨道或深空运行、无实际功能的人造物体。",
    namespace="domain",
    parents=['ArtificialSpaceObject'],
)

CLS_072_ROCKETDEBRIS = OntologyClass(
    name_en="RocketDebris",
    name_zh="火箭碎片",
    description="由火箭体产生的空间碎片。",
    namespace="domain",
    parents=['SpaceDebris'],
)

CLS_073_SPACECRAFT = OntologyClass(
    name_en="Spacecraft",
    name_zh="航天器",
    description="具备特定任务功能、可在轨运行或深空飞行的人造空间飞行器。",
    namespace="domain",
    parents=['ArtificialSpaceObject'],
    properties=[PROP_HASMISSIONTYPE],
    restrictions=[OntologyRestriction("hasMissionType", "string", "someValuesFrom")],
)

CLS_074_SATELLITE = OntologyClass(
    name_en="Satellite",
    name_zh="卫星",
    description="围绕地球或其他天体运行的人造航天器。",
    namespace="domain",
    parents=['Spacecraft'],
)

CLS_075_SENSORNETWORK = OntologyClass(
    name_en="SensorNetwork",
    name_zh="传感器网络",
    description="由多个传感器组成的观测网络。",
    namespace="domain",
    parents=['ObservationSystem'],
)

CLS_076_SPACEWEATHER = OntologyClass(
    name_en="SpaceWeather",
    name_zh="空间天气",
    description="空间天气。",
    namespace="domain",
    parents=['SpaceEnvironment'],
)

CLS_077_SURVEILLANCESYSTEM = OntologyClass(
    name_en="SurveillanceSystem",
    name_zh="监视系统",
    description="用于监视空间区域的系统。",
    namespace="domain",
    parents=['ObservationSystem'],
)

CLS_078_TEMPORALENTITY = OntologyClass(
    name_en="TemporalEntity",
    name_zh="时序实体",
    description="时间维度的顶层抽象。",
    namespace="temporal",
)

CLS_079_THREATESCALATIONTRANSITION = OntologyClass(
    name_en="ThreatEscalationTransition",
    name_zh="威胁升级转移",
    description="威胁等级上升的状态转移。",
    namespace="domain",
    parents=['StateTransition'],
)

CLS_080_TIMEINSTANT = OntologyClass(
    name_en="TimeInstant",
    name_zh="时间点",
    description="零长度的时间点。",
    namespace="temporal",
    parents=['TemporalEntity'],
)

CLS_081_TIMEINTERVAL = OntologyClass(
    name_en="TimeInterval",
    name_zh="时间区间",
    description="具有开始与结束两个端点的时间区间。",
    namespace="temporal",
    parents=['TemporalEntity'],
    restrictions=[OntologyRestriction("hasBeginning", "TimeInstant", "someValuesFrom"), OntologyRestriction("hasEnd", "TimeInstant", "someValuesFrom")],
)

CLS_082_TRACKINGDATA = OntologyClass(
    name_en="TrackingData",
    name_zh="跟踪数据",
    description="跟踪数据。",
    namespace="domain",
    parents=['SSAData'],
)

CLS_083_TRACKINGEVENT = OntologyClass(
    name_en="TrackingEvent",
    name_zh="跟踪事件",
    description="对空间目标进行跟踪的事件。",
    namespace="domain",
    parents=['ObservationEvent'],
)

CLS_084_TRACKINGSYSTEM = OntologyClass(
    name_en="TrackingSystem",
    name_zh="跟踪系统",
    description="用于持续跟踪空间目标的系统。",
    namespace="domain",
    parents=['ObservationSystem'],
)

CLS_085_WARNINGMEASURE = OntologyClass(
    name_en="WarningMeasure",
    name_zh="预警措施",
    description="提前发出预警的响应措施。",
    namespace="domain",
    parents=['ResponseMeasure'],
)

CLS_086_WARNINGSITUATIONSTATE = OntologyClass(
    name_en="WarningSituationState",
    name_zh="预警态势状态",
    description="整体态势达到预警级别。",
    namespace="domain",
    parents=['SituationState'],
    restrictions=[OntologyRestriction("hasSeverityRank", "integer", "hasValue", has_value='2')],
)

# ============================================================
# Aggregations
# ============================================================
ALL_CLASSES: tuple[OntologyClass, ...] = (
    CLS_001_SPACEEVENT,
    CLS_002_SPATIALRELATIONEVENT,
    CLS_003_APPROACHEVENT,
    CLS_004_SPACEOBJECT,
    CLS_005_ARTIFICIALSPACEOBJECT,
    CLS_006_SSADATA,
    CLS_007_ASSESSMENTDATA,
    CLS_008_SITUATIONSTATE,
    CLS_009_ATTENTIONSITUATIONSTATE,
    CLS_010_RESPONSEMEASURE,
    CLS_011_AVOIDANCEMEASURE,
    CLS_012_CAUSALASSERTION,
    CLS_013_SECURITYRISK,
    CLS_014_COLLISIONRISK,
    CLS_015_RISKEVENT,
    CLS_016_COLLISIONRISKEVENT,
    CLS_017_CYBERSECURITYRISK,
    CLS_018_SECURITYTHREAT,
    CLS_019_CYBERTHREAT,
    CLS_020_DANGEROUSSITUATIONSTATE,
    CLS_021_SPACEORGANIZATION,
    CLS_022_DATAPROVIDER,
    CLS_023_DEBRISRISK,
    CLS_024_DEBRISRISKEVENT,
    CLS_025_OBSERVATIONEVENT,
    CLS_026_DETECTIONEVENT,
    CLS_027_DIRECTCAUSALASSERTION,
    CLS_028_ORBIT,
    CLS_029_EARTHORBIT,
    CLS_030_SPACEENVIRONMENT,
    CLS_031_ELECTROMAGNETICENVIRONMENT,
    CLS_032_ENVIRONMENTALTHREAT,
    CLS_033_ORBITALEVENT,
    CLS_034_FRAGMENTATIONEVENT,
    CLS_035_GEOMETRICCONSTRUCT,
    CLS_036_OBSERVATIONSYSTEM,
    CLS_037_SENSOR,
    CLS_038_GROUNDBASEDSENSOR,
    CLS_039_RADARSENSOR,
    CLS_040_GROUNDRADARSENSOR,
    CLS_041_GROUNDSTATION,
    CLS_042_INDIRECTCAUSALASSERTION,
    CLS_043_INFRAREDSENSOR,
    CLS_044_INHIBITINGCAUSALASSERTION,
    CLS_045_LOWEARTHORBIT,
    CLS_046_MICROMETEOROIDENVIRONMENT,
    CLS_047_MITIGATIONMEASURE,
    CLS_048_MULTICAUSEASSERTION,
    CLS_049_NORMALSITUATIONSTATE,
    CLS_050_OBJECTBEHAVIOREVENT,
    CLS_051_SSAACTIVITY,
    CLS_052_OBSERVATIONACTIVITY,
    CLS_053_OBSERVATIONDATA,
    CLS_054_OPTICALSENSOR,
    CLS_055_ORBITMANEUVEREVENT,
    CLS_056_ORBITALCONGESTIONENVIRONMENT,
    CLS_057_PAYLOAD,
    CLS_058_PHYSICALTHREAT,
    CLS_059_PREDICTIONDATA,
    CLS_060_PROMOTINGCAUSALASSERTION,
    CLS_061_SENSOROBSERVATIONDATA,
    CLS_062_RADAROBSERVATIONDATA,
    CLS_063_RADIATIONENVIRONMENT,
    CLS_064_STATETRANSITION,
    CLS_065_RECOVERYTRANSITION,
    CLS_066_SITUATIONASSESSMENTDATA,
    CLS_067_RISKASSESSMENTDATA,
    CLS_068_RISKESCALATIONTRANSITION,
    CLS_069_RISKREDUCTIONTRANSITION,
    CLS_070_ROCKETBODY,
    CLS_071_SPACEDEBRIS,
    CLS_072_ROCKETDEBRIS,
    CLS_073_SPACECRAFT,
    CLS_074_SATELLITE,
    CLS_075_SENSORNETWORK,
    CLS_076_SPACEWEATHER,
    CLS_077_SURVEILLANCESYSTEM,
    CLS_078_TEMPORALENTITY,
    CLS_079_THREATESCALATIONTRANSITION,
    CLS_080_TIMEINSTANT,
    CLS_081_TIMEINTERVAL,
    CLS_082_TRACKINGDATA,
    CLS_083_TRACKINGEVENT,
    CLS_084_TRACKINGSYSTEM,
    CLS_085_WARNINGMEASURE,
    CLS_086_WARNINGSITUATIONSTATE,
)

DATA_PROPERTIES: tuple[OntologyProperty, ...] = (
    PROP_HASARGUMENTOFPERIGEE,
    PROP_HASCAUSALCONFIDENCE,
    PROP_HASCAUSALMECHANISM,
    PROP_HASCOLLISIONPROBABILITY,
    PROP_HASCOMBINEDHARDBODYRADIUS,
    PROP_HASDATACONFIDENCE,
    PROP_HASDATAID,
    PROP_HASDATASOURCE,
    PROP_HASDATATYPE,
    PROP_HASDURATION,
    PROP_HASENCOUNTERID,
    PROP_HASENDTIME,
    PROP_HASERRORVALUE,
    PROP_HASEVENTCONFIDENCE,
    PROP_HASEVENTDESCRIPTION,
    PROP_HASEVENTID,
    PROP_HASEVENTLEVEL,
    PROP_HASEVENTTYPE,
    PROP_HASGEOMETRICERRORVALUE,
    PROP_HASIMPACTSCOPE,
    PROP_HASLAUNCHCOUNTRY,
    PROP_HASLAUNCHDATE,
    PROP_HASLOCATION,
    PROP_HASMASS,
    PROP_HASMEANANOMALY,
    PROP_HASMEASUREDESCRIPTION,
    PROP_HASMEASUREID,
    PROP_HASMEASURELEVEL,
    PROP_HASMEASURETYPE,
    PROP_HASMISSIONTYPE,
    PROP_HASOBJECTID,
    PROP_HASOBJECTNAME,
    PROP_HASOCCURRENCETIME,
    PROP_HASOPERATORNAME,
    PROP_HASORBITTYPE,
    PROP_HASORBITALPERIOD,
    PROP_HASPREDICTEDMISSDISTANCE,
    PROP_HASRAAN,
    PROP_HASRELATIVEDISTANCE,
    PROP_HASRESOLUTION,
    PROP_HASRISKLEVEL,
    PROP_HASRISKVALUE,
    PROP_HASSEMIMAJORAXIS,
    PROP_HASSENSORID,
    PROP_HASSEVERITYRANK,
    PROP_HASSIZE,
    PROP_HASSTARTTIME,
    PROP_HASSTATECONFIDENCE,
    PROP_HASSTATEDESCRIPTION,
    PROP_HASSTATEDURATION,
    PROP_HASSTATEENDTIME,
    PROP_HASSTATEID,
    PROP_HASSTATELEVEL,
    PROP_HASSTATESTARTTIME,
    PROP_HASSTATETYPE,
    PROP_HASSTATEUPDATETIME,
    PROP_HASTHREATID,
    PROP_HASTHREATSOURCE,
    PROP_HASTHREATTYPE,
)

OBJECT_PROPERTIES: tuple[OntologyRelation, ...] = (
    REL_001_AFFECTSOBJECT,
    REL_002_AFFECTSORBIT,
    REL_003_AFFECTSSTATE,
    REL_004_CAUSEDBYEVENT,
    REL_005_CAUSESEVENT,
    REL_006_CHANGESORBIT,
    REL_007_CONTAINSEVENT,
    REL_008_DEGRADESTO,
    REL_009_DESCRIBESOBJECT,
    REL_010_DETECTEDFROMDATA,
    REL_011_EVOLVESTO,
    REL_012_FOLLOWSEVENT,
    REL_013_GENERATEDBY,
    REL_014_GENERATEDBYACTIVITY,
    REL_015_GENERATESDATA,
    REL_016_HASBEGINNING,
    REL_017_HASCAUSALEVIDENCE,
    REL_018_HASCAUSE,
    REL_019_HASEFFECT,
    REL_020_HASEND,
    REL_021_HASFEATUREOFINTEREST,
    REL_022_HASOBSERVATIONRESULT,
    REL_023_HASORBIT,
    REL_024_HASPRIMARYOBJECT,
    REL_025_HASSECONDARYOBJECT,
    REL_026_HASSOURCESTATE,
    REL_027_HASTARGETSTATE,
    REL_028_IMPLEMENTSMEASURE,
    REL_029_INVOLVESOBJECT,
    REL_030_ISIMPLEMENTEDBYEVENT,
    REL_031_ISINVOLVEDINEVENT,
    REL_032_ISORBITOF,
    REL_033_LEADSTOSTATE,
    REL_034_MADEBYSENSOR,
    REL_035_MAYMANIFESTASEVENT,
    REL_036_MEETSEVENT,
    REL_037_MITIGATEDBY,
    REL_038_MITIGATESRISK,
    REL_039_OBSERVEDBYSENSOR,
    REL_040_OCCURSATTIME,
    REL_041_OCCURSDURINGEVENT,
    REL_042_OCCURSINORBIT,
    REL_043_OCCURSINTIMEINTERVAL,
    REL_044_OVERLAPSWITHEVENT,
    REL_045_PRECEDESEVENT,
    REL_046_PRODUCESDATA,
    REL_047_PRODUCESRISK,
    REL_048_RECOVERSTO,
    REL_049_REQUIRESRESPONSEMEASURE,
    REL_050_RESPONDSTOEVENT,
    REL_051_RESPONDSTOTHREAT,
    REL_052_RESULTEDFROMEVENT,
    REL_053_RESULTSINEVENT,
    REL_054_RISKLEADSTOSTATE,
    REL_055_STATECAUSEDBYEVENT,
    REL_056_SUPPORTEDBYDATA,
    REL_057_THREATMITIGATEDBY,
    REL_058_TRANSITSFROM,
    REL_059_TRANSITSTO,
    REL_060_TRIGGEREDBYEVENT,
    REL_061_TRIGGERSEVENT,
    REL_062_TRIGGERSSTATE,
    REL_063_UPDATESSTATE,
)
