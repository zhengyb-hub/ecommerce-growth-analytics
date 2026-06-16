-- Historical baseline for an at-risk customer coupon win-back test.
-- Target: customers inactive for 60-180 days before the anchor date.
-- Outcome: customer places an order within 30 days after the anchor date.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        MIN(invoice_date) AS order_date,
        SUM(line_revenue) AS revenue
    FROM transactions
    GROUP BY invoice_no, customer_id
),
anchor AS (
    SELECT DATE(MAX(order_date), '-90 day') AS anchor_date
    FROM orders
),
last_before_anchor AS (
    SELECT
        o.customer_id,
        MAX(o.order_date) AS last_order_before_anchor
    FROM orders o
    CROSS JOIN anchor a
    WHERE DATE(o.order_date) <= a.anchor_date
    GROUP BY o.customer_id
),
eligible AS (
    SELECT
        l.customer_id
    FROM last_before_anchor l
    CROSS JOIN anchor a
    WHERE DATE(l.last_order_before_anchor) BETWEEN DATE(a.anchor_date, '-180 day') AND DATE(a.anchor_date, '-60 day')
),
reactivated AS (
    SELECT DISTINCT
        o.customer_id
    FROM orders o
    JOIN eligible e
        ON o.customer_id = e.customer_id
    CROSS JOIN anchor a
    WHERE DATE(o.order_date) > a.anchor_date
      AND DATE(o.order_date) <= DATE(a.anchor_date, '+30 day')
)
SELECT
    (SELECT anchor_date FROM anchor) AS anchor_date,
    COUNT(DISTINCT e.customer_id) AS eligible_customers,
    COUNT(DISTINCT r.customer_id) AS reactivated_customers,
    ROUND(CAST(COUNT(DISTINCT r.customer_id) AS REAL) / COUNT(DISTINCT e.customer_id), 4) AS observed_30d_reactivation_rate
FROM eligible e
LEFT JOIN reactivated r
    ON e.customer_id = r.customer_id;
