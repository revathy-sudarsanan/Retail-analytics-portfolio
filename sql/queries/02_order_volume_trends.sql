-- 02_order_volume_trends.sql
-- Business question: "How is order volume/revenue trending month over
-- month, and which markets are driving growth?" This is the same kind
-- of "usage volume" reporting a product/growth team relies on, just
-- applied to orders instead of app events.

SELECT
    DATE_TRUNC('month', order_date)::date AS order_month,
    country,
    COUNT(*)                               AS total_orders,
    SUM(total_quantity)                    AS total_items_sold,
    ROUND(SUM(order_value), 2)             AS total_revenue,
    ROUND(AVG(order_value), 2)             AS avg_order_value,
    COUNT(DISTINCT customer_id)            AS unique_customers
FROM orders
GROUP BY DATE_TRUNC('month', order_date), country
ORDER BY order_month, total_revenue DESC;

-- Month-over-month revenue growth (all countries combined)
/*
WITH monthly AS (
    SELECT DATE_TRUNC('month', order_date)::date AS order_month,
           SUM(order_value) AS revenue
    FROM orders
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT
    order_month,
    revenue,
    LAG(revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
          / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 1) AS mom_growth_pct
FROM monthly
ORDER BY order_month;
*/
