"""
UK SME Loan Portfolio - Synthetic Data Generator
Produces a realistic 10,000-loan portfolio with:
 - Borrower financials (turnover, leverage, interest coverage)
 - Loan structural features (amount, term, secured/unsecured)
 - Macro overlay (BoE base rate, UK unemployment, GDP)
 - Default flag generated from a true latent PD function
"""
import numpy as np
import pandas as pd

np.random.seed(42)
N = 10000

sectors = ['Retail', 'Construction', 'Hospitality', 'Manufacturing',
           'Professional Services', 'Wholesale', 'Transport', 'Technology',
           'Real Estate', 'Healthcare']
sector_risk = {'Retail':1.4,'Construction':1.7,'Hospitality':1.8,
               'Manufacturing':1.0,'Professional Services':0.7,
               'Wholesale':1.1,'Transport':1.2,'Technology':0.8,
               'Real Estate':1.3,'Healthcare':0.6}

regions = ['London','South East','South West','East of England',
           'West Midlands','East Midlands','Yorkshire','North West',
           'North East','Scotland','Wales','Northern Ireland']
region_p = [0.18,0.13,0.08,0.09,0.10,0.08,0.09,0.10,0.04,0.07,0.03,0.01]
region_p = np.array(region_p) / np.sum(region_p)

origination_dates = pd.date_range('2021-01-01','2024-06-30',freq='D')

def gen_one(i):
    sector = np.random.choice(sectors)
    region = np.random.choice(regions, p=region_p)
    orig_date = np.random.choice(origination_dates)
    years_trading = float(np.clip(np.random.gamma(2.5, 4), 1, 60))
    turnover_gbp = float(np.exp(np.random.normal(13.8, 1.1)))
    employees = max(1, int(turnover_gbp / np.random.uniform(70000, 180000)))
    ebitda_margin = float(np.random.normal(0.10, 0.06))
    ebitda = turnover_gbp * ebitda_margin
    total_debt = turnover_gbp * float(np.clip(np.random.normal(0.35, 0.20), 0.01, 2.5))
    leverage = total_debt / max(ebitda, 1000)
    interest_coverage = ebitda / max(total_debt * 0.07, 1000)
    loan_amount = float(np.clip(np.random.lognormal(11.2, 0.9), 5000, 1500000))
    term_months = int(np.random.choice([12,24,36,48,60,72,84,120], p=[0.05,0.10,0.20,0.20,0.20,0.10,0.10,0.05]))
    secured = int(np.random.binomial(1, 0.55))
    ltv = float(np.clip(np.random.normal(0.65, 0.18), 0.10, 1.20)) if secured else np.nan
    bureau_score = int(np.clip(np.random.normal(720 - sector_risk[sector]*30, 80), 300, 999))
    dpd_buckets = [0, 5, 15, 35, 65, 95]
    dpd_probs   = [0.85, 0.05, 0.04, 0.03, 0.02, 0.01]
    days_past_due = int(np.random.choice(dpd_buckets, p=dpd_probs))
    return dict(
        loan_id=f"UKSME-{100000+i}",
        origination_date=str(pd.Timestamp(orig_date).date()),
        sector=sector, region=region,
        years_trading=round(years_trading,1),
        turnover_gbp=round(turnover_gbp,0),
        employees=employees,
        ebitda_margin=round(ebitda_margin,4),
        leverage=round(leverage,2),
        interest_coverage=round(interest_coverage,2),
        loan_amount_gbp=round(loan_amount,0),
        term_months=term_months,
        secured=secured,
        ltv=round(ltv,3) if secured else None,
        bureau_score=bureau_score,
        days_past_due=days_past_due,
    )

rows = [gen_one(i) for i in range(N)]
df = pd.DataFrame(rows)

# True latent PD (log-odds form)
z = (
    -2.4
    + 0.55 * np.log(np.clip(df['leverage'], 0.1, 30))
    - 0.40 * np.log(np.clip(df['interest_coverage'], 0.1, 30))
    - 0.0035 * (df['bureau_score'] - 700)
    + df['sector'].map(sector_risk) * 0.35
    - 0.015 * df['years_trading']
    - 0.30 * df['secured']
    + 0.020 * df['days_past_due']
    + np.random.normal(0, 0.4, N)
)
pd_true = 1 / (1 + np.exp(-z))
df['default_12m'] = np.random.binomial(1, np.clip(pd_true, 0.001, 0.9))

# LGD - secured vs unsecured
df['lgd'] = np.where(df['secured'],
                     np.clip(np.random.normal(0.25, 0.10, N), 0.05, 0.75),
                     np.clip(np.random.normal(0.65, 0.15, N), 0.20, 0.95))
df['lgd'] = df['lgd'].round(3)

# EAD = outstanding * CCF
df['ead_gbp'] = (df['loan_amount_gbp'] * np.random.uniform(0.75, 1.00, N)).round(0)

# Macro snapshot
df['boe_base_rate'] = 5.25
df['uk_unemployment_rate'] = 4.3
df['uk_gdp_yoy'] = 0.6

print(f"Generated {len(df):,} loans")
print(f"Default rate: {df['default_12m'].mean():.2%}")
print(f"Total exposure: GBP {df['ead_gbp'].sum()/1e6:,.0f}m")
print("Sector mix:")
print(df.groupby('sector')['default_12m'].agg(['count','mean']).round(3))

df.to_csv('/sessions/dreamy-vibrant-pascal/mnt/outputs/uk-sme-credit-risk/data/uk_sme_portfolio.csv', index=False)
print("\nSaved to data/uk_sme_portfolio.csv")
