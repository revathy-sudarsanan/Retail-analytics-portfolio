-- 05_top_products_and_countries.sql
-- Business question: "What sells best, and where?" - a standard
-- BI drill-down report for the product/commercial team.

-- Top 15 products by revenue
SELECT
    stock_code,
    description,
    total_quantity_sold,
    total_revenue,
    n_orders,
    ROUND(total_revenue / NULLIF(n_orders, 0), 2) AS avg_revenue_per_order
FROM top_products
ORDER BY total_revenue DESC
LIMIT 15;

-- Revenue and customer count by country
SELECT
    country,
    COUNT(DISTINCT customer_id)     AS total_customers,
    SUM(total_spend)                AS total_revenue,
    ROUND(AVG(total_spend), 2)      AS avg_customer_ltv
FROM customers
GROUP BY country
ORDER BY total_revenue DESC;
