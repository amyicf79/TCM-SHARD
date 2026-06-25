# Replication Guide: TCM-SHARD Module-00

> **Target audience**: Researchers with MIMIC-III access who want to reproduce the survival analysis results from "Unmasking Heat Collapse" (aHR 2.30 for Re Jue).
> **Time to complete**: ~2 hours (including MIMIC-III data extraction).
> **Prerequisites**: Python 3.10+, MIMIC-III credentialled access, 8GB RAM.

---

## 0. What This Guide Covers

This guide walks you through reproducing **every figure and table in the TCM-SHARD manuscript** using only open-source code. It does **not** require access to IXNO-Field (M01) or IXNO-Frame (M02) — those are closed-core engines. TCM-SHARD ships with the **pre-built classification model** (`tcm_pca_model.pkl`) and all necessary data processing scripts.

By the end of this guide, you will have reproduced:

| Output | File | Description |
|--------|------|-------------|
| Figure 1 | `docs/figure1_km_curves.png` | Kaplan-Meier curves for 5 TCM syndromes |
| Figure 2 | `docs/figure2_forest_plot.png` | Forest plot of adjusted hazard ratios |
| Table 2 | `docs/table2_cox_results.csv` | Cox regression results (aHR, 95% CI, p-values) |
| Sensitivity | `docs/validation/sensitivity_analysis_report.md` | Robustness across 4 exclusion models |

---

## 1. Obtain MIMIC-III Access

TCM-SHARD uses MIMIC-III v1.4. You need a PhysioNet credentialled account.

### Steps:
1. Go to [https://physionet.org/content/mimiciii/1.4/](https://physionet.org/content/mimiciii/1.4/)
2. Complete the "CITI Data or Specimens Only Research" course (takes ~3 hours, one-time)
3. Submit a data use agreement via PhysioNet
4. After approval (~2–3 business days), download the CSV files:

```
mimic-iii-clinical-database-1.4/
├── ADMISSIONS.csv.gz
├── PATIENTS.csv.gz
├── ICUSTAYS.csv.gz
├── DIAGNOSES_ICD.csv.gz
├── CHARTEVENTS.csv.gz       (large — 30GB+ uncompressed)
├── LABEVENTS.csv.gz          (large — 4GB+ uncompressed)
├── D_ICD_DIAGNOSES.csv.gz
└── D_LABITEMS.csv.gz
```

> ⚠️ **Do not commit MIMIC-III data to this repository.** The `.gitignore` already excludes `mimic_data/`.

---

## 2. Set Up the Environment

### 2.1 Clone the repository
```bash
git clone https://github.com/amyicf79/TCM-SHARD.git
cd TCM-SHARD
```

### 2.2 Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2.3 Install dependencies
```bash
pip install -r requirements.txt
```

Key dependencies: `pandas`, `numpy`, `lifelines`, `scikit-learn`, `matplotlib`, `seaborn`.

### 2.4 Place MIMIC-III data
Create a `mimic_data/` directory at the repo root and place **only the required CSV files** (see Section 1). The pipeline expects the following structure:

```
TCM-SHARD/
├── mimic_data/
│   ├── ADMISSIONS.csv.gz
│   ├── PATIENTS.csv.gz
│   ├── ICUSTAYS.csv.gz
│   ├── DIAGNOSES_ICD.csv.gz
│   ├── CHARTEVENTS.csv.gz
│   ├── LABEVENTS.csv.gz
│   ├── D_ICD_DIAGNOSES.csv.gz
│   └── D_LABITEMS.csv.gz
```

> You may keep files gzipped — the pipeline uses `pandas.read_csv(compression='gzip')`.

---

## 3. Run the Pipeline

The pipeline has four stages. Run them sequentially.

### Stage 1: Cohort Extraction
```bash
python src/build_cohort.py
```
**What it does**: Extracts 85,242 ICU stays from MIMIC-III, applies inclusion/exclusion criteria, and generates `data/cohort.csv`.

**Expected output**:
```
[build_cohort] Extracted 85,242 ICU stays
[build_cohort] Excluded 12,847 (age < 18)
[build_cohort] Excluded 3,102 (ICU stay < 24h)
[build_cohort] Final cohort: 69,293 stays → data/cohort.csv
```

**Time**: ~15 minutes (mostly I/O for CHARTEVENTS).

### Stage 2: Feature Engineering
```bash
python src/extract_features.py
```
**What it does**: Extracts 13 PCA anchor features (vital signs, labs, demographics) from the cohort and generates `data/features.csv`.

**Expected output**:
```
[extract_features] Processing 69,293 stays...
[extract_features] Feature matrix: 69,293 rows × 13 columns
[extract_features] Saved data/features.csv
```

**Time**: ~20 minutes.

### Stage 3: Syndrome Classification
```bash
python src/classify_syndromes.py
```
**What it does**: Loads the pre-trained PCA model (`models/tcm_pca_model.pkl`) and assigns each ICU stay to one of 5 TCM syndromes (Heat Collapse, Shaoyin Collapse, Taiyin Deficiency, Qi-Xue Stasis, Unclassified). Outputs `data/syndrome_labels.csv`.

> **Note**: The model weights are fixed — this script does not train. It only applies the pre-calibrated PCA transformation. If you need to train your own model, see Section 5 ("Advanced: Training From Scratch").

**Expected output**:
```
[classify_syndromes] Loaded tcm_pca_model.pkl (13 PCA components)
[classify_syndromes] Classified 69,293 stays:
    Heat Collapse (Re Jue):   8,421 (12.2%)
    Shaoyin Collapse:         6,103 (8.8%)
    Taiyin Deficiency:       11,247 (16.2%)
    Qi-Xue Stasis:            9,882 (14.3%)
    Unclassified:            33,640 (48.5%)
[classify_syndromes] Saved data/syndrome_labels.csv
```

**Time**: ~2 minutes.

### Stage 4: Survival Analysis
```bash
python src/run_survival_analysis.py
```
**What it does**: Runs Cox proportional hazards models, generates KM curves and forest plot, exports Table 2 CSV.

**Expected output**:
```
[survival] Cox model: Heat Collapse aHR=2.30 (2.16–2.45), p<0.001
[survival] Cox model: Shaoyin Collapse aHR=1.38 (1.28–1.49), p<0.001
[survival] Cox model: Taiyin Deficiency aHR=0.72 (0.67–0.78), p<0.001
[survival] Cox model: Qi-Xue Stasis aHR=0.61 (0.56–0.67), p<0.001
[survival] Saved docs/figure1_km_curves.png
[survival] Saved docs/figure2_forest_plot.png
[survival] Saved docs/table2_cox_results.csv
```

**Time**: ~3 minutes.

---

## 4. Verify Reproduction

### 4.1 Quick sanity check
```bash
python src/verify_reproduction.py
```
This script compares your output against the expected checksums:
```
[verify] figure1_km_curves.png   — SHA256 match ✅
[verify] figure2_forest_plot.png — SHA256 match ✅
[verify] table2_cox_results.csv  — CSV diff: 0 differences ✅
[verify] Heat Collapse aHR: 2.30 — MATCH ✅
```

### 4.2 Run sensitivity analyses
```bash
python src/run_sensitivity_analysis.py
```
Reproduces the 4 sensitivity models described in `docs/validation/sensitivity_analysis_report.md`.

---

## 5. Advanced: Training From Scratch

If you want to train the PCA model from raw MIMIC-III data (rather than using the pre-built `tcm_pca_model.pkl`):

```bash
python src/train_pca.py --bootstrap 1000
```

**⚠️ This will overwrite `models/tcm_pca_model.pkl`.** 

**Note on reproducibility**: The published model was calibrated against a larger proprietary dataset (85k MIMIC-III + internal validation). Training from MIMIC-III alone may produce slightly different PCA loadings. The `.pkl` shipped with this repo is the reference model — use `train_pca.py` only for methodological exploration.

---

## 6. Expected Differences from Published Results

Minor discrepancies may arise from:

| Source | Expected Δ | Reason |
|--------|-----------|--------|
| MIMIC-III version | ±0.02 aHR | v1.4 vs older versions may have minor data corrections |
| lifelines version | ±0.01 aHR | Numerical differences in optimization |
| OS/platform | ±0.01 aHR | Floating-point precision (x86 vs ARM) |

aHR values within ±0.05 of the published 2.30 are considered a successful reproduction.

---

## 7. Troubleshooting

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| `FileNotFoundError: mimic_data/CHARTEVENTS.csv.gz` | MIMIC-III data not placed correctly | Verify `mimic_data/` has all 8 files from Section 1 |
| `MemoryError` during `build_cohort.py` | CHARTEVENTS too large for RAM | Use `--chunksize 50000` flag, or run on a machine with 16GB+ |
| `ModuleNotFoundError: lifelines` | Missing dependency | `pip install lifelines` |
| PCA classification differs from paper | Model file mismatch | Ensure you are using the shipped `tcm_pca_model.pkl`, not a retrained one |
| KM curves look different | matplotlib version | Install exact version: `pip install matplotlib==3.7.1` |

---

## 8. Citation

If you use TCM-SHARD in your research, please cite:

```
@article{tcm-shard-2026,
  title   = {Unmasking Heat Collapse: A Rule-Based TCM Syndrome Differentiation Framework
             for Critical Care Using the MIMIC-III Database},
  author  = {IXNO-TCM Consortium},
  journal = {Preprint},
  year    = {2026},
  note    = {Module-00 of the IXNO Modular Architecture. aHR 2.30 for Heat Collapse (Re Jue).}
}
```

---

*This replication guide covers TCM-SHARD Module-00 only. For commercial licensing of IXNO-Field (M01) and IXNO-Frame (M02), refer to `docs/IXNO_MODULE_WHITEPAPER.md`.*
