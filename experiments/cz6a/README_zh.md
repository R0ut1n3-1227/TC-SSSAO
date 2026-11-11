# CZ-6A 2022-151B 单案例表示与推理实验

本实验仿照“面向太空网络战威胁的态势感知本体建模”的单案例验证范式：
围绕一个具体案例建立实例知识库，执行OWL/RDFS与SHACL-SPARQL推理，展示推理前后的新增知识。

## 放置位置

将本目录复制到：

```text
TC-SSSAO/experiments/cz6a_case_reasoning/
```

## 运行

在TC-SSSAO工程根目录执行：

```bash
python -m pip install -r requirements.txt
python experiments/cz6a_case_reasoning/run_case_reasoning.py
```

## 结果

运行后生成：

- `outputs/graph_before.ttl`：推理前显式事实；
- `outputs/case_abox_after.ttl`：推理后的案例ABox；
- `outputs/inferred_triples.csv`：新增案例三元组；
- `outputs/query_results.csv`：四类能力问题查询结果；
- `outputs/case_reasoning_graph.dot`：推理关系图源文件（不再随附
  渲染版 SVG：本地无 graphviz 时旧的 SVG 渲染会滞后于 .dot 内容；
  需要渲染时在具备 graphviz 的环境执行
  `dot -Tsvg outputs/case_reasoning_graph.dot -o outputs/case_reasoning_graph.svg`）；
- `outputs/case_reasoning_report.md`：实验报告；
- `outputs/case_reasoning_summary.json`：机器可读摘要。

## 论文结论边界

本实验可以证明TC-SSSAO能够统一表示CZ-6A解体案例中的空间对象、轨道、观测数据、评估数据、事件、威胁、风险和响应措施，并通过通用规则推导隐含的事件时序、因果桥接以及威胁—风险—响应投影关系。态势状态与状态转移的推导由通用规则验证场景（rule_logic_verification，R5—R8、B3）承担，本案例不含态势状态与状态转移实例。

本实验不能证明具体碰撞预测准确率。
