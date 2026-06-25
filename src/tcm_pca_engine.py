#!/usr/bin/env python3
"""
TCM PCA Trainer + MIMIC Extrapolation Engine
============================================
基于13金标证型构建PCA主成分空间，Bootstrap稳定性检验，
MIMIC样本外推至最近锚点。

特征结构（10维参与PCA）:
  tongue[0-3]: 苔色质, 苔厚腻, 舌形, 络脉
  pulse[0-3]:  浮沉, 数迟, 虚实, 有力无力
  symptom[0-1]: 主症严重度, 兼症广度

元数据（不参与PCA):
  course_days: 归一化病程 [0-1], 第13列(CSV index 12)
  用于后续 collapse ~ course_days 分层分析

用法:
  python tcm_pca_engine.py --mode train        # 仅训练+验证
  python tcm_pca_engine.py --mode all          # 训练+保存模型
  python tcm_pca_engine.py --mode extrapolate  # 加载模型→外推MIMIC
  python tcm_pca_engine.py --mode demo         # 自测演示

依赖: numpy, sklearn, matplotlib (可选, 仅绘图需要)
"""

import json, csv, os, sys, pickle, argparse
import numpy as np
from pathlib import Path

# ============================================================
# 0. 配置
# ============================================================
MATRIX_CSV  = Path(__file__).parent / "tcm_syndrome_matrix.csv"
MODEL_PATH  = Path(__file__).parent / "tcm_pca_model.pkl"
FEATURE_COLS = list(range(2, 12))   # CSV列索引: tongue[0-3]=2-5, pulse[0-3]=6-9, symptom[0-1]=10-11
COURSE_COL   = 12                    # course_days 列索引 (不参与PCA)
N_COMPONENTS = 2
BOOTSTRAP_N  = 1000
RANDOM_SEED  = 42

# ============================================================
# 1. 加载特征矩阵
# ============================================================
def load_matrix():
    """返回 (names, codes, X_10d, course_days, anchors_dict)"""
    names, codes, X, courses, anchors = [], [], [], [], {}
    with open(MATRIX_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            names.append(row[0])
            codes.append(row[1])
            X.append([float(row[i]) for i in FEATURE_COLS])
            courses.append(float(row[COURSE_COL]))
            # anchor cols: x4_lo(13),x4_hi(14),col_lo(15),col_hi(16),mc_lo(17),mc_hi(18)
            anchors[row[1]] = {
                "x4": [float(row[13]), float(row[14])],
                "collapse": [float(row[15]), float(row[16])],
                "margin_corr": [float(row[17]), float(row[18])],
            }
    return names, codes, np.array(X), np.array(courses), anchors


# ============================================================
# 2. PCA 训练 + Bootstrap
# ============================================================
def train_pca(X, codes, names, do_bootstrap=True):
    """训练PCA并返回模型、坐标、loading矩阵、Bootstrap CI"""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=N_COMPONENTS, random_state=RANDOM_SEED)
    X_pca = pca.fit_transform(X_scaled)

    # 坐标
    coords = {}
    for i, code in enumerate(codes):
        coords[code] = {"name": names[i], "PC1": float(X_pca[i, 0]), "PC2": float(X_pca[i, 1])}

    # 方差解释率
    var_explained = pca.explained_variance_ratio_

    # Loading矩阵
    loadings = pca.components_  # shape (2, 10)

    # Bootstrap 稳定性
    bootstrap_ci = None
    if do_bootstrap and len(X) >= 3:
        np.random.seed(RANDOM_SEED)
        n = len(X)
        boot_loadings = np.zeros((BOOTSTRAP_N, N_COMPONENTS, len(FEATURE_COLS)))
        for b in range(BOOTSTRAP_N):
            idx = np.random.choice(n, size=n, replace=True)
            Xb = X[idx]
            Xb_scaled = scaler.fit_transform(Xb)
            pca_b = PCA(n_components=N_COMPONENTS)
            pca_b.fit(Xb_scaled)
            boot_loadings[b] = pca_b.components_
        loadings_ci = np.percentile(boot_loadings, [2.5, 97.5], axis=0)  # shape (2, 2, 10)
        # Sign alignment: flip if first feature loading disagrees with full-data
        for b in range(BOOTSTRAP_N):
            for pc in range(N_COMPONENTS):
                if np.sign(boot_loadings[b, pc, 0]) != np.sign(loadings[pc, 0]):
                    boot_loadings[b, pc] *= -1
        loadings_ci = np.percentile(boot_loadings, [2.5, 97.5], axis=0)
        bootstrap_ci = {
            "PC1": {"lo": loadings_ci[0,0].tolist(), "hi": loadings_ci[1,0].tolist()},
            "PC2": {"lo": loadings_ci[0,1].tolist(), "hi": loadings_ci[1,1].tolist()},
        }

    return {
        "pca": pca,
        "scaler": scaler,
        "coords": coords,
        "var_explained": var_explained.tolist(),
        "loadings": loadings.tolist(),
        "bootstrap_ci": bootstrap_ci,
        "feature_names": ["tongue_苔色质","tongue_苔厚腻","tongue_舌形","tongue_络脉",
                          "pulse_浮沉","pulse_数迟","pulse_虚实","pulse_有力无力",
                          "symptom_主症","symptom_兼症"],
    }


# ============================================================
# 3. 留一法交叉验证
# ============================================================
def leave_one_out_cv(X, codes, names):
    """LOOCV: 每次留一个金标样本，用其余12个训PCA，看留出样本的投影误差"""
    results = []
    for i in range(len(X)):
        X_train = np.delete(X, i, axis=0)
        X_test = X[i:i+1]

        result = train_pca(X_train,
                          [c for j,c in enumerate(codes) if j!=i],
                          [n for j,n in enumerate(names) if j!=i],
                          do_bootstrap=False)

        X_test_scaled = result["scaler"].transform(X_test)
        X_test_pca = result["pca"].transform(X_test_scaled)

        # 计算到其余12个锚点的最小欧氏距离
        anchor_coords = np.array([[v["PC1"], v["PC2"]] for v in result["coords"].values()])
        test_coord = X_test_pca[0]
        dists = np.sqrt(np.sum((anchor_coords - test_coord) ** 2, axis=1))
        nearest_idx = np.argmin(dists)
        nearest_code = list(result["coords"].keys())[nearest_idx]

        results.append({
            "held_out": codes[i],
            "held_out_name": names[i],
            "PC1": float(test_coord[0]),
            "PC2": float(test_coord[1]),
            "nearest_anchor": nearest_code,
            "distance": float(dists[nearest_idx]),
            "correct": nearest_code == codes[i],
        })

    accuracy = sum(1 for r in results if r["correct"]) / len(results) if results else 0
    return results, accuracy


# ============================================================
# 4. MIMIC外推
# ============================================================
def extrapolate_mimic(model_data, mimic_vectors, mimic_ids=None):
    """
    mimic_vectors: np.array (n_samples, 10) — 必须与金标10维对齐
    mimic_ids: list of str — 样本ID
    返回: list of {id, PC1, PC2, nearest_anchor, distance, anchor_name}
    """
    X_scaled = model_data["scaler"].transform(mimic_vectors)
    X_pca = model_data["pca"].transform(X_scaled)

    anchor_coords = np.array([[v["PC1"], v["PC2"]] for v in model_data["coords"].values()])
    anchor_codes = list(model_data["coords"].keys())
    anchor_names = [model_data["coords"][c]["name"] for c in anchor_codes]

    results = []
    for i in range(len(X_pca)):
        dists = np.sqrt(np.sum((anchor_coords - X_pca[i]) ** 2, axis=1))
        nearest_idx = np.argmin(dists)
        results.append({
            "id": mimic_ids[i] if mimic_ids else f"MIMIC_{i}",
            "PC1": float(X_pca[i, 0]),
            "PC2": float(X_pca[i, 1]),
            "nearest_anchor": anchor_codes[nearest_idx],
            "anchor_name": anchor_names[nearest_idx],
            "distance": float(dists[nearest_idx]),
            "all_distances": {anchor_codes[j]: float(dists[j]) for j in range(len(dists))},
        })
    return results


# ============================================================
# 5. 五条高确信粗糙映射规则（便签函数）
# ============================================================
def crude_map_mimic(icd_codes, meds, labs, vitals, has_tcm=False):
    """
    输入MIMIC单个患者的原始数据片段，返回 (cluster_code, confidence)

    icd_codes: list of str — ICD诊断码，如 ['I50.9','N17.9']
    meds: list of str — 西药通用名，如 ['norepinephrine','furosemide']
    labs: dict — Lab指标，如 {'BNP':600,'WBC':14,'PCT':0.8,'Glucose':13,...}
    vitals: dict — 体征，如 {'Temp':39.5,'HR':95,'anhidrosis':True,'edema':True}
    has_tcm: bool — 是否有中药记录（极罕见）

    返回: (cluster_code, confidence) 其中 confidence ∈ {0, 0.5, 1.0}
          cluster_code 为 None 表示未归类
    """
    candidates = []

    # Rule 1: 少阴寒化簇 (四逆汤证)
    # ICD: 心衰/心源性休克/急性肾损伤
    rule1_icd = any(c.startswith('I50') or c.startswith('R57.0') or c.startswith('N17')
                    for c in icd_codes)
    # Meds: 血管活性药连续≥24h (简化：存在即触发)
    rule1_med = any(m in [m.lower() for m in meds] for m in ['norepinephrine','dopamine','epinephrine'])
    # Labs: BNP>500 或 NT-proBNP>4500, LVEF<40%
    rule1_lab = labs.get('BNP',0) > 500 or labs.get('NTproBNP',0) > 4500
    # Exclude: 低血容量性休克 E86.0
    rule1_exclude = any(c.startswith('E86.0') for c in icd_codes)

    if rule1_icd and rule1_med and rule1_lab and not rule1_exclude:
        conf = 1.0 if has_tcm else 0.5
        candidates.append(("sy_hn", conf))

    # Rule 2: 阳明经证簇 (白虎汤证)
    rule2_icd = any(c.startswith('A41') or c.startswith('J18') for c in icd_codes)
    rule2_temp = vitals.get('Temp', 0) > 39.0
    rule2_lab = labs.get('WBC', 0) > 12 or labs.get('PCT', 0) > 0.5
    rule2_exclude = any(c.startswith('G93.89') for c in icd_codes)  # 中枢性高热

    if rule2_icd and rule2_temp and rule2_lab and not rule2_exclude:
        conf = 1.0 if has_tcm else 0.5
        candidates.append(("ym_bh", conf))

    # Rule 3: 气虚血瘀痰湿簇 (杂证3)
    rule3_icd = any(c.startswith('J44') or c.startswith('I50') for c in icd_codes)
    rule3_o2 = labs.get('PaO2_FiO2', 500) < 300
    rule3_med = any(m in [m.lower() for m in meds] for m in ['furosemide'])
    rule3_exclude = any(c.startswith('I26.9') for c in icd_codes)  # 急性肺栓塞

    if rule3_icd and rule3_o2 and rule3_med and not rule3_exclude:
        conf = 1.0 if has_tcm else 0.5
        candidates.append(("qx_yt_003", conf))

    # Rule 4: 太阳伤寒簇 (麻黄汤证)
    rule4_icd = any(c.startswith('J06') or c.startswith('J15') for c in icd_codes)
    rule4_temp = vitals.get('Temp', 0) > 38.5
    rule4_sweat = vitals.get('anhidrosis', False)  # 无汗
    rule4_exclude = any(c.startswith('B08.1') for c in icd_codes)  # 风疹

    if rule4_icd and rule4_temp and rule4_sweat and not rule4_exclude:
        conf = 1.0 if has_tcm else 0.5
        candidates.append(("ty_sh", conf))

    # Rule 5: 气郁痰热簇 (杂证2)
    rule5_icd = any(c.startswith('F41') or c.startswith('N95.1') for c in icd_codes)
    rule5_hr = vitals.get('HR', 70) > 90
    rule5_med = any(m in [m.lower() for m in meds] for m in ['alprazolam','estradiol'])
    rule5_exclude = any(c.startswith('E05.9') for c in icd_codes)  # 甲亢

    if rule5_icd and rule5_hr and rule5_med and not rule5_exclude:
        conf = 1.0 if has_tcm else 0.5
        candidates.append(("qy_tr_002", conf))

    # 通用兜底
    if not candidates:
        return None, 0.0
    if len(candidates) == 1:
        return candidates[0]
    # 多条命中：取最高置信度
    best = max(candidates, key=lambda x: x[1])
    # 置信度相同 → 标记多候选
    ties = [c for c in candidates if c[1] == best[1]]
    if len(ties) > 1:
        return None, 0.0  # 多候选不参与锚点距离计算
    return best


# ============================================================
# 6. 可视化
# ============================================================
def plot_pca_space(model_data, mimic_results=None, save_path=None):
    """散点图: 13锚点(彩色圆) + MIMIC样本(灰色小点)"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARN] matplotlib not available, skipping plot")
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # 13个锚点 — 纯证实心圆, 杂证(三层嵌套)空心圆
    MIXED_CODES = {"kj_qys_001", "qy_tr_002", "qx_yt_003"}
    colors = plt.cm.tab10(np.linspace(0, 1, 13))
    for i, (code, v) in enumerate(model_data["coords"].items()):
        is_mixed = code in MIXED_CODES
        marker_style = 'o'
        face_alpha = 0.3 if is_mixed else 1.0
        ax.scatter(v["PC1"], v["PC2"], c=[colors[i]], s=200, edgecolors='black',
                   linewidth=1.5, zorder=5, marker=marker_style, alpha=face_alpha)
        label_suffix = " [杂]" if is_mixed else ""
        ax.annotate(code + label_suffix, (v["PC1"], v["PC2"]),
                    textcoords="offset points", xytext=(8, 8), fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))

    # MIMIC样本
    if mimic_results:
        mimic_x = [r["PC1"] for r in mimic_results]
        mimic_y = [r["PC2"] for r in mimic_results]
        ax.scatter(mimic_x, mimic_y, c='gray', s=15, alpha=0.4, zorder=3, marker='.')

    ax.set_xlabel(f"PC1 ({model_data['var_explained'][0]*100:.1f}% var)")
    ax.set_ylabel(f"PC2 ({model_data['var_explained'][1]*100:.1f}% var)")
    ax.set_title("TCM PCA Space: 13 Gold-Standard Anchors + MIMIC Extrapolation")
    ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='black', linewidth=0.5, linestyle='--', alpha=0.3)
    ax.grid(True, alpha=0.2)

    path = save_path or (Path(__file__).parent / "tcm_pca_plot.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[OK] Plot saved: {path}")


# ============================================================
# 7. 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="TCM PCA Engine")
    parser.add_argument("--mode", choices=["train","all","extrapolate","demo","test_rules"],
                        default="demo", help="运行模式")
    parser.add_argument("--no-bootstrap", action="store_true", help="跳过Bootstrap")
    parser.add_argument("--sample", type=int, default=0, help="MIMIC分层抽样数 (0=全量)")
    parser.add_argument("--threshold", type=float, default=0.0, help="距离阈值 (<threshold=高匹配, 0=禁用)")
    args = parser.parse_args()

    # ——— 加载数据 ———
    names, codes, X, courses, anchors = load_matrix()
    print(f"Loaded {len(codes)} syndromes, X shape={X.shape}, course_days range=[{courses.min():.2f}, {courses.max():.2f}]")

    if args.mode == "test_rules":
        # 测试五条规则
        print("\n=== Rule Smoke Tests ===")
        tests = [
            # Rule 1: 少阴
            (["I50.9","N17.9"], ["norepinephrine"], {"BNP":600}, {"Temp":37}, False),
            # Rule 2: 阳明
            (["A41.9"], ["acetaminophen"], {"WBC":15,"PCT":2.0}, {"Temp":40}, False),
            # Rule 3: 气虚血瘀痰湿
            (["J44.9"], ["furosemide","salbutamol"], {"PaO2_FiO2":250}, {"Temp":37}, False),
            # Rule 4: 太阳伤寒
            (["J06.9"], ["ibuprofen"], {}, {"Temp":39,"anhidrosis":True}, False),
            # Rule 5: 气郁痰热
            (["F41.9"], ["alprazolam"], {}, {"HR":95}, False),
            # Negative
            (["Z00.0"], [], {}, {"Temp":37}, False),
        ]
        for i, (icd, meds, labs, vitals, tcm) in enumerate(tests):
            code, conf = crude_map_mimic(icd, meds, labs, vitals, tcm)
            print(f"  Test {i+1}: ICD={icd[0]} → {code} (conf={conf})")
        return

    if args.mode in ("train", "all", "demo"):
        # ——— 训练 ———
        print("\n=== Training PCA ===")
        model_data = train_pca(X, codes, names, do_bootstrap=not args.no_bootstrap)

        print(f"Variance explained: PC1={model_data['var_explained'][0]*100:.1f}%, "
              f"PC2={model_data['var_explained'][1]*100:.1f}%")
        print(f"Cumulative: {sum(model_data['var_explained'])*100:.1f}%")

        print("\n--- PC Coordinates ---")
        for code, v in model_data["coords"].items():
            print(f"  {code:12s} PC1={v['PC1']:+7.3f}  PC2={v['PC2']:+7.3f}  | {v['name'][:30]}")

        print("\n--- Loading Matrix ---")
        for pc_idx, pc_name in enumerate(["PC1", "PC2"]):
            ld = model_data["loadings"][pc_idx]
            print(f"  {pc_name}: " + " ".join(f"{v:+6.3f}" for v in ld))

        if model_data["bootstrap_ci"]:
            print("\n--- Bootstrap 95% CI (PC1 loadings) ---")
            for j, fname in enumerate(model_data["feature_names"]):
                lo = model_data["bootstrap_ci"]["PC1"]["lo"][j]
                hi = model_data["bootstrap_ci"]["PC1"]["hi"][j]
                mean = model_data["loadings"][0][j]
                print(f"  {fname:20s}: {mean:+6.3f}  CI=[{lo:+6.3f}, {hi:+6.3f}]")

        # ——— LOOCV ———
        print("\n=== Leave-One-Out CV ===")
        cv_results, cv_acc = leave_one_out_cv(X, codes, names)
        for r in cv_results:
            mark = "PASS" if r["correct"] else "MISS"
            print(f"  {mark} Held out {r['held_out']:12s} → nearest={r['nearest_anchor']:12s} dist={r['distance']:.3f}")
        print(f"\n  LOOCV Accuracy: {cv_acc:.2%} ({sum(1 for r in cv_results if r['correct'])}/{len(cv_results)})")

        # ——— 保存模型 ———
        if args.mode == "all":
            save_data = {
                "pca": model_data["pca"],
                "scaler": model_data["scaler"],
                "coords": model_data["coords"],
                "var_explained": model_data["var_explained"],
                "loadings": model_data["loadings"],
                "bootstrap_ci": model_data["bootstrap_ci"],
                "feature_names": model_data["feature_names"],
                "anchors": anchors,
                "codes": codes,
                "names": names,
            }
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(save_data, f)
            print(f"\n[OK] Model saved: {MODEL_PATH}")

        # ——— Demo: 自测外推 ———
        if args.mode == "demo":
            print("\n=== Demo: Self-Extrapolation ===")
            mimic_results = extrapolate_mimic(model_data, X, mimic_ids=codes)
            for r in mimic_results:
                print(f"  {r['id']:12s} → {r['nearest_anchor']:12s} dist={r['distance']:.3f}  ({r['anchor_name'][:40]})")

            # 画图
            plot_pca_space(model_data, mimic_results,
                          save_path=Path(__file__).parent / "tcm_pca_demo.png")

            # course_days vs collapse 分层分析提示
            print("\n=== Stratified Analysis Hint ===")
            print("course_days NOT in PCA. For post-hoc analysis:")
            for code in codes:
                idx = codes.index(code)
                print(f"  {code}: course_days={courses[idx]:.2f}, "
                      f"collapse_anchor={anchors[code]['collapse']}, "
                      f"PC1={model_data['coords'][code]['PC1']:+.3f}")

    elif args.mode == "extrapolate":
        # ——— 加载模型 ———
        if not MODEL_PATH.exists():
            print(f"ERROR: Model not found at {MODEL_PATH}. Run --mode all first.")
            sys.exit(1)
        with open(MODEL_PATH, "rb") as f:
            model_data = pickle.load(f)
        print(f"Model loaded: {len(model_data['codes'])} anchors")

        # MIMIC外推示例：生成假样本(少阴+阳明+太阴簇)
        np.random.seed(99)
        cluster_specs = [
            ("sy_hn", 0.3, 30),   # 少阴寒化
            ("ym_bh", 0.4, 30),   # 阳明经证
            ("ty_xh", 0.35, 20),  # 太阴虚寒
            ("qy_tr_002", 0.5, 15),  # 气郁痰热(杂)
            ("kj_qys_001", 0.4, 10), # 肾虚清阳不升(杂)
        ]
        all_mimic_pca, all_mimic_raw = [], []
        cluster_labels = []
        for anchor_code, std, n in cluster_specs:
            coord = np.array([[model_data["coords"][anchor_code]["PC1"],
                              model_data["coords"][anchor_code]["PC2"]]])
            pca_pts = coord + np.random.normal(0, std, (n, 2))
            all_mimic_pca.append(pca_pts)
            all_mimic_raw.append(
                model_data["scaler"].inverse_transform(
                    model_data["pca"].inverse_transform(pca_pts)))
            cluster_labels.extend([anchor_code] * n)

        mimic_pca_all = np.vstack(all_mimic_pca)
        mimic_raw = np.vstack(all_mimic_raw)
        n_total = len(mimic_raw)

        # ——— --sample 分层抽样 ———
        if args.sample > 0 and args.sample < n_total:
            from collections import defaultdict
            by_cluster = defaultdict(list)
            for i, lbl in enumerate(cluster_labels):
                by_cluster[lbl].append(i)
            n_clusters = len(by_cluster)
            per_cluster = max(1, args.sample // n_clusters)
            sampled_idx = []
            for lbl, indices in by_cluster.items():
                n_take = min(per_cluster, len(indices))
                sampled_idx.extend(np.random.choice(indices, n_take, replace=False))
            mimic_raw = mimic_raw[sampled_idx]
            cluster_labels = [cluster_labels[i] for i in sampled_idx]
            print(f"Stratified sampling: {n_total} -> {len(sampled_idx)} ({n_clusters} clusters, ~{per_cluster}/cluster)")

        mimic_ids = [f"MIMIC_{i:04d}" for i in range(len(mimic_raw))]
        results = extrapolate_mimic(model_data, mimic_raw, mimic_ids)

        # ——— --threshold 距离阈值过滤 ———
        high_match, low_match, unmatched = [], [], []
        if args.threshold > 0:
            for r in results:
                if r["distance"] <= args.threshold:
                    r["match_quality"] = "high"
                    high_match.append(r)
                else:
                    r["match_quality"] = "low"
                    low_match.append(r)
            print(f"\nThreshold={args.threshold}: high={len(high_match)}, low={len(low_match)}")
        else:
            high_match = results

        # 统计
        from collections import Counter
        cnt = Counter(r["nearest_anchor"] for r in results)
        print("\nMIMIC Extrapolation Summary:")
        for code, count in cnt.most_common():
            marker = " [杂]" if code in {"kj_qys_001","qy_tr_002","qx_yt_003"} else ""
            print(f"  {code}{marker}: {count} samples")

        if args.threshold > 0:
            print(f"\n  High-confidence (dist<={args.threshold}): {len(high_match)}/{len(results)}")

        # 写入JSON
        out_path = Path(__file__).parent / "mimic_extrapolation_results.json"
        export = [{"id": r["id"], "PC1": r["PC1"], "PC2": r["PC2"],
                    "nearest_anchor": r["nearest_anchor"],
                    "anchor_name": r["anchor_name"],
                    "distance": r["distance"],
                    "match_quality": r.get("match_quality", "none")}
                  for r in results]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Results saved: {out_path}")

        plot_pca_space(model_data, results,
                      save_path=Path(__file__).parent / "tcm_pca_mimic.png")


if __name__ == "__main__":
    main()
