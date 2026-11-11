# 工作区目录说明

更新日期：2026-10-22。项目入口见根目录 README.md。

```text
TC-SSSAO/
├── README.md                 项目入口与常用路径
├── AGENTS.md                 工作约定
├── paper/                    论文工作目录
│   ├── TC-SSSAO.tex          正式论文主文件
│   ├── TC-SSSAO.pdf          论文 PDF
│   ├── sections/            正文章节
│   ├── bibliography/        参考文献
│   └── figures/             论文图件及编辑文件
├── ontology/                 OWL、标准对齐、本体说明
├── rules/                    规则、配置和约束
├── src/tc_sssao/              本体源码
├── experiments/              按实验划分的工作目录
├── data/
│   ├── tracss/raw/           TraCSS 原始数据与用户指南
│   ├── esa_cdm/              ESA 原始、处理数据与元数据
│   ├── baselines/            对齐基线与控制图
│   ├── decisions/            概念决策记录
│   └── current/              保留的本体统计和重建结果
├── docs/
│   ├── methods/              时间语义、终止性与可扩展性说明
│   ├── esa_cdm/              ESA 字段映射、统计及口径说明
│   ├── literature/           本地参考文献 PDF
│   └── figures/sources/      早期概念图的可编辑源
├── scripts/                  构建和辅助工具
└── tests/                    独立测试代码
```

实验目录通常包含运行器、data/ 或 queries/ 输入，以及 results/ 或 outputs/ 结果。结果留在各自实验中，避免与原始数据混放。ESA 的已有日志集中到 results/logs/，反事实实验的过程记录集中到 logs/。

本体 schema 从 src/tc_sssao/ 维护，由构建工具生成 ontology/tc_sssao.owl。融合模块保留现有文件名，避免破坏模块导入。

旧 dataset/ 已合并到 data/tracss/raw/；旧 reports/ 已并入 docs/esa_cdm/；论文不再套 English/ 子目录。CZ-6A 与 ESA 阈值实验分别使用 cz6a/、esa_threshold_sensitivity/。

本次只整理文件位置、名称和路径说明，不自动运行审核或实验。
