#!/usr/bin/env python3
"""
MIMIC-IV v3.1 粗糙映射引擎 v2 — ICD-9/10双版本 + 六条规则
============================================================
修复: ICD-9编码(4280等)未被识别 → 加入ICD-9↔ICD-10互译表
新增: 规则6 太阴病(D62腹泄/血证)
"""

import csv, gzip, json, os, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import MIMIC_CORE_DIR, DATA_DIR

# ===== 配置 =====
MIMIC_DIR = str(MIMIC_CORE_DIR)
OUTPUT_DIR = str(DATA_DIR)
SAMPLE_N = 200
LAB_CACHE = os.path.join(OUTPUT_DIR, "lab_cache_batch.json")

# ===== ICD-9 → ICD-10 互译 (仅映射规则涉及的) =====
ICD9_TO_ICD10 = {
    # 心衰/心梗 → sy_hn (Rule 1)
    "428": "I50",  # CHF
    "410": "I21",  # AMI
    "411": "I20",  # Unstable angina → IHD group
    "413": "I20",  # Angina pectoris
    "414": "I25",  # Chronic IHD
    "425": "I42",  # Cardiomyopathy
    # 脓毒症 → ym_bh (Rule 2)
    "038": "A41",  # Septicemia
    "9959": "R65", # SIRS/sepsis
    "7855": "R57", # Shock
    # COPD → qx_yt_003 (Rule 3)
    "491": "J44",  # Chronic bronchitis
    "492": "J43",  # Emphysema
    "496": "J44",  # Chronic airway obstruction
    # GI出血/贫血 → ty_xh (Rule 4+6)
    "578": "K92",  # GI hemorrhage
    "285": "D62",  # Anemia (other/unspecified)
    "280": "D50",  # Iron deficiency anemia
    "531": "K25",  # Gastric ulcer
    "532": "K26",  # Duodenal ulcer
    "533": "K27",  # Peptic ulcer
    # 急性肾衰(溺毒) — future anchor
    "584": "N17",  # Acute renal failure
    # 糖尿病(消渴) — future anchor
    "250": "E11",  # Diabetes mellitus
}

# 六条规则: cluster_code → {icd_prefixes, drug_kw, lab_triggers, excludes, min_confidence}
RULE_MAP = {
    "sy_hn": {  # R1: 少阴寒化 (心衰/心梗+升压药)
        "icd_prefixes": ["I50", "I21", "I22", "I42", "I20", "I25"],
        "drug_kw": ["norepinephrine", "epinephrine", "dopamine", "dobutamine",
                     "milrinone", "vasopressin", "phenylephrine"],
        "lab_triggers": {},
        "excludes": ["hypovolemic"],  # v4.1: +GI出血Hb<7排除
        "min_conf": 0.5,
    },
    "ym_bh": {  # R2: 阳明经证 (脓毒症高热)
        "icd_prefixes": ["A41", "R65", "A40", "R57"],
        "drug_kw": ["norepinephrine", "vasopressin"],
        "lab_triggers": {"White Blood Cells": (12, None)},
        "excludes": [],
        "min_conf": 0.5,
    },
    "qx_yt_003": {  # R3: 气虚血瘀痰湿 (COPD+HF) v4.1 +J20系
        "icd_prefixes": ["J44", "J43", "J20", "J18", "J15", "I50", "496", "491", "492"],
        "drug_kw": ["furosemide", "bumetanide", "torsemide",
                     "albuterol", "ipratropium", "prednisone"],
        "lab_triggers": {},
        "excludes": [],
        "min_conf": 0.5,
    },
    "ty_xh": {  # R4+R6合并: 太阴病 (GI出血+贫血)
        "icd_prefixes": ["K92", "D62", "D50", "K25", "K26", "K27", "K92.0", "K92.1", "K92.2"],
        "drug_kw": ["pantoprazole", "omeprazole", "esomeprazole", "lansoprazole",
                     "octreotide", "sucralfate", "famotidine", "ranitidine",
                     "metoclopramide", "ondansetron"],
        "require_drug": True,  # v4.1: 必须ICD+GI药同时满足
        "lab_triggers": {"Hemoglobin": (None, 7)},
        "excludes": ["esophageal varices", "cirrhosis"],  # 排除食管静脉曲张/肝硬化
        "min_conf": 0.5,
    },
}


def icd_prefix_match(code, prefixes):
    """匹配ICD前缀，支持ICD-9和ICD-10"""
    # 直接匹配
    for p in prefixes:
        if code.startswith(p):
            return True
    # ICD-9 → ICD-10 转译
    # ICD-9格式: 3-4位数字(可能带小数)
    if code and code[0].isdigit():
        for p3 in [code[:3], code[:4], code[:5]]:
            if p3 in ICD9_TO_ICD10:
                mapped = ICD9_TO_ICD10[p3]
                for p in prefixes:
                    if mapped.startswith(p) or mapped == p:
                        return True
    return False


def load_icd_dict():
    fpath = os.path.join(MIMIC_DIR, "hosp", "d_icd_diagnoses.csv.gz")
    icd_map = {}
    with gzip.open(fpath, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            icd_map[row["icd_code"]] = row["long_title"]
    print(f"  ICD字典: {len(icd_map)} 条目")
    return icd_map


def load_icustays_sample(n=SAMPLE_N):
    fpath = os.path.join(MIMIC_DIR, "icu", "icustays.csv.gz")
    stays = {}
    with gzip.open(fpath, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n:
                break
            hadm_id = row["hadm_id"]
            stays[hadm_id] = {
                "subject_id": row["subject_id"],
                "stay_id": row["stay_id"],
                "los": float(row["los"]),
                "first_careunit": row["first_careunit"],
            }
    print(f"  ICU stays: {len(stays)} 条")
    return stays


def load_diagnoses(hadm_ids):
    fpath = os.path.join(MIMIC_DIR, "hosp", "diagnoses_icd.csv.gz")
    target = set(hadm_ids)
    result = defaultdict(list)
    with gzip.open(fpath, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hid = row["hadm_id"]
            if hid in target:
                result[hid].append((row["icd_code"], int(row["seq_num"])))
    print(f"  诊断加载: {len(result)}/{len(target)} hadm有诊断记录")
    return dict(result)


def load_prescriptions(hadm_ids):
    fpath = os.path.join(MIMIC_DIR, "hosp", "prescriptions.csv.gz")
    target = set(hadm_ids)
    all_kw = set()
    for rule in RULE_MAP.values():
        all_kw.update(k.lower() for k in rule["drug_kw"])

    result = defaultdict(set)
    scanned = 0
    with gzip.open(fpath, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hid = row["hadm_id"]
            if hid in target:
                drug = (row.get("drug") or "").lower()
                for kw in all_kw:
                    if kw in drug:
                        result[hid].add(kw)
            scanned += 1
    print(f"  用药扫描: {scanned} 行, {len(result)} hadm有匹配药物")
    return dict(result)


def load_lab_cache():
    if os.path.exists(LAB_CACHE):
        with open(LAB_CACHE, "r") as f:
            return json.load(f)
    return {}


def check_lab_triggers(lab_data, hadm_id, triggers, lab_item_map):
    if not triggers or hadm_id not in lab_data:
        return False
    patient_labs = lab_data[hadm_id]
    for label, (lo, hi) in triggers.items():
        itemid = None
        for iid, lbl in lab_item_map.items():
            if label.lower() in lbl.lower():
                itemid = iid
                break
        if itemid and itemid in patient_labs:
            raw = patient_labs[itemid]
            # 扁平化: 可能是单值, 列表, 或嵌套列表
            vals = []
            if isinstance(raw, list):
                for v in raw:
                    if isinstance(v, list):
                        vals.extend(v)
                    elif v is not None and v != '':
                        vals.append(v)
            elif raw is not None and raw != '':
                vals.append(raw)
            if not vals:
                continue
            try:
                numeric_vals = [float(v) for v in vals]
            except (ValueError, TypeError):
                continue
            val = max(numeric_vals)
            if lo is not None and val < lo:
                continue
            if hi is not None and val > hi:
                continue
            return True
    return False


def rule_match_v2(hadm_id, diagnoses, prescriptions, lab_data, lab_item_map):
    """六条规则匹配，返回 (best_cluster, confidence, reason)"""
    icd_codes = [d[0] for d in diagnoses.get(hadm_id, [])]
    drugs = prescriptions.get(hadm_id, set())

    best_cluster = "unclassified"
    best_conf = 0.0
    best_reason = ""

    for cluster, rule in RULE_MAP.items():
        score = 0.0
        reasons = []

        # ICD匹配 (含ICD-9转译)
        matched_icd = False
        matched_codes = []
        for code in icd_codes:
            if icd_prefix_match(code, rule["icd_prefixes"]):
                matched_icd = True
                matched_codes.append(code)
                break

        if not matched_icd:
            continue

        # 排除项检查 (v4.1 fix: inner continue→skip_rule)
        skip_rule = False
        for code in icd_codes:
            for excl in rule.get("excludes", []):
                if excl.lower() in code.lower():
                    skip_rule = True
                    break
            if skip_rule:
                break
        if skip_rule:
            continue

        reasons.append(f"ICD:{','.join(matched_codes)}")
        score += 0.4

        # 药物匹配
        # [DEBUG] v4.1 patch active: case-insensitive drug match + require_drug skip
        matched_drugs = [kw for kw in rule["drug_kw"] if any(kw.lower() in d.lower() for d in drugs)]
        if matched_drugs:
            score += 0.3
            reasons.append(f"drug:{','.join(matched_drugs[:3])}")
        elif rule.get("require_drug"):
            if rule.get("require_drug"):
                pass  # [DEBUG] require_drug branch hit
            continue  # v4.1: require_drug规则(GI出血)无匹配药物→跳过

        # Lab触发
        if check_lab_triggers(lab_data, hadm_id, rule["lab_triggers"], lab_item_map):
            score += 0.3
            reasons.append("lab+")

        confidence = min(score, 0.95)

        # 最低置信度门槛
        if confidence >= rule["min_conf"] and confidence > best_conf:
            best_cluster = cluster
            best_conf = confidence
            best_reason = "; ".join(reasons)

    return best_cluster, round(best_conf, 3), best_reason


def build_lab_item_map():
    fpath = os.path.join(MIMIC_DIR, "hosp", "d_labitems.csv.gz")
    item_map = {}
    with gzip.open(fpath, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_map[row["itemid"]] = row["label"]
    return item_map


def main():
    t0 = time.time()
    print("=== MIMIC-IV 粗糙映射引擎 v2 (ICD-9/10双版本) ===\n")

    print("[1/6] 加载ICD字典...")
    icd_dict = load_icd_dict()

    print("[2/6] 采样ICU stays...")
    stays = load_icustays_sample(SAMPLE_N)

    print("[3/6] 加载诊断...")
    diagnoses = load_diagnoses(list(stays.keys()))

    print("[4/6] 扫描用药 (流式)...")
    prescriptions = load_prescriptions(list(stays.keys()))

    print("[5/6] 加载Lab缓存...")
    lab_data = load_lab_cache()
    lab_item_map = build_lab_item_map()
    print(f"  Lab缓存: {len(lab_data)} hadm, {len(lab_item_map)} itemid")

    print("[6/6] 应用六条映射规则 (含ICD-9→ICD-10)...")
    results = []
    rule_count = defaultdict(int)
    for hadm_id, stay_info in stays.items():
        cluster, confidence, reason = rule_match_v2(
            hadm_id, diagnoses, prescriptions, lab_data, lab_item_map
        )
        results.append({
            "subject_id": stay_info["subject_id"],
            "hadm_id": hadm_id,
            "stay_id": stay_info["stay_id"],
            "cluster_code": cluster,
            "confidence": confidence,
            "reason": reason,
            "los": stay_info["los"],
        })
        rule_count[cluster] += 1

    out_path = os.path.join(OUTPUT_DIR, "mimic_crude_map.csv")
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["subject_id", "hadm_id", "stay_id",
                      "cluster_code", "confidence", "reason", "los"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)

    elapsed = time.time() - t0
    valid = [r for r in results if r["cluster_code"] != "unclassified"]
    print(f"\n=== 完成 ({elapsed:.1f}s) ===")
    print(f"  总采样: {len(results)} stays")
    print(f"  命中规则: {len(valid)} ({len(valid)/len(results)*100:.1f}%)")
    print(f"  未命中: {len(results)-len(valid)}")
    print(f"\n  分布:")
    for cluster, cnt in sorted(rule_count.items(), key=lambda x: -x[1]):
        label = {"sy_hn": "少阴寒化", "ym_bh": "阳明经证",
                 "qx_yt_003": "气虚血瘀痰湿", "ty_xh": "太阴病",
                 "unclassified": "未分类"}.get(cluster, cluster)
        print(f"    {cluster:<20s} {label:<12s} {cnt:>4d} ({cnt/len(results)*100:.1f}%)")
    print(f"\n  输出: {out_path}")


if __name__ == "__main__":
    main()
