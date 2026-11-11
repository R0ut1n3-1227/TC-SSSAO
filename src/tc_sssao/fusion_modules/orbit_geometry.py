"""轨道与几何模块（Orbit & GeometricConstruct）

为 TC-SSSAO 太空安全态势感知本体提供轨道分类与几何构造的
OntologyClass / OntologyProperty / OntologyRelation 定义。

轨道层级：
  Orbit
  └── EarthOrbit (LowEarthOrbit)

几何构造层级：
  GeometricConstruct（轨道与空间态势中使用的几何构造抽象）
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation


# ============================================================
# Data Properties
# ============================================================

# ---------- Orbit properties ----------
PROP_HAS_ORBIT_TYPE = OntologyProperty(
    name="hasOrbitType",
    datatype="string",
    name_zh="轨道类型",
    description="轨道类型，如 LEO、MEO、GEO、HEO 等。",
    domain="Orbit",
)
PROP_HAS_SEMI_MAJOR_AXIS = OntologyProperty(
    name="hasSemiMajorAxis",
    datatype="float",
    name_zh="半长轴",
    description="轨道半长轴。",
    domain="Orbit",
)


PROP_HAS_RAAN = OntologyProperty(
    name="hasRAAN",
    datatype="float",
    name_zh="升交点赤经",
    description="升交点赤经（Right Ascension of Ascending Node）。",
    domain="Orbit",
)
PROP_HAS_ARGUMENT_OF_PERIGEE = OntologyProperty(
    name="hasArgumentOfPerigee",
    datatype="float",
    name_zh="近地点幅角",
    description="轨道近地点幅角。",
    domain="Orbit",
)
PROP_HAS_MEAN_ANOMALY = OntologyProperty(
    name="hasMeanAnomaly",
    datatype="float",
    name_zh="平近点角",
    description="轨道平近点角。",
    domain="Orbit",
)



PROP_HAS_ORBITAL_PERIOD = OntologyProperty(
    name="hasOrbitalPeriod",
    datatype="float",
    name_zh="轨道周期",
    description="轨道运行周期。",
    domain="Orbit",
)
# ---------- GeometricConstruct properties ----------



PROP_HAS_ERROR_VALUE = OntologyProperty(
    name="hasErrorValue",
    datatype="float",
    name_zh="误差值",
    description="观测或计算误差。",
    domain="GeometricConstruct",
)
PROP_HAS_DATA_CONFIDENCE = OntologyProperty(
    name="hasDataConfidence",
    datatype="float",
    name_zh="数据置信度",
    description="数据可信程度。",
    domain="GeometricConstruct",
)


# ============================================================
# Classes
# ============================================================

# ---------- Orbit ----------
CLS_ORBIT = OntologyClass(
    name_en="Orbit",
    name_zh="轨道",
    description="描述空间目标运行轨道。",
    namespace="domain",
    properties=[PROP_HAS_ORBIT_TYPE, PROP_HAS_SEMI_MAJOR_AXIS, PROP_HAS_RAAN, PROP_HAS_ARGUMENT_OF_PERIGEE, PROP_HAS_MEAN_ANOMALY, PROP_HAS_ORBITAL_PERIOD],
)

CLS_EARTH_ORBIT = OntologyClass(
    name_en="EarthOrbit",
    name_zh="地球轨道",
    parents=["Orbit"],
    description="以地球为中心天体的轨道。",
    namespace="domain",
)

CLS_LOW_EARTH_ORBIT = OntologyClass(
    name_en="LowEarthOrbit",
    name_zh="低地球轨道",
    parents=["EarthOrbit"],
    description="低地球轨道（LEO）。",
    namespace="domain",
)


# ---------- GeometricConstruct ----------
CLS_GEOMETRIC_CONSTRUCT = OntologyClass(
    name_en="GeometricConstruct",
    name_zh="几何构造",
    description="轨道与空间态势中使用的几何构造抽象。",
    namespace="domain",
    properties=[PROP_HAS_ERROR_VALUE, PROP_HAS_DATA_CONFIDENCE],
)


# ============================================================
# Object Properties
# ============================================================

REL_HAS_ORBIT = OntologyRelation(
    name="hasOrbit",
    name_zh="具有轨道",
    domain="SpaceObject",
    range="Orbit",
    description="空间目标具有轨道。",
)
REL_IS_ORBIT_OF = OntologyRelation(
    name="isOrbitOf",
    name_zh="是某目标的轨道",
    domain="Orbit",
    range="SpaceObject",
    description="轨道属于空间目标。",
    inverse_of="hasOrbit",
)












OBJECT_PROPERTIES: tuple[OntologyRelation, ...] = (REL_HAS_ORBIT, REL_IS_ORBIT_OF)


# ============================================================
# Aggregations
# ============================================================

ALL_ORBIT_CLASSES: tuple[OntologyClass, ...] = (CLS_ORBIT, CLS_EARTH_ORBIT, CLS_LOW_EARTH_ORBIT)

ALL_GEOMETRIC_CLASSES: tuple[OntologyClass, ...] = (CLS_GEOMETRIC_CONSTRUCT)

ALL_ORBIT_GEOMETRY_PROPERTIES: tuple[OntologyProperty, ...] = (PROP_HAS_ORBIT_TYPE, PROP_HAS_SEMI_MAJOR_AXIS, PROP_HAS_RAAN, PROP_HAS_ARGUMENT_OF_PERIGEE, PROP_HAS_MEAN_ANOMALY, PROP_HAS_ORBITAL_PERIOD, PROP_HAS_ERROR_VALUE, PROP_HAS_DATA_CONFIDENCE)

ALL_ORBIT_GEOMETRY_RELATIONS: tuple[OntologyRelation, ...] = OBJECT_PROPERTIES
