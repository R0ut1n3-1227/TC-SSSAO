"""导出本体库为标准 OWL/RDF 格式 (Protege 兼容版)

生成符合 OWL-DL 规范的 RDF/XML 文件，可直接在 Protege 中打开。
复用 OWL-Time 表达时间，复用 PROV-O 表达数据来源。
"""
from __future__ import annotations

import sys
from pathlib import Path

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE_DIR = _find_project_root(Path(__file__).parent)
sys.path.insert(0, str(BASE_DIR / "src"))

from tc_sssao.domain_layer import ALL_CLASSES, OBJECT_PROPERTIES
from tc_sssao.axioms import AXIOMS


# ---------- OWL 命名空间 ----------
NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "onto": "https://w3id.org/tc-sssao#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "time": "http://www.w3.org/2006/time#",
    "prov": "http://www.w3.org/ns/prov#",
    "sosa": "http://www.w3.org/ns/sosa/",
    "geo": "http://www.opengis.net/ont/geosparql#",
    "ssn": "http://www.w3.org/ns/ssn/",
}


EXTERNAL_NS = {
    "time": "http://www.w3.org/2006/time#",
    "prov": "http://www.w3.org/ns/prov#",
    "sosa": "http://www.w3.org/ns/sosa/",
    "geo": "http://www.opengis.net/ont/geosparql#",
    "ssn": "http://www.w3.org/ns/ssn/",
}


# ---------- 注释属性 (Annotation Properties) ----------
ANNOTATION_PROPERTIES = (
    # 外部本体复用与映射（自定义属性）
    ("reusedOntology", "复用本体"),
    ("mappedToExternalTerm", "映射到外部术语"),
    # R1–R18 规则元数据
    ("implementationStatus", "实现状态"),
    ("ruleCategory", "规则类别"),
    ("targetClass", "目标类"),
    ("inputProperties", "输入属性"),
    ("outputRelation", "输出关系"),
    ("validationSeverity", "验证严重级别"),
    ("naturalLanguageRule", "自然语言规则"),
    ("formalExpression", "形式化表达"),
    # Core/Extension 分层
    ("modelLayer", "模型分层"),
)

# 外部注释属性：显式声明类型以满足 OWL 2 DL
EXTERNAL_ANNOTATION_PROPERTIES = (
    ("dc", "creator"),
    ("dc", "description"),
    ("dc", "title"),
    ("dc", "type"),
    ("skos", "notation"),
)

# Extension 类名集合（与 extensions.py 完全对齐）
EXTENSION_CLASS_NAMES: frozenset[str] = frozenset({
    "DirectCausalAssertion",
    "IndirectCausalAssertion",
    "PromotingCausalAssertion",
    "InhibitingCausalAssertion",
    "RiskEscalationTransition",
    "RiskReductionTransition",
    "ThreatEscalationTransition",
    "RecoveryTransition",
    "CyberThreat",
    "CyberSecurityRisk",
    "TrackingSystem",
    "SurveillanceSystem",
    "MitigationMeasure",
    "WarningMeasure",
})


def qname(prefix: str, local: str) -> str:
    return f"{NS[prefix]}{local}"


def esc(s: str) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def resolve_uri(ref: str, all_classes: set[str]) -> str:
    """将类名引用解析为完整 URI。支持内部类和外部 qname（如 time:Instant）。"""
    if not ref:
        return ""
    if ":" in ref:
        prefix, local = ref.split(":", 1)
        if prefix in NS:
            return f"{NS[prefix]}{local}"
        raise ValueError(f"Unknown namespace prefix in reference: {ref}")
    if ref in all_classes:
        return qname("onto", ref)
    return ""


def resolve_restriction_target(target: str, all_classes: set[str]) -> str:
    """解析类限制中的目标：内部类返回 onto:Class；已知 xsd 数据类型返回 xsd:Type；geo:wktLiteral 返回 geo:wktLiteral。"""
    if not target:
        return ""
    if target in all_classes:
        return qname("onto", target)
    if target in {"string", "integer", "int", "float", "double", "boolean", "dateTime", "time", "date", "duration"}:
        return qname("xsd", target)
    if target == "geo:wktLiteral":
        return qname("geo", "wktLiteral")
    return ""


def collect_ontology():
    classes = []
    for cls in ALL_CLASSES:
        classes.append({
            "name_en": cls.name_en,
            "name_zh": cls.name_zh,
            "description": cls.description,
            "parents": getattr(cls, "parents", [cls.parent] if getattr(cls, "parent", None) else []),
            "equivalent_to": getattr(cls, "equivalent_to", []),
            "restrictions": [
                {
                    "property_name": r.property_name,
                    "target": r.target,
                    "restriction_type": r.restriction_type,
                    "min_cardinality": getattr(r, "min_cardinality", None),
                    "max_cardinality": getattr(r, "max_cardinality", None),
                    "cardinality": getattr(r, "cardinality", None),
                    "has_value": getattr(r, "has_value", None),
                }
                for r in cls.restrictions
            ],
        })

    relations = []
    for rel in OBJECT_PROPERTIES:
        relations.append({
            "name": rel.name,
            "name_zh": rel.name_zh,
            "description": rel.description,
            "domain": rel.domain,
            "range": rel.range,
            "symmetric": rel.symmetric,
            "transitive": rel.transitive,
            "irreflexive": getattr(rel, "irreflexive", False),
            "asymmetric": getattr(rel, "asymmetric", False),
            "sub_property_of": getattr(rel, "sub_property_of", None),
            "inverse_of": rel.inverse_of,
            "deprecated": getattr(rel, "deprecated", False),
        })

    properties = []
    seen = set()
    for cls in ALL_CLASSES:
        for p in cls.properties:
            if p.name not in seen:
                seen.add(p.name)
                properties.append({
                    "name": p.name,
                    "datatype": p.datatype,
                    "name_zh": p.name_zh,
                    "description": p.description,
                    "domain": getattr(p, "domain", ""),
                })

    axioms = [{
        "axiom_id": ax.axiom_id,
        "title_zh": ax.title_zh,
        "statement": ax.statement,
        "description": ax.description,
        "category": ax.category,
        "implementation_status": getattr(ax, "implementation_status", "specification_only"),
        "rule_category": getattr(ax, "rule_category", ""),
        "target_class": getattr(ax, "target_class", ""),
        "input_properties": getattr(ax, "input_properties", ""),
        "output_relation": getattr(ax, "output_relation", ""),
        "validation_severity": getattr(ax, "validation_severity", ""),
        "natural_language_rule": getattr(ax, "natural_language_rule", ""),
        "formal_expression": getattr(ax, "formal_expression", ""),
        "governs_classes": getattr(ax, "governs_classes", ()),
        "governs_relations": getattr(ax, "governs_relations", ()),
        "restrictions": [
            {
                "property_name": r.property_name,
                "target": r.target,
                "restriction_type": r.restriction_type,
                "min_cardinality": getattr(r, "min_cardinality", None),
                "max_cardinality": getattr(r, "max_cardinality", None),
                "cardinality": getattr(r, "cardinality", None),
            }
            for r in getattr(ax, "restrictions", ())
        ],
    } for ax in AXIOMS]

    return {
        "classes": classes,
        "relations": relations,
        "properties": properties,
        "axioms": axioms,
    }


def generate_owl(data: dict, output_path: Path):
    lines = []
    ind = "    "
    i2 = ind * 2
    i3 = ind * 3

    all_classes = {c["name_en"] for c in data["classes"]}

    # ---------- 头部 ----------
    lines.append('<rdf:RDF')
    lines.append(f'    xmlns="{NS["onto"]}"')
    for prefix, uri in NS.items():
        lines.append(f'    xmlns:{prefix}="{uri}"')
    lines.append(f'    xml:base="{NS["onto"]}"')
    lines.append('>')
    lines.append('')

    # ---------- Ontology 声明（M4：与 ontology/tc_sssao.owl 权威头部保持一致）----------
    onto_iri = NS["onto"].rstrip("#")  # https://w3id.org/tc-sssao
    # 本体语义版本声明（owl:versionInfo / versionIRI）随本体冻结，属科学内容；
    # 项目已无工程版本号文件（2026-09-13 起取消工程版本管理）
    version = "1.0.0"
    lines.append(f'{ind}<owl:Ontology rdf:about="{onto_iri}">')
    lines.append(f'{i2}<owl:versionInfo>{version}</owl:versionInfo>')
    lines.append(f'{i2}<owl:versionIRI rdf:resource="{onto_iri}/{version}"/>')
    lines.append(f'{i2}<dcterms:title>TC-SSSAO: Temporal-Causal Space Security Situational Awareness Ontology</dcterms:title>')
    lines.append(f'{i2}<dcterms:title xml:lang="zh">TC-SSSAO：时序—因果太空安全态势感知本体</dcterms:title>')
    lines.append(f'{i2}<dcterms:description xml:lang="en">OWL 2 ontology and SHACL-SPARQL rule set for representing and reasoning over space-security situational-awareness knowledge: space objects, orbits, observation systems and data, space events, temporal relations, reified causal assertions, graded situation states, threats, risks, and response measures.</dcterms:description>')
    lines.append(f'{i2}<dcterms:description xml:lang="zh">面向太空安全态势感知知识的 OWL 2 本体与 SHACL-SPARQL 规则集，统一组织空间目标、轨道、观测系统与数据、空间事件、时序关系、实体化因果断言、分级态势状态、威胁、风险与响应措施。</dcterms:description>')
    lines.append(f'{i2}<dcterms:created>2026-07</dcterms:created>')
    lines.append(f'{i2}<dcterms:modified rdf:datatype="http://www.w3.org/2001/XMLSchema#date">2026-09-04</dcterms:modified>')
    lines.append(f'{i2}<dcterms:license rdf:resource="https://opensource.org/license/mit"/>')
    lines.append(f'{i2}<rdfs:comment xml:lang="en">Canonical ontology identifier. The IRI is used as the ontology identifier for this release; resolution will be configured when the public repository is published.</rdfs:comment>')
    lines.append(f'{i2}<rdfs:comment xml:lang="zh">规范本体标识符。当前发布包使用该 IRI 作为本体标识；解析地址将在公开仓库发布后同步配置。</rdfs:comment>')
    lines.append(f'{ind}</owl:Ontology>')
    lines.append('')

    # ---------- 类定义 (Classes) ----------
    lines.append(f'{ind}<!-- ========== Classes ({len(data["classes"])}) ========== -->')
    for c in data["classes"]:
        name = c["name_en"]
        parents = c.get("parents", [])
        if not parents:
            parents = [c["parent"]] if c.get("parent") else []
        equivalent_to = c.get("equivalent_to", [])
        lines.append(f'{ind}<owl:Class rdf:about="{qname("onto", name)}">')
        lines.append(f'{i2}<rdfs:label xml:lang="zh">{esc(c.get("name_zh", ""))}</rdfs:label>')
        if c.get("description"):
            lines.append(f'{i2}<rdfs:comment xml:lang="zh">{esc(c["description"])}</rdfs:comment>')
        # Core / Extension 分层标注
        if c["name_en"] in EXTENSION_CLASS_NAMES:
            lines.append(f'{i2}<onto:modelLayer rdf:datatype="{qname("xsd", "string")}">extension</onto:modelLayer>')
        else:
            lines.append(f'{i2}<onto:modelLayer rdf:datatype="{qname("xsd", "string")}">core</onto:modelLayer>')
        for parent in parents:
            if parent and parent in all_classes:
                lines.append(f'{i2}<rdfs:subClassOf rdf:resource="{qname("onto", parent)}"/>')
        # owl:equivalentClass + owl:intersectionOf
        if equivalent_to and all(p in all_classes for p in equivalent_to):
            lines.append(f'{i2}<owl:equivalentClass>')
            lines.append(f'{i3}<owl:Class>')
            lines.append(f'{i3}{ind}<owl:intersectionOf rdf:parseType="Collection">')
            for p in equivalent_to:
                lines.append(f'{i3}{i2}<owl:Class rdf:about="{qname("onto", p)}"/>')
            lines.append(f'{i3}{ind}</owl:intersectionOf>')
            lines.append(f'{i3}</owl:Class>')
            lines.append(f'{i2}</owl:equivalentClass>')
        for r in c.get("restrictions", []):
            prop_name = r.get("property_name", "")
            prop_uri = qname("onto", prop_name) if prop_name else ""
            target_uri = resolve_restriction_target(r.get("target", ""), all_classes)
            if not prop_uri or not target_uri:
                continue
            restriction_type = r.get("restriction_type", "someValuesFrom")
            lines.append(f'{i2}<rdfs:subClassOf>')
            lines.append(f'{i3}<owl:Restriction>')
            lines.append(f'{i3}{ind}<owl:onProperty rdf:resource="{prop_uri}"/>')
            if restriction_type in ("someValuesFrom", "allValuesFrom"):
                lines.append(f'{i3}{ind}<owl:{restriction_type} rdf:resource="{target_uri}"/>')
            elif restriction_type == "hasValue":
                # owl:hasValue 用于数据属性时值为 typed literal
                hv = r.get("has_value", "")
                lines.append(f'{i3}{ind}<owl:hasValue rdf:datatype="{qname("xsd", "integer")}">{hv}</owl:hasValue>')
            elif restriction_type in ("minCardinality", "maxCardinality", "cardinality"):
                card_value = r.get("min_cardinality") or r.get("max_cardinality") or r.get("cardinality")
                if card_value is None:
                    lines.append(f'{i3}{ind}</owl:Restriction>')
                    lines.append(f'{i2}</rdfs:subClassOf>')
                    continue
                has_filler = r.get("target") in all_classes
                # 带类 filler 的使用 qualified cardinality；数据属性使用无 filler 的基数
                tag_map = {
                    "minCardinality": "minQualifiedCardinality" if has_filler else "minCardinality",
                    "maxCardinality": "maxQualifiedCardinality" if has_filler else "maxCardinality",
                    "cardinality": "qualifiedCardinality" if has_filler else "cardinality",
                }
                tag = tag_map[restriction_type]
                lines.append(f'{i3}{ind}<owl:{tag} rdf:datatype="{qname("xsd", "nonNegativeInteger")}">{card_value}</owl:{tag}>')
                if has_filler:
                    lines.append(f'{i3}{ind}<owl:onClass rdf:resource="{target_uri}"/>')
            lines.append(f'{i3}</owl:Restriction>')
            lines.append(f'{i2}</rdfs:subClassOf>')
        lines.append(f'{ind}</owl:Class>')
        lines.append('')

    # ---------- 成对 disjointWith 声明 ----------
    disjoint_pairs_map = {
        # 综合态势状态互斥（M2 四态模型）
        "NormalSituationState": ["AttentionSituationState", "WarningSituationState", "DangerousSituationState"],
        "AttentionSituationState": ["WarningSituationState", "DangerousSituationState"],
        "WarningSituationState": ["DangerousSituationState"],
    }
    lines.append(f'{ind}<!-- ========== Disjoint Classes (owl:disjointWith) ========== -->')
    for source, targets in disjoint_pairs_map.items():
        if source not in all_classes:
            continue
        lines.append(f'{ind}<rdf:Description rdf:about="{qname("onto", source)}">')
        for target in targets:
            if target in all_classes:
                lines.append(f'{i2}<owl:disjointWith rdf:resource="{qname("onto", target)}"/>')
        lines.append(f'{ind}</rdf:Description>')
        lines.append('')

    # ---------- AllDisjointClasses ----------
    disjoint_groups = [
        ["NormalSituationState", "AttentionSituationState", "WarningSituationState", "DangerousSituationState"],
    ]
    lines.append(f'{ind}<!-- ========== AllDisjointClasses ========== -->')
    for group in disjoint_groups:
        valid = [g for g in group if g in all_classes]
        if len(valid) >= 2:
            lines.append(f'{ind}<rdf:Description>')
            lines.append(f'{i2}<rdf:type rdf:resource="{qname("owl", "AllDisjointClasses")}"/>')
            lines.append(f'{i2}<owl:members rdf:parseType="Collection">')
            for cls_name in valid:
                lines.append(f'{i3}<rdf:Description rdf:about="{qname("onto", cls_name)}"/>')
            lines.append(f'{i2}</owl:members>')
            lines.append(f'{ind}</rdf:Description>')
            lines.append('')

    # ---------- 注释属性 (Annotation Properties) ----------
    lines.append(f'{ind}<!-- ========== Annotation Properties ({len(ANNOTATION_PROPERTIES) + len(EXTERNAL_ANNOTATION_PROPERTIES)}) ========== -->')
    for name, name_zh in ANNOTATION_PROPERTIES:
        lines.append(f'{ind}<owl:AnnotationProperty rdf:about="{qname("onto", name)}">')
        lines.append(f'{i2}<rdfs:label xml:lang="zh">{esc(name_zh)}</rdfs:label>')
        lines.append(f'{ind}</owl:AnnotationProperty>')
        lines.append('')
    for prefix, local in EXTERNAL_ANNOTATION_PROPERTIES:
        lines.append(f'{ind}<owl:AnnotationProperty rdf:about="{qname(prefix, local)}"/>')
        lines.append('')

    # ---------- 显式声明被复用的外部对象/数据属性（满足 OWL 2 DL） ----------
    lines.append(f'{ind}<!-- ========== Reused External Properties ========== -->')
    for prefix, local in (("sosa", "madeBySensor"), ("sosa", "hasFeatureOfInterest"),
                          ("sosa", "hasResult"), ("prov", "wasGeneratedBy")):
        lines.append(f'{ind}<owl:ObjectProperty rdf:about="{qname(prefix, local)}"/>')
        lines.append('')
    lines.append(f'{ind}<owl:DatatypeProperty rdf:about="{qname("geo", "asWKT")}"/>')
    lines.append('')

    # ---------- 复用映射声明 (Reuse Mappings) ----------
    reuse_mappings = {
        # 类级复用（仅使用注释属性或自定义映射属性，避免将 skos:closeMatch 当作 AnnotationProperty 使用）
        "SpaceEvent": [
            ("rdfs:seeAlso", "time:Instant"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "ObservationData": [
            ("rdfs:seeAlso", "sosa:Observation"),
            ("onto:reusedOntology", "http://www.w3.org/ns/sosa/"),
        ],
        "Sensor": [
            ("rdfs:seeAlso", "sosa:Sensor"),
            ("onto:mappedToExternalTerm", "sosa:Sensor"),
        ],
        "ObservationSystem": [
            ("rdfs:seeAlso", "sosa:Platform"),
            ("onto:reusedOntology", "http://www.w3.org/ns/sosa/"),
        ],
        "Orbit": [
            ("rdfs:seeAlso", "geo:SpatialObject"),
            ("onto:reusedOntology", "http://www.opengis.net/ont/geosparql#"),
        ],
        "SpaceObject": [
            ("rdfs:seeAlso", "sosa:FeatureOfInterest"),
            ("onto:mappedToExternalTerm", "sosa:FeatureOfInterest"),
        ],
        "SituationState": [
            ("rdfs:seeAlso", "prov:Entity"),
            ("onto:reusedOntology", "http://www.w3.org/ns/prov#"),
        ],
        # 属性级复用 — 时间
        "hasOccurrenceTime": [
            ("rdfs:seeAlso", "time:hasTime"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "hasStartTime": [
            ("rdfs:seeAlso", "time:hasBeginning"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "hasEndTime": [
            ("rdfs:seeAlso", "time:hasEnd"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "hasDuration": [
            ("rdfs:seeAlso", "time:hasXSDDuration"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "hasStateStartTime": [
            ("rdfs:seeAlso", "time:hasBeginning"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        "hasStateEndTime": [
            ("rdfs:seeAlso", "time:hasEnd"),
            ("onto:reusedOntology", "http://www.w3.org/2006/time#"),
        ],
        # 属性级复用 — 观测与溯源
        "hasDataSource": [
            ("rdfs:seeAlso", "prov:wasAttributedTo"),
            ("onto:reusedOntology", "http://www.w3.org/ns/prov#"),
        ],
        "generatedBy": [
            ("rdfs:seeAlso", "prov:wasGeneratedBy"),
            ("onto:reusedOntology", "http://www.w3.org/ns/prov#"),
        ],
    }
    # 校验实体存在：类名必须在 all_classes 中，属性名必须在对象属性或数据属性集合中
    data_property_names = {p["name"] for p in data["properties"]}
    object_property_names = {r["name"] for r in data["relations"]}
    valid_entities = all_classes | data_property_names | object_property_names
    lines.append(f'{ind}<!-- ========== External Ontology Reuse Mappings ========== -->')
    for entity_name, annotations in reuse_mappings.items():
        if entity_name not in valid_entities:
            continue
        lines.append(f'{ind}<rdf:Description rdf:about="{qname("onto", entity_name)}">')
        for prop_qname, target_ref in annotations:
            if target_ref.startswith("http://") or target_ref.startswith("https://"):
                target_uri = target_ref  # 复用本体的规范 IRI 原样输出
            elif ":" in target_ref:
                target_uri = resolve_uri(target_ref, all_classes)
            else:
                target_uri = target_ref
            prop_local = prop_qname.split(":", 1)[-1]
            if prop_qname.startswith("onto:"):
                prop_tag = f'onto:{prop_local}'
            elif prop_qname.startswith("rdfs:"):
                prop_tag = f'rdfs:{prop_local}'
            elif prop_qname.startswith("skos:"):
                prop_tag = f'skos:{prop_local}'
            else:
                prop_tag = prop_local
            if target_uri:
                lines.append(f'{i2}<{prop_tag} rdf:resource="{target_uri}"/>')
        lines.append(f'{ind}</rdf:Description>')
        lines.append('')

    # ---------- 对象属性 (Object Properties) ----------
    lines.append(f'{ind}<!-- ========== Object Properties ({len(data["relations"])}) ========== -->')
    for r in data["relations"]:
        name = r["name"]
        lines.append(f'{ind}<owl:ObjectProperty rdf:about="{qname("onto", name)}">')
        lines.append(f'{i2}<rdfs:label xml:lang="zh">{esc(r.get("name_zh", ""))}</rdfs:label>')
        if r.get("description"):
            lines.append(f'{i2}<rdfs:comment xml:lang="zh">{esc(r["description"])}</rdfs:comment>')

        # domain
        domain_uri = resolve_uri(r.get("domain", ""), all_classes)
        if domain_uri:
            lines.append(f'{i2}<rdfs:domain rdf:resource="{domain_uri}"/>')
        elif r.get("domain") == "":
            lines.append(f'{i2}<rdfs:domain rdf:resource="{qname("owl", "Thing")}"/>')

        # range
        range_uri = resolve_uri(r.get("range", ""), all_classes)
        if range_uri:
            lines.append(f'{i2}<rdfs:range rdf:resource="{range_uri}"/>')

        # 属性层次: subPropertyOf
        if r.get("sub_property_of"):
            lines.append(f'{i2}<rdfs:subPropertyOf rdf:resource="{qname("onto", r["sub_property_of"])}"/>')
        if r.get("symmetric"):
            lines.append(f'{i2}<rdf:type rdf:resource="{qname("owl", "SymmetricProperty")}"/>')
        if r.get("transitive"):
            lines.append(f'{i2}<rdf:type rdf:resource="{qname("owl", "TransitiveProperty")}"/>')
        if r.get("irreflexive"):
            lines.append(f'{i2}<rdf:type rdf:resource="{qname("owl", "IrreflexiveProperty")}"/>')
        if r.get("asymmetric"):
            lines.append(f'{i2}<rdf:type rdf:resource="{qname("owl", "AsymmetricProperty")}"/>')
        if r.get("inverse_of"):
            inv_uri = resolve_uri(r["inverse_of"], all_classes)
            if inv_uri:
                lines.append(f'{i2}<owl:inverseOf rdf:resource="{inv_uri}"/>')
            else:
                lines.append(f'{i2}<owl:inverseOf rdf:resource="{qname("onto", r["inverse_of"])}"/>')
        if r.get("deprecated"):
            lines.append(f'{i2}<owl:deprecated rdf:datatype="{qname("xsd", "boolean")}">true</owl:deprecated>')
        lines.append(f'{ind}</owl:ObjectProperty>')
        lines.append('')

    # ---------- 数据类型属性 (Datatype Properties) ----------
    lines.append(f'{ind}<!-- ========== Datatype Properties ({len(data["properties"])}) ========== -->')
    dt_map = {
        "string": "string", "integer": "int", "int": "int",
        "float": "float", "decimal": "decimal",
        "double": "double", "boolean": "boolean",
        "dateTime": "dateTime", "datetime": "dateTime", "time": "time",
        # HermiT 对 xsd:date 支持不完整，统一导出为 dateTime
        "date": "dateTime",
        # 主本体保留 xsd:duration 标准语义；HermiT 兼容投影在验证脚本中临时处理
        "duration": "duration",
        # GeoSPARQL WKT 几何文字
        "geo:wktLiteral": "wktLiteral",
    }
    for p in data["properties"]:
        name = p["name"]
        dt_key = p["datatype"]
        if dt_key.startswith("xsd:"):
            dt_key = dt_key[4:]
        xsd = dt_map.get(dt_key, "string")
        lines.append(f'{ind}<owl:DatatypeProperty rdf:about="{qname("onto", name)}">')
        lines.append(f'{i2}<rdfs:label xml:lang="zh">{esc(p.get("name_zh", ""))}</rdfs:label>')
        if dt_key == "geo:wktLiteral":
            lines.append(f'{i2}<rdfs:range rdf:resource="{qname("geo", "wktLiteral")}"/>')
        else:
            lines.append(f'{i2}<rdfs:range rdf:resource="{qname("xsd", xsd)}"/>')
        prop_domain = p.get("domain", "")
        if prop_domain and prop_domain in all_classes:
            lines.append(f'{i2}<rdfs:domain rdf:resource="{qname("onto", prop_domain)}"/>')
        else:
            lines.append(f'{i2}<rdfs:domain rdf:resource="{qname("owl", "Thing")}"/>')
        if p.get("description"):
            lines.append(f'{i2}<rdfs:comment xml:lang="zh">{esc(p["description"])}</rdfs:comment>')
        lines.append(f'{ind}</owl:DatatypeProperty>')
        lines.append('')

    lines.append('</rdf:RDF>')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    print("=" * 60)
    print("Space Security Ontology -> OWL Export (Protege Compatible)")
    print("=" * 60)

    data = collect_ontology()
    total_classes = len(data['classes'])
    print(f"  本体类总数:    {total_classes}")
    print(f"    - 核心概念类: {len(data['classes'])}")
    print(f"  对象属性:      {len(data['relations'])}")
    print(f"  数据属性:      {len(data['properties'])}")

    output_dir = BASE_DIR / "ontology"
    output_path = output_dir / "tc_sssao.owl"
    generate_owl(data, output_path)

    print(f"\nOWL file saved: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    print("\nYou can now open this file in Protege.")


if __name__ == "__main__":
    main()
