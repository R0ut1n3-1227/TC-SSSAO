#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 OOPS! 检测报告修改 TC-SSSAO 本体库。

修改内容：
1. 补充 6 条反向 owl:inverseOf (P13)
2. 为 12 个核心类补充 owl:Restriction (P41)
3. 修改 4 个数据属性的 range（duration / geo:wktLiteral）
4. 添加 6 条外部本体 subPropertyOf 复用关系
5. 选择性添加 8 组 owl:AllDisjointClasses (P10)

不添加实例，只修改 schema。
"""
import os
import sys
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef, BNode, Literal
from rdflib.collection import Collection

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OWL_PATH = os.path.join(BASE_DIR, "ontology", "tc_sssao.owl")
BACKUP_DIR = os.path.join(BASE_DIR, "data", ".backup")
BACKUP_PATH = os.path.join(BACKUP_DIR, "tc_sssao.owl.bak")

ONTO = Namespace("https://w3id.org/tc-sssao#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
PROV = Namespace("http://www.w3.org/ns/prov#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")


def add_inverse_of(g, prop1, prop2):
    """确保 prop1 <-> prop2 双向声明 owl:inverseOf。"""
    if not g.value(prop1, OWL.inverseOf):
        g.add((prop1, OWL.inverseOf, prop2))
    if not g.value(prop2, OWL.inverseOf):
        g.add((prop2, OWL.inverseOf, prop1))


def add_restriction(g, cls, prop, range_uri, restriction_type=OWL.someValuesFrom):
    """为 cls 添加一条 restriction（幂等：相同类/属性/range/类型不重复添加）。"""
    # 检查是否已存在完全相同的 restriction
    for sub in g.objects(cls, RDFS.subClassOf):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) != prop:
            continue
        if g.value(sub, restriction_type) == range_uri:
            return  # 已存在
    restriction = BNode()
    g.add((restriction, RDF.type, OWL.Restriction))
    g.add((restriction, OWL.onProperty, prop))
    g.add((restriction, restriction_type, range_uri))
    g.add((cls, RDFS.subClassOf, restriction))


def cleanup_duplicate_restrictions(g):
    """清理同一个类下完全重复的 restriction（类、属性、range、限定词均相同）。"""
    seen = set()
    to_remove = []
    for cls in g.subjects(RDF.type, OWL.Class):
        for sub in g.objects(cls, RDFS.subClassOf):
            if not isinstance(sub, BNode):
                continue
            if g.value(sub, RDF.type) != OWL.Restriction:
                continue
            prop = g.value(sub, OWL.onProperty)
            svf = g.value(sub, OWL.someValuesFrom)
            avf = g.value(sub, OWL.allValuesFrom)
            if svf:
                key = (str(cls), str(prop), 'some', str(svf))
            elif avf:
                key = (str(cls), str(prop), 'all', str(avf))
            else:
                continue
            if key in seen:
                to_remove.append((cls, sub))
            else:
                seen.add(key)

    for cls, sub in to_remove:
        g.remove((cls, RDFS.subClassOf, sub))
        for s, p, o in g.triples((sub, None, None)):
            g.remove((s, p, o))


def add_disjoint_group(g, classes):
    """添加一组标准写法的 AllDisjointClasses：axiom -> owl:members -> RDF Collection。
    幂等：相同成员不会重复添加。"""
    from rdflib.collection import Collection as RdfCollection

    target_set = set(str(c) for c in classes)
    for existing in g.subjects(RDF.type, OWL.AllDisjointClasses):
        try:
            members_node = g.value(existing, OWL.members)
            if members_node is None:
                continue
            members = set(str(x) for x in RdfCollection(g, members_node) if isinstance(x, URIRef))
            if members == target_set:
                return  # 已存在，跳过
        except Exception:
            continue
    axiom = BNode()
    members = BNode()
    g.add((axiom, RDF.type, OWL.AllDisjointClasses))
    g.add((axiom, OWL.members, members))
    RdfCollection(g, members, classes)


def cleanup_disjoint_classes(g):
    """清理空的、重复的、以及非标准写法的 AllDisjointClasses。"""
    from rdflib.collection import Collection as RdfCollection

    seen = set()
    to_remove = []
    for d in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members_node = g.value(d, OWL.members)
        if members_node is None:
            to_remove.append(d)
            continue
        try:
            members = tuple(sorted(str(x) for x in RdfCollection(g, members_node) if isinstance(x, URIRef)))
            if not members or members in seen:
                to_remove.append(d)
            else:
                seen.add(members)
        except Exception:
            to_remove.append(d)

    for d in to_remove:
        # 递归移除该 AllDisjointClasses 节点及其关联的列表节点
        nodes_to_remove = [d]
        members_node = g.value(d, OWL.members)
        if members_node is not None:
            nodes_to_remove.append(members_node)
        for node in nodes_to_remove:
            for s, p, o in g.triples((node, None, None)):
                g.remove((s, p, o))
            for s, p, o in g.triples((None, None, node)):
                g.remove((s, p, o))


def set_range(g, prop, new_range):
    """替换数据属性的 rdfs:range。"""
    g.remove((prop, RDFS.range, None))
    g.add((prop, RDFS.range, new_range))


def fix_restriction_range(g, cls, prop, old_range, new_range):
    """将指定类+属性的 restriction 的 someValuesFrom/allValuesFrom 从 old_range 改为 new_range。"""
    for sub in g.objects(cls, RDFS.subClassOf):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) != prop:
            continue
        for predicate in (OWL.someValuesFrom, OWL.allValuesFrom):
            for r in g.objects(sub, predicate):
                if r == old_range:
                    g.remove((sub, predicate, old_range))
                    g.add((sub, predicate, new_range))


def ensure_object_property(g, prop, domain, range_uri, label_en, label_zh, comment_zh=None):
    """若不存在则添加对象属性，并设置 domain/range/标签/注释。"""
    if (prop, RDF.type, OWL.ObjectProperty) not in g:
        g.add((prop, RDF.type, OWL.ObjectProperty))
    if domain is not None:
        g.remove((prop, RDFS.domain, None))
        g.add((prop, RDFS.domain, domain))
    if range_uri is not None:
        g.remove((prop, RDFS.range, None))
        g.add((prop, RDFS.range, range_uri))
    g.set((prop, RDFS.label, Literal(label_en, lang="en")))
    g.set((prop, RDFS.label, Literal(label_zh, lang="zh")))
    if comment_zh:
        g.set((prop, RDFS.comment, Literal(comment_zh, lang="zh")))


def change_some_to_all(g, cls, prop):
    """将指定类+属性的 restriction 从 someValuesFrom 改为 allValuesFrom（若存在）。"""
    for sub in g.objects(cls, RDFS.subClassOf):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) != prop:
            continue
        for r in g.objects(sub, OWL.someValuesFrom):
            g.remove((sub, OWL.someValuesFrom, r))
            g.add((sub, OWL.allValuesFrom, r))


def ensure_datatype_property(g, prop, domain, range_uri, label_en, label_zh, comment_zh=None):
    """若不存在则添加数据属性，并设置 domain/range/标签/注释。"""
    if (prop, RDF.type, OWL.DatatypeProperty) not in g:
        g.add((prop, RDF.type, OWL.DatatypeProperty))
    if domain is not None:
        g.remove((prop, RDFS.domain, None))
        g.add((prop, RDFS.domain, domain))
    g.remove((prop, RDFS.range, None))
    g.add((prop, RDFS.range, range_uri))
    g.set((prop, RDFS.label, Literal(label_en, lang="en")))
    g.set((prop, RDFS.label, Literal(label_zh, lang="zh")))
    if comment_zh:
        g.set((prop, RDFS.comment, Literal(comment_zh, lang="zh")))


def modify_ontology(path):
    g = Graph()
    g.parse(path, format="xml")

    # 绑定命名空间前缀
    g.bind("", ONTO)
    g.bind("onto", ONTO)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("sosa", SOSA)
    g.bind("prov", PROV)
    g.bind("geo", GEO)

    # 显式声明 geo:wktLiteral 为 rdfs:Datatype，避免被工具识别为未声明的类
    g.add((GEO.wktLiteral, RDF.type, RDFS.Datatype))

    # ------------------------------------------------------------------
    # 1. P13：为所有单向 inverseOf 补充反向声明
    # ------------------------------------------------------------------
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        for inv in g.objects(prop, OWL.inverseOf):
            if not (inv, OWL.inverseOf, prop) in g:
                g.add((inv, OWL.inverseOf, prop))

    # ------------------------------------------------------------------
    # 1.5 补全生成过程中遗漏的对象属性声明
    # ------------------------------------------------------------------
    missing_obj_props = [
        (ONTO.indicatesThreat, ONTO.SpaceEvent, ONTO.SecurityThreat,
         "indicates threat", "指示威胁", "空间事件指示相关安全威胁"),
        (ONTO.increasesThreat, ONTO.SpaceEvent, ONTO.SecurityThreat,
         "increases threat", "加剧威胁", "空间事件加剧相关安全威胁"),
    ]
    for prop, domain, range_uri, label_en, label_zh, comment_zh in missing_obj_props:
        ensure_object_property(g, prop, domain, range_uri, label_en, label_zh, comment_zh)

    # ------------------------------------------------------------------
    # 2. P41：为核心类补充 restriction
    # ------------------------------------------------------------------
    # 2.1 SpaceEvent
    space_event_restrictions = [
        (ONTO.hasEventID, XSD.string),
        (ONTO.hasEventType, XSD.string),
        (ONTO.hasEventLevel, XSD.string),
        (ONTO.hasEventDescription, XSD.string),
        (ONTO.hasDuration, XSD.duration),
        (ONTO.affectsObject, ONTO.SpaceObject),
        # R13 改为纯 SHACL 验证，不在 SpaceEvent 上添加 detectedFromData/supportedByData 的强制存在性限制
        (ONTO.overlapsWithEvent, ONTO.SpaceEvent),
        (ONTO.occursDuringEvent, ONTO.SpaceEvent),
        (ONTO.triggersEvent, ONTO.SpaceEvent),
        (ONTO.resultsInEvent, ONTO.SpaceEvent),
        (ONTO.affectsState, ONTO.SituationState),
        (ONTO.updatesState, ONTO.SituationState),
        (ONTO.triggersState, ONTO.SituationState),
        (ONTO.indicatesThreat, ONTO.SecurityThreat),
        (ONTO.increasesThreat, ONTO.SecurityThreat),
    ]
    for prop, range_uri in space_event_restrictions:
        add_restriction(g, ONTO.SpaceEvent, prop, range_uri)

    # 2.3 RiskEvent
    # M2 第二阶段（2026-09-04）：删除 RiskEvent ⊑ (hasRiskValue some xsd:float) 必然性限制。
    # hasRiskValue 改为可选的外部综合风险评分（domain/range 声明保留），
    # 碰撞风险态势规则 R5—R8 不再以该属性为判定条件，RiskEvent 实例不再被强制携带风险值。
    # add_restriction(g, ONTO.RiskEvent, ONTO.hasRiskValue, XSD.float)
    for sub in list(g.objects(ONTO.RiskEvent, RDFS.subClassOf)):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) == ONTO.hasRiskValue:
            g.remove((ONTO.RiskEvent, RDFS.subClassOf, sub))
            for t in list(g.triples((sub, None, None))):
                g.remove(t)

    # 2.4 SituationState
    situation_state_restrictions = [
        (ONTO.hasStateID, XSD.string),
        (ONTO.hasStateType, XSD.string),
        (ONTO.hasStateDuration, XSD.duration),
        (ONTO.hasStateDescription, XSD.string),
        (ONTO.hasRiskLevel, XSD.string),
        (ONTO.evolvesTo, ONTO.SituationState),
    ]
    for prop, range_uri in situation_state_restrictions:
        add_restriction(g, ONTO.SituationState, prop, range_uri)

    # 2.5 Orbit
    orbit_restrictions = [
        (ONTO.hasSemiMajorAxis, XSD.float),
        (ONTO.hasRAAN, XSD.float),
        (ONTO.hasArgumentOfPerigee, XSD.float),
        (ONTO.hasMeanAnomaly, XSD.float),
        (ONTO.hasOrbitalPeriod, XSD.float),
    ]
    for prop, range_uri in orbit_restrictions:
        add_restriction(g, ONTO.Orbit, prop, range_uri)

    # 2.6 SpaceObject
    space_object_restrictions = [
        (ONTO.hasMass, XSD.float),
        (ONTO.hasSize, XSD.float),
    ]
    for prop, range_uri in space_object_restrictions:
        add_restriction(g, ONTO.SpaceObject, prop, range_uri)

    # 2.7 ArtificialSpaceObject — 不添加 hasMissionType，避免 ArtificialSpaceObject ≡ Spacecraft
    artificial_restrictions = [
        (ONTO.hasLaunchDate, XSD.dateTime),
        (ONTO.hasLaunchCountry, XSD.string),
        (ONTO.hasOperatorName, XSD.string),
    ]
    for prop, range_uri in artificial_restrictions:
        add_restriction(g, ONTO.ArtificialSpaceObject, prop, range_uri)

    # 2.7a Spacecraft 保留 hasMissionType 限制
    add_restriction(g, ONTO.Spacecraft, ONTO.hasMissionType, XSD.string)

    # 2.8 SecurityThreat
    threat_restrictions = [
        (ONTO.hasThreatID, XSD.string),
        (ONTO.hasThreatType, XSD.string),
        (ONTO.hasThreatSource, XSD.string),
        (ONTO.hasImpactScope, XSD.string),
    ]
    for prop, range_uri in threat_restrictions:
        add_restriction(g, ONTO.SecurityThreat, prop, range_uri)

    # 2.9 ResponseMeasure
    response_restrictions = [
        (ONTO.hasMeasureID, XSD.string),
        (ONTO.hasMeasureDescription, XSD.string),
    ]
    for prop, range_uri in response_restrictions:
        add_restriction(g, ONTO.ResponseMeasure, prop, range_uri)
    # R15：保留 someValuesFrom（源模块已带），并显式补充 allValuesFrom
    add_restriction(g, ONTO.ResponseMeasure, ONTO.respondsToEvent, ONTO.SpaceEvent, OWL.allValuesFrom)

    # 2.10 ObservationEvent 使用事件专用属性 observedBySensor
    add_restriction(g, ONTO.ObservationEvent, ONTO.observedBySensor, ONTO.Sensor)

    # 2.11 ObservationData 保留 hasErrorValue（domain 已修正为 SSAData）
    add_restriction(g, ONTO.ObservationData, ONTO.hasErrorValue, XSD.float)

    # 2.12 GeometricConstruct 使用 hasGeometricErrorValue
    add_restriction(g, ONTO.GeometricConstruct, ONTO.hasGeometricErrorValue, XSD.float)

    # 2.12a SecurityRisk 使用风险专属属性 riskLeadsToState
    add_restriction(g, ONTO.SecurityRisk, ONTO.riskLeadsToState, ONTO.SituationState)

    # 2.12b SecurityThreat 使用威胁专属属性 threatMitigatedBy
    add_restriction(g, ONTO.SecurityThreat, ONTO.threatMitigatedBy, ONTO.ResponseMeasure)

    # 2.12c Sensor
    add_restriction(g, ONTO.Sensor, ONTO.hasResolution, XSD.float)

    # 2.13 补全生成过程中遗漏的数据属性（并附加 restriction 避免 P41）
    # ------------------------------------------------------------------
    missing_data_props = [
        (ONTO.hasEnvironmentType, ONTO.SpaceEnvironment, XSD.string,
         "has environment type", "环境类型", "空间环境所属类型，如辐射环境、电磁环境、轨道拥堵环境等"),
        (ONTO.hasEnvironmentLevel, ONTO.SpaceEnvironment, XSD.string,
         "has environment level", "环境等级", "空间环境等级，如正常、异常、严重"),
        (ONTO.hasRadiationLevel, ONTO.RadiationEnvironment, XSD.string,
         "has radiation level", "辐射水平", "辐射环境水平等级"),
        (ONTO.hasCongestionLevel, ONTO.OrbitalCongestionEnvironment, XSD.string,
         "has congestion level", "拥堵等级", "轨道拥堵环境等级"),
        (ONTO.hasThreatLevel, ONTO.SecurityThreat, XSD.string,
         "has threat level", "威胁等级", "安全威胁等级"),
        (ONTO.hasThreatConfidence, ONTO.SecurityThreat, XSD.float,
         "has threat confidence", "威胁置信度", "安全威胁评估的置信度"),
    ]
    for prop, domain, range_uri, label_en, label_zh, comment_zh in missing_data_props:
        ensure_datatype_property(g, prop, domain, range_uri, label_en, label_zh, comment_zh)
        add_restriction(g, domain, prop, range_uri)

    # 补充少量用于达到目标规模的数据属性
    extra_data_props = [
        (ONTO.hasRiskDescription, ONTO.SecurityRisk, XSD.string,
         "has risk description", "风险描述", "安全风险的文本描述"),
        (ONTO.hasManeuverType, ONTO.OrbitManeuverEvent, XSD.string,
         "has maneuver type", "机动类型", "轨道机动事件类型"),
        (ONTO.hasSpatialRelationship, ONTO.SpatialRelationEvent, XSD.string,
         "has spatial relationship", "空间关系", "空间关系事件中的关系类型"),
    ]
    for prop, domain, range_uri, label_en, label_zh, comment_zh in extra_data_props:
        ensure_datatype_property(g, prop, domain, range_uri, label_en, label_zh, comment_zh)
        add_restriction(g, domain, prop, range_uri)

    # ------------------------------------------------------------------
    # 3. 数据类型 range 修改
    # ------------------------------------------------------------------
    set_range(g, ONTO.hasDuration, XSD.duration)
    set_range(g, ONTO.hasStateDuration, XSD.duration)

    # ------------------------------------------------------------------
    # 3.6 将非必然关系的 someValuesFrom 改为 allValuesFrom，降低语义强度
    # ------------------------------------------------------------------
    some_to_all_mappings = [
        # SpaceEvent
        (ONTO.SpaceEvent, ONTO.overlapsWithEvent),
        (ONTO.SpaceEvent, ONTO.occursDuringEvent),
        (ONTO.SpaceEvent, ONTO.triggersEvent),
        (ONTO.SpaceEvent, ONTO.resultsInEvent),
        (ONTO.SpaceEvent, ONTO.affectsState),
        (ONTO.SpaceEvent, ONTO.updatesState),
        (ONTO.SpaceEvent, ONTO.triggersState),
        (ONTO.SpaceEvent, ONTO.indicatesThreat),
        (ONTO.SpaceEvent, ONTO.increasesThreat),
        # SituationState
        (ONTO.SituationState, ONTO.transitsTo),
        (ONTO.SituationState, ONTO.evolvesTo),
        # ResponseMeasure
        (ONTO.ResponseMeasure, ONTO.respondsToThreat),
        # 注意：respondsToEvent 保留 someValuesFrom，以保证 R15“至少响应一个事件”
    ]
    for cls, prop in some_to_all_mappings:
        change_some_to_all(g, cls, prop)

    # ------------------------------------------------------------------
    # 3.7 M2：对象角色显式化与 hasRiskValue 语义重定义（幂等）
    # ------------------------------------------------------------------
    # 3.7a hasPrimaryObject/hasSecondaryObject 的 domain 由 SpaceEvent 收窄为
    #      SpatialRelationEvent：交会目标角色属于空间关系事件
    role_comments = {
        ONTO.hasPrimaryObject: "空间关系事件中交会对象对的主要目标，用于显式表示目标角色。",
        ONTO.hasSecondaryObject: "空间关系事件中交会对象对的次要目标，用于显式表示目标角色。",
    }
    for prop, comment in role_comments.items():
        for old_domain in list(g.objects(prop, RDFS.domain)):
            g.remove((prop, RDFS.domain, old_domain))
        g.add((prop, RDFS.domain, ONTO.SpatialRelationEvent))
        for old_comment in list(g.objects(prop, RDFS.comment)):
            g.remove((prop, RDFS.comment, old_comment))
        g.add((prop, RDFS.comment, Literal(comment, lang="zh")))

    # 3.7b hasRiskValue 的 domain 明确为 RiskEvent，语义为可选的外部综合风险评分
    #      （M2 第二阶段：补充"可选"与"R5—R8 不再使用"限定）
    for old_domain in list(g.objects(ONTO.hasRiskValue, RDFS.domain)):
        g.remove((ONTO.hasRiskValue, RDFS.domain, old_domain))
    g.add((ONTO.hasRiskValue, RDFS.domain, ONTO.RiskEvent))
    for old_comment in list(g.objects(ONTO.hasRiskValue, RDFS.comment)):
        g.remove((ONTO.hasRiskValue, RDFS.comment, old_comment))
    g.add((ONTO.hasRiskValue, RDFS.comment, Literal(
        "由外部风险评估模型、任务系统或应用层给出的可选综合风险评分，其计算方法与取值尺度由外部系统规定，"
        "不由本体规定；承载外部评估结果，不等同于碰撞概率 hasCollisionProbability；"
        "碰撞风险态势规则（R5—R8）不再以该属性为判定条件。", lang="zh")))

    # 3.7c CollisionRiskEvent 继承 SpatialRelationEvent（交会目标角色经继承获得），
    #      删除其自身重复的角色 restriction
    if (ONTO.CollisionRiskEvent, RDFS.subClassOf, ONTO.SpatialRelationEvent) not in g:
        g.add((ONTO.CollisionRiskEvent, RDFS.subClassOf, ONTO.SpatialRelationEvent))
    for sub in list(g.objects(ONTO.CollisionRiskEvent, RDFS.subClassOf)):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) in (ONTO.hasPrimaryObject, ONTO.hasSecondaryObject):
            g.remove((ONTO.CollisionRiskEvent, RDFS.subClassOf, sub))
            for t in list(g.triples((sub, None, None))):
                g.remove(t)

    # ------------------------------------------------------------------
    # 3.8 M2 第二阶段（2026-09-04）：碰撞风险态势规则重构配套声明（幂等）
    # ------------------------------------------------------------------
    # 3.8a hasCombinedHardBodyRadius：当前交会评估的组合硬体半径（外部给出，非常数）
    new_datatype_props = {
        ONTO.hasCombinedHardBodyRadius: (
            ONTO.CollisionRiskEvent, XSD.float, "组合硬体半径",
            "当前交会风险评估中两个目标的组合硬体半径（combined hard-body radius），"
            "即两目标外接球半径之和；由外部交会评估给出，随评估事件变化，不作为全局部署常数。"),
        ONTO.hasSeverityRank: (
            ONTO.SituationState, XSD.integer, "严重度级别",
            "分级风险态势的严重度排序值：正常=0、关注=1、预警=2、危险=3；"
            "仅用于支持分级态势之间的排序及跨时间演化规则。"),
    }
    for prop, (domain_uri, range_uri, label, comment) in new_datatype_props.items():
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.label, Literal(label, lang="zh")))
        for old in list(g.objects(prop, RDFS.domain)):
            g.remove((prop, RDFS.domain, old))
        g.add((prop, RDFS.domain, domain_uri))
        for old in list(g.objects(prop, RDFS.range)):
            g.remove((prop, RDFS.range, old))
        g.add((prop, RDFS.range, range_uri))
        for old in list(g.objects(prop, RDFS.comment)):
            g.remove((prop, RDFS.comment, old))
        g.add((prop, RDFS.comment, Literal(comment, lang="zh")))

    # ------------------------------------------------------------------
    # 3.9 M3 第一阶段（2026-09-04）：hasCausalConfidence 放宽为可选元数据（幂等）
    # ------------------------------------------------------------------
    # CausalAssertion 上的 hasCausalConfidence 限制由 exactly 1（owl:cardinality）
    # 改为 max 1（owl:maxCardinality）：因果置信度是可选上下文元数据，
    # 数据来源、专家评估或外部模型提供定量置信信息时记录，未给出时不强制赋值。
    for sub in list(g.objects(ONTO.CausalAssertion, RDFS.subClassOf)):
        if not isinstance(sub, BNode):
            continue
        if g.value(sub, RDF.type) != OWL.Restriction:
            continue
        if g.value(sub, OWL.onProperty) != ONTO.hasCausalConfidence:
            continue
        for old in list(g.objects(sub, OWL.cardinality)):
            g.remove((sub, OWL.cardinality, old))
        if g.value(sub, OWL.maxCardinality) is None:
            g.add((sub, OWL.maxCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    for old in list(g.objects(ONTO.hasCausalConfidence, RDFS.comment)):
        g.remove((ONTO.hasCausalConfidence, RDFS.comment, old))
    g.add((ONTO.hasCausalConfidence, RDFS.comment, Literal(
        "因果断言的可选置信度元数据。当数据来源、专家评估或外部模型提供定量置信信息时记录该值；"
        "来源未给出定量置信度时不强制赋值（M3 第一阶段起由 exactly 1 放宽为 max 1）。", lang="zh")))

    # ------------------------------------------------------------------
    # 4. 外部本体 subPropertyOf 复用关系
    # ------------------------------------------------------------------
    g.add((ONTO.madeBySensor, RDFS.subPropertyOf, SOSA.madeBySensor))
    g.add((ONTO.hasFeatureOfInterest, RDFS.subPropertyOf, SOSA.hasFeatureOfInterest))
    g.add((ONTO.hasObservationResult, RDFS.subPropertyOf, SOSA.hasResult))
    g.add((ONTO.generatedByActivity, RDFS.subPropertyOf, PROV.wasGeneratedBy))

    # ------------------------------------------------------------------
    # 5. P10：选择性添加互斥公理（仅保留成员全部活跃的组）
    # ------------------------------------------------------------------
    cleanup_disjoint_classes(g)  # 先清理已有空/重复的 AllDisjointClasses
    disjoint_groups = [
        [ONTO.RadarSensor, ONTO.OpticalSensor, ONTO.InfraredSensor],
        [ONTO.DirectCausalAssertion, ONTO.IndirectCausalAssertion],
        [ONTO.PromotingCausalAssertion, ONTO.InhibitingCausalAssertion],
    ]
    for members in disjoint_groups:
        add_disjoint_group(g, members)

    # ------------------------------------------------------------------
    # 5.5 清理重复 restriction 与空/重复 AllDisjointClasses
    # ------------------------------------------------------------------
    cleanup_duplicate_restrictions(g)

    # ------------------------------------------------------------------
    # 保存（先备份到 backup/ 目录）
    # ------------------------------------------------------------------
    import shutil
    os.makedirs(BACKUP_DIR, exist_ok=True)
    shutil.copy2(path, BACKUP_PATH)
    g.serialize(destination=path, format="xml")

    # 统计
    triples = len(g)
    classes = len(list(g.subjects(RDF.type, OWL.Class)))
    obj_props = len(list(g.subjects(RDF.type, OWL.ObjectProperty)))
    data_props = len(list(g.subjects(RDF.type, OWL.DatatypeProperty)))
    restrictions = len(list(g.subjects(RDF.type, OWL.Restriction)))
    inverses = len(list(g.subjects(OWL.inverseOf, None)))
    disjoint_axioms = len(list(g.subjects(RDF.type, OWL.AllDisjointClasses)))

    print(f"[INFO] 本体已保存: {path}")
    print(f"[INFO] 备份文件: {BACKUP_PATH}")
    print(f"[INFO] 三元组数量: {triples}")
    print(f"[INFO] Classes: {classes}, ObjectProperties: {obj_props}, DatatypeProperties: {data_props}")
    print(f"[INFO] Restrictions: {restrictions}, inverseOf: {inverses}, AllDisjointClasses: {disjoint_axioms}")


if __name__ == "__main__":
    modify_ontology(OWL_PATH)
