# TC-SSSAO

**Temporal-Causal Space Security Situational Awareness Ontology**  
时序因果太空安全态势感知本体。

TC-SSSAO 以空间事件为核心，组织空间目标、轨道、观测数据、事件关系、风险状态和响应措施。本体使用 OWL 表达概念和关系。SHACL-SPARQL 规则支持时间关系、事件关联、风险状态和状态转移推理。

## 本体文件

- [OWL 本体](ontology/tc_sssao.owl)
- [标准对齐](ontology/tc_sssao_alignments.ttl)
- [中文本体说明](ontology/tc_sssao_ontology_anatomy_zh.md)
- [English ontology documentation](ontology/tc_sssao_ontology_anatomy_en.md)
- [SHACL-SPARQL 规则](rules/tc_sssao_rules.ttl)
- [规则参数配置](rules/tc_sssao_rule_config.ttl)

本体 IRI：`https://w3id.org/tc-sssao`  
命名空间：`https://w3id.org/tc-sssao#`

## 目录

| 路径 | 内容 |
|---|---|
| `ontology/` | OWL 本体、标准对齐及中英文说明 |
| `rules/` | R1—R18、B1—B5、配置、完整性约束及示例夹具 |
| `src/tc_sssao/` | 本体模式层源码和融合模块 |
| `scripts/build/` | 本体构建、导出、规范化及说明生成工具 |
| `scripts/utils/` | SHACL 固定点推理工具 |
| `requirements.txt` | Python 依赖 |

## 使用

可使用 Protégé 打开 `ontology/tc_sssao.owl`。支持 RDF 的工具可直接读取 OWL 和 Turtle 文件。

Python 中加载本体：

```python
from rdflib import Graph

ontology = Graph().parse("ontology/tc_sssao.owl", format="xml")
```

需要应用规则时，加载 `rules/tc_sssao_rules.ttl`、参数配置和对应的完整性约束。`scripts/utils/shacl_utils.py` 提供固定点推理工具。

## 源码维护

安装依赖：

```bash
pip install -r requirements.txt
```

本体模式层在 `src/tc_sssao/` 中维护。`domain_layer.py` 是融合模块生成的中间文件。

按需构建本体：

```bash
python scripts/build/build_ontology.py
```

构建器包含内部检查；仅在明确需要构建时运行。日常编辑不自动执行构建、验证或审核。

公开仓库仅收录本体相关资源。论文、实验结果、数据集和其他本地资料不在发布范围内。
