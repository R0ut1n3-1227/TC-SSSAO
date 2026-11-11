# 模块消融、因果一致性故障注入与证据反事实实验

回答的审稿问题：**现有实验是否只是验证规则按定义运行？时序、因果、态势和
一致性模块分别对系统能力产生什么实际作用？**

## 设计原则

- 全部消融 variant 从**同一份本体、同一份输入数据、同一份主规则库**
  （`rules/tc_sssao_rules.ttl`）出发；variant 之间的唯一差别是在**内存中**
  禁用指定 `onto:ruleModule` 的规则 Shape（Shape 连同其 sh:rule/sh:sparql
  匿名子结构整体摘除）。
- 不修改任何规则的 WHERE/CONSTRUCT；不修改主规则文件；不修改输入事实；
  不手工删除结果三元组；不按 variant 单独调整输入。
- CQ 判定规则固定在 `run_ablation_study.py` 的 `cq_verdicts()` 中，
  PASS/PARTIAL/FAIL 由实验输出自动生成，不手工填表。

## 模块标签（规则 Shape 上的 onto:ruleModule）

| 模块 | Shape |
|---|---|
| Temporal | R1 事件先后、R2 事件重叠 |
| Causal | R3 机动→接近、R4 接近→风险、B1 因果断言桥接 |
| Situation | R5—R8 四级态势、B2 状态转移桥接、B3 态势演化桥接 |
| Consistency | R9 因果时序、R10 因果方向、R11 因果环 |
| SemanticProjection | B4 碎片风险语义投影、B5 风险响应投影 |
| DataValidation | R12—R18 等 15 个数据/结构验证 Shape |

## 输入数据（全部 variant 共享）

- `experiments/rule_logic_verification/data/scenario_facts.ttl`：四风险
  快照通用场景（同一交会目标对 T0—T3，承担 R1/R3—R8/B3 探针）；
- `data/bridge_fixtures.ttl`：B1 独立桥接夹具（CausalAssertion）、B2 独立
  桥接夹具（StateTransition）、时序重叠夹具（承担 CQ2 的 overlap 子项，
  四快照场景事件互不重叠、R2 在该场景无输出）；
- `data/causal_fault_F1.ttl` / `causal_fault_F2.ttl` / `causal_fault_F3.ttl`：
  故障注入，**三个文件各自独立成图运行**（不并入主消融数据图），避免
  不同故障的焦点节点混入同一次检出结果。F1 时间逆序（主检测器 R9）、
  F2 双向互指（主检测器 R10；互指结构同时构成 `(causesEvent)+` 意义下
  长度为 2 的闭环，R11 为附加检测器）、F3 三事件因果环（主检测器 R11，
  焦点节点仅 EvtCycle1/2/3）。故障事件为 SpaceEvent 直接实例 + 携带证据，
  隔离 R3/R4/R5—R8/R13 附带触发；F2/F3 同刻以隔离 R9。
- `data/evidence_counterfactual.ttl`：证据反事实 E1（Approach 缺 R3 所需
  ObservationData 证据）/E2（CollisionRisk 缺 R4 所需 ObservationData
  证据）。E1 与 E2 使用互不相同的交会目标对，套件中不存在跨场景附带
  因果边。该数据单独成图运行，不进入主消融数据图。

## 运行

```bash
python experiments/module_ablation/run_ablation_study.py
```

## 输出（outputs/，全部由脚本生成）

| 文件 | 内容 |
|---|---|
| `ablation_results.csv` / `.json` | 5 个 variant 的模块能力布尔探针与 CQ2—CQ6 判定 |
| `consistency_fault_results.csv` | F1/F2/F3 在 FULL 与 w/o Consistency 下的检出对比（Shape + 焦点节点） |
| `evidence_counterfactual_results.csv` | E1/E2 在 FULL 与 NO_EVIDENCE_CONSTRAINT 下的边生成对比与 spurious_causal_edges 指标 |
| `robustness_results.csv` | 五项稳健性测试的解释表（Test/FULL/AblatedVariant/Interpretation） |
| `ablation_table.tex` / `robustness_table.tex` | 论文 4.2.5 直接 `\input` 的表片段，数值禁止手工编辑 |
| `ablation_summary.json` | 汇总（含固定点轮数、图同构校验结果） |

## 关键结果（本次运行）

- **FULL**：CQ2—CQ6 全部 PASS；主数据图完全 conforms（故障夹具独立成图，
  不在主图内）；F1/F2/F3 主检测器全部命中；E1/E2 不生成因果边
  （spurious=0）。
- **w/o Temporal（R1、R2）**：CQ2 FAIL、CQ3 FAIL、CQ5 PARTIAL。
  状态分类（R5—R8）与 B1/B2 仍在，但因果链（R3/R4 的 WHERE 引用
  `precedesEvent`）与 B3 跨快照演化全部消失——**时序模块为因果与态势
  演化提供前提**。
- **w/o Causal（R3、R4、B1）**：CQ3 FAIL、CQ4 FAIL；R5—R8 状态分类与
  B3 演化不受影响（CQ5 PASS）——外部评估仍可映射态势。
- **w/o Situation（R5—R8、B2、B3）**：CQ5 FAIL、CQ6 FAIL；时序与因果
  完好。
- **w/o Consistency（R9—R11）**：CQ3 PARTIAL；**知识生成与 FULL 完全
  一致**（IRI 差集为空 + 收敛图同构），但三类故障检出从 3/3 降为 0/3——
  一致性模块的作用是把"能生成"升级为"能发现矛盾"，不是无作用。
- **证据反事实**：NO_EVIDENCE_CONSTRAINT（仅在内存中摘除 R3/R4 的证据
  图模式，每条规则恰删 4 行，主规则文件不变）使 spurious_causal_edges
  从 0 升至 2——证据前件的实际作用是**抑制无证据因果关联**（不声称
  "证明因果关系正确"）。

## 故障检测器归属（逐故障独立运行的实测结果）

| 故障 | 主检测器 | 附加检测器 | 焦点节点 |
|---|---|---|---|
| F1 时间逆序 | R9 | — | EvtLate |
| F2 双向互指 | R10 | R11 | EvtPairA、EvtPairB |
| F3 因果闭环 | R11 | — | EvtCycle1、EvtCycle2、EvtCycle3 |

双向因果本身同时构成长度为 2 的因果闭环，因此 R10 为 F2 的直接冲突
检测器，R11 可同时识别其闭环结构。三类故障的主检测器在 w/o Temporal、
w/o Causal、w/o Situation 下仍全部命中（故障的 causesEvent 与时间均为
显式输入），在 w/o Consistency 下全部消失——故障检测能力唯一依赖
一致性模块。
