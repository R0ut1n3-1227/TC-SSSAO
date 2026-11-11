# TraCSS IVV 数据集适配实验（experiments/tracss）

将 TC-SSSAO 主风险实验数据集由 ESA Collision Avoidance Challenge 迁移至
TraCSS Conjunction Assessment Verification Dataset 的第一阶段工作：
新数据集适配与可行性验证。

本目录为独立实验区，严格只读于：ESA 现有实验、R5–R8 规则与阈值
（θA=1e-7、θM=1e-4，冻结值）、本体文件、论文文件、原始 TraCSS 下载。

## 输入（用户提供，原始文件不改动，位于 data/tracss/raw/）

| 文件 | 用途 |
| --- | --- |
| data/tracss/raw/IVV_Releasable_Dataset_SFSH_DiscreteHBR.csv.gz | SFSH 离散 HBR 答案键（CSieve run_id 1662，283,595 行） |
| data/tracss/raw/AerospaceIVVDataset_20251009a_Size_ScreeningVolumes.csv.gz | 逐对象 HBR（m）与 SFSH 筛查体积映射 |
| data/tracss/raw/Conjunction_Screening_Testset_Users_Guide.pdf | 字段语义与单位的唯一权威依据（Table 5 等） |

未使用：完整星历数据集（约 21.74 GB，任务约束暂不处理）；
IVV_Releasable_Dataset_Spherical_DefaultHBR.csv.gz（常数 HBR 0.5 m，
无法构造事件级 h(e)）。

## 结构

- `scripts/` — 01 字段审计 → 02 适配器 → 03 分布审计 → 04 R5–R8 评估
  → 05 Dangerous 可达性分析 → 06 ESA 内部对照；`run_all.py` 顺序执行。
- `data/` — 适配器输出（标准字段归一化 CSV，非原始数据）。
- `results/` — 各步骤 JSON/CSV 结果。
- `tracss_dataset_migration_report.md` — 迁移可行性报告（主交付物）。

## 运行

```bash
cd experiments/tracss/scripts
python run_all.py
```

## 关键语义（依据 User's Guide，禁止凭字段名猜测）

- `prob` = 碰撞概率 Pc（Alfano 2004），无量纲，直接可用；
  38 行 NULL（协方差度无法计算时），预检剔除。
- `min_range` = 最小miss distance，单位 km，直接可用。
- `mdistance` = Mahalanobis 距离，**不是** miss distance，禁止映射为 d。
- `epoch` = TCA（UTC）；筛查窗 2025-01-01T12:00Z – 2025-01-08T12:00Z。
- 映射文件 `HBR` 为逐对象半径，单位 m（证据：指南 0.5 m 默认 HBR +
  ISS 25544 → 55.0）；h(e) = (HBR[obj1] + HBR[obj2]) / 1000（km）。
- `conj_id` 每行唯一（一个 conjunction 一行，obj2 > obj1），
  无 ESA 式多时相 CDM 序列。
