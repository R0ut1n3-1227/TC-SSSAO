# TC-SSSAO

Temporal-Causal Space Security Situational Awareness Ontology。

## 从这里开始

- 论文源码：[paper/TC-SSSAO.tex](paper/TC-SSSAO.tex)
- 论文 PDF：[paper/TC-SSSAO.pdf](paper/TC-SSSAO.pdf)
- 本体文件：[ontology/tc_sssao.owl](ontology/tc_sssao.owl)
- 详细目录：[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)
- 数据与事实来源：[docs/source_mapping.md](docs/source_mapping.md)

## 目录分工

| 目录 | 放什么 |
|---|---|
| `paper/` | 论文、章节、参考文献、图件及论文构建脚本 |
| `ontology/` | 构建后的 OWL、标准对齐及本体说明 |
| `rules/` | 推理规则、阈值配置、SHACL 约束 |
| `src/` | 本体的 Python 源码 |
| `experiments/` | 各实验的脚本、输入、查询与结果 |
| `data/` | 原始数据、处理数据、本体统计、对齐基线和概念决策 |
| `docs/` | 方法说明、来源映射、ESA 说明与参考文献资料 |
| `scripts/` | 本体构建、图件和其他工具 |
| `tests/` | 保留的独立测试代码，按需使用 |

## 主要实验

| 目录 | 用途 |
|---|---|
| `experiments/tracss/` | TraCSS 数据适配与风险状态分类 |
| `experiments/tracss_threshold_sensitivity/` | TraCSS 阈值敏感性 |
| `experiments/cz6a/` | CZ-6A 案例推理 |
| `experiments/counterfactual_verification/` | 反事实实验 |
| `experiments/rule_logic_verification/` | 规则场景与边界实验 |
| `experiments/module_ablation/` | 模块消融 |
| `experiments/standard_interoperability/` | 标准互操作 |
| `experiments/esa_cdm/` | 保留的 ESA 实验及内部对照 |
| `experiments/esa_threshold_sensitivity/` | 保留的 ESA 阈值敏感性对照 |

TraCSS 原始文件统一位于 `data/tracss/raw/`；ESA 数据位于 `data/esa_cdm/`。

## 按需运行

构建论文：`python paper/build_paper.py`。

论文使用 Applied Ontology 的 SAGE 单栏 Royal 模板（`paper/sagej.cls`），引用采用 APA 作者—年份形式。模板来自 [SAGE 官方下载](https://www.sagepub.com/docs/default-source/rp-pages/info-for-authors/sage-latex-template.zip?sfvrsn=54789065_1)，期刊要求见 [Applied Ontology 投稿指南](https://journals.sagepub.com/author-instructions/apo)。原 `fcs.cls` 和 `fcs.bst` 保留，主文件不再使用。

论文已按用户要求编译，并查看 PDF 排版。`paper/submission-layout.sty` 保留 Royal 页面尺寸，使用全宽标题，并隐藏尚未分配的出版元数据。编译结果记录于 `paper/build_report.json`。已补入伦理与同意声明、公开数据来源，并补充参考文献作者列表和来源链接。作者贡献分工、通讯电话，以及 TC-SSSAO 本体、代码和派生结果的公开地址或获取方式仍需作者提供；稿件和源码中保留明确提示。

构建本体：`python scripts/build/build_ontology.py`。

实验分别从各目录的运行器启动。常规维护不自动运行审核、测试或实验复测，约定见 [AGENTS.md](AGENTS.md)。
