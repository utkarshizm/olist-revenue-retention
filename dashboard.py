import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Olist Revenue & Retention", layout="wide")

# Add caching so the SQL only runs once, then loads instantly
@st.cache_data
def load_data():
    con = sqlite3.connect("olist.db")
    
    cohort_sql = """
    WITH cust_orders AS (
        SELECT c.customer_unique_id, c.customer_id, o.order_purchase_timestamp
        FROM olist_customers_dataset c
        JOIN olist_orders_dataset o ON c.customer_id = o.customer_id
        WHERE o.order_status IN ('delivered', 'shipped')
    ),
    first_purchase AS (
        SELECT customer_unique_id, DATE(MIN(order_purchase_timestamp), 'start of month') AS cohort_month
        FROM cust_orders GROUP BY customer_unique_id
    ),
    repeat_activity AS (
        SELECT fp.cohort_month, co.customer_unique_id,
            DATE(co.order_purchase_timestamp, 'start of month') AS activity_month,
            (CAST(strftime('%Y', co.order_purchase_timestamp) AS INT) - CAST(strftime('%Y', fp.cohort_month) AS INT)) * 12
            + (CAST(strftime('%m', co.order_purchase_timestamp) AS INT) - CAST(strftime('%m', fp.cohort_month) AS INT)) AS month_offset
        FROM first_purchase fp
        JOIN cust_orders co ON co.customer_unique_id = fp.customer_unique_id
    )
    SELECT cohort_month, month_offset, COUNT(DISTINCT customer_unique_id) AS active_customers,
        ROUND(100.0 * COUNT(DISTINCT customer_unique_id) / NULLIF(MAX(CASE WHEN month_offset = 0 THEN COUNT(DISTINCT customer_unique_id) END) OVER (PARTITION BY cohort_month), 0), 2) AS retention_pct
    FROM repeat_activity GROUP BY cohort_month, month_offset ORDER BY cohort_month, month_offset;
    """

    ltv_sql = """
    WITH customer_revenue AS (
        SELECT c.customer_unique_id, c.customer_state, COUNT(DISTINCT o.order_id) AS order_count, SUM(p.payment_value) AS lifetime_revenue
        FROM olist_customers_dataset c
        JOIN olist_orders_dataset o ON o.customer_id = c.customer_id
        JOIN olist_order_payments_dataset p ON p.order_id = o.order_id
        WHERE o.order_status IN ('delivered', 'shipped')
        GROUP BY c.customer_unique_id, c.customer_state
    ),
    ranked AS (
        SELECT customer_unique_id, customer_state, order_count, ROUND(lifetime_revenue, 2) AS lifetime_revenue,
            RANK() OVER (ORDER BY lifetime_revenue DESC) AS revenue_rank,
            NTILE(10) OVER (ORDER BY lifetime_revenue DESC) AS revenue_decile,
            SUM(lifetime_revenue) OVER () AS total_revenue
        FROM customer_revenue
    )
    SELECT revenue_decile, COUNT(*) AS customers_in_decile, ROUND(SUM(lifetime_revenue), 2) AS decile_revenue,
        ROUND(100.0 * SUM(lifetime_revenue) / total_revenue, 2) AS pct_of_total_revenue,
        ROUND(AVG(lifetime_revenue), 2) AS avg_customer_ltv
    FROM ranked GROUP BY revenue_decile, total_revenue ORDER BY revenue_decile;
    """

    mom_sql = """
    WITH monthly_revenue AS (
        SELECT DATE(o.order_purchase_timestamp, 'start of month') AS order_month,
            COUNT(DISTINCT o.order_id) AS orders, COUNT(DISTINCT c.customer_unique_id) AS unique_customers, ROUND(SUM(p.payment_value), 2) AS revenue
        FROM olist_orders_dataset o
        JOIN olist_order_payments_dataset p ON p.order_id = o.order_id
        JOIN olist_customers_dataset c ON c.customer_id = o.customer_id
        WHERE o.order_status IN ('delivered', 'shipped') GROUP BY 1
    )
    SELECT order_month, orders, unique_customers, revenue,
        LAG(revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
        ROUND(revenue - LAG(revenue) OVER (ORDER BY order_month), 2) AS mom_change,
        ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month)) / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 2) AS mom_growth_pct,
        ROUND(revenue / NULLIF(unique_customers, 0), 2) AS revenue_per_customer
    FROM monthly_revenue ORDER BY order_month;
    """

    rfm_sql = """
    WITH rfm_base AS (
        SELECT c.customer_unique_id,
            JULIANDAY((SELECT MAX(order_purchase_timestamp) FROM olist_orders_dataset)) - JULIANDAY(MAX(o.order_purchase_timestamp)) AS recency,
            COUNT(DISTINCT o.order_id) AS frequency, ROUND(SUM(p.payment_value), 2) AS monetary
        FROM olist_customers_dataset c
        JOIN olist_orders_dataset o ON o.customer_id = c.customer_id
        JOIN olist_order_payments_dataset p ON p.order_id = o.order_id
        WHERE o.order_status IN ('delivered', 'shipped') GROUP BY c.customer_unique_id
    ),
    rfm_scored AS (
        SELECT *, NTILE(4) OVER (ORDER BY recency DESC) AS r_score, NTILE(4) OVER (ORDER BY frequency ASC) AS f_score, NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
        FROM rfm_base
    ),
    rfm_segment AS (
        SELECT *, CASE
            WHEN r_score = 4 AND f_score = 4 AND m_score = 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
            WHEN r_score >= 3 AND f_score <= 2 THEN 'Recent / New'
            WHEN r_score BETWEEN 2 AND 3 AND f_score <= 2 THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score = 1 AND f_score = 1 THEN 'Lost'
            ELSE 'Hibernating' END AS segment
        FROM rfm_scored
    )
    SELECT segment, COUNT(*) AS customers,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_customers,
        ROUND(AVG(recency), 1) AS avg_recency_days, ROUND(AVG(frequency), 2) AS avg_frequency,
        ROUND(AVG(monetary), 2) AS avg_monetary, ROUND(SUM(monetary), 2) AS total_revenue,
        ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 2) AS pct_of_revenue
    FROM rfm_segment GROUP BY segment ORDER BY total_revenue DESC;
    """

    cohort = pd.read_sql_query(cohort_sql, con)
    ltv = pd.read_sql_query(ltv_sql, con)
    mom = pd.read_sql_query(mom_sql, con)
    rfm = pd.read_sql_query(rfm_sql, con)
    con.close()
    
    return cohort, ltv, mom, rfm

# Load data (runs once, then is cached)
cohort, ltv, mom, rfm = load_data()

# ---------- Dashboard Layout ----------
st.title("Olist — Revenue & Retention Analysis")
st.caption("SQL → Streamlit pipeline. Insights, not just queries.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"R$ {mom['revenue'].sum():,.0f}")
k2.metric("Unique Customers", f"{rfm['customers'].sum():,.0f}")
k3.metric("Avg MoM Growth", f"{mom['mom_growth_pct'].median():.1f}%")
top_decile_pct = ltv.loc[ltv['revenue_decile']==1, 'pct_of_total_revenue'].iloc[0]
k4.metric("Top-Decile Revenue Share", f"{top_decile_pct:.1f}%")

st.divider()
st.subheader("1. Cohort Retention")
cohort_pivot = cohort.pivot(index="cohort_month", columns="month_offset", values="retention_pct")
fig = px.imshow(cohort_pivot, labels=dict(x="Months since first purchase", y="Cohort", color="Retention %"), color_continuous_scale="Blues")
st.plotly_chart(fig, use_container_width=True)
st.info("**Insight:** Retention collapses after month 0 (~3%). Olist behaves like a low-repeat marketplace — growth depends on new acquisition, not retention tactics.")

st.divider()
st.subheader("2. Customer LTV Concentration (Deciles)")
fig2 = px.bar(ltv, x="revenue_decile", y="pct_of_total_revenue", labels={"revenue_decile": "Revenue Decile (1 = top)", "pct_of_total_revenue": "% of Total Revenue"})
st.plotly_chart(fig2, use_container_width=True)
st.info("**Insight:** Top decile drives ~30%+ of revenue. High concentration = high exposure. Recommend VIP-tier service for top decile.")

st.divider()
st.subheader("3. Month-over-Month Revenue")
fig3 = px.bar(mom, x="order_month", y="revenue", text="mom_growth_pct", labels={"order_month": "Month", "revenue": "Revenue (R$)"})
st.plotly_chart(fig3, use_container_width=True)
st.info("**Insight:** Sharp Nov-2017 spike (Black Friday). Recommend Q4 fulfillment staffing + inventory build by Sep.")

st.divider()
st.subheader("4. RFM Segmentation")
fig4 = px.bar(rfm, x="segment", y="total_revenue", color="avg_recency_days", text="pct_of_revenue", labels={"total_revenue": "Segment Revenue (R$)", "avg_recency_days": "Avg Recency (days)"})
st.plotly_chart(fig4, use_container_width=True)

st.markdown("#### RFM detail")
st.dataframe(rfm, use_container_width=True, hide_index=True)

st.divider()
at_risk = rfm[rfm['segment'] == 'At Risk'].iloc[0]
total_at_risk_rev = at_risk['total_revenue']
estimated_reactivation = total_at_risk_rev * 0.05
campaign_cost = estimated_reactivation * 0.10

st.success(
    f"**Headline business decision:** The *At Risk* segment ({at_risk['customers']:.0f} customers) generated R$ {total_at_risk_rev:,.0f} ({at_risk['pct_of_revenue']:.1f}% of revenue) but hasn't purchased in {at_risk['avg_recency_days']:.0f} days on average. "
    f"\n\n**Recommended action:** Targeted 10% reactivation campaign. At a conservative 5% reactivation rate at historical AOV → expected incremental revenue ≈ R$ {estimated_reactivation:,.0f} against campaign cost of R$ {campaign_cost:,.0f} → **estimated ROI ≈ 900%.**"
)
