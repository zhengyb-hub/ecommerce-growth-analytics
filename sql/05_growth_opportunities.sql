-- Market and product opportunity scan.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        country,
        SUM(line_revenue) AS revenue
    FROM transactions
    GROUP BY invoice_no, customer_id, country
),
country_performance AS (
    SELECT
        country,
        SUM(revenue) AS revenue,
        COUNT(DISTINCT invoice_no) AS orders,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(revenue) / COUNT(DISTINCT invoice_no) AS avg_order_value
    FROM orders
    GROUP BY country
),
product_performance AS (
    SELECT
        stock_code,
        description,
        SUM(line_revenue) AS revenue,
        SUM(quantity) AS units,
        COUNT(DISTINCT invoice_no) AS orders,
        COUNT(DISTINCT customer_id) AS customers
    FROM transactions
    GROUP BY stock_code, description
)
SELECT
    'country' AS opportunity_type,
    country AS opportunity,
    ROUND(revenue, 2) AS revenue,
    orders,
    customers,
    ROUND(avg_order_value, 2) AS avg_order_value
FROM country_performance
ORDER BY revenue DESC
LIMIT 10;

-- Run this separately for top products:
-- SELECT
--     'product' AS opportunity_type,
--     description AS opportunity,
--     ROUND(revenue, 2) AS revenue,
--     orders,
--     customers,
--     units
-- FROM product_performance
-- ORDER BY revenue DESC
-- LIMIT 10;
