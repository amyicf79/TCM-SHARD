# TCM-SHARD
### **S**yndromic **H**ierarchy **A**nalysis via **R**ule-based **D**ifferentiation
*Bridging Critical Care Data and Traditional Chinese Medicine (TCM) Theory*

![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)
![MIMIC-III v1.4](https://img.shields.io/badge/MIMIC--III-v1.4-orange.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)

> **Key Finding**: We analyzed 85,242 ICU stays from the MIMIC-III database and identified a novel high-mortality phenotype—**Heat Collapse (Re Jue, 热厥)**—within patients previously conflated with "Yangming Syndrome". Heat Collapse carries a 32.5% mortality rate, with an adjusted hazard ratio (aHR) of 2.30 (95% CI 2.16–2.45) independent of age and sex, significantly exceeding Shaoyin Collapse (17.8%, aHR 1.37).

---

## 📜 Abstract
TCM syndrome differentiation lacks standardized, scalable tools for critical care research. We developed TCM-SHARD, a rule-based framework that maps ICU electronic health record (EHR) data to 6 core TCM syndromes: Shaoyin Collapse (少阴寒化), Taiyin Deficiency (太阴病), Qi-Xue Stasis (气虚血瘀痰湿), Yangming Syndrome (阳明经证), Heat Collapse (热厥), and Unclassified. Validated on 85,242 MIMIC-III ICU stays, the framework achieved a 61.4% mapping hit rate with 63.3% manual agreement. Multivariable Cox regression confirmed independent prognostic value of TCM syndromes, with Heat Collapse emerging as the highest-risk phenotype. ICD mining of 32,911 unclassified stays revealed high prevalence of diabetes (E11*, 13.6%) and acute kidney injury (N17*, 13.7%), supporting future expansion of syndrome anchors. TCM-SHARD provides an open-source, reproducible platform for integrating TCM theory with critical care big data.

---

## 🔍 Background
In TCM, syndrome differentiation guides personalized treatment, but its subjectivity limits large-scale research. Critical care populations (e.g., sepsis, shock) exhibit complex pathophysiology that aligns with TCM concepts of "Yang Collapse" and "Heat Blocking Yang". Prior studies using EHR data often relied on black-box machine learning, lacking clinical interpretability. TCM-SHARD addresses this gap with transparent, rule-based mapping grounded in clinical expertise.

---

## ⚙️ Methods
### 1. Syndrome Definition
Six core syndromes were defined based on clinical guidelines and expert consensus:

| Syndrome Code | Clinical Name | Key Features |
|---------------|---------------|--------------|
| `sy_hn` | Shaoyin Collapse (少阴寒化) | Cardiogenic shock, vasopressor dependence, AKI |
| `rejue` | Heat Collapse (热厥) | Septic shock, vasopressor dependence, hyperinflammation |
| `ty_xh` | Taiyin Deficiency (太阴病) | GI bleeding, spleen deficiency, anemia |
| `qx_yt_003` | Qi-Xue Stasis (气虚血瘀痰湿) | COPD, chronic heart failure, diuretic use |
| `ym_bh` | Yangming Syndrome (阳明经证) | Sepsis without vasopressors, high fever |
| `unclassified` | Unclassified | No matching syndrome criteria |

### 2. Rule-Based Mapping
Mapping rules integrated ICD-9/10 codes, medication orders, and laboratory results (full rules in `src/mimic_crude_mapper_full.py`). Key innovations include splitting "Yangming Syndrome" into mild (no vasopressors) and severe (Heat Collapse, vasopressors) subtypes.

### 3. PCA Phase-Space Embedding
A Principal Component Analysis (PCA) model was trained on 13 gold-standard syndromes (`data/tcm_syndrome_matrix.csv`), capturing 56% variance in the first two principal components (PC1: Yin-Yang axis, PC2: Collapse severity). MIMIC cases were projected onto this space via anchor proxy logic (`src/bridge_mimic_to_pca.py`).

### 4. Prognostic Validation
Multivariable Cox proportional hazards models were used to assess the association between syndromes and mortality, adjusting for age and sex. Kaplan-Meier curves and log-rank tests evaluated survival differences.

### 5. Unclassified Mining
ICD frequency analysis of unclassified stays identified candidate syndromes for future expansion (e.g., Xiao Ke [消渴, diabetes], Ni Du [溺毒, renal failure]).

---

## 📊 Results
### 1. Mapping Performance
- Total ICU stays: 85,242
- Mapping hit rate: 61.4% (52,331/85,242)
- Manual agreement: 63.3% (19/30 randomly sampled cases)
- Syndrome distribution: Shaoyin (23.8%), Qi-Xue Stasis (17.5%), Taiyin (12.6%), Heat Collapse (7.5%), Yangming (0.8%), Unclassified (38.6%)

### 2. Prognostic Value

| Syndrome | N (%) | Mortality | Adjusted HR (95% CI) | P-value |
| :--- | :--- | :--- | :--- | :--- |
| Unclassified (Ref) | 32,911 (38.6%) | 6.4% | 1.00 | — |
| Taiyin Deficiency | 10,745 (12.6%) | 5.7% | 0.65 (0.59–0.71) | <0.001 |
| Qi-Xue Stasis | 14,950 (17.5%) | 7.1% | 0.66 (0.61–0.71) | <0.001 |
| Shaoyin Collapse | 20,244 (23.8%) | 17.8% | 1.37 (1.29–1.44) | <0.001 |
| **Heat Collapse** | **6,374 (7.5%)** | **32.5%** | **2.30 (2.16–2.45)** | **<0.001** |

### 3. Survival Analysis
![Kaplan-Meier Survival Curves](docs/figure1_km_curves.png)
*Figure 1: Kaplan-Meier survival curves by TCM syndrome. Heat Collapse (red) exhibits early, rapid mortality decline compared to Shaoyin Collapse (orange) and Unclassified (gray). Log-rank test p<0.001.*

![Forest Plot of Hazard Ratios](docs/figure2_forest_plot.png)
*Figure 2: Forest plot of adjusted hazard ratios for TCM syndromes. Error bars represent 95% confidence intervals.*

### 4. Unclassified Mining
- Top ICD categories: Diabetes (E11*, 13.6%, n=4,475), Acute Kidney Injury (N17*, 13.7%, n=4,514)
- Candidate new anchors: **Xiao Ke (消渴, diabetes)** and **Ni Du (溺毒, renal failure)**, which would increase mapping hit rate to ~72% if added.

---

## 🚀 Quick Start
### Prerequisites
1. Python 3.8+
2. MIMIC-III v1.4 access ([PhysioNet credentialed](https://physionet.org/content/mimiciii/1.4/))
3. Place MIMIC core CSVs in `data/mimic_core/` (or set `TCM_SHARD_DATA` environment variable)

### Installation
```bash
git clone https://github.com/amyicf79/TCM-SHARD.git
cd TCM-SHARD
pip install -r requirements.txt
```

### Run Demo Pipeline
1. **Train PCA model on gold-standard syndromes**:
```bash
python src/tcm_pca_engine.py --mode demo
```

2. **Map MIMIC stays to TCM syndromes**:
```bash
python src/mimic_crude_mapper_full.py
```

3. **Run survival analysis (generates Table 2 + Figures)**:
```bash
python src/analysis/survival_analysis.py
```

---

## 📂 Repository Structure
```
TCM-SHARD/
├── src/                         # Core source code
│   ├── config.py                # Path configuration (centralized, no hardcoding)
│   ├── tcm_pca_engine.py        # PCA training + bootstrap validation
│   ├── mimic_crude_mapper.py    # Lightweight mapper (small datasets)
│   ├── mimic_crude_mapper_full.py # Full MIMIC mapper (ICD-9/10 compatible)
│   ├── bridge_mimic_to_pca.py   # Anchor proxy connector
│   └── analysis/                # Analysis modules
│       └── survival_analysis.py # Cox regression + KM curves + forest plots
├── data/                        # Gold-standard data (no PHI)
│   ├── tcm_syndrome_matrix.csv  # 13 gold-standard syndromes (12 features)
│   ├── tcm_syndrome_matrix.json # Syndrome metadata (anchor roles, expectations)
│   └── validation/              # Manual verification datasets (de-identified)
│       ├── verification_30_final.csv    # 30-case manual review results
│       └── verification_30_enriched.csv # 30-case enriched clinical context
├── models/                      # Pretrained PCA model
│   └── tcm_pca_model.pkl
├── docs/                        # Results + manuscript drafts
│   ├── figure1_km_curves.png    # Kaplan-Meier survival curves
│   ├── figure2_forest_plot.png  # Forest plot of hazard ratios
│   ├── table2_cox_results.csv   # Full Cox regression results
│   └── unclassified_top50_icds.csv # Top 50 ICD codes in unclassified stays
├── requirements.txt             # Dependency list
├── .gitignore                   # Firewall for PHI and intermediate files
├── LICENSE                      # MIT License
└── README.md                    # This file
```

---

## ⚖️ Ethical Compliance
- **Data Privacy**: TCM-SHARD does not host any MIMIC-III data. Users must obtain their own PhysioNet credentials and comply with MIMIC data use agreements. All intermediate files containing protected health information (PHI) are excluded via `.gitignore`.
- **De-identification**: Validation datasets (`data/validation/`) are fully de-identified, containing only hadm_id, syndrome labels, and clinical reasoning (no patient identifiers).
- **Reproducibility**: All scripts are modular, commented, and configurable via `src/config.py` to ensure results can be reproduced across institutions.

---

## 📈 Future Work
1. **Expand Syndrome Anchors**: Integrate Xiao Ke (消渴, diabetes) and Ni Du (溺毒, renal failure) anchors to increase mapping hit rate to ~72%.
2. **Prospective Validation**: Validate the framework in real-time ICU settings with direct TCM expert assessment.
3. **Natural Language Processing**: Incorporate nursing notes and discharge summaries to capture tongue/pulse features missing from structured EHR data.
4. **Multi-Database Generalization**: Extend the framework to eICU, HiRID, and domestic ICU databases.

---

## 📜 Citation
If you use TCM-SHARD in your research, please cite:

```bibtex
@article{ixno2025tcmshard,
  title     = {Unmasking Heat Collapse: A Rule-Based TCM Syndrome Differentiation Framework for Critical Care Using the MIMIC-III Database},
  author    = {IXNO},
  journal   = {Critical Care Medicine},
  year      = {2025},
  volume    = {53},
  pages     = {XXX--XXX},
  doi       = {10.1097/CCM.000000000000XXXX},
  note      = {Code available at https://github.com/amyicf79/TCM-SHARD}
}
```

*Please also cite the MIMIC-III database:*

```bibtex
@article{johnson2016mimic,
  title   = {MIMIC-III, a freely accessible critical care database},
  author  = {Johnson, Alistair EW and Pollard, Tom J and Shen, Lu and
             Li-Wei, H Lehman and Feng, Mengling and Ghassemi, Mohammad and
             Moody, Benjamin and Szolovits, Peter and Celi, Leo Anthony and
             Mark, Roger G},
  journal = {Scientific Data},
  volume  = {3},
  pages   = {160035},
  year    = {2016},
  publisher = {Nature Publishing Group}
}
```

---

## 🤝 Contributing
Contributions are welcome! Please open an issue to discuss proposed changes or submit a pull request. For major changes, please contact the maintainer first.

---

## 📧 Contact
IXNO — amyicf79@gmail.com  
Project Link: [https://github.com/amyicf79/TCM-SHARD](https://github.com/amyicf79/TCM-SHARD)
