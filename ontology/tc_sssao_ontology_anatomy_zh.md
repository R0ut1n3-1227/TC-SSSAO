# TC-SSSAO 本体库解剖文档

**文件**：`ontology/tc_sssao.owl`

---

## 1. 概览

| 指标 | 数量 |
|---|---|
| 类（Class，onto:） | 86 |
| 对象属性（ObjectProperty，onto:） | 65 |
| 数据属性（DatatypeProperty，onto:） | 68 |
| 注释属性（AnnotationProperty，onto:） | 12 |
| 顶层模块（直接子类于 owl:Thing） | 11 |
| 约束公理（独立规则层） | 0 |
| 外部标准术语最小声明（第 9.2 节） | 16 |

## 2. 类层次结构

```
└── owl:Thing
    ├── GeometricConstruct (几何构造)
    ├── ObservationSystem (观测系统)
    │   ├── GroundStation (地面站)
    │   ├── Sensor (传感器)
    │   │   ├── GroundBasedSensor (地基传感器)
    │   │   │   └── GroundRadarSensor (地基雷达传感器)
    │   │   ├── InfraredSensor (红外传感器)
    │   │   ├── OpticalSensor (光学传感器)
    │   │   └── RadarSensor (雷达传感器)
    │   │       └── GroundRadarSensor (地基雷达传感器)
    │   ├── SensorNetwork (传感器网络)
    │   ├── SurveillanceSystem (监视系统)
    │   └── TrackingSystem (跟踪系统)
    ├── ResponseMeasure (响应措施)
    │   ├── AvoidanceMeasure (规避措施)
    │   ├── MitigationMeasure (缓解措施)
    │   └── WarningMeasure (预警措施)
    ├── SecurityRisk (安全风险)
    │   ├── CollisionRisk (碰撞风险)
    │   ├── CyberSecurityRisk (网络安全风险)
    │   └── DebrisRisk (碎片风险)
    ├── SecurityThreat (安全威胁)
    │   ├── CyberThreat (网络威胁)
    │   ├── EnvironmentalThreat (环境威胁)
    │   └── PhysicalThreat (物理威胁)
    ├── SituationState (态势状态)
    │   ├── AttentionSituationState (关注态势状态)
    │   ├── DangerousSituationState (危险态势状态)
    │   ├── NormalSituationState (正常态势状态)
    │   └── WarningSituationState (预警态势状态)
    ├── SpaceEnvironment (空间环境)
    │   ├── ElectromagneticEnvironment (电磁环境)
    │   ├── MicrometeoroidEnvironment (微流星体环境)
    │   ├── OrbitalCongestionEnvironment (轨道拥堵环境)
    │   ├── RadiationEnvironment (辐射环境)
    │   └── SpaceWeather (空间天气)
    ├── SpaceEvent (空间事件)
    │   ├── ObjectBehaviorEvent (目标行为事件)
    │   │   └── OrbitManeuverEvent (轨道机动事件)
    │   ├── ObservationEvent (观测事件)
    │   │   ├── DetectionEvent (探测事件)
    │   │   └── TrackingEvent (跟踪事件)
    │   ├── OrbitalEvent (轨道事件)
    │   │   ├── FragmentationEvent (解体事件)
    │   │   └── OrbitManeuverEvent (轨道机动事件)
    │   ├── RiskEvent (风险事件)
    │   │   ├── CollisionRiskEvent (碰撞风险事件)
    │   │   └── DebrisRiskEvent (碎片风险事件)
    │   └── SpatialRelationEvent (空间关系事件)
    │       ├── ApproachEvent (接近事件)
    │       └── CollisionRiskEvent (碰撞风险事件)
    ├── SpaceOrganization (空间组织)
    │   └── DataProvider (数据提供方)
    ├── StateTransition (状态转移)
    │   ├── RecoveryTransition (恢复转移)
    │   ├── RiskEscalationTransition (风险升级转移)
    │   ├── RiskReductionTransition (风险降级转移)
    │   └── ThreatEscalationTransition (威胁升级转移)
    └── TemporalEntity (时序实体)
        ├── TimeInstant (时间点)
        └── TimeInterval (时间区间)
```

## 3. 对象属性

### 3.1 domain: `CausalAssertion`

- **`hasCausalEvidence`** *具有因果证据* — range: `SSAData`
  - 支撑因果断言的 SSA 数据。
- **`hasCause`** *具有原因* — range: `SpaceEvent`
  - 因果断言中的原因事件。
- **`hasEffect`** *具有结果* — range: `SpaceEvent`
  - 因果断言中的结果事件。

### 3.2 domain: `ObservationActivity`

- **`madeBySensor`** *由传感器执行* — range: `Sensor`
  - 观测活动由传感器执行。

### 3.3 domain: `ObservationData`

- **`generatedBy`** *由……生成* — range: `ObservationSystem`；逆属性: `generatesData`
  - 观测数据由观测系统生成。
- **`hasObservationResult`** *具有观测结果* — range: `SpaceObject`
  - 观测数据具有观测结果目标。

### 3.4 domain: `ObservationEvent`

- **`observedBySensor`** *由传感器观测* — range: `Sensor`
  - 观测事件由传感器观测。

### 3.5 domain: `ObservationSystem`

- **`generatesData`** *生成数据* — range: `ObservationData`；逆属性: `generatedBy`
  - 观测系统生成观测数据。

### 3.6 domain: `Orbit`

- **`isOrbitOf`** *是某目标的轨道* — range: `SpaceObject`；逆属性: `hasOrbit`
  - 轨道属于空间目标。

### 3.7 domain: `ResponseMeasure`

- **`isImplementedByEvent`** *由事件实施* — range: `SpaceEvent`；逆属性: `implementsMeasure`
  - 响应措施由空间事件实施。
- **`mitigatesRisk`** *缓解风险* — range: `SecurityRisk`；逆属性: `mitigatedBy`
  - 响应措施缓解安全风险。
- **`respondsToEvent`** *响应事件* — range: `SpaceEvent`
  - 响应措施响应空间事件。
- **`respondsToThreat`** *响应威胁* — range: `SecurityThreat`；逆属性: `requiresResponseMeasure`
  - 响应措施响应安全威胁。

### 3.8 domain: `SSAActivity`

- **`producesData`** *产生活动数据* — range: `SSAData`；逆属性: `generatedByActivity`
  - SSA 活动产生 SSA 数据。

### 3.9 domain: `SSAData`

- **`describesObject`** *描述目标* — range: `SpaceObject`
  - SSA 数据描述空间目标。
- **`generatedByActivity`** *由活动生成* — range: `SSAActivity`；逆属性: `producesData`
  - SSA 数据由 SSA 活动生成。
- **`hasFeatureOfInterest`** *具有关注目标* — range: `SpaceObject`
  - SSA 数据所关注的空间目标。

### 3.10 domain: `SecurityRisk`

- **`mitigatedBy`** *被缓解* — range: `ResponseMeasure`；逆属性: `mitigatesRisk`
  - 安全风险被响应措施缓解。
- **`riskLeadsToState`** *风险导致状态* — range: `SituationState`
  - 安全风险导致态势状态。

### 3.11 domain: `SecurityThreat`

- **`mayManifestAsEvent`** *可能表现为事件* — range: `SpaceEvent`
  - 安全威胁可能表现为空间事件。
- **`producesRisk`** *产生风险* — range: `SecurityRisk`
  - 安全威胁产生安全风险。
- **`requiresResponseMeasure`** *需要响应措施* — range: `ResponseMeasure`；逆属性: `respondsToThreat`
  - 安全威胁需要响应措施。
- **`threatMitigatedBy`** *威胁被缓解* — range: `ResponseMeasure`
  - 安全威胁被响应措施缓解。

### 3.12 domain: `SituationState`

- **`degradesTo`** *恶化为* — range: `SituationState`
  - 态势状态恶化为另一状态。
- **`evolvesTo`** *演化为* — range: `SituationState`
  - 态势状态演化为另一状态。
- **`recoversTo`** *恢复为* — range: `SituationState`
  - 态势状态恢复为另一状态。
- **`stateCausedByEvent`** *状态由事件导致* — range: `SpaceEvent`；逆属性: `leadsToState`
  - 态势状态由事件导致。
- **`transitsFrom`** *转移自* — range: `SituationState`；逆属性: `transitsTo`
  - 态势状态转移自另一状态。
- **`transitsTo`** *转移到* — range: `SituationState`；逆属性: `transitsFrom`
  - 态势状态转移到另一状态。

### 3.13 domain: `SpaceEvent`

- **`affectsObject`** *影响目标* — range: `SpaceObject`
  - 空间事件影响空间目标。
- **`affectsOrbit`** *影响轨道* — range: `Orbit`
  - 空间事件影响轨道。
- **`affectsState`** *影响状态* — range: `SituationState`
  - 空间事件影响态势状态。
- **`causedByEvent`** *由事件导致* — range: `SpaceEvent`；逆属性: `causesEvent`
  - 某事件由另一事件导致。
- **`causesEvent`** *导致事件* — range: `SpaceEvent`；逆属性: `causedByEvent`
  - 某事件导致另一事件发生。
- **`changesOrbit`** *改变轨道* — range: `Orbit`
  - 空间事件改变轨道。
- **`containsEvent`** *包含事件* — range: `SpaceEvent`；逆属性: `occursDuringEvent`
  - 某事件包含另一事件。
- **`detectedFromData`** *由数据发现* — range: `SSAData`
  - 空间事件由 SSA 数据发现。
- **`followsEvent`** *后于事件* — range: `SpaceEvent`；特征: 传递；逆属性: `precedesEvent`
  - 某事件在时间上后于另一事件。
- **`implementsMeasure`** *实施措施* — range: `ResponseMeasure`；逆属性: `isImplementedByEvent`
  - 空间事件实施响应措施。
- **`increasesThreat`** *加剧威胁* — range: `SecurityThreat`
  - 空间事件加剧相关安全威胁
- **`indicatesThreat`** *指示威胁* — range: `SecurityThreat`
  - 空间事件指示相关安全威胁
- **`involvesObject`** *涉及目标* — range: `SpaceObject`；逆属性: `isInvolvedInEvent`
  - 空间事件涉及空间目标。
- **`leadsToState`** *导致状态* — range: `SituationState`；逆属性: `stateCausedByEvent`
  - 事件导致态势状态。
- **`meetsEvent`** *邻接事件* — range: `SpaceEvent`
  - 一个事件结束时间等于另一个事件开始时间。
- **`occursAtTime`** *发生于时间点* — range: `TimeInstant`
  - 事件发生在某一时间点。
- **`occursDuringEvent`** *发生于另一事件期间* — range: `SpaceEvent`；逆属性: `containsEvent`
  - 某事件发生于另一事件期间。
- **`occursInOrbit`** *发生于轨道* — range: `Orbit`
  - 空间事件发生于某轨道。
- **`occursInTimeInterval`** *发生于时间区间* — range: `TimeInterval`
  - 事件发生在某一时间区间内。
- **`overlapsWithEvent`** *与事件时间重叠* — range: `SpaceEvent`；特征: 对称
  - 两个事件在时间上重叠。
- **`precedesEvent`** *先于事件* — range: `SpaceEvent`；特征: 传递；逆属性: `followsEvent`
  - 某事件在时间上先于另一事件。
- **`resultedFromEvent`** *由事件产生* — range: `SpaceEvent`；逆属性: `resultsInEvent`
  - 某事件由另一事件产生。
- **`resultsInEvent`** *产生事件* — range: `SpaceEvent`；逆属性: `resultedFromEvent`
  - 某事件产生另一事件。
- **`supportedByData`** *由数据支撑* — range: `SSAData`
  - 空间事件由 SSA 数据支撑。
- **`triggersEvent`** *触发事件* — range: `SpaceEvent`
  - 某事件触发另一事件发生。
- **`triggersState`** *触发状态* — range: `SituationState`
  - 空间事件触发态势状态。
- **`updatesState`** *更新状态* — range: `SituationState`
  - 空间事件更新态势状态。

### 3.14 domain: `SpaceObject`

- **`hasOrbit`** *具有轨道* — range: `Orbit`；逆属性: `isOrbitOf`
  - 空间目标具有轨道。
- **`isInvolvedInEvent`** *参与事件* — range: `SpaceEvent`；逆属性: `involvesObject`
  - 空间目标参与空间事件。

### 3.15 domain: `SpatialRelationEvent`

- **`hasPrimaryObject`** *具有主目标* — range: `SpaceObject`
  - 空间关系事件中交会对象对的主要目标，用于显式表示目标角色。
- **`hasSecondaryObject`** *具有次目标* — range: `SpaceObject`
  - 空间关系事件中交会对象对的次要目标，用于显式表示目标角色。

### 3.16 domain: `StateTransition`

- **`hasSourceState`** *具有源状态* — range: `SituationState`
  - 状态转移的源状态。
- **`hasTargetState`** *具有目标状态* — range: `SituationState`
  - 状态转移的目标状态。
- **`triggeredByEvent`** *由事件触发* — range: `SpaceEvent`
  - 触发状态转移的空间事件。

### 3.17 domain: `TimeInterval`

- **`hasBeginning`** *具有开始* — range: `TimeInstant`
  - 时间区间的开始时间点。
- **`hasEnd`** *具有结束* — range: `TimeInstant`
  - 时间区间的结束时间点。

## 4. 数据属性

### 4.1 domain: `CausalAssertion`

- **`hasCausalConfidence`** *因果置信度* — range: `float`
  - 因果断言的可选置信度元数据。当数据来源、专家评估或外部模型提供定量置信信息时记录该值；来源未给出定量置信度时不强制赋值（M3 第一阶段起由 exactly 1 放宽为 max 1）。
- **`hasCausalMechanism`** *因果机制* — range: `string`
  - 因果断言背后的物理或逻辑机制描述。

### 4.2 domain: `CollisionRiskEvent`

- **`hasCollisionProbability`** *碰撞概率* — range: `float`
  - 碰撞风险概率。
- **`hasCombinedHardBodyRadius`** *组合硬体半径* — range: `float`
  - 当前交会风险评估中两个目标的组合硬体半径（combined hard-body radius），即两目标外接球半径之和；由外部交会评估给出，随评估事件变化，不作为全局部署常数。
- **`hasPredictedMissDistance`** *预测最近交会距离* — range: `float`
  - 碰撞风险事件预测最近交会距离。

### 4.3 domain: `GeometricConstruct`

- **`hasGeometricErrorValue`** *几何误差值* — range: `float`
  - 几何构造的误差值。

### 4.4 domain: `ObservationSystem`

- **`hasLocation`** *部署位置* — range: `string`
  - 观测系统或传感器的部署位置。

### 4.5 domain: `Orbit`

- **`hasArgumentOfPerigee`** *近地点幅角* — range: `float`
  - 轨道近地点幅角。
- **`hasMeanAnomaly`** *平近点角* — range: `float`
  - 轨道平近点角。
- **`hasOrbitType`** *轨道类型* — range: `string`
  - 轨道类型，如 LEO、MEO、GEO、HEO 等。
- **`hasOrbitalPeriod`** *轨道周期* — range: `float`
  - 轨道运行周期。
- **`hasRAAN`** *升交点赤经* — range: `float`
  - 升交点赤经（Right Ascension of Ascending Node）。
- **`hasSemiMajorAxis`** *半长轴* — range: `float`
  - 轨道半长轴。

### 4.6 domain: `OrbitManeuverEvent`

- **`hasManeuverType`** *机动类型* — range: `string`
  - 轨道机动事件类型

### 4.7 domain: `OrbitalCongestionEnvironment`

- **`hasCongestionLevel`** *拥堵等级* — range: `string`
  - 轨道拥堵环境等级

### 4.8 domain: `RadiationEnvironment`

- **`hasRadiationLevel`** *辐射水平* — range: `string`
  - 辐射环境水平等级

### 4.9 domain: `ResponseMeasure`

- **`hasMeasureDescription`** *措施描述* — range: `string`
  - 响应措施描述。
- **`hasMeasureID`** *措施编号* — range: `string`
  - 响应措施唯一标识。
- **`hasMeasureLevel`** *措施等级* — range: `string`
  - 措施等级，如一般、重要、紧急。
- **`hasMeasureType`** *措施类型* — range: `string`
  - 措施类型，如规避、应急、缓解、预警等。

### 4.10 domain: `RiskEvent`

- **`hasRiskValue`** *风险值* — range: `float`
  - 由外部风险评估模型、任务系统或应用层给出的可选综合风险评分，其计算方法与取值尺度由外部系统规定，不由本体规定；承载外部评估结果，不等同于碰撞概率 hasCollisionProbability；碰撞风险态势规则（R5—R8）不再以该属性为判定条件。

### 4.11 domain: `SSAData`

- **`hasDataConfidence`** *数据置信度* — range: `float`
  - 数据可信程度。
- **`hasDataID`** *数据编号* — range: `string`
  - SSA 数据唯一标识。
- **`hasDataSource`** *数据来源* — range: `string`
  - 数据来源说明。
- **`hasDataType`** *数据类型* — range: `string`
  - 数据类型说明。
- **`hasErrorValue`** *误差值* — range: `float`
  - 观测或计算误差。

### 4.12 domain: `SecurityRisk`

- **`hasRiskDescription`** *风险描述* — range: `string`
  - 安全风险的文本描述

### 4.13 domain: `SecurityThreat`

- **`hasImpactScope`** *影响范围* — range: `string`
  - 威胁影响范围，如目标、轨道区域、任务系统等。
- **`hasThreatConfidence`** *威胁置信度* — range: `float`
  - 安全威胁评估的置信度
- **`hasThreatID`** *威胁编号* — range: `string`
  - 安全威胁唯一标识。
- **`hasThreatLevel`** *威胁等级* — range: `string`
  - 安全威胁等级
- **`hasThreatSource`** *威胁来源* — range: `string`
  - 威胁来源，如碎片、目标、环境、网络等。
- **`hasThreatType`** *威胁类型* — range: `string`
  - 威胁类型，如物理、网络、电磁、环境、运行等。

### 4.14 domain: `Sensor`

- **`hasResolution`** *分辨率* — range: `float`
  - 传感器探测分辨率。
- **`hasSensorID`** *传感器编号* — range: `string`
  - 传感器唯一标识。

### 4.15 domain: `SituationState`

- **`hasRiskLevel`** *风险等级* — range: `string`
  - 低、中、高、极高。
- **`hasSeverityRank`** *严重度级别* — range: `integer`
  - 分级风险态势的严重度排序值：正常=0、关注=1、预警=2、危险=3；仅用于支持分级态势之间的排序及跨时间演化规则。
- **`hasStateConfidence`** *状态置信度* — range: `float`
  - 状态判断的可信程度。
- **`hasStateDescription`** *状态描述* — range: `string`
  - 态势状态的文字说明。
- **`hasStateDuration`** *状态持续时间* — range: `duration`
  - 状态持续时间（ISO 8601 时长字符串，如 PT1H30M）。
- **`hasStateEndTime`** *状态结束时间* — range: `dateTime`
  - 状态结束时间。
- **`hasStateID`** *状态编号* — range: `string`
  - 态势状态唯一标识。
- **`hasStateLevel`** *状态等级* — range: `string`
  - 正常、关注、异常、预警、危险、恢复等。
- **`hasStateStartTime`** *状态开始时间* — range: `dateTime`
  - 状态开始时间。
- **`hasStateType`** *状态类型* — range: `string`
  - 运行状态、空间安全状态、威胁状态、综合态势状态等。
- **`hasStateUpdateTime`** *态势状态更新时间* — range: `dateTime`
  - 态势状态最近一次更新时间。

### 4.16 domain: `SpaceEnvironment`

- **`hasEnvironmentLevel`** *环境等级* — range: `string`
  - 空间环境等级，如正常、异常、严重
- **`hasEnvironmentType`** *环境类型* — range: `string`
  - 空间环境所属类型，如辐射环境、电磁环境、轨道拥堵环境等

### 4.17 domain: `SpaceEvent`

- **`hasDuration`** *持续时间* — range: `duration`
  - 事件持续时间（ISO 8601 时长字符串,如 PT1H30M）。
- **`hasEncounterID`** *交会编号* — range: `string`
  - 交会事件编号，标识同一物理交会事件的所有风险评估快照。ESA数据中对应event_id字段，同一物理交会的所有CDM共享同一event_id。B3规则使用此属性实现跨交会隔离。
- **`hasEndTime`** *结束时间* — range: `dateTime`
  - 事件结束时间。
- **`hasEventConfidence`** *事件置信度* — range: `float`
  - 事件判断可信程度。
- **`hasEventDescription`** *事件描述* — range: `string`
  - 事件文字说明。
- **`hasEventID`** *事件编号* — range: `string`
  - 事件唯一标识。
- **`hasEventLevel`** *事件等级* — range: `string`
  - 一般、重要、严重等。
- **`hasEventType`** *事件类型* — range: `string`
  - 轨道机动、接近、碰撞风险等。
- **`hasOccurrenceTime`** *发生时间* — range: `dateTime`
  - 事件发生时间。
- **`hasStartTime`** *开始时间* — range: `dateTime`
  - 事件开始时间。

### 4.18 domain: `SpaceObject`

- **`hasLaunchCountry`** *发射国家* — range: `string`
  - 空间目标的发射国家或责任机构。
- **`hasLaunchDate`** *发射日期* — range: `dateTime`
  - 空间目标的发射日期与时间。
- **`hasMass`** *质量* — range: `float`
  - 空间目标的质量，通常以千克为单位。
- **`hasObjectID`** *目标编号* — range: `string`
  - 空间目标的唯一标识编号。
- **`hasObjectName`** *目标名称* — range: `string`
  - 空间目标的名称。
- **`hasOperatorName`** *运营方名称* — range: `string`
  - 空间目标当前运营方的名称。
- **`hasSize`** *尺寸* — range: `float`
  - 空间目标的特征尺寸。

### 4.19 domain: `Spacecraft`

- **`hasMissionType`** *任务类型* — range: `string`
  - 航天器承担的任务类型。

### 4.20 domain: `SpatialRelationEvent`

- **`hasRelativeDistance`** *相对距离* — range: `float`
  - 两目标之间距离。
- **`hasSpatialRelationship`** *空间关系* — range: `string`
  - 空间关系事件中的关系类型

## 5. 注释属性

- **`alignmentRationale`** *对齐理由* — 说明 TC-SSSAO 与标准词汇之间采用 subClassOf / subPropertyOf / seeAlso 或不做正式对齐的理由。
- **`formalExpression`** *形式化表达*
- **`implementationStatus`** *实现状态*
- **`inputProperties`** *输入属性*
- **`mappedToExternalTerm`** *映射到外部术语*
- **`modelLayer`** *模型分层*
- **`naturalLanguageRule`** *自然语言规则*
- **`outputRelation`** *输出关系*
- **`reusedOntology`** *复用本体*
- **`ruleCategory`** *规则类别*
- **`targetClass`** *目标类*
- **`validationSeverity`** *验证严重级别*

## 6. 约束公理（R1–R18）

| 编号 | 名称 | ruleCategory | implementationStatus | 目标类 | 输入属性 | 输出关系 | 自然语言规则 |
|---|---|---|---|---|---|---|---|

## 7. 规则执行覆盖表

| 编号 | 规则名称 | ruleCategory | implementationStatus | 实现位置（Shape / OWL 公理） | 正例测试 | 负例测试 | 推导结果 / 错误消息 | 结果 |
|---|---|---|---|---|---|---|---|---|

## 8. 外部本体复用映射

### 8.1 `onto:reusedOntology`

| 复用本体 | 对齐实体 |
|---|---|
| geosparql# | Orbit |
| time# | hasDuration, hasEndTime, hasOccurrenceTime, hasStartTime, hasStateEndTime, hasStateStartTime |
| prov# | SituationState, generatedBy, hasDataSource |
|  | ObservationData, ObservationSystem |

### 8.2 `onto:mappedToExternalTerm`

| 外部术语 | 对齐实体 |
|---|---|
| http://www.w3.org/ns/sosa/FeatureOfInterest | SpaceObject |
| http://www.w3.org/ns/sosa/Sensor | Sensor |

## 9. 标准词汇对齐（M5 Phase 1）

### 9.1 正式对齐公理

| 本地术语 | 对齐方式 | 标准术语 |
|---|---|---|
| `CausalAssertion` | 子类 | `prov:Entity` |
| `DataProvider` | 子类 | `prov:Agent` |
| `ObservationActivity` | 子类 | `sosa:Observation` |
| `ObservationData` | 子类 | `sosa:Result` |
| `Orbit` | 子类 | `geo:Feature` |
| `SSAActivity` | 子类 | `prov:Activity` |
| `SSAData` | 子类 | `prov:Entity` |
| `Sensor` | 子类 | `sosa:Sensor` |
| `SpaceObject` | 子类 | `geo:Feature` |
| `TimeInstant` | 子类 | `time:Instant` |
| `TimeInterval` | 子类 | `time:Interval` |
| `generatedByActivity` | 子属性 | `prov:wasGeneratedBy` |
| `hasCausalEvidence` | 子属性 | `prov:wasDerivedFrom` |
| `madeBySensor` | 子属性 | `sosa:madeBySensor` |
| `occursAtTime` | 子属性 | `time:hasTime` |
| `occursInTimeInterval` | 子属性 | `time:hasTime` |

### 9.2 外部术语最小声明

| 外部术语 | 声明类型 |
|---|---|
| `geo:Feature` | `owl:Class` |
| `geo:Geometry` | `owl:Class` |
| `prov:Activity` | `owl:Class` |
| `prov:Agent` | `owl:Class` |
| `prov:Entity` | `owl:Class` |
| `sosa:Observation` | `owl:Class` |
| `sosa:Result` | `owl:Class` |
| `sosa:Sensor` | `owl:Class` |
| `time:Instant` | `owl:Class` |
| `time:Interval` | `owl:Class` |
| `geo:hasGeometry` | `owl:ObjectProperty` |
| `prov:wasDerivedFrom` | `owl:ObjectProperty` |
| `prov:wasGeneratedBy` | `owl:ObjectProperty` |
| `sosa:madeBySensor` | `owl:ObjectProperty` |
| `time:hasTime` | `owl:ObjectProperty` |
| `geo:wktLiteral` | `rdfs:Datatype` |

### 9.3 对齐原则

- 正式对齐的唯一真源为 `ontology/tc_sssao_alignments.ttl`，由 `scripts/build/apply_standard_alignments.py` 并入主本体；
- 不通过 `owl:imports` 整体导入外部本体，外部术语仅保留 OWL 2 DL 类型完整性所需的最小声明；
- 不使用 `owl:equivalentClass` / `owl:equivalentProperty` 声明与外部术语的等价关系；
- 对象属性与数据属性之间不建立跨类型映射；语义层次不同的关联（如 `precedesEvent` 与 `time:before`）仅使用 `rdfs:seeAlso` 参照；
- 标准版本基线：OWL-Time W3C REC 2017-10-19；SOSA/SSN W3C REC 2017-10-19；PROV-O W3C REC 2013-04-30；GeoSPARQL 1.1 OGC 22-047r1。

## 10. 说明

- 树型结构仅展示本体 onto: 命名空间各类之间的 `rdfs:subClassOf` 关系；外部标准术语声明不进入类层次树。
- 属性按 `rdfs:domain` 分组；若一个属性声明了多个 domain，仅在第一个 domain 下出现。
- R1–R18 与 B1–B5 规则定义保留在 rules/tc_sssao_rules.ttl 与 src/tc_sssao/axioms.py，作为独立 SHACL-SPARQL 规则层实现，不作为领域本体类。
- R1–R8 为 SHACL-SPARQL 推导规则，R9–R11、R13、R14、R18 为 SHACL-SPARQL 验证规则，R12、R15–R17 为 OWL StructuralRestriction。
- 当前 pyshacl 0.40.0 未暴露 `iterate_rules` 参数，正式验证采用外部固定点包装器执行。第一轮将主本体作为本体图注入工作图，完成 RDFS 展开与 SHACL 规则推导；后续轮次复用同一工作图，不再重复加载本体，直至领域规则输出不再增加。收敛判断仅统计时序、因果和状态推导关系（`precedesEvent`、`followsEvent`、`overlapsWithEvent`、`causesEvent`、`leadsToState`、`transitsTo`、`degradesTo`）及派生状态类型（`NormalSituationState`、`AttentionSituationState`、`WarningSituationState`、`DangerousSituationState`），不统计 TBox 匿名节点。当前测试数据在第一轮完成有效推导，第二轮确认无新增领域三元组并达到固定点。
- R17 的 SHACL Shape 不再排除 `Sensor`，所有 `ObservationSystem` 及其子类均须满足 `generatesData` 约束。
