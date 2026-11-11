# 标准互操作测试（标准对齐验证，spec 第 12 节）

验证 TC-SSSAO 与四个通用标准本体之间的**选择性语义对齐**在 RDFS 闭包下
按预期工作。对齐公理的唯一真源为 `ontology/tc_sssao_alignments.ttl`，已由
`scripts/build/apply_standard_alignments.py` 合并进 `ontology/tc_sssao.owl`。

## 标准版本基线

| 标准 | 版本 |
|---|---|
| OWL-Time | W3C Recommendation, 19 October 2017 |
| SOSA/SSN | W3C Recommendation, 19 October 2017（"2023 Edition" 为草案，不作基线） |
| PROV-O | W3C Recommendation, 30 April 2013 |
| GeoSPARQL | OGC GeoSPARQL 1.1, OGC 22-047r1 |

## 测试组

| 组 | 数据 | 验证内容 |
|---|---|---|
| T1 OWL-Time | `data/temporal_alignment.ttl` | `TimeInstant⊑time:Instant`、`TimeInterval⊑time:Interval`、`occursAtTime/occursInTimeInterval⊑time:hasTime` 的类型/属性推断 |
| T2 SOSA/SSN | `data/sosa_alignment.ttl` | `Sensor⊑sosa:Sensor`、`ObservationActivity⊑sosa:Observation`、`madeBySensor⊑sosa:madeBySensor`、`ObservationData⊑sosa:Result`；负向：本地 `hasObservationResult`/`hasFeatureOfInterest` 不再错误生成 SOSA 关系 |
| T3 PROV-O | `data/prov_alignment.ttl` | `SSAData⊑prov:Entity`、`SSAActivity⊑prov:Activity`、`DataProvider⊑prov:Agent`、`generatedByActivity⊑prov:wasGeneratedBy`、`CausalAssertion⊑prov:Entity`、`hasCausalEvidence⊑prov:wasDerivedFrom`；实例级 `prov:wasAttributedTo` 溯源模式 |
| T4 GeoSPARQL | `data/geosparql_alignment.ttl` | `SpaceObject⊑geo:Feature`、`Orbit⊑geo:Feature`；`Feature—geo:hasGeometry→geo:Geometry—geo:asWKT→wktLiteral` 标准模式；负向：Feature 不被错误推断为 `geo:Geometry` |
| REMOVED（负向） | （schema） | 6 条已移除错误映射/注解不得回归 |

所有测试实例均为合成测试数据（`Interop*` 前缀），不含任何案例事实。

## 运行

```bash
python experiments/standard_interoperability/run_alignment_tests.py
```

输出：`outputs/standard_alignment_test_results.json` / `.csv`；全部通过时退出码 0。

## 设计约束（spec 第 1 节）

- 不 `owl:imports` 任何外部本体；仅保留外部术语的最小 OWL 2 DL 声明；
- 不使用 `owl:equivalentClass` / `owl:equivalentProperty` 声明与外部术语的等价；
- ObjectProperty 与 DatatypeProperty 不跨类型映射（字面量时间属性仅 `rdfs:seeAlso`）；
- `precedesEvent` / `overlapsWithEvent`（事件级时间关系）与 OWL-Time（时间实体关系）
  语义层次不同，仅 `rdfs:seeAlso`，见对齐模块 rationale。
