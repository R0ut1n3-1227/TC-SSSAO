import re, sys
from pathlib import Path

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE_DIR = _find_project_root(Path(__file__).parent)
sys.path.insert(0, str(BASE_DIR / "src"))
from tc_sssao.meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction

modules_dir = BASE_DIR / "src" / "tc_sssao" / "fusion_modules"

module_files = [
    'space_object_converted.py',
    'orbit_geometry.py',
    'ontology_observation_system_ssa_activity_py.py',
    'data_and_format.py',
    'e__PythonProject_spaceOntologic_ontology_space_event_module_py.py',
    'ontology_security_threat_risk_response_py.py',
    'temporal_causal_state.py',
    'ontology_space_mission_organization.py',
    'extensions.py',
]

all_classes = {}
all_properties = {}
all_relations = {}

def collect_objects(obj):
    if isinstance(obj, OntologyClass):
        if obj.name_en not in all_classes:
            all_classes[obj.name_en] = obj
        else:
            existing = all_classes[obj.name_en]
            # 合并后续定义提供的父类与等价交集
            merged_parents = list(dict.fromkeys(existing.parents + obj.parents))
            existing.parents = merged_parents
            merged_equiv = list(dict.fromkeys(getattr(existing, 'equivalent_to', []) + getattr(obj, 'equivalent_to', [])))
            existing.equivalent_to = merged_equiv
            # 后续定义的 description 更长时采用后续定义
            if len(obj.description) > len(existing.description):
                existing.description = obj.description
    elif isinstance(obj, OntologyProperty):
        if obj.name not in all_properties:
            all_properties[obj.name] = obj
    elif isinstance(obj, OntologyRelation):
        if obj.name not in all_relations:
            all_relations[obj.name] = obj
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            collect_objects(item)

for filename in module_files:
    path = modules_dir / filename
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()
    code = re.sub(r'from\s+\.\.?meta_schema\s+import\s+[^\n]+',
                  'from tc_sssao.meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction', code)
    code = re.sub(r'parents=\[([A-Za-z_][A-Za-z0-9_]*)\]', r'parents=["\1"]', code)
    code = re.sub(r'domain=([A-Z][A-Za-z0-9_]*)(\s*[\),])', r'domain="\1"\2', code)
    code = re.sub(r'range=([A-Z][A-Za-z0-9_]*)(\s*[\),])', r'range="\1"\2', code)

    module_globals = {
        '__name__': f'fusion_modules.{filename[:-3]}',
        '__package__': 'ontology.fusion_modules',
        '__file__': str(path),
    }
    exec(compile(code, str(path), 'exec'), module_globals)

    for name, obj in module_globals.items():
        if name.startswith('_'):
            continue
        collect_objects(obj)

# 修复命名冲突并更新类 properties 引用
old_to_new_prop = {}
if 'hasOperatorName' not in all_properties and 'hasOperator' in all_properties:
    old = all_properties.pop('hasOperator')
    new = OntologyProperty(
        name='hasOperatorName', datatype=old.datatype, name_zh='运营方名称',
        description='目标运营方名称。', domain=old.domain,
    )
    all_properties['hasOperatorName'] = new
    old_to_new_prop[id(old)] = new

for cls in all_classes.values():
    cls.properties = [old_to_new_prop.get(id(p), p) for p in cls.properties]

# 更新类 restriction 中的属性名引用
prop_rename_map = {
    'hasOperator': 'hasOperatorName',
}
for cls in all_classes.values():
    new_restrictions = []
    for r in cls.restrictions:
        if r.property_name in prop_rename_map:
            new_restrictions.append(OntologyRestriction(
                property_name=prop_rename_map[r.property_name],
                target=r.target,
                restriction_type=r.restriction_type,
            ))
        else:
            new_restrictions.append(r)
    cls.restrictions = new_restrictions

# 添加缺失的核心关系
core_relations = [
    ('causesEvent', '导致事件', 'SpaceEvent', 'SpaceEvent', '某事件导致另一事件发生。', None, False, False),
    ('causedByEvent', '由事件导致', 'SpaceEvent', 'SpaceEvent', '某事件由另一事件导致。', 'causesEvent', False, False),
    ('triggersEvent', '触发事件', 'SpaceEvent', 'SpaceEvent', '某事件触发另一事件发生。', None, False, False),
    ('triggeredByEvent', '被事件触发', 'SpaceEvent', 'SpaceEvent', '某事件被另一事件触发。', 'triggersEvent', False, False),
    ('resultsInEvent', '产生事件', 'SpaceEvent', 'SpaceEvent', '某事件产生另一事件。', None, False, False),
    ('resultedFromEvent', '由事件产生', 'SpaceEvent', 'SpaceEvent', '某事件由另一事件产生。', 'resultsInEvent', False, False),
]
for name, zh, domain, range_, desc, inv, sym, trans in core_relations:
    if name not in all_relations:
        all_relations[name] = OntologyRelation(
            name=name, name_zh=zh, domain=domain, range=range_,
            description=desc, inverse_of=inv, symmetric=sym, transitive=trans,
        )

# 更新类 restriction 中的属性名引用
prop_rename_map = {
    'hasOperator': 'hasOperatorName',
}
for cls in all_classes.values():
    new_restrictions = []
    for r in cls.restrictions:
        if r.property_name in prop_rename_map:
            new_restrictions.append(OntologyRestriction(
                property_name=prop_rename_map[r.property_name],
                target=r.target,
                restriction_type=r.restriction_type,
            ))
        else:
            new_restrictions.append(r)
    cls.restrictions = new_restrictions

# 添加缺失的 SpaceEnvironment 及其子类
space_env_children = [
    ("SpaceWeather", "空间天气"),
    ("RadiationEnvironment", "辐射环境"),
    ("MicrometeoroidEnvironment", "微流星体环境"),
    ("OrbitalCongestionEnvironment", "轨道拥堵环境"),
    ("ElectromagneticEnvironment", "电磁环境"),
]
space_env = OntologyClass(
    name_en="SpaceEnvironment",
    name_zh="空间环境",
    description="描述空间环境条件。",
    namespace="domain",
)
all_classes["SpaceEnvironment"] = space_env
all_classes["SpaceWeather"] = OntologyClass(
    name_en="SpaceWeather", name_zh="空间天气", description="空间天气。",
    namespace="domain", parents=["SpaceEnvironment"],
)
for name, zh in space_env_children:
    if name in all_classes:
        continue
    all_classes[name] = OntologyClass(
        name_en=name, name_zh=zh, description=f"{zh}。",
        namespace="domain", parents=["SpaceEnvironment"],
    )

# ============================================================
# 后处理：修复 domain 污染、整理数据/活动关系、补全基数
# ============================================================

# -- 数据属性 domain 修正
for _pname, _new_domain in (("hasErrorValue", "SSAData"), ("hasDataConfidence", "SSAData"), ("hasRiskValue", "RiskEvent")):
    if _pname in all_properties:
        old = all_properties.pop(_pname)
        all_properties[_pname] = OntologyProperty(
            name=old.name, datatype=old.datatype, name_zh=old.name_zh,
            description=old.description, domain=_new_domain,
        )
for _pname in ("hasDuration", "hasStateDuration"):
    if _pname in all_properties:
        old = all_properties.pop(_pname)
        all_properties[_pname] = OntologyProperty(
            name=old.name, datatype="duration", name_zh=old.name_zh,
            description=old.description, domain=old.domain,
        )
if "hasMissionType" in all_properties:
    old = all_properties.pop("hasMissionType")
    all_properties["hasMissionType"] = OntologyProperty(
        name=old.name, datatype=old.datatype, name_zh=old.name_zh,
        description=old.description, domain="Spacecraft",
    )

# 新增几何误差属性
if "hasGeometricErrorValue" not in all_properties:
    all_properties["hasGeometricErrorValue"] = OntologyProperty(
        name="hasGeometricErrorValue", datatype="float",
        name_zh="几何误差值", description="几何构造的误差值。",
        domain="GeometricConstruct",
    )

# -- 对象属性 domain/range 修正
if "generatesData" in all_relations:
    old = all_relations.pop("generatesData")
    all_relations["generatesData"] = OntologyRelation(
        name="generatesData", name_zh=old.name_zh,
        domain="ObservationSystem", range="ObservationData",
        description="观测系统生成观测数据。", inverse_of="generatedBy",
    )

if "generatedBy" in all_relations:
    old = all_relations.pop("generatedBy")
    all_relations["generatedBy"] = OntologyRelation(
        name="generatedBy", name_zh=old.name_zh,
        domain="ObservationData", range="ObservationSystem",
        description="观测数据由观测系统生成。",
        inverse_of="generatesData",
    )
else:
    all_relations["generatedBy"] = OntologyRelation(
        name="generatedBy", name_zh="由……生成",
        domain="ObservationData", range="ObservationSystem",
        description="观测数据由观测系统生成。",
        inverse_of="generatesData",
    )

if "generatedByActivity" in all_relations:
    old = all_relations.pop("generatedByActivity")
    all_relations["generatedByActivity"] = OntologyRelation(
        name="generatedByActivity", name_zh=old.name_zh,
        domain="SSAData", range="SSAActivity",
        description="SSA 数据由 SSA 活动生成。",
        inverse_of="producesData",
    )

if "producesData" not in all_relations:
    all_relations["producesData"] = OntologyRelation(
        name="producesData", name_zh="产生活动数据",
        domain="SSAActivity", range="SSAData",
        description="SSA 活动产生 SSA 数据。",
        inverse_of="generatedByActivity",
    )

# 新增事件专用属性
if "observedBySensor" not in all_relations:
    all_relations["observedBySensor"] = OntologyRelation(
        name="observedBySensor", name_zh="由传感器观测",
        domain="ObservationEvent", range="Sensor",
        description="观测事件由传感器观测。",
    )
if "riskLeadsToState" not in all_relations:
    all_relations["riskLeadsToState"] = OntologyRelation(
        name="riskLeadsToState", name_zh="风险导致状态",
        domain="SecurityRisk", range="SituationState",
        description="安全风险导致态势状态。",
    )
if "threatMitigatedBy" not in all_relations:
    all_relations["threatMitigatedBy"] = OntologyRelation(
        name="threatMitigatedBy", name_zh="威胁被缓解",
        domain="SecurityThreat", range="ResponseMeasure",
        description="安全威胁被响应措施缓解。",
    )


def replace_restriction(cls, old_prop, new_prop=None):
    """移除指定属性的 restriction；若 new_prop 为 None 仅移除。"""
    cls.restrictions = [r for r in cls.restrictions if r.property_name != old_prop]


def add_restriction(cls, prop, target, rtype="someValuesFrom", **kwargs):
    """幂等地添加 restriction（避免完全重复）。"""
    for r in cls.restrictions:
        if r.property_name == prop and r.target == target and r.restriction_type == rtype:
            return
    cls.restrictions.append(OntologyRestriction(prop, target, rtype, **kwargs))


if "SpaceObject" in all_classes:
    add_restriction(all_classes["SpaceObject"], "hasOrbit", "Orbit", "someValuesFrom")

if "ObservationSystem" in all_classes:
    add_restriction(all_classes["ObservationSystem"], "generatesData", "ObservationData", "someValuesFrom")

# -- 类 restriction 修正
if "Spacecraft" in all_classes:
    add_restriction(all_classes["Spacecraft"], "hasMissionType", "string", "someValuesFrom")

if "ObservationEvent" in all_classes:
    replace_restriction(all_classes["ObservationEvent"], "madeBySensor")
    replace_restriction(all_classes["ObservationEvent"], "hasFeatureOfInterest")
    add_restriction(all_classes["ObservationEvent"], "observedBySensor", "Sensor", "someValuesFrom")

if "SecurityRisk" in all_classes:
    replace_restriction(all_classes["SecurityRisk"], "leadsToState")
    add_restriction(all_classes["SecurityRisk"], "riskLeadsToState", "SituationState", "someValuesFrom")

if "SecurityThreat" in all_classes:
    replace_restriction(all_classes["SecurityThreat"], "mitigatedBy")
    add_restriction(all_classes["SecurityThreat"], "requiresResponseMeasure", "ResponseMeasure", "someValuesFrom")
    add_restriction(all_classes["SecurityThreat"], "threatMitigatedBy", "ResponseMeasure", "someValuesFrom")

if "CausalAssertion" in all_classes:
    all_classes["CausalAssertion"].restrictions = [
        r for r in all_classes["CausalAssertion"].restrictions
        if r.property_name not in {"hasCause", "hasEffect", "hasCausalEvidence", "hasCausalConfidence"}
    ]
    add_restriction(all_classes["CausalAssertion"], "hasCause", "SpaceEvent", "minCardinality", min_cardinality=1)
    add_restriction(all_classes["CausalAssertion"], "hasEffect", "SpaceEvent", "cardinality", cardinality=1)
    add_restriction(all_classes["CausalAssertion"], "hasCausalEvidence", "SSAData", "minCardinality", min_cardinality=1)
    # M3 第一阶段（2026-09-04）：hasCausalConfidence 由 exactly 1 放宽为 max 1。
    # 因果置信度是可选上下文元数据：来源/专家/外部模型提供定量置信信息时记录，
    # 未给出时不强制赋值（公开来源通常不提供因果关系的定量置信度）。
    add_restriction(all_classes["CausalAssertion"], "hasCausalConfidence", "float", "maxCardinality", max_cardinality=1)

if "MultiCauseAssertion" in all_classes:
    # 移除可能存在的 hasCause some
    all_classes["MultiCauseAssertion"].restrictions = [
        r for r in all_classes["MultiCauseAssertion"].restrictions if r.property_name != "hasCause"
    ]
    add_restriction(all_classes["MultiCauseAssertion"], "hasCause", "SpaceEvent", "minCardinality", min_cardinality=2)

if "StateTransition" in all_classes:
    all_classes["StateTransition"].restrictions = [
        r for r in all_classes["StateTransition"].restrictions
        if r.property_name not in {"hasSourceState", "hasTargetState", "triggeredByEvent"}
    ]
    add_restriction(all_classes["StateTransition"], "hasSourceState", "SituationState", "cardinality", cardinality=1)
    add_restriction(all_classes["StateTransition"], "hasTargetState", "SituationState", "cardinality", cardinality=1)
    add_restriction(all_classes["StateTransition"], "triggeredByEvent", "SpaceEvent", "minCardinality", min_cardinality=1)

if "GeometricConstruct" in all_classes:
    geom = all_classes["GeometricConstruct"]
    if "hasGeometricErrorValue" not in {p.name for p in geom.properties}:
        geom.properties.append(all_properties["hasGeometricErrorValue"])

# 生成新的 domain_layer.py
lines = []
lines.append('"""TC-SSSAO -- 基于时序因果联合建模的太空安全态势感知本体')
lines.append('')
lines.append('Top-level branches: SpaceObject, Orbit, GeometricConstruct, SpaceEnvironment,')
lines.append('                   ObservationSystem, SSAActivity, SSAData, SpaceEvent,')
lines.append('                   SecurityThreat, SecurityRisk, SituationState, StateTransition,')
lines.append('                   CausalAssertion, ResponseMeasure, SpaceOrganization,')
lines.append('                   TemporalEntity')
lines.append('"""')
lines.append('from __future__ import annotations')
lines.append('')
lines.append('from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation, OntologyRestriction')
lines.append('')

lines.append('# ============================================================')
lines.append('# Data Properties')
lines.append('# ============================================================')
for name in sorted(all_properties.keys()):
    p = all_properties[name]
    var = f'PROP_{p.name.upper()}'
    lines.append(f'{var} = OntologyProperty(')
    lines.append(f'    name="{p.name}", datatype="{p.datatype}",')
    lines.append(f'    name_zh="{p.name_zh}",')
    lines.append(f'    description="{p.description}",')
    lines.append(f'    domain="{p.domain}",')
    lines.append(')')
    lines.append('')

lines.append('# ============================================================')
lines.append('# Object Properties / Relations')
lines.append('# ============================================================')
rel_vars = {}
for i, name in enumerate(sorted(all_relations.keys()), 1):
    r = all_relations[name]
    var = f'REL_{i:03d}_{r.name.upper()}'
    rel_vars[name] = var
    lines.append(f'{var} = OntologyRelation(')
    lines.append(f'    name="{r.name}",')
    lines.append(f'    name_zh="{r.name_zh}",')
    lines.append(f'    domain="{r.domain}",')
    lines.append(f'    range="{r.range}",')
    lines.append(f'    description="{r.description}",')
    if r.inverse_of:
        lines.append(f'    inverse_of="{r.inverse_of}",')
    if r.symmetric:
        lines.append('    symmetric=True,')
    if r.transitive:
        lines.append('    transitive=True,')
    if r.irreflexive:
        lines.append('    irreflexive=True,')
    if r.asymmetric:
        lines.append('    asymmetric=True,')
    if r.sub_property_of:
        lines.append(f'    sub_property_of="{r.sub_property_of}",')
    if getattr(r, "deprecated", False):
        lines.append('    deprecated=True,')
    lines.append(')')
    lines.append('')

lines.append('# ============================================================')
lines.append('# Classes')
lines.append('# ============================================================')
cls_vars = {}

def topo_sort(classes):
    visited = set()
    order = []
    def visit(name):
        if name in visited:
            return
        visited.add(name)
        for p in classes[name].parents:
            if p in classes:
                visit(p)
        order.append(name)
    for name in sorted(classes.keys()):
        visit(name)
    return order

order = topo_sort(all_classes)
for i, name in enumerate(order, 1):
    c = all_classes[name]
    var = f'CLS_{i:03d}_{c.name_en.upper()}'
    cls_vars[name] = var
    lines.append(f'{var} = OntologyClass(')
    lines.append(f'    name_en="{c.name_en}",')
    lines.append(f'    name_zh="{c.name_zh}",')
    lines.append(f'    description="{c.description}",')
    lines.append(f'    namespace="{c.namespace}",')
    if c.parents:
        lines.append(f'    parents={c.parents},')
    if getattr(c, 'equivalent_to', []):
        lines.append(f'    equivalent_to={c.equivalent_to},')
    if c.properties:
        prop_vars = [f'PROP_{p.name.upper()}' for p in c.properties]
        lines.append(f'    properties=[{", ".join(prop_vars)}],')
    if c.restrictions:
        def _restr_repr(r):
            parts = [f'"{r.property_name}"', f'"{r.target}"', f'"{r.restriction_type}"']
            if r.min_cardinality is not None:
                parts.append(f'min_cardinality={r.min_cardinality}')
            if r.max_cardinality is not None:
                parts.append(f'max_cardinality={r.max_cardinality}')
            if r.cardinality is not None:
                parts.append(f'cardinality={r.cardinality}')
            if getattr(r, 'has_value', None):
                parts.append(f'has_value={r.has_value!r}')
            return f'OntologyRestriction({", ".join(parts)})'

        restrs = [_restr_repr(r) for r in c.restrictions]
        lines.append(f'    restrictions=[{", ".join(restrs)}],')
    lines.append(')')
    lines.append('')

lines.append('# ============================================================')
lines.append('# Aggregations')
lines.append('# ============================================================')
lines.append('ALL_CLASSES: tuple[OntologyClass, ...] = (')
for name in order:
    lines.append(f'    {cls_vars[name]},')
lines.append(')')
lines.append('')
lines.append('DATA_PROPERTIES: tuple[OntologyProperty, ...] = (')
for name in sorted(all_properties.keys()):
    lines.append(f'    PROP_{name.upper()},')
lines.append(')')
lines.append('')
lines.append('OBJECT_PROPERTIES: tuple[OntologyRelation, ...] = (')
for name in sorted(all_relations.keys()):
    lines.append(f'    {rel_vars[name]},')
lines.append(')')
lines.append('')

output_path = BASE_DIR / 'src' / 'tc_sssao' / 'domain_layer.py'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'Generated {output_path}: {len(lines)} lines')
print(f'Classes: {len(all_classes)}, Properties: {len(all_properties)}, Relations: {len(all_relations)}')
