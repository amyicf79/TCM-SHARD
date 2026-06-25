# TCM-SHARD 项目路线图

> 最后更新：2026-06-25  
> 仓库：https://github.com/amyicf79/TCM-SHARD

---

## 已完成 ✅

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M1 金标锚点 | 13证型PCA矩阵，56%累计方差，锚点坐标验证通过 | ✅ |
| M2 粗糙映射 | 五条高确信规则（ICD-9/10双语），30条手工核对→63.3%吻合 | ✅ |
| M3 全量MIMIC | 85,242 ICU stays，61.4%命中率，热厥aHR 2.30 | ✅ |
| M4 Cox回归 | 多变量Cox，KM曲线，Table 2森林图 | ✅ |
| M5 ICD挖掘 | Unclassified 38.6%中Top ICD：E11*(消渴13.6%)、N17*(溺毒13.7%) | ✅ |
| M6 GitHub开源 | TCM-SHARD repo + 学术README + Release v0.1.0 + Cover Letter | ✅ |

---

## 待完成 📋

### v0.2.0 — 锚点扩展
- [ ] 消渴（糖尿病）金标向量 + 映射规则
- [ ] 溺毒（肾衰）金标向量 + 映射规则
- [ ] 命中率目标：61.4% → ~72%
- [ ] Cox回归重跑（含新证型）

### v0.3.0 — 论文投稿
- [ ] 论文正文初稿（Abstract/Methods/Results/Discussion）
- [ ] Zenodo绑定 → 生成真实DOI
- [ ] 投稿 CCM（Cover Letter已备）
- [ ] 补充材料打包（Figures 300DPI + Tables可编辑格式）

### 远期
- [ ] 多数据库扩展（eICU / HiRID）
- [ ] NLP 舌脉特征提取（护理记录 + 出院小结）
- [ ] 前瞻性验证（实时ICU + TCM专家并行评估）
- [ ] 国自然申请

---

## 文件结构

```
J:\IXNOV1.0-中医\
├── TCM-SHARD/          ← GitHub开源仓库
│   ├── src/            ← 核心代码
│   ├── data/           ← 金标矩阵 + 验证集
│   ├── docs/           ← Cover Letter + Data Availability + 论文草稿
│   └── results/        ← Cox结果CSV + KM图 + ICD频次表
│
├── temp/               ← 实验脚本/中间产物（不入Git）
│   └── mimic_to_soul_bridge.py  ← MIMIC→Soul桥接引擎
│
├── tcm_knowledge.db    ← TCM文档自学习知识库
├── gene_pool/          ← 基因池（GA进化引擎用）
└── start_all.bat       ← 一键全栈启动
```
