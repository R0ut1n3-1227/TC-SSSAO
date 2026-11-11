# 规则逻辑验证实验（通用场景）

通用规则验证：同一交会目标对的四快照（T0—T3）场景，承担
R1/R3—R8/B3 探针与 R9—R11 一致性检查的正面验证。

## 输入

- `data/scenario_facts.ttl`：四快照场景事实（唯一手工维护输入）。

## 运行器

| 脚本 | 覆盖 |
|---|---|
| `run_rule_scenario.py` | 主场景推理：R1 时序、R3/R4 因果、R5—R8 四级态势、B3 跨快照演化 |
| `run_boundary_tests.py` | 阈值边界测试（θ_A/θ_M 临界值两侧判定翻转） |
| `run_generic_projection_tests.py` | B4/B5 语义投影通用夹具 |
| `run_causal_confidence_tests.py` | B1 因果断言置信度投影 |

需要运行某项实验时，直接调用上表对应脚本；不再通过自动复现套件执行。

## 输出

`outputs/`（瞬态，不长期保存）：`graph_before.ttl` / `graph_after_full.ttl`
（图4-1/4-3 与图生成器的内容来源）及各实验输出。
