# 反事实能力验证实验报告（CF-1 观测证据删除 / CF-2 时间方向反转）

回应审稿意见："能力问题验证存在自证循环、缺少负例验证"。
正式能力验证回答"完整条件下能否得到预期结果"；本实验回答其逆命题：
当关键语义条件被删除或改变后，原有派生关系是否相应消失或改变。

- 运行器：`run_counterfactual_experiments.py`（与正式实验同一 pySHACL 执行路径：
  数据图=输入+本体+规则部署配置，rdfs 闭包 + advanced 规则，迭代至完整图不动点）；
- 机器可读结果：`outputs/counterfactual_results.json`；
- 三个运行的推理后完整图与 SHACL 报告：`outputs/graph_{baseline,cf1,cf2}_after.ttl`、
  `outputs/shacl_report_{baseline,cf1,cf2}.ttl/.txt`；
- 本实验只新增独立反事实副本与结果：本体、R1—R18、B1—B5、CZ-6A 数据、
  TraCSS 实验、正式实验数据与正式实验结果均未改动；
- CF-3（TraCSS 风险状态边界反事实）已完成，本报告仅引用其结论（见第 7 节），不重复运行。

## 1. 实验目的与单变量干预原则

干预原则为单变量：F ∧ C → R。保持事实集合 F 不变，仅移除或改变关键条件 C，
重新运行相同规则，观察结果 R 是否变化。不同时改变多个变量。

每个反事实运行均满足以下流程（运行时强制校验）：

1. 从原始基础事实复制构建独立测试图；
2. 施加且仅施加声明的单变量干预（差异集合运行时逐三元组校验）；
3. 测试图不含任何派生谓词三元组（未推理干净状态，运行时校验）；
4. 从干净状态重新执行同一正式规则集至不动点；
5. 检查目标派生关系是否重新产生——输出图中的派生三元组全部来自本次运行，
   不存在旧推理结果残留。

## 2. 实验前真实性核验

目标事件对取自**正式规则逻辑验证场景**
（`experiments/rule_logic_verification`，论文能力验证的正式 CQ 场景）中
已由规则真实生成的派生因果关系，不是为本实验新造的理想示例。

| 核验项 | 内容 |
| --- | --- |
| cause event | `https://w3id.org/tc-sssao/data/rule-scenario#Evt_Maneuver` |
| effect event | `https://w3id.org/tc-sssao/data/rule-scenario#Evt_Approach` |
| 事件类型 | OrbitManeuverEvent → ApproachEvent |
| 原因事件时间 | 发生 2026-08-01T09:00:00+00:00，区间 2026-08-01T09:00:00+00:00 — 2026-08-01T09:10:00+00:00 |
| 结果事件时间 | 发生 2026-08-01T10:00:00+00:00，区间 2026-08-01T10:00:00+00:00 — 2026-08-01T10:20:00+00:00 |
| 参与对象与角色 | 机动 affectsObject = https://w3id.org/tc-sssao/data/rule-scenario#TestSat_A；接近 hasPrimaryObject = https://w3id.org/tc-sssao/data/rule-scenario#TestSat_A、hasSecondaryObject = https://w3id.org/tc-sssao/data/rule-scenario#TestSat_B（o1≠o2） |
| 支持该关系的观测/评估数据 | 两事件各经 detectedFromData 关联 `rs:TestObsData`（RadarObservationData ⊂ SensorObservationData ⊂ ObservationData，经 RDFS 闭包满足 R3 的 `?d a ObservationData` 条件） |
| CausalAssertion IRI | 无（见下注记） |
| 原始 causesEvent 是否显式存在 | 否（输入图不含任何派生谓词） |
| 生成规则 | R3 OrbitManeuverCausesApproachRuleShape（直接生成）；其 precedesEvent 前提由 R1 EventPrecedenceRuleShape 生成 |

> **关于 CausalAssertion 的注记**：当前冻结规则集中 R3/R4 直接生成事件级
> causesEvent，不实例化 CausalAssertion；hasCausalEvidence 是 CausalAssertion 的
> 溯源属性（domain CausalAssertion，range SSAData），仅被完整性 Shape
>（tc_sssao_causal_assertion_integrity.ttl）检查，不被任何生成规则作为前提。
> CZ-6A 案例中的 causesEvent 由 B1 从显式 DirectCausalAssertion
>（`case:CZ6A_FragmentationRiskAssertion`）桥接生成，B1 同样不含证据前提。
> 因此 CF-1 的删除对象以 R3/R4 真实检查的事件级
> supportedByData/detectedFromData 证据链接为准。

**事件对选择理由**：R3 目标对（Evt_Maneuver → Evt_Approach）中两事件各有且仅有
一条证据链接，单三元组即可构成干净的证据删除干预；R4 目标对（Evt_Approach →
Risk_T0—T3）的风险事件侧各有两条证据链接，删除面更大。CZ-6A 事件对不适合作为
证据删除反事实的目标：其 causesEvent 由 B1 从显式断言桥接，不含 T/O/E_obs 联合
前提，删除事件级证据或 hasCausalEvidence 均不构成对 B1 前提的干预。

**基线复跑**（本实验内独立重跑正式场景，不触碰正式输出）：固定点 3 轮，每轮新增 [2013, 133, 0]，SHACL conforms=True；目标 causesEvent 重新生成：✓。正式实验输出对照：固定点新增序列 [2013, 133, 0]、conforms=True、R3 检查=True；本次基线复跑与正式结果一致：True。

## 3. CF-1：观测证据删除反事实

### 3.1 干预（单变量）

测试图 `data/cf1_evidence_removed_facts.ttl` 为正式场景事实的完整副本，
唯一差异（运行时校验通过）是删除 1 个三元组：

```
rs:Evt_Maneuver  onto:detectedFromData  rs:TestObsData
```

即移除 R3 证据条件 E_obs 中原因事件一侧的全部证据。事件实例、事件类型、
时间、对象、对象角色、结果事件与四个风险快照的证据链接及其余全部事实
与原场景逐三元组一致。

### 3.2 验证结果

| Item | Original | Evidence removed |
| --- | --- | --- |
| Temporal condition：precedesEvent(e_i, e_j)（R1 派生） | ✓ | ✓ |
| Object-role condition：affectsObject/primary/secondary 且 o1≠o2（显式） | ✓ | ✓ |
| Observation evidence：两事件均有 detectedFromData/supportedByData → ObservationData | ✓ | × |
| CausalAssertion generated | —（R3 不生成 CausalAssertion，见第 2 节注记） | —（同上） |
| causesEvent(e_i, e_j) generated（R3 目标） | ✓ | × |

补充观察（干预局部性与附带效应）：

- R4 因果边 causesEvent(Evt_Approach, Risk_T0—T3) 共 4 条仍全部生成：✓（被删证据不属于这些边的前提）；
- R1 时序关系不受影响：precedesEvent(Evt_Maneuver, Evt_Approach) 仍成立：✓；
- 推理后图中 Evt_Approach 的证据条件仍满足：✓，
  Evt_Maneuver 的证据条件已失效：✓；
- SHACL conforms=False，违规：R13（EventDataEvidenceShape，焦点 Evt_Maneuver）：空间事件缺少数据证据（detectedFromData 或 supportedByData）。该违规是 R13（EventDataEvidenceShape）对"被删除证据"这一干预本身的检出，
  即验证层正确报告了证据缺失，而非推理引入的不一致；
- CF-1 固定点 3 轮，每轮新增 [2012, 133, 0]：第一轮恰比基线少 1（2012 对 2013），差值对应未生成的目标 causesEvent 三元组；第二轮新增与基线一致，R5—R8 态势与 B3 演化派生不受影响。

### 3.3 判定：**PASS**

T 与 O 条件保持不变、E_obs 在原因事件侧被移除后，目标 causesEvent 未重新产生；其余 R4 因果边照常生成，无双向因果/因果环/时间方向冲突。

原始：T ∧ O ∧ E_obs → causesEvent 成立；反事实：T ∧ O ∧ ¬E_obs 下
相同规则未重新产生目标因果关系。

## 4. CF-2：时间方向反转反事实

### 4.1 干预（单变量）

测试图 `data/cf2_time_reversed_facts.ttl` 为正式场景事实的完整副本，
唯一差异（运行时校验通过）是互换两事件的时间区间，共 6 个时间三元组：

| 事件 | 原时间区间（发生时间） | 反转后时间区间（发生时间） | 持续时间 |
| --- | --- | --- | --- |
| Evt_Maneuver | 09:00—09:10（09:00） | 10:00—10:10（10:00） | 10 分钟，不变 |
| Evt_Approach | 10:00—10:20（10:00） | 09:00—09:20（09:00） | 20 分钟，不变 |

修改后每事件仍满足 start ≤ end，无非法日期，事件持续时间未改变；
事件实例、类型、对象、对象角色、观测证据、四个风险快照及其余领域事实全部不变。
事件顺序由 Evt_Maneuver < Evt_Approach 反转为 Evt_Approach < Evt_Maneuver。

### 4.2 时间关系结果

| 关系 | 原始 | 时间反转后 |
| --- | --- | --- |
| precedesEvent(Evt_Maneuver, Evt_Approach) | ✓ | × |
| precedesEvent(Evt_Approach, Evt_Maneuver) | × | ✓ |
| followsEvent(Evt_Approach, Evt_Maneuver) | ✓ | × |
| followsEvent(Evt_Maneuver, Evt_Approach) | × | ✓ |

原方向 precedesEvent 消失，反方向 precedesEvent/followsEvent 按 R1 重新生成。

### 4.3 因果方向结果

| 关系 | 原始 | 时间反转后 |
| --- | --- | --- |
| causesEvent(Evt_Maneuver, Evt_Approach)（原方向，R3 目标） | ✓ | × |
| causesEvent(Evt_Approach, Evt_Maneuver)（反方向） | × | × |
| causesEvent(Evt_Approach, Risk_T0—T3)（R4，共 4 条） | ✓ | ✓ |

如实记录：

- 原方向 causesEvent(Evt_Maneuver, Evt_Approach) 在其时间前提
  precedesEvent(Evt_Maneuver, Evt_Approach) 失效后**未继续成立**；
- 反方向 causesEvent(Evt_Approach, Evt_Maneuver) **未生成**——当前规则集中
  不存在产生它的路径：R3 要求原因侧为 OrbitManeuverEvent、结果侧为
  ApproachEvent（类型方向固定），R4 要求结果侧为 CollisionRiskEvent，
  B1 要求显式 CausalAssertion。本实验的重点不是强制出现反向因果，而是验证
  原方向 causesEvent 不能在其时间前提失效后无条件继续成立——已验证；
- R4 因果边（Evt_Approach → Risk_T0—T3）不受影响：Evt_Approach 移至 09:00 后
  仍先于全部风险快照（11:00—14:00），其前提完好；
- SHACL conforms=True，违规：无；
- CF-2 固定点 3 轮，每轮新增 [2012, 133, 0]：第一轮恰比基线少 1（2012 对 2013），差值对应未生成的目标 causesEvent 三元组（时序边总数不变，仅方向反转）；第二轮新增与基线一致。

### 4.4 判定：**PASS**

原向 precedesEvent 消失、反向 precedesEvent/followsEvent 按 R1 生成；原向 causesEvent 随其时间前提失效而消失；R4 因果边不受影响；无 R9/R10/R11 违规、无双向因果、无因果环。

## 5. 一致性检查

三个运行均从未推理干净输入图启动，输出中的派生三元组全部来自本次运行
（输入残留校验通过，见第 1 节流程 3）。

| 检查项 | Baseline | CF-1 | CF-2 |
| --- | --- | --- | --- |
| SHACL conforms | True | False | True |
| SHACL violations | 无 | R13（EventDataEvidenceShape，焦点 Evt_Maneuver）：空间事件缺少数据证据（detectedFromData 或 supportedByData） | 无 |
| 双向因果对数量 | 0 | 0 | 0 |
| 因果环（causesEvent⁺ 自环） | 无 | 无 | 无 |
| 时间方向冲突（precedesEvent 双向对） | 0 | 0 | 0 |
| 输入残留派生三元组 | 0 | 0 | 0 |

CF-1 的唯一违规是 R13 对被删除证据的检出（预期信号，表明证据缺失可被验证层
发现）；CF-1/CF-2 均未出现双向因果、因果环或时间方向冲突。

## 6. 结果判定汇总

判定标准——PASS：关键条件改变后，目标派生结果按规则预期消失或改变；
PARTIAL PASS：目标结果变化但存在额外规则路径仍可产生部分关系；
FAIL：关键条件已被删除/反转，但原有目标关系仍以相同方式重新生成。
本实验未为得到 PASS 修改任何正式规则。

| 实验 | 判定 | 说明 |
| --- | --- | --- |
| CF-1 观测证据删除 | PASS | T 与 O 条件保持不变、E_obs 在原因事件侧被移除后，目标 causesEvent 未重新产生；其余 R4 因果边照常生成，无双向因果/因果环/时间方向冲突。 |
| CF-2 时间方向反转 | PASS | 原向 precedesEvent 消失、反向 precedesEvent/followsEvent 按 R1 生成；原向 causesEvent 随其时间前提失效而消失；R4 因果边不受影响；无 R9/R10/R11 违规、无双向因果、无因果环。 |
| CF-3 风险状态边界（引用） | PASS | 引用已完成的 TraCSS 风险状态边界反事实（experiments/tracss_threshold_sensitivity 报告第5节），本实验不重复运行。 |

## 7. CF-3：风险状态边界反事实（引用 TraCSS，不重跑）

第三组反事实已在 `experiments/tracss_threshold_sensitivity` 完成
（见其报告第 5 节，25 参数点全绿），本实验仅引用，不重复运行。

真实近距离样本（event_id 1723730887，逐字段核验）：

| Pc | d (km) | h(e) (km) | d/h |
| ---: | ---: | ---: | ---: |
| 6.593401×10⁻⁶ | 0.008684 | 0.011017 | 0.7882（d < h(e) 成立） |

同一样本、同一 θ_A=10⁻⁷，仅改变部署参数 θ_M：

| θ_M | Pc > θ_M ∧ d < h(e) | 该样本派生状态 |
| --- | --- | --- |
| 10⁻⁴（基线） | 不成立 | Warning |
| 10⁻⁶ | 成立 | Dangerous |

精确边界：Dangerous 当且仅当 θ_M < 6.593401×10⁻⁶（严格不等）。
风险状态随关键边界条件翻转而改变，与 CF-1/CF-2 共同构成三类反事实验证。

## 8. 三项反事实验证汇总

| Test | Changed condition | Other facts fixed | Original result | Counterfactual result | Verdict |
| --- | --- | --- | --- | --- | --- |
| CF-1 观测证据删除 | 删除 Evt_Maneuver 的 detectedFromData 证据链接（R3 的 E_obs 前提） | 事件实例/类型/时间/对象角色/其余证据/风险快照全部固定 | causesEvent(Evt_Maneuver, Evt_Approach) 由 R3 生成 | 未重新生成；R13 检出证据缺失；R4 边不受影响 | PASS |
| CF-2 时间方向反转 | 互换两事件时间区间（持续时间不变，6 个时间三元组） | 事件实例/类型/对象角色/观测证据/风险快照全部固定 | precedesEvent(Man, App) ∧ causesEvent(Man, App) | 时序关系反向生成；原向 causesEvent 随前提失效消失；无反向因果与一致性违规 | PASS |
| CF-3 风险状态边界（TraCSS） | θ_M：10⁻⁴ → 10⁻⁶（部署参数） | 样本 Pc=6.593401×10⁻⁶、d=0.008684 km、h(e)=0.011017 km 与 θ_A=10⁻⁷ 固定 | Warning | Dangerous（Pc > θ_M ∧ d < h(e) 成立） | PASS |

## 9. 复现与边界

```
python experiments/counterfactual_verification/run_counterfactual_experiments.py
```

结论边界：

- 本实验验证的是规则层负例行为（条件缺失/改变时派生关系相应消失或改变），
  不构成对真实事件物理因果性的主张；
- 反事实副本仅存在于本实验目录，正式实验数据、正式规则与正式结果未改动；
- CF-1 中 R13 违规是对干预的检出，不应解读为规则不一致；
- CF-2 中反方向 causesEvent 未生成是规则类型方向的如实结果，
  不构成对反向物理因果的否定。
