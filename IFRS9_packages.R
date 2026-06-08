# Run this once before executing R/01_credit_risk_ifrs9_model.R
install.packages(c(
  "scorecard",   # IV / WoE binning
  "glmnet",      # regularised logistic
  "pROC",        # AUC / ROC
  "dplyr",
  "tidyr",
  "readr",
  "ggplot2",
  "lubridate"
))
