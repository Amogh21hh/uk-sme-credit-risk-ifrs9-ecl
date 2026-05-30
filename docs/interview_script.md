# Interview Script — UK SME Credit Risk & IFRS 9 ECL Project

## How to use this document

1. **Memorise the 90-second pitch.** Word for word. You'll use it in every interview, networking call, and HireVue.
2. **Drill the deep-dive answers.** Out loud, in front of a mirror or recording yourself.
3. **Anticipate the technical follow-ups** — they're listed below with model answers.
4. **Tie everything back to the role.** Always end an answer with one sentence linking it to what *they* need.

---

## A. The 90-second pitch (memorise this)

> "One of my recent projects was building an IFRS 9 expected credit loss model on a 10,000-loan UK SME portfolio. The context was that every UK bank has to calculate ECL under IFRS 9 — PD × LGD × EAD with a forward-looking macro overlay — and I wanted to demonstrate I can actually do that work, not just describe it.
>
> I generated a realistic UK SME book with sector, region, leverage, interest coverage and bureau-style scores, then trained a logistic regression PD model with WoE binning and Information Value screening — that's the industry-standard scorecard approach. The model came in at AUC 0.77, Gini 0.54 and a KS of 0.42, which is in the 'good model' range for SME credit.
>
> I then layered IFRS 9 staging on top — Stage 1 / 2 / 3 with SICR triggers — and ran ECL across Upside, Base and Downside scenarios with a 20 / 55 / 25 weighting, which is what the big UK banks use. The final book came out at about GBP 204 million ECL on GBP 973 million EAD, around 21% coverage.
>
> The whole thing is in R and Excel, with a one-page HTML dashboard for non-technical stakeholders. What I learned was as much about the regulatory framing — SICR, lifetime versus 12-month ECL, forward-looking adjustment — as it was about the modelling. That's the gap I wanted to close before applying for credit risk roles in London."

**Timing:** Practice until this runs in 80–95 seconds. Do not exceed 100 seconds.

---

## B. Deep-dive technical Q&A

### Q1: "Walk me through how you built the PD model."

> "I started with feature engineering — leverage, interest coverage, bureau score, sector, DPD, secured flag, years trading. Then I ran a WoE / IV screen to identify variables with strong predictive power; leverage and interest coverage had IVs above 0.5 — very strong — while bureau score and DPD were in the medium range. I dropped variables with IV below 0.02.
>
> Then I WoE-transformed the features and fit a logistic regression. The reason for WoE rather than raw values is two-fold: it handles non-linearity, and it gives you a stable, interpretable scorecard — important for model risk and regulatory submissions. I split 70/30 stratified on the default flag, calibrated the model output to the long-run default rate, and validated using AUC, Gini, KS and PSI between train and test."

### Q2: "Why logistic regression and not XGBoost or a neural net?"

> "Three reasons. First, interpretability — every coefficient maps back to a feature with a known direction, which is what model validation teams and the PRA expect for regulatory models. Second, stability — logistic regression is far more stable across populations than tree ensembles, which matters when you're predicting on next quarter's loan book. Third, regulatory norm — IRB and IFRS 9 PD models at most UK banks are still logistic regression for these exact reasons. That said, I would use XGBoost or a gradient-boosted model as a challenger model to benchmark the logistic, which is exactly what model risk teams do in practice."

### Q3: "How did you handle IFRS 9 staging?"

> "Three stages. Stage 1 is performing — no significant increase in credit risk — and you book a 12-month ECL. Stage 2 is when you've had a significant increase in credit risk, the SICR trigger; my proxies were PD greater than 15% or DPD of 30 or more. Stage 2 moves you to lifetime ECL. Stage 3 is credit-impaired, which I triggered at DPD 90 or the default flag, and that's also lifetime ECL.
>
> For the lifetime PD, I used the standard approximation: 1 minus (1 minus 12-month PD) to the power of horizon over 12. In production you'd use a more sophisticated term structure model, but for an SME book this is acceptable and what's used in some satellite models."

### Q4: "Explain the forward-looking macro overlay."

> "IFRS 9 explicitly requires forward-looking information — you can't just use historical PDs. The standard approach is to define three macro scenarios — Upside, Base, Downside — assign probability weights, and run ECL under each. The final ECL is the probability-weighted sum.
>
> I used 20 / 55 / 25 weights, which is roughly what Lloyds and Barclays disclose. The Downside scenario applies a 1.45× PD multiplier and 1.2× LGD multiplier, reflecting higher default rates and lower recoveries under stress. The result is a single ECL number that's higher than the Base case alone, which is the conservatism IFRS 9 is designed to deliver."

### Q5: "What's the difference between expected credit loss and unexpected loss?"

> "Expected credit loss is the mean loss — what you provision for on the balance sheet under IFRS 9. Unexpected loss is the volatility around that mean — what you hold capital for under the Basel framework. ECL goes through P&L; UL drives risk-weighted assets and capital requirements. The same PD and LGD inputs feed both, but the regulatory architecture is completely separate — IFRS 9 is accounting, Basel is prudential."

### Q6: "How would you validate this model in a production setting?"

> "Four buckets. First, discrimination — AUC, Gini, KS, on out-of-time data not just out-of-sample. Second, calibration — actual vs predicted default rates across PD buckets, with Hosmer-Lemeshow. Third, stability — PSI on the input features and on the predicted PD distribution; you want PSI under 0.1, definitely under 0.25. Fourth, qualitative — sense-checks on coefficient signs, conceptual soundness, sector-level back-testing. Model risk teams typically have a documented validation framework — something like SS3/18 — and you'd produce a validation report annually."

### Q7: "What were the limitations?"

> "Three honest ones. One, synthetic data — a real UK SME book has fatter tails and more sector concentration, particularly in hospitality and retail post-Covid. Two, my LGD is a static distribution; in production you'd build a downturn LGD model with collateral-specific recovery rates. Three, my macro overlay is judgement-based on the multipliers; the next iteration would regress PD directly on BoE unemployment and GDP forecasts so the overlay is fully data-driven."

---

## C. Likely follow-up questions

| Question | Sharp answer |
|---|---|
| "Why this project?" | "Because every UK bank is hiring for IFRS 9 work, and I wanted hands-on proof I can do PD modelling and the regulatory framing — not just describe it." |
| "What's PD floor?" | "Regulatory minimum applied to your PD estimates — typically 3 basis points under IRB — to prevent models from understating risk." |
| "What's a Stage 2 backstop?" | "A presumption-based trigger — typically 30 days past due — that forces a loan into Stage 2 regardless of your PD model output." |
| "What's the difference between PIT and TTC PD?" | "Point-in-time reflects current economic conditions and is volatile; through-the-cycle is averaged over a full cycle and is used for capital. IFRS 9 wants PIT or PIT-adjusted PDs." |
| "What's LGD floor?" | "EBA sets minimum LGDs for certain exposure classes — 10% for residential mortgages, for example — to prevent banks from under-provisioning." |
| "How would you stress-test this portfolio?" | "Apply the BoE annual stress test macro scenario — typically unemployment to 8%+, GDP contraction, house price falls — flex the PD and LGD multipliers accordingly, and report the change in ECL and capital." |
| "What's the link to capital?" | "ECL provisions reduce CET1 capital. Under IFRS 9 transitional rules, banks were allowed to phase in the day-one ECL hit. The ongoing ECL volatility flows through P&L and equity." |

---

## D. Behavioural integration

When asked **"tell me about a project you're proud of"** or **"give me an example of when you learned something complex independently"**, use this project. Frame it as:

> "I knew credit risk was the area I wanted to break into, but my exposure was academic. So I taught myself the IFRS 9 framework from the standard itself and the PRA supervisory statements, built the model end-to-end in R, and packaged it so a hiring manager could see exactly what I can do. The skill that mattered most wasn't the modelling — it was structuring an ambiguous regulatory problem into something measurable."

---

## E. Cold email / outreach hook

When messaging credit risk people on LinkedIn:

> *"Hi [Name] — I'm finishing my MSc Business Analytics at Essex and recently built an IFRS 9 ECL model on a synthetic UK SME book (PD/LGD/EAD with 3-scenario overlay) to deepen my credit risk fundamentals. AUC came in at 0.77 with a 21% coverage ratio. Would value 15 minutes of your time to ask how someone with my profile — strong analytics, MBA in finance, no UK banking experience yet — typically breaks into credit risk in London. Happy to share the project if useful."*

This works because (a) it's specific, (b) you've done the work, (c) you're asking for advice not a job, (d) you're offering something concrete (the project).
