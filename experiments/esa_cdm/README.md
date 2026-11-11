# ESA CDM 实验（experiments/esa_cdm/）

ESA Collision Avoidance Challenge 数据集上的保留实验，当前用于内部对照和部分验证；正式英文论文的主要风险状态实验使用 TraCSS。

## 目录

| 路径 | 内容 |
|---|---|
| `figures/`、`rdf/` | 可再生中间产物（13 生成图、04 生成 RDF；可安全删除后由管线重建） |
| `requirements.txt` | 本实验额外依赖 |

数据集本体不在本目录：`data/esa_cdm/{raw,processed,metadata}/`

## 配置

实验参数无独立 configs/ 目录：部署阈值（θ_A/θ_M 等）的唯一来源是
`rules/tc_sssao_rule_config.ttl`；管线常量（数据目录、官方 URL、
DOI、文件名）集中在 `scripts/common.py`；评估用到的 NASA 阈值与四级状态
逻辑在评估脚本内与规则配置保持一致。

## 运行

```bash
cd experiments/esa_cdm
python scripts/run_all.py     # 完整管线（约 8 分钟）：01 下载/解包官方 ZIP
                              # → 02 数据集审计 → 03 预处理 → 04 构建 RDF
                              # → 05 预检 → 06 风险状态 → 07 状态演化
                              # → 08 故障注入 → 09 可扩展性 → 10 流式回放
                              # → 11 消融 → 12 表 → 13 图
```

任一步失败即停止并写 `results/pipeline_log.json`；全部 PASS 后重建
`results/results_manifest.json`（清单键为 workspace 相对路径）。


运行结果表和 JSON 保留在 results/；已有控制台日志与 XML 记录集中到 results/logs/。
