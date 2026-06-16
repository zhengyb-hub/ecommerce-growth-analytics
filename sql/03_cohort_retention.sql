-- Monthly cohort retention by first purchase month.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        DATE(MIN(invoice_date), 'start of month') AS order_month
    FROM transactions
    GROUP BY invoice_no, customer_id
),
cohorts AS (
    SELECT
        customer_id,
        MIN(order_month) AS cohort_month
    FROM orders
    GROUP BY customer_id
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        CAST(strftime('%Y', o.order_month) AS INTEGER) * 12 + CAST(strftime('%m', o.order_month) AS INTEGER)
        - CAST(strftime('%Y', c.cohort_month) AS INTEGER) * 12 - CAST(strftime('%m', c.cohort_month) AS INTEGER)
            AS months_since_first_order,
        COUNT(DISTINCT o.customer_id) AS active_customers
    FROM orders o
    JOIN cohorts c
        ON o.customer_id = c.customer_id
    GROUP BY c.cohort_month, months_since_first_order
),
cohort_sizes AS (
    SELECT
        cohort_month,
        active_customers AS cohort_size
    FROM cohort_activity
    WHERE months_since_first_order = 0
)
SELECT
    a.cohort_month,
    a.months_since_first_order,
    a.active_customers,
    s.cohort_size,
    ROUND(CAST(a.active_customers AS REAL) / s.cohort_size, 4) AS retention_rate
FROM cohort_activity a
JOIN cohort_sizes s
    ON a.cohort_month = s.cohort_month
ORDER BY a.cohort_month, a.months_since_first_order;
