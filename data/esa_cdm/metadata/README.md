# ESA Collision Avoidance Challenge 数据集元数据

本目录保存数据集的**来源与结构统计**。原始大数据本体位于
`../raw/`（官方 ZIP 归档，下载/解包均在该层完成）；预处理产物位于
`../processed/`。

## 来源

| 项 | 值 |
|---|---|
| 数据集 | ESA Collision Avoidance Challenge dataset（Zenodo v1） |
| DOI | [10.5281/zenodo.4463683](https://doi.org/10.5281/zenodo.4463683) |
| 官方 URL | <https://zenodo.org/records/4463683/files/Collision%20Avoidance%20Challenge%20-%20Dataset.zip?download=1> |
| 下载日期 | 2026-09-11 |
| 官方归档 | `Collision Avoidance Challenge - Dataset.zip`（221,128,642 字节） |

## 官方口径（审计已逐项核验）

- 训练集：162,634 行 / 13,154 个独立事件 / 103 列
- 测试集：24,484 行 / 2,167 个独立事件

## 文件

- `download_verification.json` — 下载记录：官方 URL、归档字节数与解包文件列表。
- `DATASET_AUDIT.json` — 数据集审计（`experiments/esa_cdm/scripts/02_dataset_audit.py`
  生成）：官方口径核验、逐文件行数/事件数/列数、缺失与重复统计。
  字段语义说明见 `../../../docs/esa_cdm/DATASET_AUDIT.md` 与
  `../../../docs/esa_cdm/ESA_FIELD_SEMANTIC_AUDIT.md`；CDM→TC-SSSAO 字段映射见
  `../../../docs/esa_cdm/CDM_TO_TC_SSSAO_MAPPING.md`。

## 重新获取

```bash
cd ../../..                              # workspace 根
python experiments/esa_cdm/scripts/01_download_or_verify.py
```

已有归档直接解包，缺失时从官方 URL 下载。
