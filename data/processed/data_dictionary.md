# Data Dictionary

Source: UCI Machine Learning Repository, Online Retail II.

Cleaning rules:
- Removed rows without customer_id.
- Removed cancellations and returns, identified by invoice numbers beginning with C or negative quantity.
- Removed rows with non-positive quantity or unit price.
- Created line_revenue as quantity * unit_price.
- Created invoice_month as the first day of the invoice month.

Row quality summary:
- raw_rows: 1,067,371
- missing_customer_rows: 243,007
- cancellation_or_return_rows: 22,951
- non_positive_quantity_rows: 22,950
- non_positive_price_rows: 6,207
- invalid_date_rows: 0
- clean_rows: 805,549

Core fields:
- invoice_no: order or invoice identifier.
- stock_code: product identifier.
- description: product name.
- quantity: units purchased on the invoice line.
- invoice_date: timestamp of the transaction.
- invoice_month: month bucket used for cohort and KPI analysis.
- unit_price: product unit price in GBP.
- line_revenue: quantity multiplied by unit_price.
- customer_id: anonymized customer identifier.
- country: customer country.
