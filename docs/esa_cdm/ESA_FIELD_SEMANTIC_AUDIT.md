# ESA字段语义与单位审计

## 权威依据

本审计仅采用ESA随Zenodo v1归档发布的`raw_data_2015-2019.txt`字段说明及数据论文（Uriot等，DOI: 10.1007/s42064-021-0101-5）。归档中的每一行是一条CDM，`event_id`标识一个交会事件，同一事件的多行构成CDM时间序列。数据已匿名化。

## 本研究使用或保留的字段

| 字段 | 官方含义 | 官方单位 | 当前处理 |
|---|---|---:|---|
| `event_id` | 每个collision/close-approach event的唯一ID | 标识符 | 映射为一个ApproachEvent语境；不映射为每行一个交会 |
| `risk` | 每条CDM历元的self-computed risk，base-10 log | `log10(Pc)` | 保留原值，并严格转换为`Pc=10^risk`后才执行Preflight/R5—R8 |
| `time_to_tca` | CDM创建时刻到TCA的时间间隔 | day | 仅在同一`event_id`内降序排序；不伪造绝对时间 |
| `mission_id` | 受影响任务的标识符 | 标识符 | 作为匿名任务元数据，不解释为稳定航天器ID |
| `max_risk_estimate` | 缩放组合协方差得到的最大碰撞概率 | probability | 保留，不替代本实验使用的`risk` |
| `max_risk_scaling` | 最大碰撞概率的缩放因子 | 官方说明未给单位 | 保留，不参与R5—R8 |
| `miss_distance` | TCA时追踪体与目标体相对位置/距离 | m | 除以1000映射为km |
| `relative_speed` | TCA时两目标相对速度 | m/s | 保留为评估元数据 |
| `relative_position_{r,t,n}` | 径向、切向、法向相对位置 | m | 保留 |
| `relative_velocity_{r,t,n}` | 径向、切向、法向相对速度 | m/s | 保留 |
| `t_span`,`c_span` | 碰撞风险算法使用的目标尺寸；追踪体最小假定2 m直径 | m | 依据官方“size”和数据论文“diameter”语义，计算组合硬体半径`(t_span+c_span)/(2*1000)` km |
| `c_object_type` | 与卫星存在碰撞风险的目标类型 | 类别 | 映射为追踪体类型元数据 |
| `x_sigma_{r,t,n}` | 位置协方差标准差 | m | 保留为来源质量候选信息 |
| `x_sigma_{rdot,tdot,ndot}` | 速度协方差标准差 | m/s | 保留为来源质量候选信息 |
| `x_c*`相关项 | 协方差相关系数 | 无量纲 | 保留，不进入本版因果规则 |
| `x_obs_available` | 每条CDM可用于轨道确定的观测数 | count | 保留为未来Evidence Quality输入 |
| `x_obs_used` | 每条CDM实际用于轨道确定的观测数 | count | 同上 |
| `x_weighted_rms` | 最小二乘轨道确定的加权RMS | 官方说明未给单位 | 原样保留，不猜测单位 |
| `x_actual_od_span` | 轨道确定更新区间实际长度 | day | 保留 |
| `x_recommended_od_span` | 轨道确定更新区间建议长度 | day | 保留 |
| `x_time_lastob_{start,end}` | 相对CDM创建历元的末次接收观测区间 | day | 保留，不当作绝对时间 |
| `x_j2k_sma`,`x_j2k_inc`,`x_ecc` | 半长轴、倾角、偏心率 | km, degree, 无量纲 | 保留 |
| `x_h_apo`,`x_h_per` | 相对地球半径的远/近地点高度 | km | 保留 |
| `x_rcs_estimate` | 雷达散射截面积 | m2 | 保留 |
| `x_cd_area_over_mass` | 弹道系数 | m2/kg | 保留 |

## 审计结论

用于R5—R8的`risk`、`miss_distance`、`t_span`和`c_span`在训练集162634行中均完整，转换后全部通过输入契约。无法从匿名数据恢复绝对CDM创建时刻、绝对TCA时刻或跨事件稳定追踪体身份，因此当前适配层没有构造这些事实。官方未说明单位的字段保持原值且不进入规则判断。
