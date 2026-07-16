# Olist — Revenue & Retention Analytics Dashboard

**Interactive SQL + Streamlit dashboard analyzing 97K+ orders from Olist, a Brazilian e-commerce marketplace, to uncover revenue concentration, retention patterns, and a data-backed reactivation opportunity.**

🔗 **Live app:** [olist-revenue-retention.streamlit.app](https://olist-revenue-retention.streamlit.app/)
📊 **Dataset:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle)

![Dashboard preview](assets/dashboard-preview.png)

---

## The business question

Olist is a multi-vendor marketplace. Marketplaces face a structural growth question: **do you win by retaining existing customers, or by acquiring new ones?** This project answers that with data — segmenting customers by value and behavior, quantifying how much revenue is concentrated in a small group of buyers, and modeling a specific, costed intervention rather than just reporting metrics.

## Headline finding

> **The "At Risk" customer segment (23,082 customers, ~412 days since last purchase) accounts for R$6.17M — 39.6% of total historical revenue.** A targeted reactivation campaign, modeled at a conservative 5% win-back rate, projects ~R$308K in recovered revenue against an estimated R$31K campaign cost — an estimated ROI of ~900%. *(Reactivation rate and cost ratio are illustrative assumptions used to demonstrate the framework, not historical/backtested figures.)*

## Key insights

| Area | Finding |
|---|---|
| **Retention** | Cohort retention collapses to ~3% after month 0 — Olist behaves like a low-repeat marketplace. Growth is driven by new customer acquisition, not repeat purchasing. |
| **Revenue concentration** | The top revenue decile (9,444 customers) drives **38.25%** of all revenue (avg LTV: R$632/customer) — high concentration means high exposure to churn in a small group. |
| **Seasonality** | Sharp revenue spike in Nov 2017 (Black Friday) — signals a need for Q4 fulfillment and inventory planning starting in September. |
| **RFM segmentation** | 7 behavioral segments identified; "At Risk" is both the largest revenue pool *and* the most actionable — unlike "Lost" customers, they have high historical value and a real chance of reactivation. |

## How it was built

Rather than pulling data into pandas and doing everything in Python, the analysis is done **in SQL** (window functions, CTEs) against a local SQLite database, then visualized in Streamlit. This mirrors how analytics is actually done in most companies — SQL for the heavy lifting, a BI/app layer for delivery.

- **Cohort retention** — customers grouped by first-purchase month, tracked against monthly repeat activity
- **Customer LTV deciles** — `NTILE(10)` + `RANK()` to rank customers by lifetime spend and measure revenue concentration
- **Month-over-month revenue** — `LAG()` window function for growth-rate and revenue-per-customer trends
- **RFM segmentation** — Recency/Frequency/Monetary scoring (`NTILE(4)`) with rule-based segment labeling (Champions, Loyal, At Risk, Lost, etc.)

## Tech stack

`Python` · `SQLite` · `SQL (window functions, CTEs)` · `Pandas` · `Streamlit` · `Plotly`

## Project structure

```
├── dashboard.py         # Streamlit app: SQL queries, data loading, chart rendering
├── olist.db              # SQLite database (Olist public dataset, pre-loaded)
├── requirements.txt       # Python dependencies
└── README.md
```

## Run it locally

```bash
git clone https://github.com/utkarshizm/olist-revenue-retention.git
cd olist-revenue-retention
pip install -r requirements.txt
streamlit run dashboard.py
```

## What I'd extend next

- Statistical validation of the 5% reactivation assumption using a holdout/A-B framework instead of a flat estimate
- Add a "predicted CLV" model (e.g., BG/NBD) instead of relying on historical LTV alone
- Break out retention and revenue concentration by `customer_state` to see if the At-Risk pattern is uniform across Brazil or regionally concentrated

---

**Author:** Utkarsh Pandey — [LinkedIn](https://linkedin.com/in/utkarsh-pandey-076286298) · [GitHub](https://github.com/utkarshizm)
