-- KPI tree for revenue growth.
-- Revenue = active customers * orders per customer * average order value.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        MIN(invoice_date) AS order_date,
        SUM(line_revenue) AS revenue
    FROM transactions
    GROUP BY invoice_no, customer_id
),
customer_orders AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY customer_id
)
SELECT
    ROUND(SUM(o.revenue), 2) AS total_revenue,
    COUNT(DISTINCT o.invoice_no) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    ROUND(SUM(o.revenue) / COUNT(DISTINCT o.invoice_no), 2) AS avg_order_value,
    ROUND(CAST(COUNT(DISTINCT o.invoice_no) AS REAL) / COUNT(DISTINCT o.customer_id), 2) AS orders_per_customer,
    ROUND(
        CAST((SELECT COUNT(*) FROM customer_orders WHERE order_count >= 2) AS REAL)
        / (SELECT COUNT(*) FROM customer_orders),
        4
    ) AS repeat_customer_rate
FROM orders o
JOIN customer_orders co
    ON o.customer_id = co.customer_id;
