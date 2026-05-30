# UK SME Credit Risk Scorecard & IFRS 9 Expected Credit Loss (ECL) Model

> An end-to-end credit risk modelling pipeline on a 10,000-loan UK SME portfolio, producing PRA-aligned IFRS 9 expected credit loss estimates with a 3-scenario forward-looking macro overlay.

**Author:** Amogh H. H. — MSc Business Analytics (University of Essex) · MBA Finance & Marketing
**Target roles:** Credit Risk Analyst · IFRS 9 Analyst · Financial Analyst · Model Risk Analyst · Risk & Reporting Analyst (UK banking & financial services)

---

## 1. Why this project

UK banks (Lloyds, Barclays, HSBC, NatWest, Santander, Nationwide) and Big-4 risk advisory teams (KPMG, PwC, Deloitte, EY) all run sizeable IFRS 9 ECL programmes. Entry-level Credit Risk Analyst and IFRS 9 Analyst roles routinely list:

- **PD / LGD / EAD modelling** (PRA SS3/17, EBA IRB guidance)
- **IFRS 9 staging logic** (Stage 1 / 2 / 3, SICR triggers)
- **Forward-looking macro overlays** (probability-weighted scenarios)
- **Model validation** (AUC, Gini, KS, PSI, Hosmer–Lemeshow)
- **Excel, R, SQL, Power BI**

This project demonstrates competence in every one of those areas on a UK-contextualised dataset.

---

## 2. Methodology

### 2.1 Data
- **10,000 synthetic UK SME loans** across 10 sectors and all 12 UK regions
- Borrower-level features: turnover, leverage, interest coverage, sector, years trading
- Loan-level features: amount, term, secured/unsecured, LTV, days past due
- Bureau-style credit score (Experian-equivalent range 300–999)
- Macro snapshot: BoE base rate, UK unemployment, GDP YoY

### 2.2 PD model
- Train/test split 70/30, stratified on default flag
- **WoE binning + Information Value screening** (industry-standard scorecard prep)
- **Logistic regression** on WoE-transformed features
- Calibrated to the long-run portfolio default rate

### 2.3 LGD & EAD
- **LGD:** Beta-distributed by collateral status (secured ≈ 25%, unsecured ≈ 65%)
- **EAD:** Outstanding × Credit Conversion Factor (75–100%)

### 2.4 IFRS 9 staging
| Stage | Trigger | ECL horizon |
|---|---|---|
| Stage 1 | Performing, no SICR | 12-month ECL |
| Stage 2 | SICR – PD > 15% **or** DPD ≥ 30 | Lifetime ECL |
| Stage 3 | Credit-impaired – DPD ≥ 90 **or** default | Lifetime ECL |

### 2.5 Forward-looking macro overlay
| Scenario | Weight | PD multiplier | LGD multiplier |
|---|---|---|---|
| Upside | 20% | 0.85× | 0.95× |
| Base | 55% | 1.00× | 1.00× |
| Downside | 25% | 1.45× | 1.20× |

**ECL = Σ wᵢ · PDᵢ · LGDᵢ · EAD** — the IFRS 9 reported figure.

---

## 3. Headline results

| Metric | Value |
|---|---|
| Portfolio EAD | **GBP 973.4m** |
| Weighted ECL | **GBP 203.6m** |
| Coverage ratio | **20.92%** |
| AUC (test) | **0.770** |
| Gini | **0.539** |
| KS statistic | **0.418** |
| Stage 1 coverage | 3.91% |
| Stage 2 coverage | 29.55% |
| Stage 3 coverage | 31.47% |

**Top risk sectors by ECL contribution:** Retail, Hospitality, Transport, Real Estate (coverage 21–23%) — consistent with post-pandemic UK SME stress observed in PRA and UK Finance reporting.

---

## 4. Repository structure

```
uk-sme-credit-risk/
├── data/
│   ├── generate_data.py             # Synthetic UK SME loan generator
│   └── uk_sme_portfolio.csv         # 10,000-loan portfolio
├── R/
│   ├── 01_credit_risk_ifrs9_model.R # Primary R deliverable (171 lines)
│   └── _validate_python.py          # Python parity check / output generator
├── excel/
│   └── UK_SME_ECL_Model.xlsx        # 5-tab interactive ECL workbook (7,076 formulas, zero errors)
├── dashboard/
│   └── dashboard.html               # Single-file interactive dashboard (Chart.js)
├── outputs/
│   ├── scored_portfolio.csv         # Loan-level PD, stage, ECL
│   ├── ecl_summary_by_stage.csv
│   ├── ecl_summary_by_sector.csv
│   ├── model_validation.csv         # AUC, Gini, KS, coverage
│   ├── feature_iv.csv               # Information values
│   └── chart_*.png                  # ROC, PD box, sector, stage charts
└── docs/
    ├── cv_bullets.md                # CV-ready bullet points
    ├── interview_script.md          # 90-second pitch + deep-dive Q&A
    └── uk_keyword_pack.md           # ATS keywords for UK finance roles
```

---

## 5. How to run

### R model (recommended deliverable)
```r
setwd("R")
source("01_credit_risk_ifrs9_model.R")
```
Required packages: `tidyverse`, `glmnet`, `pROC`, `scorecard`, `caret`, `broom`, `janitor`, `scales`.

### Excel model
Open `excel/UK_SME_ECL_Model.xlsx`. Edit any blue input cell on the **Cover & Assumptions** tab (scenario weights, SICR threshold, multipliers) and the entire ECL recalculates live.

### Dashboard
Open `dashboard/dashboard.html` in any browser — no server required.

### Regenerate data
```bash
python3 data/generate_data.py
```

---

## 6. Tech stack

**R:** tidyverse · glmnet · pROC · scorecard · caret · ggplot2
**Python (validation):** pandas · scikit-learn · matplotlib · openpyxl
**Excel:** structured 5-tab model with `SUMIF`, `COUNTIF`, scenario-driven recalculation, conditional formatting, named ranges
**Dashboard:** HTML + Chart.js
**Standards referenced:** IFRS 9 (paragraphs 5.5), PRA SS3/17, EBA IRB guidelines

---

## 7. Limitations & next steps

- Synthetic data – real UK SME portfolios show fatter tails (long-tailed leverage, sector concentration)
- Single point-in-time PD – production models use through-the-cycle (TTC) and point-in-time (PIT) conversion
- LGD modelled as static distribution – a downturn LGD model would improve regulatory alignment
- Macro overlay is judgement-based – next iteration could regress PD on BoE unemployment forecasts directly

---

## 8. Contact

**Amogh H. H.** · MSc Business Analytics, University of Essex
amoghmallikarjun0321@gmail.com · [LinkedIn](https://linkedin.com/in/amogh-hh-34129a1b9) · [Portfolio](https://amogh-h-h-portfolio.vercel.app)

Open to entry-level / graduate roles in **Credit Risk, IFRS 9, Financial Analytics, and Model Risk** across London and the wider UK market.

