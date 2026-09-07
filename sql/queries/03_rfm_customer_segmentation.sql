-- 03_rfm_customer_segmentation.sql
-- Business question: "Which customers are our most valuable, and which
-- are slipping away?" RFM (Recency, Frequency, Monetary) segmentation is
-- a standard technique for turning transaction data into an actionable
-- customer list for marketing/retention teams - directly relevant to the
-- job's "translate technical product data into business strategy" ask.

WITH rfm_base AS (
    SELECT
        customer_id,
        country,
        -- Recency: days since last order, relative to the most recent
        -- order date in the whole dataset (stand-in for "today")
        (SELECT MAX(order_date) FROM orders) - MAX(order_date)   AS recency_days,
        COUNT(*)                                                  AS frequency,
        SUM(order_value)                                          AS monetary
    FROM orders
    GROUP BY customer_id, country
),
rfm_scored AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY recency_days DESC)  AS r_score,  -- 4 = most recent
        NTILE(4) OVER (ORDER BY frequency ASC)       AS f_score,  -- 4 = most frequent
        NTILE(4) OVER (ORDER BY monetary ASC)        AS m_score   -- 4 = highest spend
    FROM rfm_base
)
SELECT
    customer_id,
    country,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 2                  THEN 'Loyal / Engaged'
        WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3  THEN 'At Risk - High Value'
        WHEN r_score <= 2 AND f_score <= 2                  THEN 'Churned / Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scored
ORDER BY monetary DESC;
