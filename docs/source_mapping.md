# TC-SSSAO 数据来源与来源映射

本文档明确哪些资源是项目原创、哪些事实来自第三方公开数据/文献，
以及 CZ-6A 案例中每条关键事实的具体出处。

## 1. 项目原创资源

| 资源 | 路径 | 说明 |
|---|---|---|
| 本体模式层 | `ontology/tc_sssao.owl` | OWL 2 模式（不含实例） |
| 通用规则集 | `rules/tc_sssao_rules.ttl` | SHACL-SPARQL 规则 R1—R18、B1—B5 及数据约束 |
| 规则部署配置 | `rules/tc_sssao_rule_config.ttl` | θ_A/θ_M 实验参考值（工程判据的部署配置，非领域常数） |
| 通用验证场景 | `experiments/rule_logic_verification/data/scenario_facts.ttl` | 人工构造的合成数据，不对应真实历史事件 |
| 边界/投影/置信度/消融/故障/反事实夹具 | `experiments/**/data/*.ttl` | 人工构造的合成测试数据 |
| 全部运行与验证脚本 | `experiments/`、`scripts/`、`tests/` | Python 源码 |

## 2. 外部事实来源（不重新分发原文）

本项目**不重新分发**任何受版权限制的第三方文献全文；仓库中仅保存来源
元数据、引用信息，以及由公开文献内容整理的案例事实（见下表）。
《面向太空网络战威胁的态势感知本体建模_刘斌.pdf》仅为图形风格参考文献，
不存于项目内（2026-09-13 扁平化随 references/ 一并移除），不进入任何构建。

| 外部来源 | 用途 | 在仓库中的存在形式 |
|---|---|---|
| NASA Orbital Debris Quarterly News, Vol. 27, Issue 1 | CZ-6A 解体时间、编目/在轨碎片数量 | 引用 + 案例事实字段值 |
| CelesTrak 历史编目资料 | CZ-6A 母体轨道（近地点 813 km / 远地点 847 km 等） | 引用 + 轨道字段值 |
| Wacker D R, et al. 2025（SDC9 paper 220） | 碎片环境长期碰撞风险评估 | 引用 + RiskAssessmentData 记录 |
| NASA CARA 手册（NASA-SP-20205011318）与 NPR 8079.1 | θ_A=1E-7 / θ_M=1E-4 碰撞概率判据、组合硬体半径定义 | 引用 + 部署配置参考值 |
| CCSDS 交会数据消息（CDM）标准 | hasCollisionProbability / hasPredictedMissDistance 等字段语义 | 引用（字段语义依据） |

## 3. CZ-6A 案例逐项来源映射

数据文件：`experiments/cz6a/data/case_facts.ttl`
（实例命名空间 `https://w3id.org/tc-sssao/data/cz6a-case#`）。

| 案例事实 | 字段/实例 | 来源 |
|---|---|---|
| 火箭末级身份（NORAD 编号 54236） | `CZ6A_2022_151B.hasObjectID` | NASA 编目 / ODQN 记录（论文引文 nasa2023odqn、celestrak） |
| 解体时间 2022-11-12 05:19 UTC | `CZ6A_Fragmentation_2022.hasOccurrenceTime` | NASA ODQN Vol.27 Issue 1 |
| 编目碎片 533 / 在轨 529 | `catalogedFragmentCount`、`fragmentsInOrbitCount` | NASA ODQN Vol.27 Issue 1 |
| 母体轨道 813×847 km、倾角 98.8° 等 | `CZ6A_Orbit_2022` 各字段 | CelesTrak 历史编目资料整理论文引文 celestrak |
| 碎片早期轨道（54263/54334/54344） | `Orbit_*_Early` 各字段 | CelesTrak 历史编目资料整理 |
| 解体碎片环境长期碰撞风险评估 | `CZ6A_DebrisRiskAssessment`（RiskAssessmentData） | Wacker et al. 2025 |
| "十年碰撞风险总体增加约20%"（仅论文行文） | 不记录为任何实例属性（见 case_facts.ttl 注释） | Wacker et al. 2025；该数值为 2022-151B 与 2024-140U 两次事件的联合估计，刻意不作为 2022-151B 单事件属性 |
| 碎片风险事件（显式知识） | `CZ6A_DebrisRiskEvent` | 依 Wacker et al. 2025 整理的显式事件知识 |
| 因果断言（解体→长期碎片风险） | `CZ6A_FragmentationRiskAssertion`（DirectCausalAssertion） | 依公开来源整理的显式断言；来源未给定量置信度，故不记录 |
| 持续跟踪响应措施 | `ContinuousTrackingMeasure` | 论文作者整理的案例层响应知识（非 NASA/Wacker 明确提出，见 case_facts.ttl 注释） |
| 碰撞概率/最近交会距离字段语义 | `hasCollisionProbability`、`hasPredictedMissDistance` | CCSDS CDM 标准字段语义 |
| θ_A / θ_M 实验参考值 | `RiskSituationRuleConfig`（rules/tc_sssao_rule_config.ttl） | NASA CARA / NPR 8079.1 工程判据 |

## 4. 本体生成关系（非来源事实）

以下关系**不来自任何外部来源**，由 TC-SSSAO 通用规则在案例数据上推理生成
（CZ-6A 不使用任何案例专属推理 Shape）：

- `precedesEvent` / `followsEvent`（R1）
- `causesEvent`（B1 由显式断言投影）
- 派生 `PhysicalThreat` / `DebrisRisk` 实例及 `indicatesThreat` /
  `mayManifestAsEvent` / `producesRisk`（B4）
- `requiresResponseMeasure` / `respondsToThreat` / `threatMitigatedBy` /
  `mitigatesRisk` / `mitigatedBy` / `respondsToEvent`（B5）

通用场景中的四级态势状态（Normal/Attention/Warning/Dangerous）是 TC-SSSAO
对 NASA 工程判据的实验语义映射，不是 NASA 官方状态分类。
