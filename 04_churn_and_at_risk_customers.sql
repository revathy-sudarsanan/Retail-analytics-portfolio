-- 04_churn_and_at_risk_customers.sql
-- Business question: "Which previously good customers have gone quiet,
-- and how big is that revenue risk?" Without subscription end-dates,
-- churn for a transactional business is best defined by recency: a
-- customer is "at risk" if they've gone much longer than their own
-- typical reorder gap without buying again.

WITH order_gaps AS (
    SELECT
        customer_id,
        order_date,
        order_date - LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS days_since_prev_order
    FROM orders
),
customer_reorder_profile AS (
    SELECT
        customer_id,
        AVG(days_since_prev_order) AS avg_reorder_gap_days,
        MAX(order_date)            AS last_order_date
    FROM order_gaps
    WHERE days_since_prev_order IS NOT NULL
    GROUP BY customer_id
    HAVING COUNT(*) >= 2   -- need at least 2 gaps (3+ orders) for a meaningful average
),
dataset_max_date AS (
    SELECT MAX(order_date) AS max_date FROM orders
)
SELECT
    p.customer_id,
    o.country,
    p.last_order_date,
    ROUND(p.avg_reorder_gap_days, 0)                                   AS avg_reorder_gap_days,
    (d.max_date - p.last_order_date)                                   AS days_since_last_order,
    o.total_spend,
    CASE
        WHEN (d.max_date - p.last_order_date) > 2 * p.avg_reorder_gap_days THEN 'At risk'
        ELSE 'Healthy'
    END AS churn_status
FROM customer_reorder_profile p
JOIN customers o ON o.customer_id = p.customer_id
CROSS JOIN dataset_max_date d
ORDER BY days_since_last_order DESC;

-- Summary: total revenue at risk
/*
SELECT
    churn_status,
    COUNT(*)            AS customers,
    SUM(total_spend)    AS revenue_at_risk
FROM ( ... the query above as a subquery ... ) t
GROUP BY churn_status;
*/
