# TC-SSSAO 权威源地图

更新日期：2026-10-22。

| 信息 | 权威源或生成入口 |
|---|---|
| 正式论文正文 | `paper/TC-SSSAO.tex` 及其 sections/、bibliography/ |
| 正式论文 PDF | `paper/TC-SSSAO.pdf`，由 `paper/build_paper.py` 构建 |
| 论文图件 | `paper/figures/`；生成入口及编辑载体见 figure_sources.md |
| 本体模式层源 | `src/tc_sssao/`；domain_layer.py 是生成中间层 |
| 标准对齐源 | `ontology/tc_sssao_alignments.ttl` |
| 构建后的本体 | `ontology/tc_sssao.owl`，由 `scripts/build/build_ontology.py` 生成 |
| 规则与配置 | `rules/` |
| 当前 TraCSS 原始数据与字段依据 | `data/tracss/raw/` 中离散 HBR 数据、对象映射、用户指南 |
| TraCSS 状态结果 | `experiments/tracss/results/`，由该实验 scripts/ 生成 |
| TraCSS 敏感性结果 | `experiments/tracss_threshold_sensitivity/results/` |
| CZ-6A 事实、推理与结果 | `experiments/cz6a/` |
| 本体统计 | `scripts/report/generate_ontology_statistics.py` 对 canonical OWL 的实测 |
| 概念决策 | `data/decisions/` |

ESA 结果仍保留作内部对照，不再作为当前论文主要实验数字来源。
最近结果文件不等于本次重新运行的结果。论文与结果不一致时应核对执行路径和统计范围，不直接沿用旧值。
