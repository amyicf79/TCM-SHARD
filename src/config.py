"""
TCM-SHARD Configuration
Centralizes paths to eliminate hardcoding.
Users can override DATA_DIR via environment variable:
  Windows: set TCM_SHARD_DATA=J:\\your\\mimic\\csv
  Linux/Mac: export TCM_SHARD_DATA=/your/mimic/csv
"""
import os
from pathlib import Path

# Project root: assumes this file is in TCM-SHARD/src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --------------------------
# User-configurable paths
# --------------------------
# Primary data directory (gold standards + user-generated maps)
DATA_DIR = Path(os.environ.get(
    "TCM_SHARD_DATA",
    PROJECT_ROOT / "data"  # Default: project's data folder
))

# MIMIC-III core tables (users must place their MIMIC csvs here)
MIMIC_CORE_DIR = DATA_DIR / "mimic_core"  # Contains admissions.csv, patients.csv, diagnoses_icd.csv
MIMIC_ICU_DIR = DATA_DIR / "mimic_icu"    # Contains icustays.csv

# --------------------------
# Fixed internal paths (do not change)
# --------------------------
# Gold-standard syndrome matrices
SYNDROME_MATRIX_CSV = DATA_DIR / "tcm_syndrome_matrix.csv"
SYNDROME_MATRIX_JSON = DATA_DIR / "tcm_syndrome_matrix.json"

# Pretrained PCA model
PCA_MODEL_PKL = PROJECT_ROOT / "models" / "tcm_pca_model.pkl"

# Validation datasets
VERIFICATION_30_FINAL = DATA_DIR / "validation" / "verification_30_final.csv"
VERIFICATION_30_ENRICHED = DATA_DIR / "validation" / "verification_30_enriched.csv"
VERIFICATION_30_SAMPLES = DATA_DIR / "validation" / "verification_30_samples.csv"

# Analysis output directory (matches existing docs structure)
ANALYSIS_OUTPUT_DIR = PROJECT_ROOT / "docs"
ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------
# Constants
# --------------------------
BOOTSTRAP_ITERS = 1000
RANDOM_SEED = 42
DEFAULT_SAMPLE_SIZE = 1000

# ==================== v0.2.0 Pending Anchors (Placeholder) ====================
# Xiao Ke (消渴, Diabetes Spectrum): E11* ICD mapping
# Clinical rationale: High prevalence (13.6%) in unclassified MIMIC stays
# Vector dimension: 12 (consistent with tcm_syndrome_matrix.csv)
XIAOKE_VECTOR = [0.0] * 12  # Placeholder for v0.2.0 calibration
XIAOKE_CODE = "xk_xy_zr"

# Ni Du (溺毒, Renal Failure Spectrum): N17*/N18* ICD mapping
# Clinical rationale: High prevalence (13.7%) in unclassified MIMIC stays
# Vector dimension: 12 (consistent with tcm_syndrome_matrix.csv)
NIDU_VECTOR = [0.0] * 12    # Placeholder for v0.2.0 calibration
NIDU_CODE = "nd_zd_ny"

# Future validation dataset path (external ICU data)
EXTERNAL_VALIDATION_DIR = DATA_DIR / "external_validation"  # To be populated with domestic ICU data
