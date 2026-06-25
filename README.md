# TCM-SHARD
### **S**yndromic **H**ierarchy **A**nalysis via **R**ule-based **D**ifferentiation
*Bridging Critical Care Data and TCM Theory*

![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

> **Core Discovery**: Analyzing 85,242 ICU stays in MIMIC-III revealed a distinct high-mortality phenotype—**Heat Collapse (Re Jue)**—within patients previously conflated with "Yangming Syndrome". Heat Collapse carries a **32.5% mortality rate** (adjusted HR 2.30, 95% CI 2.16-2.45), significantly exceeding Shaoyin Collapse (17.8%, HR 1.37).

---

## 📊 Key Results
| Syndrome | N (%) | Mortality | Adjusted HR (95% CI) |
| :--- | :--- | :--- | :--- |
| **Heat Collapse (Re Jue)** | 6,374 (7.5%) | 32.5% | **2.30 (2.16-2.45)** |
| **Shaoyin Collapse** | 20,244 (23.8%) | 17.8% | 1.37 (1.29-1.44) |
| Taiyin Deficiency | 10,745 (12.6%) | 5.7% | 0.65 (0.59-0.71) |
| Qi-Xue Stasis | 14,950 (17.5%) | 7.1% | 0.66 (0.61-0.71) |
| Unclassified (Ref) | 32,911 (38.6%) | 6.4% | 1.00 |

![Kaplan-Meier Survival Curves](docs/figure1_km_curves.png)
![Forest Plot of Hazard Ratios](docs/figure2_forest_plot.png)

---

## 🚀 Quick Start
### Prerequisites
1. Python 3.8+
2. MIMIC-III v1.4 access (PhysioNet credentialed)
3. Place MIMIC core CSVs in `data/mimic_core/` (or set `TCM_SHARD_DATA` env var)

### Installation

```bash
git clone https://github.com/your-username/TCM-SHARD.git
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

## 📁 Repository Structure

```
TCM-SHARD/
├── src/                    # Core source code
│   ├── config.py           # Path configuration
│   ├── tcm_pca_engine.py   # PCA training + bootstrap validation
│   ├── mimic_crude_mapper.py # Lightweight mapper
│   ├── mimic_crude_mapper_full.py # Full MIMIC mapper (ICD-9/10)
│   ├── bridge_mimic_to_pca.py # Anchor proxy connector
│   └── analysis/           # Analysis modules
│       └── survival_analysis.py # Cox regression + KM curves
├── data/                   # Gold-standard data (no PHI)
│   ├── tcm_syndrome_matrix.csv
│   ├── tcm_syndrome_matrix.json
│   └── validation/         # Manual verification datasets
├── models/                 # Pretrained PCA model
├── docs/                   # Results + manuscript drafts
│   ├── figure1_km_curves.png
│   ├── figure2_forest_plot.png
│   └── paper_manuscript.md
└── requirements.txt
```

---

## 📜 Citation
If you use TCM-SHARD in your research, please cite:

```bibtex
@article{yourname2024tcmshard,
  title={Unmasking Heat Collapse: A Rule-Based TCM Syndrome Differentiation Framework for Critical Care Using the MIMIC-III Database},
  author={Your Name},
  journal={Critical Care Medicine},
  year={2024},
  note={Code available at https://github.com/your-username/TCM-SHARD}
}
```

---

## 📧 Contact
Your Name - your.email@example.com
Project Link: [https://github.com/your-username/TCM-SHARD](https://github.com/your-username/TCM-SHARD)
