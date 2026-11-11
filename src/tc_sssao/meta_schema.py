"""元模式(Meta-Schema)基础设施

定义本体的元节点与元关系,以 Python dataclass 封装,
供 OWL/RDF XML 导出器使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------- 元节点 dataclass ----------

@dataclass(frozen=True)
class OntologyNamespace:
    """本体命名空间:domain / temporal / causal / meta。"""
    name: str
    description: str = ""


@dataclass(frozen=True)
class OntologyProperty:
    """数据属性定义,挂在 OntologyClass 上。"""
    name: str
    datatype: str  # 例如 string / integer / float / datetime / boolean
    name_zh: str = ""
    description: str = ""
    required: bool = False
    domain: str = ""  # 定义域类名,空字符串表示 owl:Thing


@dataclass(frozen=True)
class OntologyRestriction:
    """类限制（支持 owl:someValuesFrom / allValuesFrom / cardinality / hasValue 系列）。

    hasValue 模式下 target 为字面量字符串（owl:hasValue 要求字面量或个体），
    restriction_type 设为 "hasValue"。
    """
    property_name: str   # 对象属性或数据属性名
    target: str          # 目标类名 / xsd 数据类型名 / 字面量（hasValue 模式）
    restriction_type: str = "someValuesFrom"
    min_cardinality: int | None = None
    max_cardinality: int | None = None
    cardinality: int | None = None
    # hasValue 字面量（restriction_type == "hasValue" 时使用）
    has_value: str | None = None


@dataclass
class OntologyClass:
    """本体类(概念)。"""
    name_en: str
    name_zh: str
    description: str = ""
    namespace: str = "domain"
    parents: list[str] = field(default_factory=list)  # 父类 name_en 列表，支持多重继承
    equivalent_to: list[str] = field(default_factory=list)  # 等价于所列类的交集（owl:intersectionOf）
    properties: list[OntologyProperty] = field(default_factory=list)
    restrictions: list[OntologyRestriction] = field(default_factory=list)


@dataclass(frozen=True)
class OntologyRelation:
    """对象属性/关系类型定义,带 domain / range。"""
    name: str            # 例如 THREATENED_BY
    name_zh: str
    domain: str          # 定义域类名 name_en
    range: str = ""      # 值域类名 name_en，空字符串表示不限制
    description: str = ""
    namespace: str = "domain"
    inverse_of: Optional[str] = None
    symmetric: bool = False
    transitive: bool = False
    irreflexive: bool = False
    asymmetric: bool = False
    sub_property_of: Optional[str] = None
    deprecated: bool = False


@dataclass(frozen=True)
class OntologyAxiom:
    """时间-因果联合公理。

    描述约束规则的类别、目标类、输入属性、输出关系、自然语言规则与形式化表达。
    """
    axiom_id: str         # 例如 A1
    title_zh: str
    statement: str        # 形式化或半形式化表述
    description: str
    governs_classes: tuple[str, ...] = ()    # 受此公理约束的类 name_en
    governs_relations: tuple[str, ...] = ()  # 受此公理约束的关系 name
    category: str = "time-causal"
    implementation_status: str = "specification_only"  # specification_only / owl_restriction / shacl_sparql
    rule_category: str = ""       # StructuralRestriction / ValidationRule / InferenceRule
    target_class: str = ""
    input_properties: str = ""
    output_relation: str = ""
    validation_severity: str = ""
    natural_language_rule: str = ""
    formal_expression: str = ""
    restrictions: tuple[OntologyRestriction, ...] = ()  # 类限制（用于 Protégé Description 展示）


# ---------- 命名空间常量 ----------

NS_META = OntologyNamespace(
    name="meta",
    description="元本体命名空间:容纳本体自描述节点。",
)
NS_DOMAIN = OntologyNamespace(
    name="domain",
    description="太空安全领域命名空间:容纳 SpaceObject/Threat/Event 等领域类。",
)
NS_TEMPORAL = OntologyNamespace(
    name="temporal",
    description="时间维度命名空间:基于 OWL-Time 与 Allen 时间代数。",
)
NS_CAUSAL = OntologyNamespace(
    name="causal",
    description="因果维度命名空间:容纳因果关系类型、因果链与前置条件。",
)

ALL_NAMESPACES: tuple[OntologyNamespace, ...] = (
    NS_META,
    NS_DOMAIN,
    NS_TEMPORAL,
    NS_CAUSAL,
)
