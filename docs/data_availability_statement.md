# Data Availability Statement

> Embed this section directly in your manuscript under "Data Availability" or
> "Data Sharing Statement" — formats match *Critical Care Medicine* requirements.

---

## Option A: CCM Standard Format (Recommended)

```
Data Availability

The code and documentation for TCM-SHARD are openly available on GitHub at
https://github.com/amyicf79/TCM-SHARD (archived with Zenodo, DOI:
10.5281/zenodo.XXXXXXX). The MIMIC-III database used in this study is available
through PhysioNet (https://physionet.org/content/mimiciii/1.4/) under a data use
agreement. To access MIMIC-III, researchers must complete the CITI "Data or
Specimens Only Research" course and sign the PhysioNet data use agreement. The
gold-standard syndrome matrix (tcm_syndrome_matrix.csv) and de-identified
validation datasets (verification_30_enriched.csv) are included in the
repository. All intermediate data files containing protected health information
are excluded from the repository per PhysioNet guidelines. The pretrained PCA
model (tcm_pca_model.pkl, 4.1 KB) is included and fully reproducible using
src/tcm_pca_engine.py.
```

---

## Option B: Expanded (For Journals Requiring Detailed Data Descriptions)

```
Data Sharing Statement

1. Source Data
   The primary data source is the MIMIC-III Critical Care Database v1.4
   (Johnson et al., 2016), available from PhysioNet at
   https://physionet.org/content/mimiciii/1.4/ under a credentialed data use
   agreement. Researchers must complete CITI training and sign the PhysioNet
   DUA. The database contains de-identified health data associated with 53,423
   distinct hospital admissions for adult patients admitted to the intensive
   care units of Beth Israel Deaconess Medical Center between 2001 and 2012.

2. Code Availability
   All analysis code is publicly available on GitHub at
   https://github.com/amyicf79/TCM-SHARD under the MIT License, with a
   permanent archived version on Zenodo (DOI: 10.5281/zenodo.XXXXXXX). The
   repository includes:
   - Syndrome mapping engine (src/mimic_crude_mapper_full.py)
   - PCA model training and projection (src/tcm_pca_engine.py,
     src/bridge_mimic_to_pca.py)
   - Survival analysis pipeline (src/analysis/survival_analysis.py)
   - Centralized configuration (src/config.py) for cross-institutional
     reproducibility

3. Gold-Standard Data
   The 13-syndrome gold-standard matrix (data/tcm_syndrome_matrix.csv) and
   accompanying metadata (data/tcm_syndrome_matrix.json) are included in the
   repository. These files contain no patient data and are freely reusable.

4. Validation Data
   The 30-case manual verification dataset (data/validation/
   verification_30_enriched.csv) is fully de-identified and included in the
   repository. It contains only hadm_id, syndrome labels, and clinical reasoning
   — no patient identifiers.

5. Intermediate Files
   All intermediate output files containing potentially identifiable MIMIC-III
   derived data are excluded via .gitignore and are not distributed. Users must
   regenerate these files from their own credentialed MIMIC-III access.

6. Reproducibility
   Complete reproduction requires: (a) credentialed MIMIC-III v1.4 access,
   (b) Python 3.8+ with dependencies listed in requirements.txt, (c) MIMIC core
   CSVs placed in the directory specified by src/config.py. The entire pipeline
   from raw MIMIC tables to publication figures is scripted and executable via:
     python src/mimic_crude_mapper_full.py
     python src/analysis/survival_analysis.py
```

---

## Citation (for data availability section reference)

```
Johnson AEW, Pollard TJ, Shen L, et al. MIMIC-III, a freely accessible critical
care database. Sci Data. 2016;3:160035. doi:10.1038/sdata.2016.35
```
