# TraCSS 风险状态阈值敏感性实验报告

- 实验日期：2026-09-18
- 实验脚本：[run_tracss_threshold_sensitivity.py](run_tracss_threshold_sensitivity.py)
- 机器可读结果：[results/tracss_threshold_sensitivity_results.json](results/tracss_threshold_sensitivity_results.json)
- 数据集：TraCSS Conjunction Assessment Verification Dataset（SFSH
  DiscreteHBR 答案键），使用已通过审计的适配标准数据
  `experiments/tracss/data/tracss_sfsh_normalized.csv.gz`
  字段映射沿用已确认
  结果：`collision_probability`=线性 Pc，`predicted_miss_distance`=d（km），
  `combined_hard_body_radius`=h(e)（km），HBR 覆盖率 100%。
- 正式替代此前基于 ESA 的阈值敏感性实验
  （`experiments/esa_threshold_sensitivity/`，保留不动，仅作内部对照）。
- 约束遵守：未修改 R5–R8、本体、TraCSS 原始数据、θA/θM 正式基线值、
  论文；未删除/修改 ESA 旧实验；阈值仅在实验进程内存中变化；未删除
  异常样本、未补充 Dangerous、未按分布筛选数据。本实验只新增结果。

---

## 1. Baseline reproduction（基线复现核验）

扫描前的三道硬门全部通过（任一不过即中止，不进入扫描）：

| 检查 | 结果 |
| --- | --- |
| 总行数 / 有效样本 | 283,595 / **283,557** ✓ |
| 当前正式 R5–R8 与主实验一致（复用 tracss 适配器 classify_states） | 通过 |
| 参数化扫描引擎与主实验引擎逐行一致（基线阈值下） | 283,557/283,557 行相同，mismatch=0 |
| 基线四状态计数 | **86,585 / 196,666 / 306 / 0**，与主实验锁定值完全一致 ✓ |

| State | Count |
| --- | ---: |
| Normal | 86,585 |
| Attention | 196,666 |
| Warning | 306 |
| Dangerous | 0 |
| **合计** | **283,557** |

## 2. θA sensitivity（实验A：θM=10⁻⁴ 固定）

| θA | Normal | Attention | Warning | Dangerous | Changed Samples | Changed % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10⁻⁹ | 54,768 | 228,483 | 306 | 0 | 31,817 | 11.22% |
| 10⁻⁸ | 71,390 | 211,861 | 306 | 0 | 15,195 | 5.36% |
| **10⁻⁷（基线）** | **86,585** | **196,666** | **306** | **0** | 0 | 0.00% |
| 10⁻⁶ | 119,071 | 164,180 | 306 | 0 | 32,486 | 11.46% |
| 10⁻⁵ | 242,791 | 40,460 | 306 | 0 | 156,206 | 55.09% |

状态转换来源（相对基线；未列出的转换对全为 0，含
Normal→Warning、Normal→Dangerous、Attention→Warning、
Attention→Dangerous、Warning→Dangerous）：

| θA | Transition | Count |
| --- | --- | ---: |
| 10⁻⁹ | Normal→Attention | 31,817 |
| 10⁻⁸ | Normal→Attention | 15,195 |
| 10⁻⁶ | Attention→Normal | 32,486 |
| 10⁻⁵ | Attention→Normal | 156,206 |

分析：

1. **θA 只引起 Normal↔Attention 重新分配**：全部五个参数点下，
   Warning 恒为 306、Dangerous 恒为 0（逐行验证，非仅规则结构推断）；
   Normal+Attention 合计恒为 283,251。
2. **Warning、Dangerous 对 θA 完全稳定**（常数）。
3. **最大状态重标记比例**：55.09%（θA=10⁻⁵，距基线 +2 个数量级）；
   ±1 个数量级内最大为 11.46%。
4. **变化单调**：Normal 计数随 θA 单调不减
   （54,768→71,390→86,585→119,071→242,791），无翻转。
5. **无突然跳变**：最大相邻步进出现在 10⁻⁶→10⁻⁵（+123,720），
   对应 Pc 分布的稠密区间（Pc∈(10⁻⁶,10⁻⁵] 的样本天然较多），
   是平滑 CDF 行为，基线附近（10⁻⁸–10⁻⁶）每数量级变化仅
   5.36%–11.46%，基线处无悬崖。
6. 明确判断：**θA 主要影响低风险内部语义粒度（Normal 与 Attention
   的划分细度），不改变任何高风险结果**。

## 3. θM sensitivity（实验B：θA=10⁻⁷ 固定）

| θM | Normal | Attention | Warning | Dangerous | Changed Samples | Changed % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10⁻⁶ | 86,585 | 32,486 | 164,485 | **1** | 164,181 | 57.90% |
| 10⁻⁵ | 86,585 | 156,206 | 40,766 | 0 | 40,460 | 14.27% |
| **10⁻⁴（基线）** | **86,585** | **196,666** | **306** | **0** | 0 | 0.00% |
| 10⁻³ | 86,585 | 196,971 | 1 | 0 | 305 | 0.11% |
| 10⁻² | 86,585 | 196,971 | 1 | 0 | 305 | 0.11% |

状态转换来源（相对基线；未列出的转换对全为 0，含 Normal→Attention、
Normal→Warning、Normal→Dangerous、Attention→Dangerous、
Dangerous→Warning）：

| θM | Transition | Count |
| --- | --- | ---: |
| 10⁻⁶ | Attention→Warning | 164,180 |
| 10⁻⁶ | Warning→Dangerous | 1 |
| 10⁻⁵ | Attention→Warning | 40,460 |
| 10⁻³ | Warning→Attention | 305 |
| 10⁻² | Warning→Attention | 305 |

分析：

1. **θM 主要驱动 Attention↔Warning 转换**；Normal 集合在所有 θM 下
   恒为 86,585（Normal 条件不含 θM，实证一致）。
2. **Warning 随 θM 单调不增**：164,485→40,766→306→1→1，无非单调
   异常；10⁻³ 与 10⁻² 持平为预期饱和（数据最大 Pc=9.354×10⁻⁴<10⁻³，
   再高阈值不再改变任何判定）。
3. **Dangerous 在 θM=10⁻⁶ 出现 1 例**（详见第 5 节）。
4. 与已知结构一致：305 条高 Pc 样本的最小 d/h=1.428（d、h 不随 θM
   变化），其距离条件在任何 θM 下都不可能翻转，故 Dangerous 完全由
   唯一 d<h(e) 样本与 θM 的相对位置决定。
5. 重标记幅度：θM=10⁻⁶（基线 −2 个数量级）时 57.90% 样本改标
   （绝大多数为 Attention→Warning 的有序迁移）；±1 个数量级内最大
   14.27%。

## 4. 3×3 joint sensitivity（实验C）

| θA | θM | Normal | Attention | Warning | Dangerous |
| --- | --- | ---: | ---: | ---: | ---: |
| 10⁻⁸ | 10⁻⁵ | 71,390 | 171,401 | 40,766 | 0 |
| 10⁻⁸ | 10⁻⁴ | 71,390 | 211,861 | 306 | 0 |
| 10⁻⁸ | 10⁻³ | 71,390 | 212,166 | 1 | 0 |
| 10⁻⁷ | 10⁻⁵ | 86,585 | 156,206 | 40,766 | 0 |
| **10⁻⁷** | **10⁻⁴** | **86,585** | **196,666** | **306** | **0** |
| 10⁻⁷ | 10⁻³ | 86,585 | 196,971 | 1 | 0 |
| 10⁻⁶ | 10⁻⁵ | 119,071 | 123,720 | 40,766 | 0 |
| 10⁻⁶ | 10⁻⁴ | 119,071 | 164,180 | 306 | 0 |
| 10⁻⁶ | 10⁻³ | 119,071 | 164,485 | 1 | 0 |

分析：

1. **Normal 只受 θA 控制**（三个水平 71,390 / 86,585 / 119,071，
   同行跨 θM 完全相同）。
2. **Warning 只受 θM 控制**（三个水平 40,766 / 306 / 1，
   同列跨 θA 完全相同）。
3. **Dangerous 在全部 9 组中均为 0**（网格未下探到 10⁻⁶，见第 5 节）。
4. **无明显参数交互**：机器核验 `C_normal_depends_only_on_theta_A`
   与 `C_warning_depends_only_on_theta_M` 均为真。
5. 两参数的影响**可以近似解释为独立边界控制**（严格可加结构，与
   ESA 实验结构相同）；联合变化为两独立变化的叠加（最大改标 25.73%，
   出现在 θA=10⁻⁶∧θM=10⁻⁵）。

## 5. Dangerous threshold behavior（专项）

唯一 d<h(e) 真实样本（逐字段核验，非解析错误）：

| event_id | Pc | d (km) | h(e) (km) | d/h |
| --- | ---: | ---: | ---: | ---: |
| 1723730887 | 6.593401×10⁻⁶ | 0.008684 | 0.011017 | 0.7882 |

该样本在不同 θM 下的状态（θA=10⁻⁷ 固定），以及每个 θM 下
Pc>θM ∧ d<h(e) 的数量：

| θM | Pc>θM AND d<h Count | Dangerous Count | 该样本状态 |
| --- | ---: | ---: | --- |
| 10⁻⁷ | 1 | 1 | Dangerous |
| 10⁻⁶ | 1 | 1 | Dangerous |
| 10⁻⁵ | 0 | 0 | Warning |
| 10⁻⁴ | 0 | 0 | Warning |
| 10⁻³ | 0 | 0 | Warning |
| 10⁻² | 0 | 0 | Warning |

- **首次触发阈值（网格内自高向低扫描）：θM=10⁻⁶**；精确边界为该样本
  Pc 值：**Dangerous 当且仅当 θM < 6.593401×10⁻⁶**（严格不等；θM 等于
  其 Pc 时仍为 Warning）。
- 直接回答：**Dangerous=0 并非仅在基线成立**——在 θM ≥ 10⁻⁵ 的整个
  邻近范围内（含基线 ±1 个数量级 [10⁻⁵, 10⁻³]）均成立；仅当 θM 下探
  到低于该样本 Pc（基线以下约 1.18 个数量级，因子 15.2）时出现 1 例。
- 如实记录（不解释为错误）：**TraCSS 中存在真实近距离样本，其
  Dangerous 判定依赖 θM 的位置**。这与 ESA 的情况结构性不同——ESA
  全数据无 d<h(e)，Dangerous 对任何 θM 免疫；TraCSS 的 Dangerous 可达
  性由一个真实样本承载，是数据性质而非规则缺陷。
- 审计注记：θM=10⁻⁷ 诊断点上 θA=θM（不满足严格 θA<θM 约束，仅记录、
  未修改规则）；该点规则掩码仍构成精确划分（overlap=0、gap=0，R6 退化
  为空集），R8 判定不含 θA，Dangerous 结论不受该等值影响。

## 6. Rule coverage audit（规则覆盖审计）

对实验A/B/C 全部 19 个参数组合 + Dangerous 专项 6 个参数点，均以
独立重算掩码（不经分类引擎）核验：

| 检查项 | A/B/C 19 组 | 专项 6 点 |
| --- | --- | --- |
| no_state | 全部 0 | 全部 0 |
| multi_state | 全部 0 | 全部 0 |
| overlap | 全部 0 | 全部 0 |
| gap | 全部 0 | 全部 0 |
| 四状态总和 = 283,557 | 19/19 相等 | 6/6 相等 |
| 引擎计数 = 独立掩码计数 | 19/19 一致 | 6/6 一致 |
| 满足 θA<θM | 19/19 严格满足 | 5/6（θM=10⁻⁷ 为 θA=θM 边界点，见第 5 节注记） |
| 专项：Pc>θM∧d<h 计数 = 分类器 Dangerous 计数 | — | 6/6 一致 |

未发现规则重叠或空白；发生重叠/空白时按任务要求只报告、不改规则。

## 7. Stability assessment（基线参数稳定性判定）

判定依据（逐项对照任务标准）：

1. **状态重标记比例**：θA ±1 个数量级 ≤11.46%（±2 个数量级最大
   55.09%），全部限制在 Normal↔Attention 低风险对内部；θM ±1 个
   数量级 ≤14.27%（±2 个数量级最大 57.90%），全部限制在
   Attention↔Warning 之间。属阈值型规则的有序重分配。
2. **异常非单调变化**：无。A 中 Normal 对 θA 单调不减；B 中 Warning
   对 θM 单调不增；联合网格严格可加、无交互项。
3. **高风险状态是否剧烈改变**：Warning 规模随 θM 大幅但有序变化
   （1 ↔ 164,485，仅相邻严重度间迁移）；θM=10⁻⁵ 时 Warning 占
   14.4%——如实记录：在该低阈值下"Warning 为小比例"的表述不再成立。
   θA 对高风险状态零影响。
4. **Dangerous 是否高度依赖微小阈值扰动**：否。基线 ±1 个数量级内
   Dangerous 恒为 0；触发需 θM 降至 6.593401×10⁻⁶ 以下（基线以下约
   1.18 个数量级），且仅 1 个真实样本跨越。
5. **规则覆盖是否稳定**：25/25 个参数点完备互斥（唯一边界诊断点
   θA=θM=10⁻⁷ 仍保持精确划分，已记录）。

**判定：Moderately sensitive（中等敏感）。** 阈值扰动引起的是低风险对
（Normal/Attention）与中风险对（Attention/Warning）内部可预期、单调、
无悬崖的重分配；Dangerous 在基线 ±1 个数量级内恒为 0，其唯一可达
样本的边界位置已精确定位并如实记录。

### 与 ESA 敏感性实验的内部对照（仅内部说明，ESA 实验未动）

- **敏感性结构一致**：两个数据集上 θA 均只影响 Normal/Attention、
  θM 均只影响 Attention/Warning，联合网格均呈无交互的可加结构，
  规则覆盖均全绿。
- 幅度差异：ESA 上 θA ±2 个数量级最多重标记 11.30%、θM ±1 个数量级
  重标记 1.64%/0.41%（Warning ×4.7/÷13.8）；TraCSS 上对应幅度更大
  （θA ±2 个数量级 55.09%；θM ±1 个数量级 14.27%/0.11%，Warning
  ×133/÷306），原因是 TraCSS 答案键 Pc 分布整体上移（Pc>10⁻ 的样本
  占 14.4%，密集区贴近 θM 量级）。
- **Dangerous 行为不同**：ESA 全数据 d<h(e)=0，Dangerous 对任意 θM
  （10⁻⁷–10⁻¹）免疫；TraCSS 有 1 个真实 d<h(e) 样本，Dangerous 在
  θM<6.593401×10⁻⁶ 时出现（计数 1）。
- 结论层级一致：两数据集均判定 Moderately sensitive。

## 8. Final answers

**Q1：θA=10⁻⁷ 是否处于合理稳定区间？**
**是。** θA 扰动仅在 Normal↔Attention 间重分配（±1 个数量级
5.36%–11.46%），单调、无跳变、不触及 Warning/Dangerous；基线附近无
悬崖。

**Q2：θM=10⁻⁴ 是否处于合理稳定区间？**
**是（附如实注记）。** 基线位于 Pc 分布上尾（P99=5.28×10⁻⁵ 之上）；
±1 个数量级扰动只引起 Attention↔Warning 有序迁移，Dangerous 恒 0，
规则覆盖稳定。注记：Warning 计数对 θM 的数量级变化反应幅度大
（×133/÷306），属尾部阈值预期行为；θM=10⁻⁵ 时 Warning 占比升至
14.4%，"Warning 为小比例"在该低阈值下不成立。

**Q3：TraCSS 上的 Warning/Dangerous 结果是否对阈值高度敏感？**
**Warning 的规模对 θM 敏感、对 θA 免疫**（敏感方式为单调、有序、
仅相邻严重度间的设计内行为）；**Dangerous 对 θA 免疫，对 θM 存在
一个精确定位的单样本边界**（θM<6.593401×10⁻⁶ 时出现 1 例），在基线
±1 个数量级内恒为 0，不属于对微小扰动高度敏感。

**Q4：当前基线参数是否可以继续作为论文正式参数？**
**可以。** θA=10⁻⁷、θM=10⁻⁴ 基线可逐位复现，处于稳定、可解释区间：
扰动响应单调有序、无异常翻转、规则覆盖 25/25 完备互斥、Dangerous=0
在基线及 ±1 个数量级邻域内成立，且阈值的运行语义（NASA CARA 关注/
减缓水平）不变。

**Q5：TraCSS 阈值敏感性实验是否足以替代此前 ESA 敏感性实验？**
**足以替代。** 实验设计相同、基线与新主数据集锁定、结构结论一致
（θA→Normal/Attention、θM→Attention/Warning、联合可加、覆盖全绿、
同判 Moderately sensitive），且 TraCSS 版本首次能够探测 R8/Dangerous
边界（ESA 因无 d<h(e) 样本而无法探测），信息量为严格超集。

---

附：本实验产物
- `run_tracss_threshold_sensitivity.py`（单文件脚本，三道基线硬门 +
  25 个参数点全审计）
- `results/tracss_threshold_sensitivity_results.json`（全部机器可读
  结果：扫描表、转换矩阵、逐点覆盖审计、ESA 参照块）
