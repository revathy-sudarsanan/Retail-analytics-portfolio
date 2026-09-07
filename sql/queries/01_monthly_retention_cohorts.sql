sql/queries/01_monthly_retention_cohorts.sql
-- Business question: "Of the customers who placed their first order in
-- month X, what % placed another order in each following month?"
-- This is the standard cohort retention table used to judge whether
-- customers keep coming back.

WITH first_order AS (
    SELECT customer_id, DATE_TRUNC('month', MIN(order_date))::date AS cohort_month
    FROM orders
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT customer_id, DATE_TRUNC('month', order_date)::date AS activity_month
    FROM orders
),
cohort_activity AS (
    SELECT
        f.cohort_month,
        (DATE_PART('year', a.activity_month) - DATE_PART('year', f.cohort_month)) * 12
            + (DATE_PART('month', a.activity_month) - DATE_PART('month', f.cohort_month))
            AS months_since_first_order,
        f.customer_id
    FROM first_order f
    JOIN activity a ON a.customer_id = f.customer_id
    WHERE a.activity_month >= f.cohort_month
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM first_order
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    ca.months_since_first_order,
    COUNT(DISTINCT ca.customer_id)                                      AS active_customers,
    cs.cohort_size,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.cohort_size, 1)    AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON cs.cohort_month = ca.cohort_month
GROUP BY ca.cohort_month, ca.months_since_first_order, cs.cohort_size
ORDER BY ca.cohort_month, ca.months_since_first_order;
