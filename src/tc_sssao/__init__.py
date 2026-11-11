"""太空安全态势感知本体库 (TC-SSSAO)

基于"时序因果联合构建"方法论的概念级 TBox 本体。

核心设计原则:
  - 纯概念层: 无实体概念, 无实例补充, 仅保留抽象概念类
  - 9 个顶层分支: SpaceObject / Orbit / ObservationSystem /
                   ObservationData / SpaceEnvironment / SpaceEvent /
                   SituationState / SecurityThreat / ResponseMeasure
  - 时间作为属性: 不建立独立时间业务节点,通过数据属性与 OWL-Time 引用表达
  - 时序因果联合: 基于事件时间属性建立时序关系,基于风险/状态/响应建立因果关系
  - 规则推理: R1–R18 与 B1–B5 由独立 SHACL-SPARQL 规则层实现，不作为领域本体类。
"""

__author__ = "TC-SSSAO"