"""
Python validation pipeline - mirrors the R script logic so we can
produce numeric outputs (scored portfolio, ECL summary, validation metrics)
without needing R installed in this sandbox.
"""
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.preprocessing import OneHotEncoder
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "/sessions/dreamy-vibrant-pascal/mnt/outputs/uk-sme-credit-risk/outputs"
import os; os.makedirs(OUT, exist_ok=True)

df = pd.read_csv("/sessions/dreamy-vibrant-pascal/mnt/outputs/uk-sme-credit-risk/data/uk_sme_portfolio.csv")
df['ltv'] = df['ltv'].fillna(0)

# ---- WoE / IV (manual implementation - shows we know what scorecard pkg does)
def woe_iv(x, y, bins=10):
    if x.dtype == "object" or x.nunique() <= 12:
        cats = x.astype(str)
    else:
        cats = pd.qcut(x, q=bins, duplicates="drop").astype(str)
    tbl = pd.crosstab(cats, y).rename(columns={0:"good",1:"bad"})
    tbl["good_pct"] = tbl["good"] / tbl["good"].sum()
    tbl["bad_pct"]  = tbl["bad"]  / tbl["bad"].sum()
    tbl["woe"] = np.log((tbl["bad_pct"]+1e-6) / (tbl["good_pct"]+1e-6))
    tbl["iv_bin"] = (tbl["bad_pct"] - tbl["good_pct"]) * tbl["woe"]
    return tbl, tbl["iv_bin"].sum()

candidates = ["leverage","interest_coverage","bureau_score","years_trading",
              "ltv","days_past_due","loan_amount_gbp","term_months",
              "secured","sector"]
iv_rows = []
for c in candidates:
    _, iv = woe_iv(df[c], df["default_12m"])
    iv_rows.append({"variable":c, "iv":iv,
                    "strength": ("Very Strong" if iv>0.5 else
                                 "Strong" if iv>0.3 else
                                 "Medium" if iv>0.1 else
                                 "Weak" if iv>0.02 else "Useless")})
iv_df = pd.DataFrame(iv_rows).sort_values("iv", ascending=False)
iv_df.to_csv(f"{OUT}/feature_iv.csv", index=False)
print("=== Information Values ==="); print(iv_df.to_string(index=False))

# ---- Model -------------------------------------------------------------------
X = df[candidates].copy()
X = pd.get_dummies(X, columns=["sector","secured"], drop_first=True)
y = df["default_12m"]

X_tr, X_te, y_tr, y_te, idx_tr, idx_te = train_test_split(
    X, y, df.index, test_size=0.3, random_state=42, stratify=y)

clf = LogisticRegression(max_iter=2000, C=1.0)
clf.fit(X_tr, y_tr)
df.loc[idx_tr, "pd_raw"] = clf.predict_proba(X_tr)[:,1]
df.loc[idx_te, "pd_raw"] = clf.predict_proba(X_te)[:,1]

auc_tr = roc_auc_score(y_tr, df.loc[idx_tr,"pd_raw"])
auc_te = roc_auc_score(y_te, df.loc[idx_te,"pd_raw"])
gini_te = 2*auc_te - 1
print(f"\nAUC train: {auc_tr:.4f}  AUC test: {auc_te:.4f}  Gini test: {gini_te:.4f}")

# KS
fpr,tpr,_ = roc_curve(y_te, df.loc[idx_te,"pd_raw"])
ks = (tpr - fpr).max()
print(f"KS statistic (test): {ks:.4f}")

# Calibrate to long-run average default rate
long_run_dr = y.mean()
df["pd_calibrated"] = df["pd_raw"] * (long_run_dr / df["pd_raw"].mean())
df["pd_calibrated"] = df["pd_calibrated"].clip(0.001, 0.999)

# ---- IFRS 9 Staging ----------------------------------------------------------
def stage(row):
    if row["days_past_due"] >= 90 or row["default_12m"] == 1:
        return "Stage 3"
    if row["days_past_due"] >= 30 or row["pd_calibrated"] > 0.15:
        return "Stage 2"
    return "Stage 1"
df["stage"] = df.apply(stage, axis=1)

df["ecl_horizon_m"] = np.where(df["stage"]=="Stage 1", 12,
                       np.minimum(df["term_months"], 60))
df["pd_lifetime"] = 1 - (1 - df["pd_calibrated"])**(df["ecl_horizon_m"]/12)
df["pd_for_ecl"] = np.where(df["stage"]=="Stage 1", df["pd_calibrated"], df["pd_lifetime"])

# ---- ECL with 3-scenario macro overlay ---------------------------------------
scenarios = [
    ("Upside",  0.20, 0.85, 0.95),
    ("Base",    0.55, 1.00, 1.00),
    ("Downside",0.25, 1.45, 1.20),
]
df["ecl"] = 0.0
scn_ecl = {}
for name, w, pdm, lgm in scenarios:
    pd_s  = np.minimum(df["pd_for_ecl"] * pdm, 1)
    lgd_s = np.minimum(df["lgd"] * lgm, 1)
    ecl_s = pd_s * lgd_s * df["ead_gbp"]
    df["ecl"] += w * ecl_s
    scn_ecl[name] = ecl_s.sum()/1e6

print("\n=== ECL by scenario (GBP m) ===")
for n,v in scn_ecl.items(): print(f"  {n:9s}: {v:8.2f}")

stage_smry = df.groupby("stage").agg(
    loans=("loan_id","count"),
    ead_gbp_m=("ead_gbp", lambda x: x.sum()/1e6),
    ecl_gbp_m=("ecl",     lambda x: x.sum()/1e6)
).assign(coverage_pct=lambda d: 100*d.ecl_gbp_m/d.ead_gbp_m).round(2)
print("\n=== IFRS 9 Stage summary ===")
print(stage_smry)

total_ecl = df["ecl"].sum()/1e6
total_ead = df["ead_gbp"].sum()/1e6
print(f"\nTotal EAD: GBP {total_ead:,.1f}m | Total ECL: GBP {total_ecl:,.2f}m | Coverage: {100*total_ecl/total_ead:.2f}%")

# ---- Sector view -------------------------------------------------------------
sector_view = df.groupby("sector").agg(
    loans=("loan_id","count"),
    avg_pd=("pd_calibrated","mean"),
    default_rate=("default_12m","mean"),
    ead_gbp_m=("ead_gbp", lambda x: x.sum()/1e6),
    ecl_gbp_m=("ecl",     lambda x: x.sum()/1e6),
).round(4).sort_values("ecl_gbp_m", ascending=False)
sector_view["coverage_pct"] = (100*sector_view.ecl_gbp_m/sector_view.ead_gbp_m).round(2)
print("\n=== Sector view (top contributors) ===")
print(sector_view)

# ---- Write outputs -----------------------------------------------------------
df.to_csv(f"{OUT}/scored_portfolio.csv", index=False)
stage_smry.to_csv(f"{OUT}/ecl_summary_by_stage.csv")
sector_view.to_csv(f"{OUT}/ecl_summary_by_sector.csv")

pd.DataFrame({
    "metric":["AUC_train","AUC_test","Gini_test","KS_test",
              "Long_run_default_rate","Total_EAD_GBPm","Total_ECL_GBPm","Coverage_pct"],
    "value":[auc_tr, auc_te, gini_te, ks,
             long_run_dr, total_ead, total_ecl, 100*total_ecl/total_ead]
}).round(4).to_csv(f"{OUT}/model_validation.csv", index=False)

# ---- Charts ------------------------------------------------------------------
plt.figure(figsize=(7,5))
fpr,tpr,_ = roc_curve(y_te, df.loc[idx_te,"pd_raw"])
plt.plot(fpr,tpr,linewidth=2,label=f"Test AUC = {auc_te:.3f}")
plt.plot([0,1],[0,1],"k--",alpha=0.4)
plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
plt.title("PD Model ROC Curve - UK SME Portfolio"); plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_roc.png", dpi=110); plt.close()

plt.figure(figsize=(8,5))
df.boxplot(column="pd_calibrated", by="default_12m")
plt.suptitle(""); plt.title("PD distribution: Defaulters vs Non-defaulters")
plt.xlabel("Default (1) vs Non-default (0)"); plt.ylabel("Calibrated PD")
plt.tight_layout(); plt.savefig(f"{OUT}/chart_pd_box.png", dpi=110); plt.close()

plt.figure(figsize=(9,5))
sv = sector_view.sort_values("coverage_pct", ascending=True)
plt.barh(sv.index, sv["coverage_pct"], color="#1f4e79")
plt.xlabel("ECL coverage ratio (%)"); plt.title("ECL Coverage by Sector")
plt.tight_layout(); plt.savefig(f"{OUT}/chart_sector_coverage.png", dpi=110); plt.close()

stage_smry2 = stage_smry.reset_index()
plt.figure(figsize=(8,5))
plt.bar(stage_smry2["stage"], stage_smry2["ecl_gbp_m"], color=["#2e7d32","#f9a825","#c62828"])
for i,v in enumerate(stage_smry2["ecl_gbp_m"]):
    plt.text(i, v+0.3, f"GBP {v:.1f}m", ha="center", fontweight="bold")
plt.ylabel("ECL (GBP m)"); plt.title("ECL by IFRS 9 Stage")
plt.tight_layout(); plt.savefig(f"{OUT}/chart_ecl_by_stage.png", dpi=110); plt.close()

print(f"\n[OK] All outputs written to {OUT}")
