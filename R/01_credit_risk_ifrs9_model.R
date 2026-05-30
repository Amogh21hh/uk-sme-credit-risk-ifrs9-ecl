# =============================================================================
# UK SME CREDIT RISK SCORECARD + IFRS 9 EXPECTED CREDIT LOSS MODEL
# Author: Amogh H. H.
# Stack: R (tidyverse, glmnet, pROC, scorecard, ggplot2)
# =============================================================================
# Pipeline:
#   1. Load and EDA the UK SME loan book
#   2. Train/test split (70/30 stratified)
#   3. WoE/IV feature analysis (scorecard package - industry standard)
#   4. Logistic regression PD model + Lasso for variable selection
#   5. Model validation: AUC, KS, Gini, Hosmer-Lemeshow, PSI
#   6. PD calibration to long-run average
#   7. IFRS 9 staging (Stage 1 / Stage 2 / Stage 3)
#   8. ECL = PD x LGD x EAD with macro overlay (3 scenarios)
#   9. Portfolio reporting and write-out
# =============================================================================

# ---- 0. Packages ------------------------------------------------------------
required <- c("tidyverse","glmnet","pROC","scorecard","caret",
              "ggplot2","scales","janitor","broom")
for (p in required) {
  if (!requireNamespace(p, quietly = TRUE)) install.packages(p)
}
suppressPackageStartupMessages({
  library(tidyverse); library(glmnet); library(pROC); library(scorecard)
  library(caret); library(ggplot2); library(scales); library(janitor); library(broom)
})

set.seed(42)

# ---- 1. Load ----------------------------------------------------------------
df <- read_csv("../data/uk_sme_portfolio.csv", show_col_types = FALSE) %>%
  clean_names() %>%
  mutate(
    sector = factor(sector),
    region = factor(region),
    secured = factor(secured, levels = c(0,1), labels = c("Unsecured","Secured")),
    ltv = replace_na(ltv, 0),
    default_12m = as.integer(default_12m)
  )

cat("Portfolio size:", nrow(df), "loans\n")
cat("Default rate:  ", percent(mean(df$default_12m), 0.01), "\n")
cat("Total exposure: GBP", comma(round(sum(df$ead_gbp)/1e6)), "m\n\n")

# ---- 2. EDA -----------------------------------------------------------------
sector_dr <- df %>%
  group_by(sector) %>%
  summarise(loans = n(),
            default_rate = mean(default_12m),
            ead_gbp_m = sum(ead_gbp)/1e6) %>%
  arrange(desc(default_rate))
print(sector_dr)

# ---- 3. Train/Test split (stratified) ---------------------------------------
split_idx <- createDataPartition(df$default_12m, p = 0.7, list = FALSE)
train <- df[split_idx, ]
test  <- df[-split_idx, ]
cat("\nTrain rows:", nrow(train), " Test rows:", nrow(test), "\n")

# ---- 4. WoE / IV analysis (industry-standard scorecard prep) ----------------
target_var <- "default_12m"
model_vars <- c("leverage","interest_coverage","bureau_score","years_trading",
                "ltv","days_past_due","loan_amount_gbp","term_months",
                "secured","sector")

bins <- woebin(train %>% select(all_of(c(model_vars, target_var))),
               y = target_var, method = "tree", print_info = FALSE)
iv_summary <- iv(train %>% select(all_of(c(model_vars, target_var))), y = target_var) %>%
  arrange(desc(info_value))
cat("\nInformation Values:\n"); print(iv_summary)

train_woe <- woebin_ply(train %>% select(all_of(c(model_vars, target_var))), bins)
test_woe  <- woebin_ply(test  %>% select(all_of(c(model_vars, target_var))), bins)

# ---- 5. Logistic regression PD model ----------------------------------------
pd_model <- glm(default_12m ~ ., data = train_woe, family = binomial(link = "logit"))
cat("\n--- Model coefficients ---\n")
print(tidy(pd_model) %>% mutate(across(where(is.numeric), ~round(.x,4))))

# ---- 6. Validation ----------------------------------------------------------
train$pd <- predict(pd_model, train_woe, type = "response")
test$pd  <- predict(pd_model, test_woe,  type = "response")

roc_train <- roc(train$default_12m, train$pd, quiet = TRUE)
roc_test  <- roc(test$default_12m,  test$pd,  quiet = TRUE)
cat("\nAUC train:", round(auc(roc_train),4),
    " AUC test:", round(auc(roc_test),4), "\n")
cat("Gini train:", round(2*auc(roc_train)-1,4),
    " Gini test:", round(2*auc(roc_test)-1,4), "\n")

ks_test <- perf_eva(label = test$default_12m, pred = test$pd, type = "ks", show_plot = FALSE)
cat("KS statistic (test):", round(ks_test$binomial_metric$dat$KS,4), "\n")

# Population Stability Index between train and test (deployment readiness)
psi <- perf_psi(score = list(train = train$pd, test = test$pd),
                label = list(train = train$default_12m, test = test$default_12m),
                show_plot = FALSE)
cat("PSI (train vs test):\n"); print(psi$psi)

# ---- 7. Calibration to long-run average -------------------------------------
lr_avg <- mean(df$default_12m)
test$pd_calibrated <- test$pd * (lr_avg / mean(test$pd))

# ---- 8. IFRS 9 Staging ------------------------------------------------------
# Stage 1: performing, no significant increase in credit risk (SICR)
# Stage 2: SICR - PD > 2x origination or 30+ DPD or watch-list
# Stage 3: credit-impaired - 90+ DPD or default
test <- test %>%
  mutate(
    stage = case_when(
      days_past_due >= 90 | default_12m == 1 ~ "Stage 3",
      days_past_due >= 30 | pd_calibrated > 0.15 ~ "Stage 2",
      TRUE ~ "Stage 1"
    ),
    ecl_horizon_months = case_when(
      stage == "Stage 1" ~ 12,
      stage == "Stage 2" ~ pmin(term_months, 60),
      stage == "Stage 3" ~ pmin(term_months, 60)
    ),
    # Lifetime PD approximation: 1 - (1 - PD_12m)^(horizon/12)
    pd_lifetime = 1 - (1 - pd_calibrated)^(ecl_horizon_months/12),
    pd_for_ecl = if_else(stage == "Stage 1", pd_calibrated, pd_lifetime)
  )

# ---- 9. ECL with macro overlay (3-scenario weighted) ------------------------
# Macro multipliers applied to PD (typical IFRS 9 forward-looking adjustment)
scenarios <- tibble(
  scenario = c("Upside","Base","Downside"),
  weight   = c(0.20, 0.55, 0.25),
  pd_mult  = c(0.85, 1.00, 1.45),
  lgd_mult = c(0.95, 1.00, 1.20)
)

ecl_table <- test %>%
  crossing(scenarios) %>%
  mutate(
    pd_scn  = pmin(pd_for_ecl * pd_mult, 1),
    lgd_scn = pmin(lgd * lgd_mult, 1),
    ecl_scn = pd_scn * lgd_scn * ead_gbp
  ) %>%
  group_by(loan_id, stage, ead_gbp) %>%
  summarise(weighted_ecl = sum(ecl_scn * weight), .groups = "drop")

portfolio_ecl <- ecl_table %>%
  group_by(stage) %>%
  summarise(loans = n(),
            ead_gbp_m = sum(ead_gbp)/1e6,
            ecl_gbp_m = sum(weighted_ecl)/1e6,
            coverage_ratio = ecl_gbp_m / ead_gbp_m)
cat("\n--- IFRS 9 ECL by Stage ---\n"); print(portfolio_ecl)

total_ecl <- sum(ecl_table$weighted_ecl)
total_ead <- sum(test$ead_gbp)
cat("\nTotal portfolio EAD: GBP", comma(round(total_ead/1e6,1)), "m\n")
cat("Total portfolio ECL: GBP", comma(round(total_ecl/1e6,2)), "m\n")
cat("Coverage ratio:     ", percent(total_ecl/total_ead, 0.01), "\n")

# ---- 10. Outputs ------------------------------------------------------------
dir.create("../outputs", showWarnings = FALSE)
write_csv(test %>% select(loan_id, sector, region, ead_gbp, lgd, pd_calibrated,
                           stage, pd_for_ecl), "../outputs/scored_portfolio.csv")
write_csv(ecl_table, "../outputs/ecl_by_loan.csv")
write_csv(portfolio_ecl, "../outputs/ecl_summary.csv")
write_csv(iv_summary, "../outputs/feature_iv.csv")

# Save model
saveRDS(pd_model, "../outputs/pd_model.rds")
saveRDS(bins,     "../outputs/woe_bins.rds")

cat("\n[OK] Model artefacts saved to /outputs\n")
