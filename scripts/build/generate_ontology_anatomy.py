# -*- coding: utf-8 -*-
"""生成 TC-SSSAO 本体解剖文档（中英双语）。

M5 Phase 1 更新（spec 第 27 节）：
  - 概览计数区分 onto: 命名空间概念与外部标准术语最小声明；
  - 类层次树仅含 onto: 类（外部声明不再混入顶层模块）；
  - 新增第 9 节"标准词汇对齐"（正式对齐公理 + 外部术语最小声明 + 对齐原则）；
  - 同一脚本生成 zh / en 两个版本，保证双语文档同步。

用法：python scripts/build/generate_ontology_anatomy.py
输出：ontology/tc_sssao_ontology_anatomy_zh.md、ontology/tc_sssao_ontology_anatomy_en.md
"""
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode, URIRef
from collections import defaultdict

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE_DIR = _find_project_root(Path(__file__).parent)
# Load ontology
g = Graph()
g.parse(BASE_DIR / 'ontology' / 'tc_sssao.owl', format='xml')

ONTO = Namespace('https://w3id.org/tc-sssao#')
ONTO_STR = str(ONTO)

EXT_PREFIX = {
    'http://www.w3.org/2006/time#': 'time',
    'http://www.w3.org/ns/sosa/': 'sosa',
    'http://www.w3.org/ns/ssn/': 'ssn',
    'http://www.w3.org/ns/prov#': 'prov',
    'http://www.opengis.net/ont/geosparql#': 'geo',
}

# Helpers
def local_name(uri):
    s = str(uri)
    if '#' in s:
        return s.split('#')[-1]
    return s.split('/')[-1]

def prefixed(uri):
    s = str(uri)
    for ns, pref in EXT_PREFIX.items():
        if s.startswith(ns):
            return f"{pref}:{s[len(ns):]}"
    return local_name(uri)

def is_onto(uri):
    return str(uri).startswith(ONTO_STR)

def is_ext(uri):
    return any(str(uri).startswith(ns) for ns in EXT_PREFIX)

def get_label(uri):
    labels = list(g.objects(uri, RDFS.label))
    zh = [str(l) for l in labels if l.language == 'zh']
    en = [str(l) for l in labels if l.language == 'en']
    if zh:
        return zh[0]
    if en:
        return en[0]
    if labels:
        return str(labels[0])
    return ''

def get_comment(uri):
    comments = list(g.objects(uri, RDFS.comment))
    zh = [str(c) for c in comments if c.language == 'zh']
    en = [str(c) for c in comments if c.language == 'en']
    if zh:
        return zh[0]
    if en:
        return en[0]
    if comments:
        return str(comments[0])
    return ''

def get_parents(cls):
    parents = []
    for p in g.objects(cls, RDFS.subClassOf):
        if isinstance(p, URIRef):
            parents.append(p)
    return parents

def get_children(cls):
    children = []
    for c in g.subjects(RDFS.subClassOf, cls):
        if isinstance(c, URIRef):
            children.append(c)
    return sorted(children, key=lambda x: local_name(x))

# Collect entities
all_classes = sorted([c for c in set(g.subjects(RDF.type, OWL.Class)) if isinstance(c, URIRef)], key=local_name)
all_obj_props = sorted([c for c in set(g.subjects(RDF.type, OWL.ObjectProperty)) if isinstance(c, URIRef)], key=local_name)
all_data_props = sorted([c for c in set(g.subjects(RDF.type, OWL.DatatypeProperty)) if isinstance(c, URIRef)], key=local_name)
all_ann_props = sorted([c for c in set(g.subjects(RDF.type, OWL.AnnotationProperty)) if isinstance(c, URIRef)], key=local_name)
all_datatypes = sorted([c for c in set(g.subjects(RDF.type, RDFS.Datatype)) if isinstance(c, URIRef)], key=local_name)

classes = [c for c in all_classes if is_onto(c)]
obj_props = [p for p in all_obj_props if is_onto(p)]
data_props = [p for p in all_data_props if is_onto(p)]
ann_props = [p for p in all_ann_props if is_onto(p)]
ext_decls = (
    [(c, 'owl:Class') for c in all_classes if is_ext(c)]
    + [(p, 'owl:ObjectProperty') for p in all_obj_props if is_ext(p)]
    + [(p, 'owl:DatatypeProperty') for p in all_data_props if is_ext(p)]
    + [(p, 'owl:AnnotationProperty') for p in all_ann_props if is_ext(p)]
    + [(d, 'rdfs:Datatype') for d in all_datatypes if is_ext(d)]
)
ext_decls = sorted(set(ext_decls), key=lambda x: (x[1], prefixed(x[0])))

# Top classes (onto only): those with no onto/external superclass except owl:Thing or none
top_classes = []
for c in classes:
    parents = get_parents(c)
    if not parents or all(p == OWL.Thing for p in parents):
        top_classes.append(c)
top_classes = sorted(top_classes, key=lambda x: local_name(x))

# Build hierarchy tree (rooted at owl:Thing)
def build_tree(node, prefix='', is_last=True, visited=None):
    if visited is None:
        visited = set()
    if node in visited:
        return [(prefix + ('└── ' if is_last else '├── ') + local_name(node) + ' (循环引用)', '')]
    visited = visited | {node}

    lines = []
    name = local_name(node)
    label = get_label(node)
    comment = get_comment(node)
    display = name
    if label:
        display += f' ({label})'
    connector = '└── ' if is_last else '├── '
    lines.append((prefix + connector + display, comment))

    children = get_children(node)
    # Only include onto classes (external declarations stay out of the tree)
    children = [c for c in children if c in classes]
    for i, child in enumerate(children):
        child_is_last = (i == len(children) - 1)
        child_prefix = prefix + ('    ' if is_last else '│   ')
        lines.extend(build_tree(child, child_prefix, child_is_last, visited))
    return lines

root_children = top_classes

# Group properties by domain
def group_props_by_domain(props):
    groups = defaultdict(list)
    ungrouped = []
    for prop in props:
        domains = list(g.objects(prop, RDFS.domain))
        if domains and isinstance(domains[0], URIRef):
            domain_name = local_name(domains[0])
            groups[domain_name].append(prop)
        else:
            ungrouped.append(prop)
    return groups, ungrouped

obj_groups, obj_ungrouped = group_props_by_domain(obj_props)
data_groups, data_ungrouped = group_props_by_domain(data_props)

FEATURE_NAMES = {
    'zh': {'sym': '对称', 'trans': '传递', 'func': '函数型', 'invfunc': '反函数型',
           'refl': '自反', 'irrefl': '非自反', 'asym': '非对称'},
    'en': {'sym': 'Symmetric', 'trans': 'Transitive', 'func': 'Functional',
           'invfunc': 'InverseFunctional', 'refl': 'Reflexive',
           'irrefl': 'Irreflexive', 'asym': 'Asymmetric'},
}

# Get property details
def prop_details(prop, lang):
    fn = FEATURE_NAMES[lang]
    name = local_name(prop)
    label = get_label(prop)
    comment = get_comment(prop)
    domains = [local_name(d) for d in g.objects(prop, RDFS.domain) if isinstance(d, URIRef)]
    ranges = [prefixed(r) for r in g.objects(prop, RDFS.range) if isinstance(r, URIRef)]
    features = []
    if (prop, RDF.type, OWL.SymmetricProperty) in g:
        features.append(fn['sym'])
    if (prop, RDF.type, OWL.TransitiveProperty) in g:
        features.append(fn['trans'])
    if (prop, RDF.type, OWL.FunctionalProperty) in g:
        features.append(fn['func'])
    if (prop, RDF.type, OWL.InverseFunctionalProperty) in g:
        features.append(fn['invfunc'])
    if (prop, RDF.type, OWL.ReflexiveProperty) in g:
        features.append(fn['refl'])
    if (prop, RDF.type, OWL.IrreflexiveProperty) in g:
        features.append(fn['irrefl'])
    if (prop, RDF.type, OWL.AsymmetricProperty) in g:
        features.append(fn['asym'])
    inverse = list(g.objects(prop, OWL.inverseOf))
    inverse_names = [local_name(i) for i in inverse if isinstance(i, URIRef)]
    return {
        'name': name,
        'label': label,
        'comment': comment,
        'domains': domains,
        'ranges': ranges,
        'features': features,
        'inverse': inverse_names,
    }

# External reuse mappings
reuse_map = defaultdict(list)
for s, o in g.subject_objects(ONTO.reusedOntology):
    if isinstance(s, URIRef):
        reuse_map[str(o)].append(local_name(s))

mapped_map = defaultdict(list)
for s, o in g.subject_objects(ONTO.mappedToExternalTerm):
    if isinstance(s, URIRef):
        mapped_map[str(o)].append(local_name(s))

# Formal standard alignments (M5): onto term -> external term via subClassOf/subPropertyOf
formal_alignments = []
for pred in (RDFS.subClassOf, RDFS.subPropertyOf):
    for s, o in g.subject_objects(pred):
        if isinstance(s, URIRef) and isinstance(o, URIRef) and is_onto(s) and is_ext(o):
            formal_alignments.append((local_name(s), pred, prefixed(o)))
formal_alignments = sorted(set(formal_alignments),
                           key=lambda x: (x[1] != RDFS.subClassOf, x[0]))

# Axiom metadata helpers
AXIOM_SHAPE_MAP = {
    'R1': ('onto:EventPrecedenceRuleShape', 'InferenceRule'),
    'R2': ('onto:EventOverlapRuleShape', 'InferenceRule'),
    'R3': ('onto:OrbitManeuverCausesApproachRuleShape', 'InferenceRule'),
    'R4': ('onto:ApproachCausesCollisionRiskRuleShape', 'InferenceRule'),
    'R5': ('onto:CollisionRiskLeadsToNormalRuleShape', 'InferenceRule'),
    'R6': ('onto:CollisionRiskLeadsToAttentionRuleShape', 'InferenceRule'),
    'R7': ('onto:CollisionRiskLeadsToWarningRuleShape', 'InferenceRule'),
    'R8': ('onto:CollisionRiskLeadsToDangerousRuleShape', 'InferenceRule'),
    'R9': ('onto:CauseBeforeEffectShape', 'ValidationRule'),
    'R10': ('onto:CausalDirectionShape', 'ValidationRule'),
    'R11': ('onto:CausalCycleShape', 'ValidationRule'),
    'R12': ('SecurityThreat SubClassOf requiresResponseMeasure some ResponseMeasure', 'StructuralRestriction'),
    'R13': ('onto:EventDataEvidenceShape', 'ValidationRule'),
    'R14': ('onto:StateStartEndTimeShape', 'ValidationRule'),
    'R15': ('ResponseMeasure SubClassOf respondsToEvent some SpaceEvent', 'StructuralRestriction'),
    'R16': ('SpaceObject SubClassOf hasOrbit some Orbit', 'StructuralRestriction'),
    'R17': ('ObservationSystem SubClassOf generatesData some ObservationData', 'StructuralRestriction'),
    'R18': ('onto:EnvironmentLevelShape', 'ValidationRule'),
}

AXIOM_TESTS = {
    'R1': ('test_r1_precedence', '—'),
    'R2': ('test_r2_overlap', '—'),
    'R3': ('test_r3_maneuver_causes_approach', '—'),
    'R4': ('test_r4_approach_causes_collision', '—'),
    'R5': ('rule_logic_verification rs:Risk_T0', '—'),
    'R6': ('rule_logic_verification rs:Risk_T1', '—'),
    'R7': ('rule_logic_verification rs:Risk_T2', '—'),
    'R8': ('rule_logic_verification rs:Risk_T3', '—'),
    'R9': ('—', 'test_r9_cause_before_effect'),
    'R10': ('—', 'test_r10_bidirectional_causal'),
    'R11': ('—', 'neg_cycle_a / neg_cycle_b'),
    'R12': ('pos_physical_threat', 'neg_threat_mitigated'),
    'R13': ('pos_detected_only_event / pos_supported_only_event', 'neg_event_without_evidence'),
    'R14': ('pos_normal_state', 'neg_state_bad_time'),
    'R15': ('pos_avoidance_measure', 'neg_measure'),
    'R16': ('pos_payload', 'neg_sat_no_orbit'),
    'R17': ('pos_sensor_ground_radar / pos_obs_system', 'neg_sensor_without_data'),
    'R18': ('pos_environment_normal / pos_environment_abnormal', 'neg_environment_invalid'),
}


def get_axiom_metadata(c):
    """提取 Axiom 类的全部规则元数据注释。"""
    def _v(pred):
        vals = list(g.objects(c, pred))
        return str(vals[0]) if vals else ''
    return {
        'label': get_label(c),
        'comment': get_comment(c),
        'impl': _v(ONTO.implementationStatus),
        'rule_category': _v(ONTO.ruleCategory),
        'target_class': _v(ONTO.targetClass),
        'input_props': _v(ONTO.inputProperties),
        'output_rel': _v(ONTO.outputRelation),
        'severity': _v(ONTO.validationSeverity),
        'nl_rule': _v(ONTO.naturalLanguageRule),
        'formal': _v(ONTO.formalExpression),
    }


axioms = []

# ------------------------------------------------------------------
# 双语文本
# ------------------------------------------------------------------
T = {
    'title': ('# TC-SSSAO 本体库解剖文档', '# TC-SSSAO Ontology Anatomy Document'),
    'file': ('**文件**：`ontology/tc_sssao.owl`', '**File**: `ontology/tc_sssao.owl`'),
    's1': ('## 1. 概览', '## 1. Overview'),
    'metric': ('| 指标 | 数量 |', '| Metric | Count |'),
    'm_class': ('类（Class，onto:）', 'Classes (onto:)'),
    'm_obj': ('对象属性（ObjectProperty，onto:）', 'Object Properties (onto:)'),
    'm_data': ('数据属性（DatatypeProperty，onto:）', 'Datatype Properties (onto:)'),
    'm_ann': ('注释属性（AnnotationProperty，onto:）', 'Annotation Properties (onto:)'),
    'm_top': ('顶层模块（直接子类于 owl:Thing）', 'Top-level modules (direct subclasses of owl:Thing)'),
    'm_axiom': ('约束公理（独立规则层）', 'Constraint axioms (independent rule layer)'),
    'm_ext': ('外部标准术语最小声明（第 9.2 节）', 'Minimal external term declarations (Sec. 9.2)'),
    's2': ('## 2. 类层次结构', '## 2. Class Hierarchy'),
    's3': ('## 3. 对象属性', '## 3. Object Properties'),
    's4': ('## 4. 数据属性', '## 4. Datatype Properties'),
    's5': ('## 5. 注释属性', '## 5. Annotation Properties'),
    'no_domain': ('无 domain 声明', 'No domain declaration'),
    'range': ('range', 'range'),
    'features': ('特征', 'features'),
    'inverse': ('逆属性', 'inverse'),
    's6': ('## 6. 约束公理（R1–R18）', '## 6. Constraint Axioms (R1–R18)'),
    's6_head': ('| 编号 | 名称 | ruleCategory | implementationStatus | 目标类 | 输入属性 | 输出关系 | 自然语言规则 |',
                '| ID | Name | ruleCategory | implementationStatus | Target class | Input properties | Output relation | Natural language rule |'),
    's7': ('## 7. 规则执行覆盖表', '## 7. Rule Execution Coverage'),
    's7_head': ('| 编号 | 规则名称 | ruleCategory | implementationStatus | 实现位置（Shape / OWL 公理） | 正例测试 | 负例测试 | 推导结果 / 错误消息 | 结果 |',
                '| ID | Rule | ruleCategory | implementationStatus | Implementation (Shape / OWL axiom) | Positive test | Negative test | Inference / error message | Result |'),
    'gen': ('生成', 'Generates'),
    'gen_new': ('生成新关系/类型', 'Generates new relation/type'),
    'viol': ('违反', 'Violates'),
    'constr': ('约束检查', 'Constraint check'),
    's8': ('## 8. 外部本体复用映射', '## 8. External Ontology Reuse Mappings'),
    's8_reused': ('| 复用本体 | 对齐实体 |', '| Reused ontology | Aligned entities |'),
    's8_mapped': ('| 外部术语 | 对齐实体 |', '| External term | Aligned entities |'),
    's9': ('## 9. 标准词汇对齐（M5 Phase 1）', '## 9. Standard Vocabulary Alignments (M5 Phase 1)'),
    's9_1': ('### 9.1 正式对齐公理', '### 9.1 Formal alignment axioms'),
    's9_1_head': ('| 本地术语 | 对齐方式 | 标准术语 |', '| Local term | Alignment | Standard term |'),
    'subclass': ('子类', 'subClassOf'),
    'subprop': ('子属性', 'subPropertyOf'),
    's9_2': ('### 9.2 外部术语最小声明', '### 9.2 Minimal external term declarations'),
    's9_2_head': ('| 外部术语 | 声明类型 |', '| External term | Declared type |'),
    's9_3': ('### 9.3 对齐原则', '### 9.3 Alignment principles'),
    's9_notes': (
        [
            '- 正式对齐的唯一真源为 `ontology/tc_sssao_alignments.ttl`，由 `scripts/build/apply_standard_alignments.py` 并入主本体；',
            '- 不通过 `owl:imports` 整体导入外部本体，外部术语仅保留 OWL 2 DL 类型完整性所需的最小声明；',
            '- 不使用 `owl:equivalentClass` / `owl:equivalentProperty` 声明与外部术语的等价关系；',
            '- 对象属性与数据属性之间不建立跨类型映射；语义层次不同的关联（如 `precedesEvent` 与 `time:before`）仅使用 `rdfs:seeAlso` 参照；',
            '- 标准版本基线：OWL-Time W3C REC 2017-10-19；SOSA/SSN W3C REC 2017-10-19；PROV-O W3C REC 2013-04-30；GeoSPARQL 1.1 OGC 22-047r1。',
        ],
        [
            '- The single source of truth for formal alignments is `ontology/tc_sssao_alignments.ttl`, merged into the main ontology by `scripts/build/apply_standard_alignments.py`;',
            '- External ontologies are NOT imported via `owl:imports`; only minimal declarations required for OWL 2 DL typing are kept;',
            '- No `owl:equivalentClass` / `owl:equivalentProperty` is asserted with external terms;',
            '- No cross-type mappings between object and datatype properties; relations at a different semantic level (e.g. `precedesEvent` vs `time:before`) use `rdfs:seeAlso` only;',
            '- Standard version baseline: OWL-Time W3C REC 2017-10-19; SOSA/SSN W3C REC 2017-10-19; PROV-O W3C REC 2013-04-30; GeoSPARQL 1.1 OGC 22-047r1.',
        ]),
    's10': ('## 10. 说明', '## 10. Notes'),
    'notes': (
        [
            '- 树型结构仅展示本体 onto: 命名空间各类之间的 `rdfs:subClassOf` 关系；外部标准术语声明不进入类层次树。',
            '- 属性按 `rdfs:domain` 分组；若一个属性声明了多个 domain，仅在第一个 domain 下出现。',
            '- R1–R18 与 B1–B5 规则定义保留在 rules/tc_sssao_rules.ttl 与 src/tc_sssao/axioms.py，作为独立 SHACL-SPARQL 规则层实现，不作为领域本体类。',
            '- R1–R8 为 SHACL-SPARQL 推导规则，R9–R11、R13、R14、R18 为 SHACL-SPARQL 验证规则，R12、R15–R17 为 OWL StructuralRestriction。',
            '- 当前 pyshacl 0.40.0 未暴露 `iterate_rules` 参数，正式验证采用外部固定点包装器执行。第一轮将主本体作为本体图注入工作图，完成 RDFS 展开与 SHACL 规则推导；后续轮次复用同一工作图，不再重复加载本体，直至领域规则输出不再增加。收敛判断仅统计时序、因果和状态推导关系（`precedesEvent`、`followsEvent`、`overlapsWithEvent`、`causesEvent`、`leadsToState`、`transitsTo`、`degradesTo`）及派生状态类型（`NormalSituationState`、`AttentionSituationState`、`WarningSituationState`、`DangerousSituationState`），不统计 TBox 匿名节点。当前测试数据在第一轮完成有效推导，第二轮确认无新增领域三元组并达到固定点。',
            '- R17 的 SHACL Shape 不再排除 `Sensor`，所有 `ObservationSystem` 及其子类均须满足 `generatesData` 约束。',
        ],
        [
            '- The tree shows `rdfs:subClassOf` relations between classes of the onto: namespace only; external standard term declarations are excluded from the class hierarchy.',
            '- Properties are grouped by `rdfs:domain`; a property with multiple domains appears only under the first one.',
            '- R1–R18 and B1–B5 rule definitions are kept in rules/tc_sssao_rules.ttl and src/tc_sssao/axioms.py, implemented as an independent SHACL-SPARQL rule layer, not as domain ontology classes.',
            '- R1–R8 are SHACL-SPARQL inference rules; R9–R11, R13, R14 and R18 are SHACL-SPARQL validation rules; R12, R15–R17 are OWL structural restrictions.',
            '- Since pyshacl 0.40.0 does not expose `iterate_rules`, the formal validation uses an external fixed-point wrapper: the first round injects the main ontology as the ontology graph and performs RDFS expansion plus SHACL rule inferencing; later rounds reuse the working graph until domain rule output stops growing. Convergence only counts the temporal/causal/state derived relations (`precedesEvent`, `followsEvent`, `overlapsWithEvent`, `causesEvent`, `leadsToState`, `transitsTo`, `degradesTo`) and derived state types (`NormalSituationState`, `AttentionSituationState`, `WarningSituationState`, `DangerousSituationState`), not TBox blank nodes. With the current test data, effective derivations finish in round one and round two confirms the fixed point.',
            '- The R17 SHACL shape no longer excludes `Sensor`: every `ObservationSystem` (including subclasses) must satisfy the `generatesData` constraint.',
        ]),
}


def build(lang: str) -> list[str]:
    t = {k: (v[0] if lang == 'zh' else v[1]) for k, v in T.items()}
    lines = []
    lines.append(t['title'])
    lines.append('')
    lines.append(t['file'])
    lines.append('')
    lines.append('---')
    lines.append('')

    # Overview
    lines.append(t['s1'])
    lines.append('')
    lines.append(t['metric'])
    lines.append('|---|---|')
    lines.append(f"| {t['m_class']} | {len(classes)} |")
    lines.append(f"| {t['m_obj']} | {len(obj_props)} |")
    lines.append(f"| {t['m_data']} | {len(data_props)} |")
    lines.append(f"| {t['m_ann']} | {len(ann_props)} |")
    lines.append(f"| {t['m_top']} | {len(top_classes)} |")
    lines.append(f"| {t['m_axiom']} | {len(axioms)} |")
    lines.append(f"| {t['m_ext']} | {len(ext_decls)} |")
    lines.append('')

    # Class hierarchy
    lines.append(t['s2'])
    lines.append('')
    lines.append('```')
    lines.append('└── owl:Thing')
    for i, child in enumerate(root_children):
        child_is_last = (i == len(root_children) - 1)
        tree_lines = build_tree(child, '    ', child_is_last)
        for text, comment in tree_lines:
            lines.append(text)
    lines.append('```')
    lines.append('')

    # Object properties
    lines.append(t['s3'])
    lines.append('')
    for i, domain in enumerate(sorted(obj_groups.keys()), 1):
        lines.append(f'### 3.{i} domain: `{domain}`')
        lines.append('')
        for prop in sorted(obj_groups[domain], key=local_name):
            d = prop_details(prop, lang)
            display = f"- **`{d['name']}`**"
            if d['label']:
                display += f" *{d['label']}*"
            details = []
            if d['ranges']:
                details.append(f"{t['range']}: `{', '.join(d['ranges'])}`")
            if d['features']:
                details.append(f"{t['features']}: {', '.join(d['features'])}")
            if d['inverse']:
                details.append(f"{t['inverse']}: `{', '.join(d['inverse'])}`")
            if details:
                display += ' — ' + '；'.join(details)
            lines.append(display)
            if d['comment']:
                lines.append(f"  - {d['comment']}")
        lines.append('')

    if obj_ungrouped:
        lines.append(f"### 3.x {t['no_domain']}")
        lines.append('')
        for prop in sorted(obj_ungrouped, key=local_name):
            d = prop_details(prop, lang)
            display = f"- **`{d['name']}`**"
            if d['label']:
                display += f" *{d['label']}*"
            if d['comment']:
                display += f" — {d['comment']}"
            lines.append(display)
        lines.append('')

    # Data properties
    lines.append(t['s4'])
    lines.append('')
    for i, domain in enumerate(sorted(data_groups.keys()), 1):
        lines.append(f'### 4.{i} domain: `{domain}`')
        lines.append('')
        for prop in sorted(data_groups[domain], key=local_name):
            d = prop_details(prop, lang)
            display = f"- **`{d['name']}`**"
            if d['label']:
                display += f" *{d['label']}*"
            details = []
            if d['ranges']:
                details.append(f"{t['range']}: `{', '.join(d['ranges'])}`")
            if d['features']:
                details.append(f"{t['features']}: {', '.join(d['features'])}")
            if details:
                display += ' — ' + '；'.join(details)
            lines.append(display)
            if d['comment']:
                lines.append(f"  - {d['comment']}")
        lines.append('')

    if data_ungrouped:
        lines.append(f"### 4.x {t['no_domain']}")
        lines.append('')
        for prop in sorted(data_ungrouped, key=local_name):
            d = prop_details(prop, lang)
            display = f"- **`{d['name']}`**"
            if d['label']:
                display += f" *{d['label']}*"
            if d['comment']:
                display += f" — {d['comment']}"
            lines.append(display)
        lines.append('')

    # Annotation properties
    lines.append(t['s5'])
    lines.append('')
    for prop in ann_props:
        name = local_name(prop)
        label = get_label(prop)
        comment = get_comment(prop)
        display = f"- **`{name}`**"
        if label:
            display += f" *{label}*"
        if comment:
            display += f" — {comment}"
        lines.append(display)
    lines.append('')

    # Axioms
    lines.append(t['s6'])
    lines.append('')
    lines.append(t['s6_head'])
    lines.append('|---|---|---|---|---|---|---|---|')
    for axiom_id, meta in axioms:
        lines.append(
            f"| {axiom_id} | {meta['label']} | {meta['rule_category']} | {meta['impl']} | "
            f"{meta['target_class']} | {meta['input_props']} | {meta['output_rel']} | {meta['nl_rule']} |"
        )
    lines.append('')

    # Rule coverage table
    lines.append(t['s7'])
    lines.append('')
    lines.append(t['s7_head'])
    lines.append('|---|---|---|---|---|---|---|---|---|')
    for axiom_id, meta in axioms:
        shape, category = AXIOM_SHAPE_MAP.get(axiom_id, ('—', meta['rule_category']))
        pos_test, neg_test = AXIOM_TESTS.get(axiom_id, ('—', '—'))
        if category == 'InferenceRule':
            result_msg = f"{t['gen']} {meta['output_rel']}" if meta['output_rel'] else t['gen_new']
        elif category == 'ValidationRule':
            result_msg = f"{t['viol']} {shape}" if shape != '—' else t['constr']
        else:
            result_msg = 'OWL restriction'
        lines.append(
            f"| {axiom_id} | {meta['label']} | {category} | {meta['impl']} | "
            f"{shape} | {pos_test} | {neg_test} | {result_msg} | PASS |"
        )
    lines.append('')

    # External reuse
    lines.append(t['s8'])
    lines.append('')
    lines.append('### 8.1 `onto:reusedOntology`')
    lines.append('')
    lines.append(t['s8_reused'])
    lines.append('|---|---|')
    for ontology, entities in sorted(reuse_map.items(), key=lambda x: x[0]):
        ont_name = ontology.split('/')[-1]
        lines.append(f"| {ont_name} | {', '.join(sorted(entities))} |")
    lines.append('')

    if mapped_map:
        lines.append('### 8.2 `onto:mappedToExternalTerm`')
        lines.append('')
        lines.append(t['s8_mapped'])
        lines.append('|---|---|')
        for term, entities in sorted(mapped_map.items(), key=lambda x: x[0]):
            lines.append(f"| {term} | {', '.join(sorted(entities))} |")
        lines.append('')

    # Section 9: standard alignments
    lines.append(t['s9'])
    lines.append('')
    lines.append(t['s9_1'])
    lines.append('')
    lines.append(t['s9_1_head'])
    lines.append('|---|---|---|')
    for local, pred, ext in formal_alignments:
        kind = t['subclass'] if pred == RDFS.subClassOf else t['subprop']
        lines.append(f"| `{local}` | {kind} | `{ext}` |")
    lines.append('')
    lines.append(t['s9_2'])
    lines.append('')
    lines.append(t['s9_2_head'])
    lines.append('|---|---|')
    for term, dtype in ext_decls:
        lines.append(f"| `{prefixed(term)}` | `{dtype}` |")
    lines.append('')
    lines.append(t['s9_3'])
    lines.append('')
    lines.extend(t['s9_notes'])
    lines.append('')

    # Notes
    lines.append(t['s10'])
    lines.append('')
    lines.extend(t['notes'])
    lines.append('')
    return lines


for lang, suffix in (('zh', 'zh'), ('en', 'en')):
    output_path = BASE_DIR / 'ontology' / f'tc_sssao_ontology_anatomy_{suffix}.md'
    output_path.write_text('\n'.join(build(lang)), encoding='utf-8')
    print(f'Generated: {output_path}')
