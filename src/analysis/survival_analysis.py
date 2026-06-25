#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MIMIC中医证型生存分析 — 主线: Cox回归 + KM曲线 | 支线: Unclassified ICD挖掘
产出: Table 2(多因素Cox) + Figure 1(KM生存曲线) + unclassified_top50_icds.csv
用法: python survival_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from lifelines import CoxPHFitter
from lifelines import KaplanMeierFitter
import gzip, csv, os, sys, warnings
from datetime import datetime
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import MIMIC_CORE_DIR, DATA_DIR, ANALYSIS_OUTPUT_DIR, VERIFICATION_30_FINAL

warnings.filterwarnings("ignore")

# ============ 路径配置 ============
MIMIC_DIR = str(MIMIC_CORE_DIR)
OUT_DIR = str(ANALYSIS_OUTPUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)

CRUDE_MAP = str(DATA_DIR / "mimic_crude_map.csv")
ADMISSIONS = str(MIMIC_CORE_DIR / "admissions.csv.gz")
PATIENTS = str(MIMIC_CORE_DIR / "patients.csv.gz")

# ============ 第一步: 加载数据 ============
print("=" * 70)
print("STEP 1: 加载 & 合并数据")
print("=" * 70)

# 1a. 粗糙映射结果
df = pd.read_csv(CRUDE_MAP)
print(f"  crude_map: {len(df):,} rows, columns={list(df.columns)}")

# 1b. Admissions (hadm_id -> admittime, dischtime, deathtime, hospital_expire_flag)
adm = pd.read_csv(ADMISSIONS, compression="gzip",
                  usecols=["hadm_id", "admittime", "dischtime", "deathtime", "hospital_expire_flag"])
print(f"  admissions: {len(adm):,} rows")

# 1c. Patients (subject_id -> gender, anchor_age)
pat = pd.read_csv(PATIENTS, compression="gzip",
                  usecols=["subject_id", "gender", "anchor_age"])
print(f"  patients: {len(pat):,} rows")

# ============ 第二步: 合并 ============
print("\n" + "=" * 70)
print("STEP 2: 合并映射+入院+患者信息")
print("=" * 70)

# Merge step by step
df = df.merge(adm, on="hadm_id", how="inner", validate="many_to_one")
print(f"  after admissions merge: {len(df):,} rows (lost {len(df) - 85242 if len(df) < 85242 else '0'}?)")

df = df.merge(pat, on="subject_id", how="inner", validate="many_to_one")
print(f"  after patients merge: {len(df):,} rows")

# ============ 第三步: 计算生存时间 & 事件 ============
print("\n" + "=" * 70)
print("STEP 3: 计算生存时间(days) & 死亡事件")
print("=" * 70)

df["admittime"] = pd.to_datetime(df["admittime"])
df["dischtime"] = pd.to_datetime(df["dischtime"])
df["deathtime_dt"] = pd.to_datetime(df["deathtime"])

# 事件: 院内死亡
df["event"] = df["hospital_expire_flag"].astype(int)

# 生存时间 (天)
mask_dead = df["deathtime_dt"].notna()
df["duration"] = np.nan
df.loc[mask_dead, "duration"] = (df.loc[mask_dead, "deathtime_dt"] - df.loc[mask_dead, "admittime"]).dt.total_seconds() / (24 * 3600)
df.loc[~mask_dead, "duration"] = (df.loc[~mask_dead, "dischtime"] - df.loc[~mask_dead, "admittime"]).dt.total_seconds() / (24 * 3600)

# 过滤: duration <= 0 (极少异常) 或 > 365 (超长住院, 截尾)
bad_dur = (df["duration"] <= 0) | (df["duration"] > 365)
print(f"  duration <= 0 or > 365: {bad_dur.sum()} rows → drop")
df = df[~bad_dur]

# 最小正duration
min_dur = df.loc[df["duration"] > 0, "duration"].min()
print(f"  min positive duration: {min_dur:.4f} days")
df["duration"] = df["duration"].clip(lower=min_dur / 2)  # Cox不能处理0, 用半分钟级微调

print(f"  final analysis sample: {len(df):,} rows")
print(f"  events (deaths): {df['event'].sum():,} ({df['event'].mean()*100:.1f}%)")
print(f"  mean duration: {df['duration'].mean():.1f} days, median: {df['duration'].median():.1f} days")

# ============ 第四步: 证型编码 ============
print("\n" + "=" * 70)
print("STEP 4: 证型编码 (unclassified=Reference)")
print("=" * 70)

print(f"  cluster_code distribution:")
vc = df["cluster_code"].value_counts()
for code, cnt in vc.items():
    mortality = df.loc[df["cluster_code"] == code, "event"].mean() * 100
    print(f"    {code:25s}: {cnt:>7,} ({cnt/len(df)*100:5.1f}%)  mortality={mortality:.1f}%")

# 编码: Reference = unclassified (最大的基础组)
cluster_list = vc.index.tolist()
if "unclassified" not in cluster_list:
    raise ValueError("unclassified not found!")
cluster_list.remove("unclassified")

# 构建df_cox
df_cox = df[["duration", "event", "cluster_code", "gender", "anchor_age"]].copy()
df_cox["age"] = df_cox["anchor_age"].astype(float)
df_cox["gender_male"] = (df_cox["gender"] == "M").astype(int)

# 创建dummy变量 (unclassified作为reference)
for cl in cluster_list:
    col_name = "cluster_" + cl.replace("-", "_").replace(" ", "_").replace(".", "_")
    df_cox[col_name] = (df_cox["cluster_code"] == cl).astype(int)

print(f"\n  dummy columns created: {len(cluster_list)} clusters + unclassified (ref)")

# ============ 第五步: 单因素 + 多因素 Cox ============
print("\n" + "=" * 70)
print("STEP 5: Cox回归 (Univariate + Multivariate)")
print("=" * 70)

# 5a. 单因素 (逐证型)
uni_results = []
for cl in cluster_list:
    col_name = "cluster_" + cl.replace("-", "_").replace(" ", "_").replace(".", "_")
    cph_uni = CoxPHFitter()
    try:
        cph_uni.fit(df_cox[["duration", "event", col_name]], duration_col="duration", event_col="event")
        summary = cph_uni.summary
        hr = np.exp(summary.loc[col_name, "coef"])
        ci_low = np.exp(summary.loc[col_name, "coef lower 95%"])
        ci_high = np.exp(summary.loc[col_name, "coef upper 95%"])
        p_val = summary.loc[col_name, "p"]
        uni_results.append({
            "cluster": cl,
            "HR": round(hr, 2),
            "CI_low": round(ci_low, 2),
            "CI_high": round(ci_high, 2),
            "p": p_val,
            "p_fmt": "<0.001" if p_val < 0.001 else f"{p_val:.3f}" if p_val >= 0.001 else "<0.001"
        })
    except Exception as e:
        print(f"  WARNING: {cl} uni cox failed: {e}")
        uni_results.append({"cluster": cl, "HR": np.nan, "CI_low": np.nan, "CI_high": np.nan, "p": np.nan, "p_fmt": "N/A"})

print("\n  [Univariate Cox]")
for r in uni_results:
    print(f"    {r['cluster']:25s}: HR={r['HR']:.2f} ({r['CI_low']:.2f}-{r['CI_high']:.2f}), p={r['p_fmt']}")

# 5b. 多因素 (全部证型 + age + gender, unclassified=ref)
multi_vars = ["age", "gender_male"] + [("cluster_" + cl.replace("-", "_").replace(" ", "_").replace(".", "_")) for cl in cluster_list]
cph_multi = CoxPHFitter()
try:
    cph_multi.fit(df_cox[["duration", "event"] + multi_vars], duration_col="duration", event_col="event")
    print(f"\n  [Multivariate Cox — age+gender adjusted]")
    multi_summary = cph_multi.summary
    multi_results = []
    for cl in cluster_list:
        col_name = "cluster_" + cl.replace("-", "_").replace(" ", "_").replace(".", "_")
        hr = np.exp(multi_summary.loc[col_name, "coef"])
        ci_low = np.exp(multi_summary.loc[col_name, "coef lower 95%"])
        ci_high = np.exp(multi_summary.loc[col_name, "coef upper 95%"])
        p_val = multi_summary.loc[col_name, "p"]
        multi_results.append({
            "cluster": cl,
            "HR": round(hr, 2),
            "CI_low": round(ci_low, 2),
            "CI_high": round(ci_high, 2),
            "p": p_val,
            "p_fmt": "<0.001" if p_val < 0.001 else f"{p_val:.3f}" if p_val >= 0.001 else "<0.001"
        })
        print(f"    {cl:25s}: HR={hr:.2f} ({ci_low:.2f}-{ci_high:.2f}), p={p_val:.4f}")
    
    # Age & gender effects
    for v in ["age", "gender_male"]:
        hr = np.exp(multi_summary.loc[v, "coef"])
        ci_low = np.exp(multi_summary.loc[v, "coef lower 95%"])
        ci_high = np.exp(multi_summary.loc[v, "coef upper 95%"])
        p_val = multi_summary.loc[v, "p"]
        print(f"    {v:25s}: HR={hr:.2f} ({ci_low:.2f}-{ci_high:.2f}), p={p_val:.4f}")
except Exception as e:
    print(f"  ERROR: Multivariate Cox failed: {e}")
    import traceback; traceback.print_exc()
    multi_results = []

# ============ 第六步: 产出 Table 2 (CSV) ============
print("\n" + "=" * 70)
print("STEP 6: 产出 Table 2 (Cox回归表)")
print("=" * 70)

table_rows = [{
    "Syndrome": "Unclassified",
    "N": str(len(df_cox[df_cox["cluster_code"] == "unclassified"])),
    "Mortality_%": f"{df_cox[df_cox['cluster_code']=='unclassified']['event'].mean()*100:.1f}",
    "Uni_HR": "1.0 (ref)",
    "Uni_P": "-",
    "Multi_HR": "1.0 (ref)",
    "Multi_P": "-"
}]

for ur, mr in zip(uni_results, multi_results):
    n = len(df_cox[df_cox["cluster_code"] == ur["cluster"]])
    mort = df_cox[df_cox["cluster_code"] == ur["cluster"]]["event"].mean() * 100
    table_rows.append({
        "Syndrome": ur["cluster"],
        "N": str(n),
        "Mortality_%": f"{mort:.1f}",
        "Uni_HR": f"{ur['HR']:.2f} ({ur['CI_low']:.2f}-{ur['CI_high']:.2f})",
        "Uni_P": ur["p_fmt"],
        "Multi_HR": f"{mr['HR']:.2f} ({mr['CI_low']:.2f}-{mr['CI_high']:.2f})",
        "Multi_P": mr["p_fmt"]
    })

table_df = pd.DataFrame(table_rows)
table_path = os.path.join(OUT_DIR, "table2_cox_results.csv")
table_df.to_csv(table_path, index=False, encoding="utf-8-sig")
print(f"  Saved: {table_path}")
print(f"\n{table_df.to_string(index=False)}")

# ============ 第七步: Figure 1 — Kaplan-Meier 曲线 ============
print("\n" + "=" * 70)
print("STEP 7: Kaplan-Meier 生存曲线 (Figure 1)")
print("=" * 70)

# 颜色方案
colors = {
    "unclassified": "#888888",
    "tai_yin": "#2E86AB",         # 太阴 — 蓝
    "qi_xu_xue_yu_tan_shi": "#A23B72",  # 气虚血瘀痰湿 — 紫
    "shao_yin_han_hua": "#F18F01",     # 少阴寒化 — 橙
    "yang_ming_jing": "#C73E1D",       # 阳明经证 — 红
    "re_jue": "#8B0000",               # 热厥 — 深红
}
# 中文标签
labels_cn = {
    "unclassified": "Unclassified (Ref)",
    "tai_yin": "Taiyin",
    "qi_xu_xue_yu_tan_shi": "Qi-Xu Xue-Yu Tan-Shi",
    "shao_yin_han_hua": "Shaoyin Hanhua",
    "yang_ming_jing": "Yangming Jing",
    "re_jue": "Re-Jue (Septic Shock)"
}

fig, ax = plt.subplots(figsize=(12, 8))

kmf = KaplanMeierFitter()
# 按死亡率排序: unclassified -> taiyin -> qixu -> shaoyin -> yangming -> rejue
plot_order = ["unclassified", "tai_yin", "qi_xu_xue_yu_tan_shi", "shao_yin_han_hua", "yang_ming_jing", "re_jue"]

for cl in plot_order:
    if cl not in df_cox["cluster_code"].values:
        continue
    mask = df_cox["cluster_code"] == cl
    n = mask.sum()
    ev = df_cox.loc[mask, "event"].sum()
    kmf.fit(
        durations=df_cox.loc[mask, "duration"],
        event_observed=df_cox.loc[mask, "event"],
        label=f"{labels_cn.get(cl, cl)} (n={n}, events={ev})"
    )
    kmf.plot_survival_function(ax=ax, color=colors.get(cl, "#333333"), linewidth=2.5)

ax.set_xlim(0, 90)
ax.set_ylim(0.4, 1.02)
ax.set_xlabel("Days since ICU admission", fontsize=13, fontweight="bold")
ax.set_ylabel("Survival Probability", fontsize=13, fontweight="bold")
ax.set_title("Figure 1: Kaplan-Meier Survival Curves by TCM Syndrome Cluster\n(MIMIC-IV ICU Cohort, N={:,})".format(len(df_cox)), 
             fontsize=14, fontweight="bold")
ax.legend(fontsize=10, loc="lower left", frameon=True, facecolor="white", edgecolor="#cccccc")
ax.grid(True, alpha=0.3)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))

# 加28天/60天/90天生存率标注
for t_day in [28, 60, 90]:
    ax.axvline(x=t_day, color="gray", linestyle="--", alpha=0.3, linewidth=0.8)

plt.tight_layout()
km_path = os.path.join(OUT_DIR, "figure1_km_curves.png")
fig.savefig(km_path, dpi=200, bbox_inches="tight")
plt.close(fig)
print(f"  Saved: {km_path}")

# 同时保存28天/90天生存率表
print("\n  KM Landmark Survival Rates:")
landmark_rows = []
for cl in plot_order:
    if cl not in df_cox["cluster_code"].values:
        continue
    mask = df_cox["cluster_code"] == cl
    kmf_temp = KaplanMeierFitter()
    kmf_temp.fit(df_cox.loc[mask, "duration"], df_cox.loc[mask, "event"])
    s28 = kmf_temp.survival_function_at_times(28).values[0] if 28 <= df_cox.loc[mask,"duration"].max() else np.nan
    s60 = kmf_temp.survival_function_at_times(60).values[0] if 60 <= df_cox.loc[mask,"duration"].max() else np.nan
    s90 = kmf_temp.survival_function_at_times(90).values[0] if 90 <= df_cox.loc[mask,"duration"].max() else np.nan
    landmark_rows.append({
        "Syndrome": labels_cn.get(cl, cl),
        "N": mask.sum(),
        "Events": df_cox.loc[mask, "event"].sum(),
        "Mortality": f"{df_cox.loc[mask,'event'].mean()*100:.1f}%",
        "28d_Survival": f"{s28*100:.1f}%" if not np.isnan(s28) else "N/A",
        "60d_Survival": f"{s60*100:.1f}%" if not np.isnan(s60) else "N/A",
        "90d_Survival": f"{s90*100:.1f}%" if not np.isnan(s90) else "N/A"
    })
    print(f"    {cl:25s}: 28d={s28*100:.1f}%  60d={s60*100:.1f}%  90d={s90*100:.1f}%")

lm_df = pd.DataFrame(landmark_rows)
lm_path = os.path.join(OUT_DIR, "km_landmark_rates.csv")
lm_df.to_csv(lm_path, index=False, encoding="utf-8-sig")
print(f"  Saved landmark rates: {lm_path}")

# ============ 第八步: Forest Plot (森林图) ============
print("\n" + "=" * 70)
print("STEP 8: Forest Plot (多因素HR森林图)")
print("=" * 70)

try:
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    # 只画证型相关的HR (不含age/gender)
    plot_clusters = [r["cluster"] for r in multi_results]
    hrs = [r["HR"] for r in multi_results]
    ci_lows = [r["CI_low"] for r in multi_results]
    ci_highs = [r["CI_high"] for r in multi_results]
    p_vals = [r["p"] for r in multi_results]
    
    y_positions = range(len(plot_clusters))
    
    # 按HR排序 (降序, 最危险的在上面)
    sort_idx = np.argsort(hrs)[::-1]
    plot_clusters = [plot_clusters[i] for i in sort_idx]
    hrs = [hrs[i] for i in sort_idx]
    ci_lows = [ci_lows[i] for i in sort_idx]
    ci_highs = [ci_highs[i] for i in sort_idx]
    p_vals = [p_vals[i] for i in sort_idx]
    
    for i, (cl, hr, lo, hi, p) in enumerate(zip(plot_clusters, hrs, ci_lows, ci_highs, p_vals)):
        color = "#8B0000" if hr > 1.5 else "#C73E1D" if hr > 1.0 else "#2E86AB"
        ax2.errorbar(hr, i, xerr=[[hr - lo], [hi - hr]], fmt='o', color=color, 
                    capsize=4, markersize=10, linewidth=2, markeredgecolor="white", markeredgewidth=1)
        
        # P值标注
        p_text = "<0.001" if p < 0.001 else f"p={p:.3f}"
        sig_mark = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        ax2.annotate(f"HR={hr:.2f} ({lo:.2f}-{hi:.2f}) {sig_mark}",
                    xy=(hi + 0.05, i), fontsize=9, va='center', color="#333333",
                    fontweight="bold" if p < 0.05 else "normal")
    
    ax2.axvline(x=1.0, color="black", linestyle="--", linewidth=1.5, alpha=0.7)
    ax2.set_yticks(range(len(plot_clusters)))
    ax2.set_yticklabels([labels_cn.get(cl, cl) for cl in plot_clusters], fontsize=11)
    ax2.set_xlabel("Adjusted Hazard Ratio (95% CI)", fontsize=13, fontweight="bold")
    ax2.set_title("Forest Plot: Multivariate Cox Regression\n(Adjusted for Age + Gender)", 
                 fontsize=14, fontweight="bold")
    ax2.set_xlim(0.3, max(hi for hi in ci_highs) * 1.3)
    ax2.grid(True, alpha=0.2, axis="x")
    
    # 标柱 保护 ↔ 危险
    mid_x = 0.3 + (max(ci_highs) * 1.3 - 0.3) / 6
    ax2.annotate("← Protective", xy=(mid_x - 0.05, -0.8), fontsize=9, color="#2E86AB", ha="right")
    ax2.annotate("Harmful →", xy=(mid_x + 0.05, -0.8), fontsize=9, color="#C73E1D", ha="left")
    
    plt.tight_layout()
    forest_path = os.path.join(OUT_DIR, "figure2_forest_plot.png")
    fig2.savefig(forest_path, dpi=200, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Saved: {forest_path}")
except Exception as e:
    print(f"  Forest plot failed (non-critical): {e}")

# ============ 第九步: Unclassified ICD 频次挖掘 (支线) ============
print("\n" + "=" * 70)
print("STEP 9: Unclassified ICD 频次挖掘 (支线)")
print("=" * 70)

uncl_mask = df["cluster_code"] == "unclassified"
print(f"  Unclassified stays: {uncl_mask.sum()}")

# 需要从原始diagnoses_icd表中提取unclassified hadm_id的ICD代码
# 先收集unclassified hadm_ids
uncl_hadm_ids = set(df.loc[uncl_mask, "hadm_id"].astype(str))
print(f"  Unique hadm_ids in unclassified: {len(uncl_hadm_ids)}")

# 扫描 diagnoses_icd.csv.gz
diag_path = os.path.join(MIMIC_DIR, "hosp", "diagnoses_icd.csv.gz")
icd_counter = Counter()
icd_detail = {}  # icd_code -> {title, long_title}

# 同时读 d_icd_diagnoses 获取标题
dicd_path = os.path.join(MIMIC_DIR, "hosp", "d_icd_diagnoses.csv.gz")
icd_title_map = {}
with gzip.open(dicd_path, "rt", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        icd_title_map[row["icd_code"]] = row.get("long_title", row.get("title", ""))

print(f"  d_icd_diagnoses loaded: {len(icd_title_map)} codes")

# 扫描 diagnoses_icd
with gzip.open(diag_path, "rt", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        hid = row.get("hadm_id", "")
        if hid in uncl_hadm_ids:
            code = row.get("icd_code", "").strip()
            if code:
                icd_counter[code] += 1

print(f"  Total ICD codes scanned in unclassified: {sum(icd_counter.values())}")
print(f"  Unique ICD codes: {len(icd_counter)}")

# Top 50
top50 = icd_counter.most_common(50)
top50_rows = []
for code, cnt in top50:
    title = icd_title_map.get(code, "")
    prev = icd_title_map.get(code[:3], "")  # 前缀匹配
    top50_rows.append({
        "icd_code": code,
        "count": cnt,
        "pct_of_uncl": f"{cnt/uncl_mask.sum()*100:.2f}%",
        "title": title[:80] if title else prev[:80]
    })

top50_df = pd.DataFrame(top50_rows)
top50_path = os.path.join(OUT_DIR, "unclassified_top50_icds.csv")
top50_df.to_csv(top50_path, index=False, encoding="utf-8-sig")
print(f"  Saved: {top50_path}")

print("\n  === Top 20 ICDs in Unclassified ===")
for i, row in enumerate(top50_rows[:20]):
    print(f"  {i+1:3d}. {row['icd_code']:10s}  n={row['count']:>6}  ({row['pct_of_uncl']})  {row['title'][:70]}")

# 检查消渴锚点 (E119/E11*) 和 溺毒锚点 (N179/N17*)
xiaoke_codes = [c for c in icd_counter if c.startswith("E11")]
nidu_codes = [c for c in icd_counter if c.startswith("N17") or c.startswith("N18")]
print(f"\n  === 消渴(Xiao Ke) ICD E11*: {len(xiaoke_codes)} codes, total count={sum(icd_counter[c] for c in xiaoke_codes)} ===")
for c in sorted(xiaoke_codes, key=lambda x: icd_counter[x], reverse=True)[:10]:
    print(f"    {c}: n={icd_counter[c]}  {icd_title_map.get(c, '')[:60]}")
print(f"\n  === 溺毒(Ni Du) ICD N17*/N18*: {len(nidu_codes)} codes, total count={sum(icd_counter[c] for c in nidu_codes)} ===")
for c in sorted(nidu_codes, key=lambda x: icd_counter[x], reverse=True)[:10]:
    print(f"    {c}: n={icd_counter[c]}  {icd_title_map.get(c, '')[:60]}")

# ============ 完成 ============
print("\n" + "=" * 70)
print("DONE! 全部产出:")
print(f"  {table_path}")
print(f"  {km_path}")
print(f"  {lm_path}")
print(f"  {forest_path}")
print(f"  {top50_path}")
print("=" * 70)
