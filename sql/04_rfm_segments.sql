-- RFM segmentation using SQLite window functions.

WITH orders AS (
    SELECT
        invoice_no,
        customer_id,
        MIN(invoice_date) AS order_date,
        SUM(line_revenue) AS revenue
    FROM transactions
    GROUP BY invoice_no, customer_id
),
snapshot AS (
    SELECT DATE(MAX(order_date), '+1 day') AS snapshot_date
    FROM orders
),
rfm_base AS (
    SELECT
        o.customer_id,
        CAST(julianday((SELECT snapshot_date FROM snapshot)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT o.invoice_no) AS frequency,
        SUM(o.revenue) AS monetary
    FROM orders o
    GROUP BY o.customer_id
),
scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        6 - NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC, customer_id ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC, customer_id ASC) AS m_score
    FROM rfm_base
),
segmented AS (
    SELECT
        *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 4 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score >= 2 THEN 'Potential Loyalists'
            WHEN r_score >= 4 AND f_score = 1 THEN 'New Customers'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Hibernating'
            ELSE 'Needs Attention'
        END AS segment
    FROM scored
)
SELECT
    segment,
    COUNT(*) AS customers,
    ROUND(SUM(monetary), 2) AS revenue,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency), 2) AS avg_frequency,
    ROUND(AVG(monetary), 2) AS avg_customer_value
FROM segmented
GROUP BY segment
ORDER BY revenue DESC;
