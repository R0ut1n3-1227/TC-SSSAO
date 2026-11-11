# TraCSS 数据集迁移可行性报告

**任务**：将 TC-SSSAO 论文主风险实验数据集由 ESA Collision Avoidance
Challenge 更换为 TraCSS Conjunction Assessment Verification Dataset
——第一阶段：新数据集适配与可行性验证。

**约束遵守声明**：本次工作未修改 R5–R8 规则、未修改 θA/θM、未修改本体、
未修改原始 TraCSS 数据、未人为补充 Dangerous 实例、未筛选样本、未混用
TraCSS 与 ESA 记录、未修改现有 ESA 实验、未修改论文。

报告日期：2026-09-18。全部数值可由 `experiments/tracss/scripts/run_all.py`
复现（只读于原始数据与 ESA 产物）。

---

## 1. 数据文件与版本

| 文件 | 字节数 | 角色 |
| --- | ---: | --- |
| data/tracss/raw/IVV_Releasable_Dataset_SFSH_DiscreteHBR.csv.gz | 65,406,532 | 主答案键（SFSH 离散 HBR） |
| data/tracss/raw/AerospaceIVVDataset_20251009a_Size_ScreeningVolumes.csv.gz | 147,659 | 逐对象 HBR/筛查体积映射 |
| data/tracss/raw/Conjunction_Screening_Testset_Users_Guide.pdf | 371,607 | 字段语义与单位权威依据 |

- 发布方：美国 Office of Space Commerce（TraCSS）；答案键由 The
  Aerospace Corporation 的 CSieve 工具生成（数据内 run_id=1662）。
- 版本标识：数据集 ID `20251009a`（2025-10-09）；User's Guide  dated
  March 2026，许可 CC0-1.0（可自由使用与传播）。
- 筛查时间窗（指南 §Configuration）：2025-01-01T12:00:00Z –
  2025-01-08T12:00:00Z；实测数据 epoch 全域覆盖该窗口
  （12:00:02.322 – 11:59:52.349）。
- Pc 方法：Alfano 2004（指南 Table 5）。
- **版本备注**：指南 Table 1 标称 SFSH 答案键为 144 MB，本地文件为
  65,406,532 字节（62.4 MiB）。本地文件通过 gzip 完整性校验、内容自洽
  （单一 run_id、conj_id 全部唯一、epoch 覆盖完整时间窗），判定为发布
- 未处理：完整星历数据集 AerospaceIVVDataset_20251009a.tar.gz
  （指南标称 21.74 GB，按任务约束暂不处理）。
- 未使用：IVV_Releasable_Dataset_Spherical_DefaultHBR.csv.gz（本地
  存在）。原因：该答案键对所有对象使用常数 HBR 0.5 m，无法构造事件级
  h(e)，不满足 TC-SSSAO 对逐事件组合硬体半径的需求。
- 映射文件含 26,793 行、26,772 个唯一对象：catalog 43476 的 21 行为
  完全重复（各列取值一致），去重后连接结果不受影响；若出现取值冲突
  的重复，适配器将直接报错中止（未发生）。

## 2. 字段映射

映射依据 User's Guide Table 5（CSieve 输出规范）与 SFSH Screening
Volume Mappings 一节，**未凭字段名猜测语义**。文件实际表头与指南
Table 5 逐列核对一致（field_audit.json: structure PASS）。

| TC-SSSAO需求字段 | TraCSS原始字段 | 单位 | 是否直接可用 | 是否需要计算 |
| --- | --- | --- | --- | --- |
| Event ID | conj_id | — | 是（283,595/283,595 行唯一） | 否 |
| Object 1 | obj1 | Sat ID | 是 | 否 |
| Object 2 | obj2 | Sat ID | 是 | 否 |
| TCA | epoch（jdate 交叉核对） | UTC | 是 | 否 |
| Collision probability Pc | prob | 无量纲 | 是（Alfano 2004 线性 Pc；38 行 NULL） | 否 |
| Miss distance d | min_range | km | 是 | 否 |
| Object size/HBR | 映射文件 HBR（按 catalog_num 连接） | m（逐对象半径） | 是 | 否 |
| Combined HBR h(e) | HBR[obj1] + HBR[obj2] | km（换算后） | 否 | 是（求和 + m→km） |

四个特别确认项的结论：

1. **prob ≡ hasCollisionProbability**：成立。指南明确 prob 为 Alfano
   2004 方法的 Pc，是无量纲线性概率（实测范围 [1e-10, 9.354e-4]）。
   与 ESA 的差异：ESA 的 risk 列存储 log10(Pc)，适配时需 pc=10^risk；
   TraCSS 无需对数还原。两者还原后同为线性 Pc ∈ [0,1]，语义一致。
   NULL（38 行，0.013%）表示协方差指标无法计算，预检剔除，与 ESA
   执行层 valid_pc 契约同构。
2. **min_range ≡ hasPredictedMissDistance**：成立。指南明确 min_range
   为 miss distance，单位 km。ESA miss_distance 为 m，换算后同为 km，
   语义一致。**陷阱规避**：mdistance 字段名为"距离"但语义为
   Mahalanobis 距离（指南 Table 5 明示），本适配将其仅作为溯源列
   保留，禁止映射为 d。
3. **SFSH 尺寸/筛查体积 → hasCombinedHardBodyRadius**：可转换。映射
   文件给出逐对象 HBR（半径，单位 m；单位证据：指南规定球形运行的
   默认 HBR 为 0.5 m，且 ISS（catalog 25544）映射值为 55.0，仅在米制
   下具有物理意义）。h(e) = (HBR[obj1] + HBR[obj2]) / 1000（km），
   与 ESA 适配的 h(e) = (t_span + c_span)/2/1000 同为"两对象半径之
   和"的组合硬体半径约定。
4. **事件级 h(e)**：可构造。映射文件对答案键全部 283,595 行的 obj1、
   obj2 覆盖率为 100%（无一缺失）。

与 ESA 原字段定义的差异（显式记录，未静默映射）：

- HBR 来源不同：ESA 由 t_span/c_span（目标/碰撞体尺寸跨度）推算半径；
  TraCSS 为官方整备的逐对象 HBR 目录。物理约定一致（半径求和），
  数据来源不同。
- 数据集用途不同：ESA 为业务 CDM 衍生的机器学习挑战赛数据；TraCSS
  为筛查工具验证答案键，按设计混入合成压力用例（机动星历、虚构对象、
  Osiris-Rex 再入等，指南 Table 2）。分布形状差异属预期，非缺陷。
- 时间结构不同：ESA 每事件含多条时序 CDM 快照；TraCSS 每个
  conjunction 一行（conj_id 唯一），无时间演化序列。
- 指南自身的 Pc 警告：Pc 跨工具直接比较需同一 Pc 方法，故 Pc 不是该
  数据集的关键比对指标。本实验消费官方答案键原值、不做跨工具比较，
  该警告不影响 R5–R8 评估；若论文引用需如实说明 Pc 方法（Alfano
  2004）。

## 3. 单位转换

| 量 | 转换 | 说明 |
| --- | --- | --- |
| collision_probability | prob 1:1 | 无量纲，无对数还原（不同于 ESA 的 10^risk） |
| predicted_miss_distance | min_range 1:1 | 原始单位即 km（指南 Table 5） |
| combined_hard_body_radius | (HBR[obj1]+HBR[obj2]) / 1000 | m → km，与 min_range 同单位后比较 |
| tca | epoch 1:1 | UTC 字符串原样保留 |

适配后标准字段（experiments/tracss/data/tracss_sfsh_normalized.csv.gz，
event_id, object1_id, object2_id, tca, collision_probability,
predicted_miss_distance, combined_hard_body_radius（另含溯源列：
run_id、met_criteria1/2、dilution、mahalanobis_distance、vrel_km_s、
jdate、hbr1_m、hbr2_m、obj1/2_filename、预检标志与剔除原因）。

预检结果：总行数 283,595；通过 283,557；剔除 38，剔除原因全部为
"missing Pc (NULL prob)"；HBR 连接覆盖率 100%，无距离/时间/角色/重复
行问题。

## 4. Pc / d / HBR 数据统计

统计总体：预检通过的 283,557 行。

### 4.1 Pc 分布

| 指标 | 值 |
| --- | ---: |
| min | 1.0000e-10 |
| max | 9.3539e-04 |
| mean | 5.3660e-06 |
| median | 1.7249e-06 |
| P90 | 1.5258e-05 |
| P95 | 2.6165e-05 |
| P99 | 5.2776e-05 |

| 阈值 | 数量 |
| --- | ---: |
| Pc > 1e-7 | 196,972 |
| Pc > 1e-6 | 164,486 |
| Pc > 1e-5 | 40,765 |
| Pc > 1e-4 | 305 |
| Pc > 1e-3 | 0 |

注：41,681 行（14.70%）Pc 恰好等于最小值 1e-10，判定为答案键发布的
下界取整地板（非适配器产物）；如实记录，未作修正。

### 4.2 d 与 h(e)

| 指标 | d (km) | h(e) (km) |
| --- | ---: | ---: |
| min | 0.008684 | 1.1833e-05 |
| median | 18.060053 | 0.011017 |
| max | 67.195619 | 0.252864 |

| 关系 | 数量 |
| --- | ---: |
| d < h(e) | **1** |
| d = h(e) | 0 |
| d > h(e) | 283,556 |

d/h：min 0.7882，median 1591.4。

### 4.3 最关键检查

**Pc > 1e-4 ∧ d < h(e)：0 行。**

> 直接回答：TraCSS 真实数据中**不存在**能够触发 R8 Dangerous 的实例
> （在冻结阈值与规则语义下，原样评估，未作任何导向性筛选）。

## 5. R5–R8 状态分布

冻结参数：θA = 1e-7，θM = 1e-4；规则语义与 ESA 实验完全一致
（04 脚本以只读方式加载 ESA 实现的 classify_states 交叉验证：
283,557/283,557 行状态逐一相同，阈值相等，mismatch=0）。

| State | Count | Percentage |
| --- | ---: | ---: |
| Normal | 86,585 | 30.54% |
| Attention | 196,666 | 69.36% |
| Warning | 306 | 0.11% |
| Dangerous | 0 | 0.00% |

完备性：no_state = 0；multi_state = 0；四条规则掩码 overlap = 0、
gap = 0；Normal+Attention+Warning+Dangerous = 283,557 = N ✓。

Attention 占比远高于 ESA（69.36% vs 12.57%）的结构性原因：TraCSS
答案键按筛查体积命中收录且按设计富集压力几何用例，Pc 中位数
（1.72e-6）高于 θA=1e-7 一个数量级以上，Pc>θA 的行占 69.5%；ESA 为
业务 CDM 流，Pc 中位数远低于 θA。属数据集用途差异，非规则行为差异。

## 6. Dangerous 可达性分析

Dangerous = 0。按任务要求未修改规则、未人为制造样本，原因分解如下
（两个合取支各自落空）：

- **d < h(e) 支**：全数据仅 1 行满足（事件 1723730887，对象
  53038/53293，TCA 2025-01-05 21:13:18.808 UTC，d = 8.68 m，
  h(e) = 11.02 m，d/h = 0.788）。但其 Pc = 6.593e-6 ≤ θM
  → 落入 R7 第二析取支（Warning）。该行 Mahalanobis 距离 0.0064
  （几何上极贴近，但协方差尺度大），dilution=0，物理上自洽：
  大协方差下即使质心贯穿组合硬体半径，Alfano Pc 仍被稀释。
- **Pc > θM 支**：305 行满足，但全部 d ≥ h(e)（其中最小 d/h =
  1.428）→ 落入 R7 第一析取支（Warning）。最高 Pc 行为事件
  1723925273（ISS 25544 对 56183，Pc = 9.354e-4，d = 2850.5 m，
  h(e) = 55.5 m，d/h = 51.3）。305 行中 304 行 dilution=1（处于
  Pc-尺度曲线的稀释侧）。
- Warning 合计 305 + 1 = 306，与第 5 节一致 ✓。

**真实原因**：该数据集中"近到贯穿组合硬体半径"与"Pc 高于 1e-4"两个
条件从未同时成立——近距事件因协方差大而被稀释 Pc，高 Pc 事件则
几何上并不贴近。这是数据与 Pc 模型的真实性质，与 ESA 上
Dangerous=0 的机制不同（ESA 全数据连 d < h(e) 都不存在）。

## 7. 规则覆盖审计

| 规则 | 触发行数 | 说明 |
| --- | ---: | --- |
| R5 Normal | 86,585 | Pc ≤ θA ∧ d ≥ h |
| R6 Attention | 196,666 | θA < Pc ≤ θM ∧ d ≥ h |
| R7 Warning（析取1：Pc>θM ∧ d≥h） | 305 | |
| R7 Warning（析取2：Pc≤θM ∧ d<h） | 1 | ESA 上该析取支从未被真实数据触发 |
| R8 Dangerous | 0 | 数据上不可达，机制见第 6 节 |

- 分区完备：四规则掩码对有效行构成精确划分（overlap=0，gap=0，
  Σ=N=283,557）。
- 语义锁定：与 ESA 实现逐行一致（100% 行相同），阈值相等。
- 相对 ESA 的覆盖增益：TraCSS 首次为 R7 第二析取支提供了 1 个真实
  实例（ESA 的 Warning 全部来自第一析取支，d<h 为 0）。

## 8. ESA 与 TraCSS 内部对照

仅用于判断换数据集后的变化，**不自动写入论文**。ESA 侧数值由
ESA 处理后 CSV 重新计算，且与锁定的 risk_state_distribution.json
核对一致（recomputed == pinned）。

注意口径差异：ESA"样本数"为 CDM 快照（每事件多条），TraCSS 每行即
独立 conjunction。

| 项目 | ESA | TraCSS |
| --- | ---: | ---: |
| 样本数 | 162,634 | 283,557 |
| conjunction数量 | 13,154 | 283,557 |
| Normal | 141,471 | 86,585 |
| Attention | 20,447 | 196,666 |
| Warning | 716 | 306 |
| Dangerous | 0 | 0 |
| d<h数量 | 0 | 1 |
| Pc>1e-4数量 | 716 | 305 |
| Pc>1e-4 AND d<h | 0 | 0 |

## 9. TraCSS 作为正式替代数据集的适用性评价

### A. 数据完整性 —— 通过

Pc、d 直接存在于答案键；h(e) 可由官方逐对象 HBR 映射可靠计算
（覆盖率 100%）；仅 38/283,595 行（0.013%）因 Pc 为 NULL 剔除。
字段语义经指南确认，无名称猜测。

### B. 语义兼容性 —— 通过（R5–R8 范围内）

不改变 R5–R8 含义即可直接使用：Pc 无量纲、d 与 h(e) 统一为 km 后
比较，规则布尔结构与阈值原样运行，并与 ESA 实现逐行一致。
已显式记录的差异（Pc 编码、单位、HBR 来源、数据集用途、单行
conjunction 结构）均不改变规则输入语义。

### C. 状态覆盖 —— 覆盖 Normal/Attention/Warning；Dangerous 未出现

Dangerous 未出现的原因已查明（第 6 节），属数据真实性质；与 ESA
主实验的现状（Dangerous=0）一致，且 TraCSS 额外提供了 1 个真实的
d<h(e) 实例。

### D. 数据规模

- 总记录数：283,595（有效 283,557）
- 独立 conjunction：283,595（conj_id 全部唯一）
- 独立对象对：89,369（其中 17,981 对发生多次 conjunction，
  单对最多 216 次）
- 独立对象：22,908（TLE 22,457；历史 CDM 类 347；机动/受害对象 86；
  虚构对象 9；Osiris-Rex 类 4；另有 5 个对象 90001–90005 略低于
  指南 Table 2 公布的机动星历号段 90006–90190，如实记录，不影响
  任何字段语义）

### E. 可复现性 —— 通过

文件名、版本（20251009a / 指南 March 2026）、来源（Office of Space
1–3 节；管线 `experiments/tracss/scripts/run_all.py` 六步全自动，
只读原始数据。

## 结论：四问直答

**Q1：TraCSS 是否能够完整替代 ESA 提供 R5–R8 需要的数据？**
**能。** Pc、d、h(e) 三要素齐备且经官方文档确认语义；h(e) 连接覆盖率
100%；NULL Pc 仅 0.013%。

**Q2：数据语义是否与当前 TC-SSSAO 规则兼容？**
**兼容。** 冻结阈值与规则语义原样运行，与 ESA 实现逐行一致
（283,557/283,557），分区完备（overlap=0，gap=0，Σ=N）。
语义差异（Pc 线性编码、d 单位 km、HBR 官方目录来源、答案键用途、
单行 conjunction）均已显式记录，不改变 R5–R8 输入语义。

**Q3：TraCSS 中是否存在 Dangerous 真实样本？**
**不存在。** Pc > 1e-4 ∧ d < h(e) = 0 行。机制：唯一 1 例 d<h(e) 的
Pc 仅 6.59e-6（大协方差稀释）；305 例 Pc>1e-4 全部 d/h ≥ 1.428。

**Q4：是否推荐正式删除论文中的 ESA 实验并改写为 TraCSS 实验？**
**推荐作为 R5–R8 主风险状态实验的替代数据集**（规模 283,557 vs
162,634、官方答案键、要素齐备、可复现、R7 第二析取支首次获得真实
实例），但附三项保留，建议由您裁决后再动论文：
1. Dangerous 仍为 0，论文中关于 Dangerous 的表述需保持分析性口径
   （与现状相同，不新增"数据集含 Dangerous"类表述）；
2. TraCSS 答案键每个 conjunction 仅一行，无 ESA 式多时相 CDM 序列，
   基于快照序列的实验（状态演化/B3 迁移类、时序一致性、流式回放）
   无法在该数据上复现——若论文保留这些实验，需保留 ESA 作为该部分
   数据源或收缩相应声明范围；
3. 论文需如实说明数据集性质（含合成压力用例的筛查验证答案键）与
   Pc 方法（Alfano 2004，含指南的跨工具比较警告）。

---

附：产物清单（experiments/tracss/）
- scripts/：01_field_audit.py … 06_esa_comparison.py、run_all.py、
  common.py（全部 PASS）
- data/tracss_sfsh_normalized.csv.gz（适配器输出）
- results/：field_audit.json、adapter_summary.json、
  distribution_audit.json、risk_state_distribution.json、
  dangerous_analysis.json、esa_tracss_comparison.json、
  dataset_scale_extra.json
