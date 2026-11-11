# TC-SSSAO 风险状态阈值敏感性实验报告

- 实验日期：2026-09-18
- 实验脚本：[run_threshold_sensitivity.py](run_threshold_sensitivity.py)（新建文件，只读使用现有代码与数据）
- 机器可读结果：[outputs/threshold_sensitivity_results.json](outputs/threshold_sensitivity_results.json)
- 数据集：ESA Collision Avoidance Challenge 训练集（`data/esa_cdm/processed/esa_train_normalized.csv.gz`，162 634 条 CDM，13 154 个交会事件，全部通过 preflight）
- 本实验未修改任何现有代码、规则、本体、数据或论文文件；阈值仅在实验进程内存中改写，官方 `common.py` 常量与 `tc_sssao_rule_config.ttl` 保持原值。

---

## 1. Current implementation audit（当前真实实现核验）

### 1.1 涉及的实现文件

| 层 | 文件 | 角色 |
| --- | --- | --- |
| 规范层（SHACL） | `rules/tc_sssao_rules.ttl` | R5–R8 的 `sh:SPARQLRule` 构造体（规范实现） |
| 部署配置 | `rules/tc_sssao_rule_config.ttl` | 唯一配置实例 `onto:RiskSituationRuleConfig`，承载 θ_A、θ_M（必须合并进**数据图**） |
| 执行层（ESA 全量） | `experiments/esa_cdm/scripts/common.py` | `THETA_A = 1e-7`、`THETA_M = 1e-4`、`classify_states()`，被 `06_risk_state_eval.py` 调用产生官方基线 |
| RDF 门 | `experiments/esa_cdm/scripts/04_build_rdf.py` | `run_r5_r8_gate()` 在 50 事件 RDF 图上原样执行未修改的 R5–R8 构造体（rdflib SPARQL，迭代至零新增收敛） |
| 本体 | `ontology/tc_sssao.owl` | 仅声明 `hasCollisionProbability` / `hasPredictedMissDistance` / `hasCombinedHardBodyRadius` 三个 float 属性；**本体中无任何阈值数值**（阈值为部署配置，非领域常数） |

### 1.2 R5–R8 完整条件（以 `rules/tc_sssao_rules.ttl` 为准）

前置条件（四条共有）：`e` 为 `CollisionRiskEvent`，且具有 `AssessmentData` 或 `PredictionData` 类型的 `detectedFromData`/`supportedByData` 证据；`p = hasCollisionProbability(e)`，`d = hasPredictedMissDistance(e)`，`h = hasCombinedHardBodyRadius(e)`；比较均经 `xsd:float()` 转型。

| 规则 | 条件 | 结论状态 | hasSeverityRank |
| --- | --- | --- | --- |
| R5 | `p ≤ θ_A ∧ d ≥ h` | `NormalSituationState` | 0 |
| R6 | `θ_A < p ≤ θ_M ∧ d ≥ h` | `AttentionSituationState` | 1 |
| R7 | `(p > θ_M ∧ d ≥ h) ∨ (p ≤ θ_M ∧ d < h)` | `WarningSituationState` | 2 |
| R8 | `p > θ_M ∧ d < h` | `DangerousSituationState` | 3 |

派生状态 IRI 均为事件 IRI 的 `LCASE(SHA256)` 哈希场景键（幂等）。执行层 `common.classify_states()` 与上述条件逐条等价（`high_pc = pc > θ_M`、`close = d < h`；Normal/Attention 要求 `~high_pc ∧ ~close` 并按 `pc ≤ θ_A` 细分；Warning 为 `high_pc ⊕ close`；Dangerous 为 `high_pc ∧ close`）。

### 1.3 阈值与 h(e) 的当前值和来源

| 项 | 当前值 / 来源 |
| --- | --- |
| θ_A（`attentionPcThreshold`） | `"1.0E-7"^^xsd:float`（NASA CARA 运行关注水平，见配置文件注释所引 NASA-SP-20205011318） |
| θ_M（`mitigationPcThreshold`） | `"1.0E-4"^^xsd:float`（NASA 高风险减缓判据，同上） |
| h(e)（`hasCombinedHardBodyRadius`） | **事件级输入，非全局常数**；ESA 适配层由原始字段计算：`hbr_km = (t_span + c_span) / 2000`（两目标直径之和的一半，米→千米），`d = miss_distance / 1000` km，`Pc = 10^risk`（ESA `risk` 字段即 log10(Pc)） |
| 状态名称 | **Normal / Attention / Warning / Dangerous**（严重度 0/1/2/3）。任务书所称 “Concern” 对应本项目实际名称 **Warning** |

### 1.4 论文文字与代码的差异

逐一比对 `paper/Chinese/sections/chapter3_ontology.tex`（状态式定义：`Normal: P_c≤θ_A∧¬H_d`；`Attention: θ_A<P_c≤θ_M∧¬H_d`；`Warning: H_p⊕H_d`；`Dangerous: H_p∧H_d`，约束 `0≤θ_A<θ_M≤1`）与 `chapter4_evaluation.tex`（基线表 141471/20447/716/0，合计 162634）：**未发现语义差异**，论文公式、状态名称、阈值取值与代码一致。

数值语义说明：配置文件将阈值声明为 `xsd:float`，但本项目 SHACL 执行路径（rdflib SPARQL，04 脚本门禁）把 `xsd:float` 字面量与 `xsd:float()` 转型映射为 Python `float`（IEEE 754 双精度，实测探针 `Literal("1.0E-7", datatype=XSD.float).toPython()` → `float 1e-07`），与 pandas 执行层的 float64 一致，两套引擎之间不存在单精度舍入分叉。

---

## 2. Baseline result（θ_A=10⁻⁷, θ_M=10⁻⁴）

使用官方执行层代码原样重跑，并与锁定的官方结果 `experiments/esa_cdm/results/risk_state_distribution.json` 及 processed CSV 的 `state` 列双向核对：**三者完全一致**。

| 状态 | 数量 | 占比 |
| --- | ---: | ---: |
| Normal | 141 471 | 86.99% |
| Attention | 20 447 | 12.57% |
| Warning | 716 | 0.44% |
| Dangerous | 0 | 0.00% |
| **合计** | **162 634** | 100.00% |

判定单位：CDM 快照（162 634 条，涉及 13 154 个事件）；`no_state=0`，`multi_state=0`。

---

## 3. θ_A sensitivity（实验 A：θ_M=10⁻⁴ 固定）

| θ_A | Normal | Attention | Warning | Dangerous | Dangerous 占比 | 变化 CDM 数（占比） | 变化事件数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10⁻⁹ | 123 100 | 38 818 | 716 | 0 | 0.00% | 18 371（11.30%） | 4 623 |
| 10⁻⁸ | 130 953 | 30 965 | 716 | 0 | 0.00% | 10 518（6.47%） | 3 024 |
| **10⁻⁷（基线）** | **141 471** | **20 447** | **716** | **0** | **0.00%** | 0 | 0 |
| 10⁻⁶ | 152 452 | 9 466 | 716 | 0 | 0.00% | 10 981（6.75%） | 2 781 |
| 10⁻⁵ | 159 253 | 2 665 | 716 | 0 | 0.00% | 17 782（10.93%） | 3 624 |

相对基线的增量全部呈 `ΔNormal = −ΔAttention`、`ΔWarning = ΔDangerous = 0` 的严格形式。

**分析**：θ_A 只出现在 R5/R6 中，±1–2 个数量级的变化会把 6.5%–11.3% 的 CDM 在 Normal↔Attention 之间重新划分（Normal+Attention 合计恒为 161 918），但**完全不触及 Warning/Dangerous 等较高风险状态**——本数据集上该结论为逐行验证的实证事实，而非仅由规则结构推断。变化随阈值单调、连续，无突变。

---

## 4. θ_M sensitivity（实验 B：θ_A=10⁻⁷ 固定）

| θ_M | Normal | Attention | Warning | Dangerous | Dangerous 占比 | 变化 CDM 数（占比） | 变化事件数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10⁻⁶ | 141 471 | 10 981 | 10 182 | 0 | 0.00% | 9 466（5.82%） | 1 950 |
| 10⁻⁵ | 141 471 | 17 782 | 3 381 | 0 | 0.00% | 2 665（1.64%） | 627 |
| **10⁻⁴（基线）** | **141 471** | **20 447** | **716** | **0** | **0.00%** | 0 | 0 |
| 10⁻³ | 141 471 | 21 111 | 52 | 0 | 0.00% | 664（0.41%） | 149 |
| 10⁻² | 141 471 | 21 155 | 8 | 0 | 0.00% | 708（0.44%） | 154 |

针对任务书四个专项问题：

1. **Dangerous 是否开始出现**：否，测试范围内全部为零。
2. **首次出现的 θ_M**：不存在。诊断性扩展计算（第 6 节）进一步表明 θ_M 取 10⁻⁷ 到 10⁻¹ 时 Dangerous 恒为 0。
3. **变化幅度**：恒 0，幅度为 0。
4. **Warning↔Dangerous 重新分配**：未发生。实际发生的重新分配在 **Attention↔Warning** 之间（θ_M=10⁻⁶ 时 Warning 从 716 增至 10 182；θ_M=10⁻³ 时减至 52），Normal 集合在所有 θ_M 下恒为 141 471（Normal 条件不含 θ_M，实证一致）。

**分析**：θ_M 是 Warning 规模的决定性参数，±1 个数量级使 Warning 计数在 716 → 3 381 / 52 之间变化（约 ×4.7 / ÷13.8）；但由于数据集中 `d<h(e)` 从不成立（第 6 节），R8 的合取条件在任何 θ_M 下都不可能满足，Dangerous 对 θ_M 完全免疫。

---

## 5. Joint sensitivity（实验 C：3×3 联合网格）

| θ_A | θ_M | Normal | Attention | Warning | Dangerous |
| --- | --- | ---: | ---: | ---: | ---: |
| 10⁻⁸ | 10⁻⁵ | 130 953 | 28 300 | 3 381 | 0 |
| 10⁻⁸ | 10⁻⁴ | 130 953 | 30 965 | 716 | 0 |
| 10⁻⁸ | 10⁻³ | 130 953 | 31 629 | 52 | 0 |
| 10⁻⁷ | 10⁻⁵ | 141 471 | 17 782 | 3 381 | 0 |
| **10⁻⁷** | **10⁻⁴** | **141 471** | **20 447** | **716** | **0** |
| 10⁻⁷ | 10⁻³ | 141 471 | 21 111 | 52 | 0 |
| 10⁻⁶ | 10⁻⁵ | 152 452 | 6 801 | 3 381 | 0 |
| 10⁻⁶ | 10⁻⁴ | 152 452 | 9 466 | 716 | 0 |
| 10⁻⁶ | 10⁻³ | 152 452 | 10 130 | 52 | 0 |

**观察**：

- 不存在导致状态分布剧烈变化的小范围阈值扰动；所有变化单调、平滑、可解释。
- **Dangerous=0 不仅在基线出现，而且在全部 9 组邻近阈值组合中出现**（事实上在全部 15 个测试参数组合中出现）。
- 网格呈现严格的可加结构：Normal 只随 θ_A 变化（130 953 / 141 471 / 152 452 三个水平），Warning 只随 θ_M 变化（3 381 / 716 / 52 三个水平），两参数无交互项——θ_A 与 θ_M 分别控制不相交的状态对边界。
- 高风险事件集合（Warning∪Dangerous，本数据集上恰为 `Pc>θ_M` 的 CDM）在同一 θ_M 下完全稳定，与 θ_A 无关。

---

## 6. Dangerous=0 diagnosis（真实原因核查）

### 6.1 Pc 分布（162 634 条有效 CDM）

| 统计量 | 值 |
| --- | --- |
| minimum | 1.0×10⁻³⁰ |
| maximum | 3.607×10⁻² |
| median | 1.347×10⁻¹⁸ |
| mean | 3.519×10⁻⁶ |
| 90th percentile | 2.654×10⁻⁷ |
| 95th percentile | 1.849×10⁻⁶ |
| 99th percentile | 3.305×10⁻⁵ |

| 越限计数 | 数量 |
| --- | ---: |
| Pc > 10⁻⁷ | 21 163 |
| Pc > 10⁻⁶ | 10 182 |
| Pc > 10⁻⁵ | 3 381 |
| Pc > 10⁻⁴ | 716 |
| Pc > 10⁻³ | 52 |

### 6.2 距离条件

| 条件 | 数量 | 占比 |
| --- | ---: | ---: |
| `d < h(e)` | **0** | **0.00%** |

### 6.3 联合条件（θ_M=10⁻⁴）

| 条件组合 | 数量 |
| --- | ---: |
| `Pc > 10⁻⁴ ∧ d < h(e)` | **0** |
| `Pc > 10⁻⁴ ∧ d ≥ h(e)` | 716 |
| `Pc ≤ 10⁻⁴ ∧ d < h(e)` | 0 |

补充：全部高 Pc（>10⁻⁴）CDM 中，最小距离余量 `min(d − h) = 0.0101 km`（10.1 m），最小比值 `min(d/h) = 2.46`——即最接近硬体半径的高 Pc 事件，其最近交会距离仍是组合硬体半径的约 2.46 倍。诊断性扩展：`Dangerous(θ_M)` 在 θ_M ∈ {10⁻⁷, 10⁻⁶, 10⁻⁵, 10⁻⁴, 10⁻³, 10⁻², 10⁻¹} 下恒为 0（Dangerous 与 θ_A 无关）。

### 6.4 对候选原因的判定

| 候选 | 判定 | 数据依据 |
| --- | --- | --- |
| A. 数据中没有高碰撞概率事件 | **否** | 716 条 Pc>10⁻⁴、52 条 Pc>10⁻³，最高 Pc=0.036 |
| **B. 有高 Pc 事件，但距离条件不成立** | **是（主因）** | 716/716 高 Pc 事件全部 `d ≥ h(e)`；`d<h(e)` 在全数据集中为 0 |
| C. 两条件分别存在但不同时满足 | 部分成立且更极端 | 距离条件对**任何**事件都不成立，而非仅对高 Pc 事件不成立 |
| D. 规则实现存在其他限制 | **否** | 全部 15 组参数下 R5–R8 完备互斥（第 7 节）；高 Pc 事件均被 R7 正确捕获为 Warning；50 事件 RDF 门原样执行未修改的 SHACL 构造体并收敛 |
| E. 阈值选择导致 | **否** | θ_M 在 10⁻⁷–10⁻¹ 全范围 Dangerous 恒 0；该结果对阈值选择不变 |

**结论：Dangerous=0 由数据分布造成（B），不是由当前阈值设置造成。** 由于没有任何 CDM 满足 `d < h(e)`，R8 的合取前提在该数据集上恒假，任何 θ_M 取值都不会产生 Dangerous。内部一致性旁证：正因 `d<h` 从不成立，R7 在本数据集上退化为纯 `Pc>θ_M` 判据，各 θ_M 下 Warning 计数与 `Pc>θ_M` 的独立计数逐一相等（10 182 / 3 381 / 716 / 52 / 8），两套独立计算完全吻合。

---

## 7. Rule coverage audit（规则覆盖与冲突）

对全部 15 个参数组合（13 个唯一组合）逐一以**独立重算的掩码**（不经分类引擎）核验：

| 检查项 | 结果 |
| --- | --- |
| 所有待判定 CDM 均获得状态 | 15/15 通过（162 634/162 634） |
| 无状态 CDM（no_state） | 全部为 0 |
| 同一 CDM 多状态（multi_state / 两两掩码交集） | 全部为 0 |
| 四状态之和 = 应判定总数 | 15/15 相等 |
| 引擎计数 = 独立审计计数 | 15/15 一致 |
| R5–R8 条件重叠或空白区间 | 未发现 |
| 参数序约束 `θ_A < θ_M` | 15/15 满足（本实验所有组合均保持在论文约束 `0≤θ_A<θ_M≤1` 内） |

附注（仅记录、未改动规则）：若未来部署取 `θ_A ≥ θ_M`，R5/R6 与 R7 的边界将失去互斥性（如 `θ_M < p ≤ θ_A ∧ d ≥ h` 区间会同时命中 R5 与 R7a），现有约束 `θ_A < θ_M` 是完备互斥的必要条件；本实验全部组合均满足该约束，故无重叠、无漏判、无多状态。

---

## 8. Final conclusion

**Q1. θ_A=10⁻⁷ 附近变化是否会明显改变总体状态分布？**

会明显改变 **Normal/Attention 的低风险划分**（±1–2 个数量级 → 6.5%–11.3% CDM 重新标记，Normal 在 75.7%–97.9% 之间移动），但变化被严格限制在这两个最低严重度状态之间；Warning（716）与 Dangerous（0）在所有 θ_A 下逐条不变。即：θ_A 改变低风险内部的语义粒度，不影响任何高风险判定。

**Q2. θ_M=10⁻⁴ 附近变化是否会明显改变 Warning/Dangerous 分布？**

明显改变 **Warning 的规模**：θ_M ±1 个数量级使 Warning 在 716 → 3 381（10⁻⁵）/ 52（10⁻³）之间变化，重新分配发生在 Attention↔Warning 之间。**Dangerous 分布不变**：所有测试 θ_M（含诊断扩展 10⁻⁷–10⁻¹）下 Dangerous 恒为 0，不存在 Warning→Dangerous 的转移。

**Q3. Dangerous=0 是否主要由当前阈值设置导致？**

**否。** Dangerous=0 由数据分布造成：162 634 条有效 CDM 中没有任何一条满足 `d < h(e)`（高 Pc 事件的最小距离余量仍为 10.1 m、d/h≈2.46），R8 的合取前提恒假；该结果对 θ_M 的任意取值（10⁻⁷–10⁻¹）不变，与 θ_A 完全无关。

**Q4. 当前 θ_A=10⁻⁷、θ_M=10⁻⁴ 是否具有足够的实验稳定性，可以继续用于论文？**

**Moderately sensitive（中等敏感），可以继续使用。** 数据依据：

- **定量计数对阈值移动有可见但平滑的响应**（θ_A ±2 个数量级最多重标记 11.30% CDM；θ_M ±1 个数量级重标记 1.64%/0.41% CDM，Warning 计数 ×4.7/÷13.8）——这是阈值型判据的预期行为，变化单调、无悬崖、无异常翻转，且每次变化只发生在相邻严重度之间；
- **论文的关键定性结论在整个测试网格上不变**：Normal+Attention 主导（≥99.5%）、Warning 为小比例（0.005%–6.26%）、**Dangerous=0 在全部 15 组参数下成立**，且 Dangerous=0 已被证明是数据属性而非阈值产物；
- 全部 15 组参数下规则覆盖完备互斥（无重叠、无空白、无多状态、无漏判），基线结果可被官方管线逐位复现（141 471 / 20 447 / 716 / 0，与锁定 JSON 一致）。

若论文需引用本实验：可以说“状态分布对 θ_A/θ_M 的数量级扰动表现为低风险对（Normal/Attention）与中风险对（Attention/Warning）内部的可预期重分配，高风险结论（Dangerous 空缺及其数据成因）对阈值选择稳健”。
