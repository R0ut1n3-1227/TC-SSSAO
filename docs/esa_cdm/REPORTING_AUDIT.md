> 适用范围（2026-10-22）：以下为保留的 ESA 旧实验统计口径记录，不代表当前 TraCSS 英文论文或本次清理后的验证结论。

# TC-SSSAO 实验报告口径审计

审计日期：2026-09-11  
审计对象：论文当时稿、ESA脚本01—13、`common.py`、机器结果JSON/CSV、正式Input Preflight及50事件RDF产物。  
结论：**发现5类必须修正的报告口径；未发现状态数、事件数或B3计数被伪造。论文修订前门禁通过。**

## 1. 数字—代码—执行路径追踪

| 论文数字/结论 | 机器来源 | 实际执行路径 | 审计结论 |
|---|---|---|---|
| 162634 CDM、13154事件、103列 | `DATASET_AUDIT.json` | 直接读取ESA训练CSV并统计 | 真实计算，可保留 |
| 输入完整162634、通过率100% | `mapping_coverage.json` | `preprocess_frame`和`05_preflight_eval.py`以Pandas检查Pc、距离、HBR、相对时间、事件键、重复行 | 真实计算，但它是**执行层等价输入契约**，不是全量RDF正式Preflight |
| Normal 141471、Attention 20447、Warning 716、Dangerous 0 | `risk_state_distribution.json` | Pandas/NumPy按锁定R5—R8前件分类 | 真实计算；属于事件分区执行层结果，不是全量SHACL物化图计数 |
| B3 1605；错误跨事件/跨未评级/下降边为0 | `state_evolution.json`、`b3_transitions.csv` | `derive_transitions`按`event_id`分组、`time_to_tca`排序并比较相邻等级 | 真实计算；属于B3执行层等价派生事实 |
| 7/5/3/2/1 d一致率及样本数 | `state_evolution.json` | Pandas事件分组、0.5 d容差选点，与最终可用CDM状态比较 | 真实计算；不是分类准确率或ground truth |
| 11/11故障检出 | `fault_injection.json` | Python受控故障判定，映射至Preflight/R10/R11/R14等职责 | 真实受控测试；不应暗示11项均通过完整SHACL引擎执行 |
| 100事件streaming与batch“同构” | `streaming_replay.json` | 比较`set[tuple]`形式的状态事实与B3派生事实 | **不是RDFLib Graph，也未调用图同构算法；必须改为派生事实集合一致** |
| 0.192…24.981 s | `scalability.json` | 完整CSV先载入Pandas；每档选择事件子集后测执行层输入检查、事件分区排序、NumPy状态判定、B3及轻量一致性检查 | 真实wall-clock，但不是4M+ RDF、pySHACL或完整SHACL-SPARQL全图推理时间 |
| 4456833输入、4946340输出“三元组” | `mapping_triple_count`和算术公式 | 按映射模板计算的确定性**估算数量**，未构建全量RDF Graph | 不能写成实际全量图三元组计数；如保留必须标“模板估算” |
| 所有规模档2轮固定点 | `09_scalability.py` | `fixed_point_iterations: 2`硬编码，未逐轮运行规则 | **不是实测，必须从脚本、结果、表格和论文删除** |
| 50事件RDF首轮新增、次轮零新增 | `rdf_50event_report.json` | 构建100条CDM的真实RDF图，直接执行锁定R5—R8 `sh:construct`两轮并统计新增量`[300,0]` | 该样本的两轮观察真实；可独立报告，不外推到全量规模档 |
| 峰值248.914 MB | `process_peak_rss_mb` | 同一Python进程已先加载完整162634行，再顺序跑所有规模档；读取累计peak working set | 只能解释为**全量数据加载条件下该进程的峰值工作集**，不能解释为每档独立内存需求 |
| 13/13、47/47、4/4、30/30、HermiT/OOPS | 旧复现、专项测试及最终验证日志 | 实际测试入口运行 | 可保留；提交前须重新执行 |

## 2. 重点问题判定

### 2.1 固定点轮数

`09_scalability.py`第76行将`fixed_point_iterations`直接赋值为2，汇总阶段仅收集该常量。因此旧稿”各档均……2轮固定点”和表8固定点列没有实测依据。本轮修正删除该字段及表列。仅保留50事件RDF实验的真实新增量`[300,0]`，并在理论终止性说明中明确不同规模不保证相同轮数。

### 2.2 24.981 s

计时对象是事件分区执行层原型：Pandas/NumPy输入契约、`event_id`内排序、状态判定、B3事实生成和轻量检查。全量训练表读取和子集选择发生在`run_once`计时之外；没有构建约445万条全量RDF，没有运行pySHACL全图固定点。因此正式表述为“事件分区执行层原型在当前硬件上的三次平均处理时间”。

### 2.3 Preflight 100%

全量162634行没有进入`check_rule_input_preflight.py`所需的RDF Graph。全量100%来自与R5—R8关键数值契约对应的Pandas检查，正式名称改为“R5—R8执行层输入契约通过率”。正式Input Preflight继续由旧受控RDF回归验证；50事件RDF门禁实际执行锁定R5—R8 CONSTRUCT，但其`preflight`字段同样来自执行层布尔列，不能称正式RDF Preflight。

### 2.4 Streaming

`10_streaming_replay.py`构造的是状态和B3关系的tuple集合。`batch == incremental`证明派生事实集合相等，不证明完整RDF图同构。输出键与论文措辞必须同步修正。

### 2.5 R1、三元组和内存

规模实验采用`event_id`分区排序，不是原始R1对全部SpaceEvent的全局pairwise物化。三元组数为映射模板估算，内存为已加载全量表的单进程累计峰值。三者均需在报告字段和论文中明示。

## 3. 硬编码、模拟与实测分类

| 类别 | 项目 |
|---|---|
| 无效硬编码结果 | scalability固定点轮数=2 |
| 确定性估算 | 全量输入/输出三元组数 |
| 执行层等价计算 | 输入契约、R5—R8、B3、streaming facts、ESA消融 |
| 真实RDF规则执行 | 50事件/100 CDM的R5—R8 CONSTRUCT两轮 |
| 正式回归 | 旧Input Preflight、语义回归、状态语义、标准对齐、HermiT、OOPS |
| 实测性能 | 事件分区Pandas/NumPy执行层wall-clock；全量加载进程峰值工作集 |

## 4. 审计决定

不新增科学模块，不补做全量pySHACL，不改变状态数与规则。通过报告字段重命名、删除伪固定点指标、改正streaming/Preflight/三元组/内存措辞，使所有claim与现有证据一致。
