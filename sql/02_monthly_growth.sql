-- Monthly growth diagnostics.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        DATE(MIN(invoice_date), 'start of month') AS order_month,
        SUM(line_revenue) AS revenue
    FROM transactions
    GROUP BY invoice_no, customer_id
),
first_orders AS (
    SELECT
        customer_id,
        MIN(order_month) AS first_order_month
    FROM orders
    GROUP BY customer_id
)
SELECT
    o.order_month,
    ROUND(SUM(o.revenue), 2) AS revenue,
    COUNT(DISTINCT o.invoice_no) AS orders,
    COUNT(DISTINCT o.customer_id) AS active_customers,
    COUNT(DISTINCT CASE WHEN o.order_month = f.first_order_month THEN o.customer_id END) AS new_customers,
    COUNT(DISTINCT CASE WHEN o.order_month > f.first_order_month THEN o.customer_id END) AS returning_customers,
    ROUND(SUM(o.revenue) / COUNT(DISTINCT o.invoice_no), 2) AS avg_order_value,
    ROUND(CAST(COUNT(DISTINCT o.invoice_no) AS REAL) / COUNT(DISTINCT o.customer_id), 2) AS orders_per_active_customer
FROM orders o
JOIN first_orders f
    ON o.customer_id = f.customer_id
GROUP BY o.order_month
ORDER BY o.order_month;
