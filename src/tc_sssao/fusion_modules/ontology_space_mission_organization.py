"""TC-SSSAO 空间组织与约束规则模块

Top-level branches:
  SpaceOrganization
  └── DataProvider

注：R1–R18 规则定义与元数据由 src/tc_sssao/axioms.py 单独维护，
    作为独立 SHACL-SPARQL 规则层实现，不作为领域本体类。
"""
from __future__ import annotations

from .meta_schema import OntologyClass, OntologyProperty, OntologyRelation


# ============================================================
# Data Properties (camelCase names)
# ============================================================


# ============================================================
# Classes (PascalCase names)
# ============================================================

# ---------- SpaceOrganization ----------
CLS_SPACE_ORGANIZATION = OntologyClass(
    name_en="SpaceOrganization",
    name_zh="空间组织",
    description="描述空间相关组织的顶层抽象类。",
    namespace="domain",
    properties=[],
)

CLS_DATA_PROVIDER = OntologyClass(
    name_en="DataProvider",
    name_zh="数据提供方",
    parents=["SpaceOrganization"],
    description="提供空间观测或态势数据的组织。",
    namespace="domain",
)


# ============================================================
# Object Properties / Relations (camelCase names)
# ============================================================


# ============================================================
# Aggregations
# ============================================================

ALL_CLASSES: tuple[OntologyClass, ...] = (CLS_SPACE_ORGANIZATION, CLS_DATA_PROVIDER)

ALL_PROPERTIES: tuple[OntologyProperty, ...] = ()

ALL_RELATIONS: tuple[OntologyRelation, ...] = ()
