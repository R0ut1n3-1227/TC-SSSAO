from __future__ import annotations

from ..meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction

NAMESPACE = "domain"

# ============================================================
# Classes
# ============================================================

SpaceObject = OntologyClass(
    name_en="SpaceObject",
    name_zh="空间目标",
    description="太空安全态势感知中的顶层空间目标概念，涵盖自然空间目标与人造空间目标。",
    parents=[]
)

ArtificialSpaceObject = OntologyClass(
    name_en="ArtificialSpaceObject",
    name_zh="人造空间目标",
    description="由人类制造并发射至外层空间的目标。",
    parents=["SpaceObject"]
)

Spacecraft = OntologyClass(
    name_en="Spacecraft",
    name_zh="航天器",
    description="具备特定任务功能、可在轨运行或深空飞行的人造空间飞行器。",
    parents=["ArtificialSpaceObject"]
)

Satellite = OntologyClass(
    name_en="Satellite",
    name_zh="卫星",
    description="围绕地球或其他天体运行的人造航天器。",
    parents=["Spacecraft"]
)

RocketBody = OntologyClass(
    name_en="RocketBody",
    name_zh="火箭体",
    description="运载火箭的末级、助推器或相关结构体。",
    parents=["ArtificialSpaceObject"]
)

Payload = OntologyClass(
    name_en="Payload",
    name_zh="有效载荷",
    description="航天器或运载火箭上承载的任务设备或载荷。",
    parents=["ArtificialSpaceObject"]
)

SpaceDebris = OntologyClass(
    name_en="SpaceDebris",
    name_zh="空间碎片",
    description="在地球轨道或深空运行、无实际功能的人造物体。",
    parents=["ArtificialSpaceObject"]
)

RocketDebris = OntologyClass(
    name_en="RocketDebris",
    name_zh="火箭碎片",
    description="由火箭体产生的空间碎片。",
    parents=["SpaceDebris"]
)


# ============================================================
# Properties
# ============================================================

hasObjectID = OntologyProperty(
    name="hasObjectID",
    datatype="xsd:string",
    name_zh="目标编号",
    description="空间目标的唯一标识编号。",
    domain="SpaceObject"
)

hasObjectName = OntologyProperty(
    name="hasObjectName",
    datatype="xsd:string",
    name_zh="目标名称",
    description="空间目标的名称。",
    domain="SpaceObject"
)

hasMass = OntologyProperty(
    name="hasMass",
    datatype="xsd:float",
    name_zh="质量",
    description="空间目标的质量，通常以千克为单位。",
    domain="SpaceObject"
)

hasSize = OntologyProperty(
    name="hasSize",
    datatype="xsd:float",
    name_zh="尺寸",
    description="空间目标的特征尺寸。",
    domain="SpaceObject"
)

hasLaunchDate = OntologyProperty(
    name="hasLaunchDate",
    datatype="xsd:dateTime",
    name_zh="发射日期",
    description="空间目标的发射日期与时间。",
    domain="SpaceObject"
)

hasLaunchCountry = OntologyProperty(
    name="hasLaunchCountry",
    datatype="xsd:string",
    name_zh="发射国家",
    description="空间目标的发射国家或责任机构。",
    domain="SpaceObject"
)

hasOperatorName = OntologyProperty(
    name="hasOperatorName",
    datatype="xsd:string",
    name_zh="运营方名称",
    description="空间目标当前运营方的名称。",
    domain="SpaceObject"
)

hasMissionType = OntologyProperty(
    name="hasMissionType",
    datatype="xsd:string",
    name_zh="任务类型",
    description="航天器承担的任务类型。",
    domain="Spacecraft"
)


# ============================================================
# Relations
# ============================================================


# ============================================================
# Assign properties to domain classes
# ============================================================

SpaceObject.properties = [hasObjectID, hasObjectName, hasMass, hasSize, hasLaunchDate, hasLaunchCountry, hasOperatorName]

Spacecraft.properties = [hasMissionType]


# ============================================================
# Module exports
# ============================================================

CLASSES = [SpaceObject, ArtificialSpaceObject, Spacecraft, Satellite, RocketBody, Payload, SpaceDebris, RocketDebris]

PROPERTIES = [hasObjectID, hasObjectName, hasMass, hasSize, hasLaunchDate, hasLaunchCountry, hasOperatorName, hasMissionType]

RELATIONS = []
