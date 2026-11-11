#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OOPS! (OntOlogy Pitfall Scanner) 风格的本体质量检测脚本。

对 TC-SSSAO 太空安全态势感知本体库执行常见本体工程陷阱的静态检测，
输出结构化的 Markdown 报告。检测结果基于 OOPS! 经典陷阱分类，
但使用本地 RDFLib 解析与启发式规则实现，无需联网调用 OOPS! REST API。
"""

import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal, URIRef, BNode
from rdflib.collection import Collection


# 在 Windows 终端保证中文输出不乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OWL_PATH = os.path.join(BASE_DIR, "ontology", "tc_sssao.owl")
REPORT_DIR = os.path.join(BASE_DIR, "data", "current")
REPORT_PATH = os.path.join(REPORT_DIR, "oops_quality_report.md")

ONTO = Namespace("https://w3id.org/tc-sssao#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

# OOPS! 陷阱编号、名称、严重级别与说明
PITFALLS = {
    "P2": {
        "name": "Creating synonyms as classes",
        "level": "Minor",
        "desc": "同义词被创建为多个独立类，应使用 skos:altLabel 或 owl:equivalentClass。"
    },
    "P3": {
        "name": "Creating unconnected ontology elements",
        "level": "Minor",
        "desc": "存在未通过 subClassOf、domain、range 或 restriction 与本体其余部分连接的类或属性。"
    },
    "P8": {
        "name": "Missing annotations",
        "level": "Minor",
        "desc": "类或属性缺少 rdfs:label 或 rdfs:comment，降低可理解性。"
    },
    "P10": {
        "name": "Missing disjoint axioms between classes of a hierarchy",
        "level": "Minor",
        "desc": "同一父类下的兄弟类可能互斥，但缺少 owl:disjointWith 或 AllDisjointClasses。"
    },
    "P11": {
        "name": "Missing domain or range in properties",
        "level": "Important",
        "desc": "对象属性或数据属性缺少 rdfs:domain 或 rdfs:range。"
    },
    "P13": {
        "name": "Inverse relationships not explicitly declared in both directions",
        "level": "Minor",
        "desc": "已声明单向 owl:inverseOf，但未在另一端显式声明。虽然 owl:inverseOf 在语义上是对称的，双向显式声明可提升可读性。"
    },
    "P22": {
        "name": "Using different naming conventions in ontology",
        "level": "Minor",
        "desc": "本体中混合使用 CamelCase、snake_case、kebab-case 等命名风格。"
    },
    "P25": {
        "name": "Defining a relationship without inverse",
        "level": "Minor",
        "desc": "对象属性未声明逆关系，可能导致推理时丢失关联。"
    },
    "P29": {
        "name": "Misusing owl:DatatypeProperty",
        "level": "Critical",
        "desc": "应使用对象属性关联实体时错误使用数据属性，或数据属性 range 非 XSD/rdfs:Literal。"
    },
    "P31": {
        "name": "Defining properties without domain or range",
        "level": "Important",
        "desc": "属性既无 domain 也无 range，导致语义约束不足。"
    },
    "P34": {
        "name": "Untyped classes or properties",
        "level": "Minor",
        "desc": "资源未显式声明为 owl:Class、owl:ObjectProperty 或 owl:DatatypeProperty。"
    },
    "P37": {
        "name": "No ontology header",
        "level": "Minor",
        "desc": "缺少 owl:Ontology 头信息（标题、描述等）。"
    },
    "P38": {
        "name": "Misusing class as instance",
        "level": "Critical",
        "desc": "将类同时用作个体实例，或个体被错误声明为 owl:Class。"
    },
    "P40": {
        "name": "Subclassing disjoint classes",
        "level": "Critical",
        "desc": "某类同时继承自两个已声明 disjoint 的父类，导致本体不一致。"
    },
    "P41": {
        "name": "Defining properties without using them",
        "level": "Minor",
        "desc": "对象属性或数据属性在任何 Restriction、domain、range 之外未被使用。"
    },
    "P42": {
        "name": "Using a class as property value",
        "level": "Important",
        "desc": "将类 URI 用作数据属性的取值，或数据属性值误填为 URI 字符串。"
    },
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def local_name(uri):
    """返回 URI 的本地名称。"""
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.split("/")[-1] if "/" in s else s


def uri_namespace(uri):
    s = str(uri)
    if "#" in s:
        return s.rsplit("#", 1)[0] + "#"
    return s.rsplit("/", 1)[0] + "/"


def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_ontology(path):
    g = Graph()
    g.parse(path, format="xml")
    return g


# ---------------------------------------------------------------------------
# 检测规则实现
# ---------------------------------------------------------------------------
class OOPSDetector:
    def __init__(self, graph):
        self.g = graph
        self.findings = defaultdict(list)
        self.stats = {}

        # 预先收集类、对象属性、数据属性
        self.classes = set()
        self.object_properties = set()
        self.data_properties = set()
        self.annotation_properties = set()
        self.individuals = set()

        for s in set(graph.subjects(RDF.type, OWL.Class)):
            self.classes.add(s)
        for s in set(graph.subjects(RDF.type, OWL.ObjectProperty)):
            self.object_properties.add(s)
        for s in set(graph.subjects(RDF.type, OWL.DatatypeProperty)):
            self.data_properties.add(s)
        for s in set(graph.subjects(RDF.type, OWL.AnnotationProperty)):
            self.annotation_properties.add(s)

        # 同时收集通过 rdfs:subClassOf 出现的未显式声明类
        for s, p, o in graph.triples((None, RDFS.subClassOf, None)):
            if isinstance(s, URIRef):
                self.classes.add(s)
            if isinstance(o, URIRef):
                self.classes.add(o)
        for s, p, o in graph.triples((None, RDFS.domain, None)):
            if isinstance(s, URIRef):
                if (s, RDF.type, OWL.ObjectProperty) in graph or (s, RDF.type, OWL.DatatypeProperty) in graph:
                    pass
            if isinstance(o, URIRef):
                self.classes.add(o)
        for s, p, o in graph.triples((None, RDFS.range, None)):
            if isinstance(o, URIRef):
                self.classes.add(o)

        # 个体：声明为某个类的实例且不是自身为 owl:Class
        for s in set(graph.subjects(RDF.type, None)):
            if isinstance(s, URIRef) and s not in self.classes:
                types = set(graph.objects(s, RDF.type))
                if OWL.NamedIndividual in types or any(t in self.classes for t in types):
                    self.individuals.add(s)

    def add_finding(self, code, entity, message):
        self.findings[code].append({"entity": entity, "message": message})

    # ---- P37: 本体头信息 ----
    def check_p37_header(self):
        ontology_headers = list(self.g.subjects(RDF.type, OWL.Ontology))
        if not ontology_headers:
            self.add_finding("P37", "", "未找到 owl:Ontology 头信息")
            return
        for header in ontology_headers:
            title = list(self.g.objects(header, URIRef("http://purl.org/dc/elements/1.1/title")))
            desc = list(self.g.objects(header, URIRef("http://purl.org/dc/elements/1.1/description")))
            if not title:
                self.add_finding("P37", local_name(header), "本体头缺少 dc:title")
            if not desc:
                self.add_finding("P37", local_name(header), "本体头缺少 dc:description")

    # ---- P8: 缺少注释 ----
    def check_p8_annotations(self):
        # 排除外部导入命名空间中的类（如 XSD 类型）
        external_ns = {
            str(XSD), str(RDFS), str(RDF), str(OWL), str(GEO),
            "http://www.w3.org/2001/XMLSchema#",
            "http://www.opengis.net/ont/geosparql#",
            "http://www.w3.org/ns/sosa/",
            "http://www.w3.org/ns/prov#",
            "http://www.w3.org/2006/time#",
            "http://www.w3.org/2004/02/skos/core#",
            "http://purl.org/dc/elements/1.1/",
        }

        def is_external(uri):
            ns = uri_namespace(uri)
            return any(ns.startswith(ex) for ex in external_ns)

        for cls in self.classes:
            if is_external(cls):
                continue
            name = local_name(cls)
            labels = list(self.g.objects(cls, RDFS.label))
            comments = list(self.g.objects(cls, RDFS.comment))
            if not labels:
                self.add_finding("P8", name, f"类 {name} 缺少 rdfs:label")
            if not comments:
                self.add_finding("P8", name, f"类 {name} 缺少 rdfs:comment")

        for prop in self.object_properties | self.data_properties:
            name = local_name(prop)
            labels = list(self.g.objects(prop, RDFS.label))
            comments = list(self.g.objects(prop, RDFS.comment))
            if not labels:
                self.add_finding("P8", name, f"属性 {name} 缺少 rdfs:label")
            if not comments:
                self.add_finding("P8", name, f"属性 {name} 缺少 rdfs:comment")

    # ---- P11/P31: Domain/Range 缺失 ----
    def check_p11_p31_domain_range(self):
        for prop in self.object_properties | self.data_properties:
            name = local_name(prop)
            if not str(prop).startswith(str(ONTO)):
                continue
            domains = list(self.g.objects(prop, RDFS.domain))
            ranges = list(self.g.objects(prop, RDFS.range))
            if not domains and not ranges:
                self.add_finding("P31", name, f"属性 {name} 同时缺少 domain 和 range")
            elif not domains:
                self.add_finding("P11", name, f"属性 {name} 缺少 domain")
            elif not ranges:
                self.add_finding("P11", name, f"属性 {name} 缺少 range")

    # ---- P25/P13: 逆关系缺失 ----
    def check_p25_p13_inverse(self):
        """
        P25: 语义上可能成对但完全未声明 inverseOf 的属性。
        P13: 已声明单向 inverseOf，但缺少反向显式声明（owl:inverseOf 在语义上是对称的，
             显式双向声明可读性更好）。
        """
        # P25: has/isOf 启发式
        for prop in self.object_properties:
            name = local_name(prop)
            if not name.startswith("has"):
                continue
            stem = name[3:]
            expected_inverse = "is" + stem + "Of"
            for other in self.object_properties:
                other_name = local_name(other)
                if other_name != expected_inverse:
                    continue
                # 任一方向存在 inverseOf 即认为已声明
                has_inverse = (
                    (prop, OWL.inverseOf, other) in self.g or
                    (other, OWL.inverseOf, prop) in self.g
                )
                if not has_inverse:
                    self.add_finding(
                        "P25", name,
                        f"属性 {name} 与 {other_name} 语义上可能互为逆关系，但未声明 owl:inverseOf"
                    )

        # P13: 检查单向声明
        for prop in self.object_properties:
            for inv in self.g.objects(prop, OWL.inverseOf):
                if not (inv, OWL.inverseOf, prop) in self.g:
                    self.add_finding(
                        "P13", local_name(prop),
                        f"声明了 {local_name(prop)} inverseOf {local_name(inv)}，建议同时在 {local_name(inv)} 上反向声明 inverseOf 以提升可读性"
                    )

    # ---- P10: 兄弟类缺少 disjoint ----
    def check_p10_disjoint(self):
        children_map = defaultdict(list)
        for cls in self.classes:
            for parent in self.g.objects(cls, RDFS.subClassOf):
                if isinstance(parent, URIRef) and parent in self.classes:
                    children_map[parent].append(cls)

        # 预收集所有 AllDisjointClasses 中的 disjoint 对
        all_disjoint_pairs = set()
        for disjoint_node in self.g.subjects(RDF.type, OWL.AllDisjointClasses):
            members = []
            # 标准写法：AllDisjointClasses -> owl:members -> RDF Collection
            members_node = self.g.value(disjoint_node, OWL.members)
            if members_node is not None:
                try:
                    members = [x for x in Collection(self.g, members_node) if isinstance(x, URIRef)]
                except Exception:
                    pass
            else:
                # 兼容旧写法：节点自身即 list 头
                try:
                    members = [x for x in Collection(self.g, disjoint_node) if isinstance(x, URIRef)]
                except Exception:
                    pass
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    all_disjoint_pairs.add(tuple(sorted([str(members[i]), str(members[j])])))

        for parent, children in children_map.items():
            if len(children) < 2:
                continue
            # 检查是否已有 disjoint 声明（包括 owl:disjointWith 和 AllDisjointClasses）
            disjoint_pairs = set()
            for c in children:
                for d in self.g.objects(c, OWL.disjointWith):
                    if d in children:
                        disjoint_pairs.add(tuple(sorted([str(c), str(d)])))
            # 补充 AllDisjointClasses 中涉及本组兄弟的对
            for i in range(len(children)):
                for j in range(i + 1, len(children)):
                    pair = tuple(sorted([str(children[i]), str(children[j])]))
                    if pair in all_disjoint_pairs:
                        disjoint_pairs.add(pair)

            total_pairs = len(children) * (len(children) - 1) // 2
            if len(disjoint_pairs) == 0:
                names = [local_name(c) for c in children]
                self.add_finding(
                    "P10", local_name(parent),
                    f"父类 {local_name(parent)} 下有 {len(children)} 个兄弟类，但均未声明 owl:disjointWith: {', '.join(names[:6])}{'...' if len(names) > 6 else ''}"
                )

    # ---- P22: 命名规范 ----
    def check_p22_naming(self):
        styles = defaultdict(list)
        pattern_camel = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
        pattern_lower_camel = re.compile(r"^[a-z][a-zA-Z0-9]*$")
        pattern_snake = re.compile(r"^[a-z][a-z0-9_]*$")
        pattern_kebab = re.compile(r"^[a-z][a-z0-9\-]*$")

        def classify(name):
            if pattern_camel.match(name):
                return "CamelCase"
            if pattern_lower_camel.match(name):
                return "lowerCamelCase"
            if pattern_snake.match(name):
                return "snake_case"
            if pattern_kebab.match(name):
                return "kebab-case"
            return "mixed/other"

        for cls in self.classes:
            n = local_name(cls)
            styles[classify(n)].append(n)
        for prop in self.object_properties | self.data_properties:
            n = local_name(prop)
            styles[classify(n)].append(n)

        non_mixed = {k: v for k, v in styles.items() if k != "mixed/other"}
        if len(non_mixed) > 2:
            dominant = max(non_mixed.items(), key=lambda x: len(x[1]))
            self.add_finding(
                "P22", "命名风格",
                f"检测到 {len(non_mixed)} 种命名风格（{', '.join(non_mixed.keys())}），主要风格为 {dominant[0]}，建议统一"
            )

    # ---- P29: DatatypeProperty range 检查 ----
    def check_p29_datatype(self):
        valid_ranges = {XSD.string, XSD.integer, XSD.float, XSD.double, XSD.boolean,
                        XSD.dateTime, XSD.date, XSD.time, XSD.decimal, XSD.anyURI,
                        XSD.duration, GEO.wktLiteral,
                        RDFS.Literal, XSD.nonNegativeInteger, XSD.positiveInteger}
        for prop in self.data_properties:
            name = local_name(prop)
            ranges = list(self.g.objects(prop, RDFS.range))
            for r in ranges:
                if isinstance(r, URIRef) and r not in valid_ranges:
                    self.add_finding(
                        "P29", name,
                        f"数据属性 {name} 的 range {local_name(r)} 可能不是标准数据类型，建议检查是否应使用 owl:ObjectProperty"
                    )

    # ---- P34: 未声明类型 ----
    def check_p34_untyped(self):
        typed = self.classes | self.object_properties | self.data_properties | self.annotation_properties
        # 收集作为 subject 出现在本体声明中但未声明类型的 URI
        untyped = set()
        for s in set(self.g.subjects()):
            if isinstance(s, URIRef) and s not in typed:
                # 如果它作为 owl:Restriction 的 onProperty 目标但不是类/属性
                p_types = set(self.g.objects(s, RDF.type))
                if not p_types:
                    # 忽略仅作为字面量谓词的对象
                    if s not in set(self.g.objects()):
                        continue
                    untyped.add(s)
        for uri in sorted(untyped, key=str)[:20]:
            self.add_finding("P34", local_name(uri), f"资源 {local_name(uri)} 未显式声明类型")

    # ---- P38: 类作为实例 ----
    def check_p38_class_instance(self):
        for ind in self.individuals:
            if ind in self.classes:
                self.add_finding(
                    "P38", local_name(ind),
                    f"资源 {local_name(ind)} 同时被声明为类（owl:Class）和个体，存在混淆"
                )

    # ---- P40: 子类继承自 disjoint 父类 ----
    def check_p40_disjoint_subclass(self):
        disjoint_pairs = set()
        for c in self.classes:
            for d in self.g.objects(c, OWL.disjointWith):
                if isinstance(d, URIRef):
                    disjoint_pairs.add(tuple(sorted([str(c), str(d)])))

        # 通过 subClassOf 传递闭包找出父类集合
        parents = {cls: set() for cls in self.classes}
        for cls in self.classes:
            stack = list(self.g.objects(cls, RDFS.subClassOf))
            visited = set()
            while stack:
                p = stack.pop()
                if isinstance(p, URIRef) and p in self.classes and p not in visited:
                    visited.add(p)
                    parents[cls].add(p)
                    stack.extend(self.g.objects(p, RDFS.subClassOf))

        for cls, pars in parents.items():
            par_list = sorted(pars, key=str)
            for i in range(len(par_list)):
                for j in range(i + 1, len(par_list)):
                    pair = tuple(sorted([str(par_list[i]), str(par_list[j])]))
                    if pair in disjoint_pairs:
                        self.add_finding(
                            "P40", local_name(cls),
                            f"类 {local_name(cls)} 同时继承自两个已声明 disjoint 的父类: {local_name(par_list[i])} 与 {local_name(par_list[j])}"
                        )

    # ---- P41: 属性未被使用 ----
    def check_p41_unused_properties(self):
        """
        在模式本体中，属性的"使用"应包括：
        1) 作为 owl:Restriction 的 owl:onProperty 被引用
        2) 声明了 rdfs:domain / rdfs:range
        3) 声明了 owl:inverseOf / rdfs:subPropertyOf
        4) 出现在实例数据中（作为谓词）

        注意：本检测仅加载 ontology/tc_sssao.owl（schema-only 模式）。
        因此 P41 "defined but unused" 的含义是：该属性在本 OWL 文件中
        没有被任何 Restriction、domain/range、subPropertyOf、inverseOf 或
        实例三元组引用——这在 schema-only 模式下是正常状态，不代表该属性
        在整个项目中未被使用。跨 artifact 的使用审计（如 rules/*.ttl、
        experiments/**/*.{ttl,py}、paper 映射）需要单独的跨文件扫描。
        """
        used_props = set()

        # 1) 出现在任何三元组中作为谓词
        for s, p, o in self.g:
            if p in self.object_properties or p in self.data_properties:
                used_props.add(p)

        # 2) 在 owl:Restriction 的 onProperty 中被引用
        for sub in self.g.subjects(OWL.onProperty, None):
            for prop in self.g.objects(sub, OWL.onProperty):
                if prop in self.object_properties or prop in self.data_properties:
                    used_props.add(prop)

        # 3) 作为 inverseOf / subPropertyOf 的目标被引用
        for prop in self.object_properties | self.data_properties:
            for pred in (OWL.inverseOf, RDFS.subPropertyOf):
                if any((sub, pred, prop) in self.g for sub in self.g.subjects(pred, prop)):
                    used_props.add(prop)

        for prop in self.object_properties | self.data_properties:
            if prop not in used_props:
                self.add_finding(
                    "P41", local_name(prop),
                    f"属性 {local_name(prop)} 在本体 schema 中未被任何 Restriction、domain/range、subPropertyOf、inverseOf 或实例三元组使用"
                )

    # ---- P42: 类 URI 用作数据属性值 ----
    def check_p42_class_as_value(self):
        for prop in self.data_properties:
            for o in self.g.objects(None, prop):
                if isinstance(o, URIRef):
                    self.add_finding(
                        "P42", local_name(prop),
                        f"数据属性 {local_name(prop)} 的取值是 URI {local_name(o)}，可能应使用 owl:ObjectProperty"
                    )

    # ---- P3: 未连接元素 ----
    def check_p3_unconnected(self):
        connected = set()
        for s, p, o in self.g:
            if p in {RDFS.subClassOf, RDFS.domain, RDFS.range, OWL.inverseOf, OWL.disjointWith,
                     OWL.onProperty, OWL.someValuesFrom, OWL.allValuesFrom, OWL.hasValue}:
                if isinstance(s, URIRef):
                    connected.add(s)
                if isinstance(o, URIRef):
                    connected.add(o)

        for cls in self.classes:
            if cls not in connected and cls != OWL.Thing:
                self.add_finding("P3", local_name(cls), f"类 {local_name(cls)} 未通过 subClassOf/disjoint/restriction 与本体连接")

        for prop in self.object_properties | self.data_properties:
            if prop not in connected:
                self.add_finding("P3", local_name(prop), f"属性 {local_name(prop)} 未声明 domain/range 或 inverseOf")

    # ---- 统计 ----
    def compute_stats(self):
        self.stats = {
            "classes": len(self.classes),
            "object_properties": len(self.object_properties),
            "data_properties": len(self.data_properties),
            "annotation_properties": len(self.annotation_properties),
            "individuals": len(self.individuals),
            "triples": len(self.g),
            "subclass_axioms": len(list(self.g.triples((None, RDFS.subClassOf, None)))),
            "restriction_axioms": len(list(self.g.triples((None, OWL.onProperty, None)))),
            "inverse_axioms": len(list(self.g.triples((None, OWL.inverseOf, None)))),
            "disjoint_axioms": len(list(self.g.triples((None, OWL.disjointWith, None)))),
        }

    # ---- 运行全部检测 ----
    def run(self):
        self.check_p37_header()
        self.check_p8_annotations()
        self.check_p11_p31_domain_range()
        self.check_p25_p13_inverse()
        self.check_p10_disjoint()
        self.check_p22_naming()
        self.check_p29_datatype()
        self.check_p34_untyped()
        self.check_p38_class_instance()
        self.check_p40_disjoint_subclass()
        self.check_p41_unused_properties()
        self.check_p42_class_as_value()
        self.check_p3_unconnected()
        self.compute_stats()


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------
def generate_report(detector):
    lines = []
    lines.append("# OOPS! 本体质量检测报告")
    lines.append("")
    lines.append(f"**检测本体**: `ontology/tc_sssao.owl`")
    lines.append(f"**检测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**检测工具**: 本地 OOPS! 风格静态检测器 (`scripts/report/oops_quality_check.py`)")
    lines.append("")

    lines.append("## 一、本体统计概览")
    lines.append("")
    lines.append("> 口径说明：本表按图中全部 IRI 计数（含 time/sosa/ssn/prov/geo 等外部"
                 "标准本体的 DL 声明），仅作结构参考；论文 4.2.1 的发布口径"
                 "（TC-SSSAO 命名空间内 87 命名类 / 65 对象属性 / 67 数据属性 / "
                 "11 注解属性）以 `data/current/ontology_statistics.json` 为准。")
    lines.append("")
    lines.append("| 指标 | 数量 |")
    lines.append("|---|---|")
    for key, value in detector.stats.items():
        lines.append(f"| {key} | {value} |")
    lines.append("")

    # 汇总
    total_findings = sum(len(v) for v in detector.findings.values())
    critical = sum(1 for code, items in detector.findings.items() for _ in items if PITFALLS.get(code, {}).get("level") == "Critical")
    important = sum(1 for code, items in detector.findings.items() for _ in items if PITFALLS.get(code, {}).get("level") == "Important")
    minor = sum(1 for code, items in detector.findings.items() for _ in items if PITFALLS.get(code, {}).get("level") == "Minor")

    lines.append("## 二、问题汇总")
    lines.append("")
    lines.append(f"- **Total pitfalls found**: {total_findings}")
    lines.append(f"- **Critical**: {critical}")
    lines.append(f"- **Important**: {important}")
    lines.append(f"- **Minor**: {minor}")
    lines.append("")

    lines.append("| 陷阱编号 | 名称 | 严重级别 | 数量 |")
    lines.append("|---|---|---|---|")
    for code in sorted(detector.findings.keys()):
        info = PITFALLS.get(code, {})
        lines.append(f"| {code} | {info.get('name', 'N/A')} | {info.get('level', 'N/A')} | {len(detector.findings[code])} |")
    lines.append("")

    lines.append("## 三、详细发现")
    lines.append("")
    for code in sorted(detector.findings.keys()):
        info = PITFALLS.get(code, {})
        lines.append(f"### {code}: {info.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"- **严重级别**: {info.get('level', 'N/A')}")
        lines.append(f"- **说明**: {info.get('desc', 'N/A')}")
        lines.append(f"- **发现数量**: {len(detector.findings[code])}")
        lines.append("")
        lines.append("| 涉及实体 | 问题描述 |")
        lines.append("|---|---|")
        for item in detector.findings[code][:50]:  # 每类最多显示 50 条
            entity = item["entity"] or "—"
            message = item["message"].replace("|", "\\|")
            lines.append(f"| {entity} | {message} |")
        if len(detector.findings[code]) > 50:
            lines.append(f"| ... | 还有 {len(detector.findings[code]) - 50} 条未显示 |")
        lines.append("")

    lines.append("## 四、修复建议优先级")
    lines.append("")
    lines.append("1. **Critical（严重）**: 立即修复，可能导致推理不一致或语义错误。")
    lines.append("2. **Important（重要）**: 建议优先修复，影响本体的可用性和查询准确性。")
    lines.append("3. **Minor（轻微）**: 根据项目时间排期逐步优化，提升可维护性。")
    lines.append("")
    lines.append("## 五、备注")
    lines.append("")
    lines.append("- 本报告基于 OOPS! (OntOlogy Pitfall Scanner) 经典陷阱分类，通过本地 RDFLib 解析实现。")
    lines.append("- 部分规则（如 P10 兄弟类 disjoint）采用启发式策略，建议由领域专家复核后决定是否真正需要添加不相交公理。")
    lines.append("- 外部本体术语（sosa:/prov:/time: 等）不参与 P8/P11 等属性级检测，避免误报。")
    lines.append("")

    return "\n".join(lines)


def main():
    print(f"[INFO] 加载本体: {OWL_PATH}")
    g = load_ontology(OWL_PATH)
    print(f"[INFO] 三元组数量: {len(g)}")

    detector = OOPSDetector(g)
    detector.run()

    report = generate_report(detector)
    ensure_dir(REPORT_PATH)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    total = sum(len(v) for v in detector.findings.values())
    print(f"[INFO] 检测完成，共发现 {total} 个问题")
    print(f"[INFO] 报告已保存: {REPORT_PATH}")
    blocking = sum(len(items) for code, items in detector.findings.items()
                   if PITFALLS.get(code, {}).get("level") in {"Critical", "Important"})
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
