"""观测系统与 SSA 活动模块

定义太空安全态势感知本体中的观测系统层级与 SSA 活动层级。
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation


# ============================================================
# Data Properties
# ============================================================

PROP_HAS_SENSOR_ID = OntologyProperty(
    name="hasSensorID",
    datatype="string",
    name_zh="传感器编号",
    description="传感器唯一标识。",
    domain="Sensor",
)

PROP_HAS_RESOLUTION = OntologyProperty(
    name="hasResolution",
    datatype="float",
    name_zh="分辨率",
    description="传感器探测分辨率。",
    domain="Sensor",
)

PROP_HAS_LOCATION = OntologyProperty(
    name="hasLocation",
    datatype="string",
    name_zh="部署位置",
    description="观测系统或传感器的部署位置。",
    domain="ObservationSystem",
)


# ============================================================
# Classes — ObservationSystem
# ============================================================

CLS_OBSERVATION_SYSTEM = OntologyClass(
    name_en="ObservationSystem",
    name_zh="观测系统",
    description="用于探测、监视、跟踪空间目标的观测系统。",
    namespace="domain",
    properties=[PROP_HAS_LOCATION],
)

CLS_SENSOR = OntologyClass(
    name_en="Sensor",
    name_zh="传感器",
    parents=["ObservationSystem"],
    description="能够探测空间目标的传感器。",
    namespace="domain",
    properties=[PROP_HAS_SENSOR_ID, PROP_HAS_RESOLUTION],
)

CLS_GROUND_BASED_SENSOR = OntologyClass(
    name_en="GroundBasedSensor",
    name_zh="地基传感器",
    parents=["Sensor"],
    description="部署于地面的传感器。",
    namespace="domain",
)

CLS_GROUND_BASED_SENSOR = OntologyClass(
    name_en="GroundBasedSensor",
    name_zh="地基传感器",
    parents=["Sensor"],
    description="部署于地面的传感器。",
    namespace="domain",
)

# 感知机制维度（与部署位置正交）
CLS_RADAR_SENSOR = OntologyClass(
    name_en="RadarSensor",
    name_zh="雷达传感器",
    parents=["Sensor"],
    description="以雷达为主要感知机制的传感器。",
    namespace="domain",
)

CLS_OPTICAL_SENSOR = OntologyClass(
    name_en="OpticalSensor",
    name_zh="光学传感器",
    parents=["Sensor"],
    description="以光学为主要感知机制的传感器。",
    namespace="domain",
)

CLS_INFRARED_SENSOR = OntologyClass(
    name_en="InfraredSensor",
    name_zh="红外传感器",
    parents=["Sensor"],
    description="以红外为主要感知机制的传感器。",
    namespace="domain",
)

# 六个组合传感器：部署位置 × 感知机制的交集
CLS_GROUND_RADAR_SENSOR = OntologyClass(
    name_en="GroundRadarSensor",
    name_zh="地基雷达传感器",
    parents=["GroundBasedSensor", "RadarSensor"],
    equivalent_to=["GroundBasedSensor", "RadarSensor"],
    description="部署于地面的雷达传感器。",
    namespace="domain",
)

# 不属于二维网格的特定传感器类型，保留为部署维度的直接子类
CLS_GROUND_STATION = OntologyClass(
    name_en="GroundStation",
    name_zh="地面站",
    parents=["ObservationSystem"],
    description="用于数据接收、指令发送与任务控制的地面站。",
    namespace="domain",
)

CLS_SENSOR_NETWORK = OntologyClass(
    name_en="SensorNetwork",
    name_zh="传感器网络",
    parents=["ObservationSystem"],
    description="由多个传感器组成的观测网络。",
    namespace="domain",
)


# ============================================================
# Classes — SSAActivity
# ============================================================

CLS_SSA_ACTIVITY = OntologyClass(
    name_en="SSAActivity",
    name_zh="空间态势感知活动",
    description="支撑空间态势感知的各类活动。",
    namespace="domain",
)

CLS_OBSERVATION_ACTIVITY = OntologyClass(
    name_en="ObservationActivity",
    name_zh="观测活动",
    parents=["SSAActivity"],
    description="对空间目标进行观测的活动。",
    namespace="domain",
)


# ============================================================
# Object Properties
# ============================================================

REL_MADE_BY_SENSOR = OntologyRelation(
    name="madeBySensor",
    name_zh="由传感器执行",
    domain="ObservationActivity",
    range="Sensor",
    description="观测活动由传感器执行。",
)

REL_GENERATES_DATA = OntologyRelation(
    name="generatesData",
    name_zh="生成数据",
    domain="ObservationSystem",
    range="ObservationData",
    description="观测系统生成观测数据。",
)

REL_GENERATED_BY_ACTIVITY = OntologyRelation(
    name="generatedByActivity",
    name_zh="由活动生成",
    domain="ObservationData",
    range="SSAActivity",
    description="观测数据由 SSA 活动生成。",
    inverse_of="generatesData",
)

OBJECT_PROPERTIES: tuple[OntologyRelation, ...] = (REL_MADE_BY_SENSOR, REL_GENERATES_DATA, REL_GENERATED_BY_ACTIVITY)

ALL_RELATIONS: tuple[OntologyRelation, ...] = OBJECT_PROPERTIES


# ============================================================
# Aggregation
# ============================================================

ALL_CLASSES: tuple[OntologyClass, ...] = (CLS_OBSERVATION_SYSTEM, CLS_SENSOR, CLS_GROUND_BASED_SENSOR, CLS_RADAR_SENSOR, CLS_OPTICAL_SENSOR, CLS_INFRARED_SENSOR, CLS_GROUND_RADAR_SENSOR, CLS_GROUND_STATION, CLS_SENSOR_NETWORK, CLS_SSA_ACTIVITY, CLS_OBSERVATION_ACTIVITY)

ALL_PROPERTIES: tuple[OntologyProperty, ...] = (PROP_HAS_SENSOR_ID, PROP_HAS_RESOLUTION, PROP_HAS_LOCATION)
