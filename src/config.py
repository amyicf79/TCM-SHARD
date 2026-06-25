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

# ==================== v0.2.0 Pending Anchors (Calibrated) ====================
# Vector structure (12-dim): tongue[0-3] + pulse[0-3] + symptom[0-1] + course_days + x4_mid
# tongue: [苔色质, 苔厚腻, 舌形, 络脉]  — higher=darker/thicker/swollen/darker
# pulse:  [浮沉, 数迟, 虚实, 有力无力]  — higher=floating/rapid/excess/forceful
# symptom: [主症严重度, 兼症广度]       — higher=more severe / more multi-system
# course_days: 归一化病程 [0-1]
# x4_mid: (x4_lo + x4_hi)/2 正气锚点均值

# Xiao Ke (消渴, Diabetes Spectrum): E11* ICD mapping
# Clinical: 阴虚燥热为本，多饮多食多尿消瘦，久病入络
# Tongue: 舌红少苔，舌体偏瘦，久病可见舌下络脉迂曲
# Pulse: 脉细数（阴虚内热之象）
# Symptom: 主症显著（三多一少），兼症广度中等（周围神经/视网膜/肾并发症）
# Course: 慢性迁延（年计），x4: 中度亏虚（与血瘀证同级）
XIAOKE_VECTOR = [
    0.75,  # tongue_0: 舌红
    0.15,  # tongue_1: 少苔（薄苔）
    0.35,  # tongue_2: 舌体偏瘦
    0.50,  # tongue_3: 久病入络→舌下络脉轻度迂曲
    0.30,  # pulse_0: 不浮（里证）
    0.70,  # pulse_1: 数（阴虚内热→心率偏快）
    0.35,  # pulse_2: 细（阴虚血少→脉道不充）
    0.45,  # pulse_3: 尚有力（非虚极）
    0.65,  # symptom_0: 主症显著（三多一少严重影响生活）
    0.55,  # symptom_1: 兼症广度中等（并发症涉及多系统）
    0.50,  # course_days: 慢性病程（年计，0.5=约3-5年）
    0.45,  # x4_mid: 中度亏虚（与血瘀证同级，0.45）
]
XIAOKE_CODE = "xk_xy_zr"

# Ni Du (溺毒, Renal Failure Spectrum): N17*/N18* ICD mapping
# Clinical: 脾肾阳虚为本，浊毒内蕴为标，水肿少尿，恶心呕吐
# Tongue: 舌淡胖有齿痕，苔白腻或灰黑
# Pulse: 脉沉细无力（脾肾阳虚，鼓动无力）
# Symptom: 主症极重（尿毒症多系统衰竭），兼症广泛
# Course: 终末期慢性（年计），x4: 极低（与少阴寒化同级）
NIDU_VECTOR = [
    0.15,  # tongue_0: 舌淡（气血不足）
    0.65,  # tongue_1: 苔厚腻（浊毒上泛）
    0.80,  # tongue_2: 舌体胖大+齿痕（水湿内停+脾虚）
    0.25,  # tongue_3: 络脉色淡（血虚不荣）
    0.15,  # pulse_0: 沉（里证，阳气虚衰）
    0.25,  # pulse_1: 迟/正常（代谢低下→心率偏慢）
    0.20,  # pulse_2: 虚（脾肾阳虚→鼓动无力）
    0.15,  # pulse_3: 极无力（与少阴寒化四逆汤证同级）
    0.85,  # symptom_0: 主症极重（水肿+少尿+恶心+乏力四联征）
    0.65,  # symptom_1: 兼症广泛（贫血/骨病/心血管/神经多系统受累）
    0.70,  # course_days: 终末期病程（0.7≈5-10年慢性肾衰竭进展）
    0.20,  # x4_mid: 极低正气（与少阴寒化0.10、慢阻肺心衰0.20同级）
]
NIDU_CODE = "nd_zd_ny"

# Future validation dataset path (external ICU data)
EXTERNAL_VALIDATION_DIR = DATA_DIR / "external_validation"  # To be populated with domestic ICU data
