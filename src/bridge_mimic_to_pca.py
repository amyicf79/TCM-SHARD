#!/usr/bin/env python3
"""
MIMIC桥接层脚本（路线A：锚点代理模式 + 路线B接口预留）
========================================================
1. 读取crude_map_mimic输出的(subject_id, cluster_code, confidence)
2. 根据cluster_code匹配金标证型的10维特征向量作为代理
3. 用预训练PCA transform代理向量，计算到对应锚点的欧氏距离
4. 输出全链路结果，标注代理来源，兼容后续B路线扩展
"""

import csv
import json
import pickle
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SYNDROME_MATRIX_CSV, PCA_MODEL_PKL, DATA_DIR

# ==================== 配置区 ====================
PCA_MODEL_PATH = PCA_MODEL_PKL
SYNDROME_MATRIX_PATH = SYNDROME_MATRIX_CSV
CRUDE_MAP_INPUT = DATA_DIR / "mimic_crude_map.csv"
OUTPUT_PATH = DATA_DIR / "mimic_pca_extrapolate.csv"

MIN_CONFIDENCE = 0.5
DISTANCE_THRESHOLDS = {"high": 0.3, "medium": 0.5}


def load_model():
    """加载预训练PCA模型（pickle格式，非joblib）"""
    with open(PCA_MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    return model_data


def load_gold_matrix():
    """加载13金标证型矩阵，构建cluster_code→特征/坐标/名称的映射"""
    codes, names, features_raw = [], [], []
    course_days_list = []
    feat_cols = [f"tongue_{i}" for i in range(4)] + \
                [f"pulse_{i}" for i in range(4)] + \
                [f"symptom_{i}" for i in range(2)]  # 10维参与PCA
    with open(SYNDROME_MATRIX_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes.append(row["code"])
            names.append(row["name"])
            feat = [float(row[c]) for c in feat_cols]
            features_raw.append(feat)
            course_days_list.append(float(row.get("course_days", 0)))
    return codes, names, np.array(features_raw), course_days_list


def process_mimic_crude_map():
    """路线A：锚点代理模式"""
    model_data = load_model()
    codes, names, gold_features, course_days_list = load_gold_matrix()

    pca = model_data["pca"]
    scaler = model_data["scaler"]

    # 构建索引
    feat_map = {c: gold_features[i] for i, c in enumerate(codes)}
    name_map = {c: names[i] for i, c in enumerate(codes)}
    course_map = {c: course_days_list[i] for i, c in enumerate(codes)}

    # 锚点PC坐标（从PCA模型直接拿，保证一致性）
    anchor_coords = model_data["coords"]

    # 读取MIMIC粗糙映射结果
    if not CRUDE_MAP_INPUT.exists():
        print(f"[WARN] {CRUDE_MAP_INPUT} 不存在，自动生成100条模拟数据")
        np.random.seed(42)
        # 模拟13个证型×约8条 = ~100条
        rows = []
        for c in codes:
            n = np.random.randint(6, 10)
            for _ in range(n):
                sid = f"MIMIC_{np.random.randint(10000000, 99999999)}"
                rows.append({
                    "subject_id": sid,
                    "cluster_code": c,
                    "confidence": round(np.random.uniform(0.5, 0.95), 3)
                })
        with open(CRUDE_MAP_INPUT, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["subject_id", "cluster_code", "confidence"])
            w.writeheader()
            w.writerows(rows)
        print(f"[OK] 生成 {len(rows)} 条模拟数据 -> {CRUDE_MAP_INPUT}")
    else:
        rows = []
        with open(CRUDE_MAP_INPUT, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append(r)

    # 过滤低置信度
    filtered = [r for r in rows if float(r["confidence"]) >= MIN_CONFIDENCE
                and r.get("cluster_code", "") != "unclassified"]
    if not filtered:
        print("[ERROR] 无符合置信度要求的样本")
        return

    results = []
    for row in filtered:
        subject_id = row["subject_id"]
        cluster_code = row["cluster_code"]
        confidence = float(row["confidence"])

        if cluster_code not in feat_map:
            print(f"[SKIP] cluster_code={cluster_code} 无对应锚点, subject={subject_id}")
            continue

        # 锚点代理：金标10维特征 = MIMIC样本的代理特征
        proxy_feat = feat_map[cluster_code].reshape(1, -1)
        proxy_scaled = scaler.transform(proxy_feat)
        proxy_pc = pca.transform(proxy_scaled)[0]  # (PC1, PC2)

        # 锚点自身坐标
        anchor = anchor_coords[cluster_code]
        ax, ay = anchor["PC1"], anchor["PC2"]

        # 欧氏距离 = 代理向量到锚点本身的距离
        dist = np.sqrt((proxy_pc[0] - ax) ** 2 + (proxy_pc[1] - ay) ** 2)

        if dist < DISTANCE_THRESHOLDS["high"]:
            quality = "high"
        elif dist < DISTANCE_THRESHOLDS["medium"]:
            quality = "medium"
        else:
            quality = "low"

        results.append({
            "subject_id": subject_id,
            "cluster_code": cluster_code,
            "anchor_name": name_map[cluster_code],
            "confidence": confidence,
            "proxy_pc1": round(float(proxy_pc[0]), 6),
            "proxy_pc2": round(float(proxy_pc[1]), 6),
            "anchor_pc1": round(ax, 6),
            "anchor_pc2": round(ay, 6),
            "distance_to_anchor": round(dist, 6),
            "match_quality": quality,
            "course_days": course_map[cluster_code],
            "feature_source": "anchor_proxy"
        })

    # 输出CSV
    fieldnames = ["subject_id", "cluster_code", "anchor_name", "confidence",
                  "proxy_pc1", "proxy_pc2", "anchor_pc1", "anchor_pc2",
                  "distance_to_anchor", "match_quality", "course_days", "feature_source"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    # 统计
    high_n = sum(1 for r in results if r["match_quality"] == "high")
    med_n = sum(1 for r in results if r["match_quality"] == "medium")
    low_n = sum(1 for r in results if r["match_quality"] == "low")

    print(f"\n=== 桥接完成 ===")
    print(f"  总样本:     {len(results)}")
    print(f"  high (<0.3):  {high_n} ({high_n/len(results)*100:.1f}%)")
    print(f"  medium(0.3-0.5): {med_n} ({med_n/len(results)*100:.1f}%)")
    print(f"  low (>0.5):    {low_n} ({low_n/len(results)*100:.1f}%)")
    print(f"  输出: {OUTPUT_PATH}")

    return results


def reconstruct_feature_from_mimic(subject_id, icd_codes, meds, labs):
    """
    预留特征重建函数（路线B用）
    输入：MIMIC的ICD、用药、Lab原始数据
    输出：10维特征向量（舌4+脉4+症2）
    后续扩展：根据规则逐维估算（如BNP>500→pulse[3]弱, WBC>12→tongue[0]偏黄）
    """
    raise NotImplementedError("路线B：特征重建模块待扩展")


if __name__ == "__main__":
    process_mimic_crude_map()
