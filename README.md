# E-commerce Growth Analytics

Portfolio project for Growth Analyst, Product Analyst, and Marketing Analytics roles.

This project analyzes a two-year e-commerce transaction dataset to diagnose revenue growth, customer retention, RFM segments, market performance, and customer win-back opportunities.

## Finished Work

- Interactive dashboard: [dashboard/growth_dashboard.html](dashboard/growth_dashboard.html)
- GitHub Pages entry file: [docs/index.html](docs/index.html)
- Executive summary: [reports/executive_summary.md](reports/executive_summary.md)
- A/B test plan: [reports/ab_test_plan.md](reports/ab_test_plan.md)
- Lifecycle activation playbook: [reports/activation_playbook.md](reports/activation_playbook.md)
- Resume bullets: [reports/resume_bullets.md](reports/resume_bullets.md)

GitHub shows HTML files as source code by default. To view the dashboard as a real web page, enable GitHub Pages:

1. Go to `Settings` -> `Pages`.
2. Under `Build and deployment`, choose `Deploy from a branch`.
3. Select branch `main` and folder `/docs`.
4. Save.

After GitHub Pages finishes deploying, the dashboard should be available at:

https://zhengyb-hub.github.io/ecommerce-growth-analytics/

## Key Results

- Clean analysis dataset: 805,549 line items, 36,969 orders, 5,878 customers.
- Clean revenue analyzed: GBP 17.7M.
- Repeat customer rate: 72.4%.
- Month-1 weighted cohort retention: 23.1%.
- Highest-value RFM segment: Champions, contributing 68.1% of clean revenue.
- Largest market: United Kingdom, contributing 83.0% of clean revenue.
- Largest modeled growth opportunity: returning-customer revenue lift, estimated at GBP 143K using the last three **complete** months (September–November 2011).

## Decision Dashboard

The standalone dashboard works offline and is generated from the committed aggregate CSVs. It includes:

- A complete-month revenue/customer trend filter and cohort-retention heatmap.
- Clickable RFM segment selection with observed segment metrics, a campaign hypothesis, and illustrative email/short-video copy.
- Market concentration chart and adjustable win-back, AOV, and returning-revenue what-if sliders.
- A sample-size feasibility check for the historical win-back test.

The source ends on 2011-12-09, so December is **partial**: it remains in all-time clean revenue but is excluded from comparable monthly trends, cohort heatmap observation windows, and the three-month scenario baseline. Modeled revenue is not realized uplift; overlapping scenarios cannot be added together. No campaign or A/B experiment was launched on this historical dataset.

## Business Objective

The retailer wants to grow repeat revenue without relying only on acquisition. The analysis answers:

- What is the current revenue engine?
- How healthy is customer retention by cohort?
- Which customer segments and markets drive the most value?
- What growth levers should the team prioritize?
- How should a win-back A/B test be designed?

## Data Source

Dataset: UCI Online Retail II.

Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii

The raw data contains transactions from a UK-based non-store online retailer between 2009-12-01 and 2011-12-09. Raw data is not committed to the repo because the Excel file is large.

## Project Structure

```text
.
|-- dashboard/
|   `-- growth_dashboard.html
|-- docs/
|   `-- index.html
|-- data/
|   |-- raw/
|   `-- processed/
|-- reports/
|   |-- ab_test_plan.md
|   |-- executive_summary.md
|   `-- resume_bullets.md
|-- scripts/
|   |-- download_data.py
|   |-- prepare_data.py
|   `-- run_analysis.py
`-- sql/
    |-- 01_kpi_tree.sql
    |-- 02_monthly_growth.sql
    |-- 03_cohort_retention.sql
    |-- 04_rfm_segments.sql
    |-- 05_growth_opportunities.sql
    `-- 06_ab_test_baseline.sql
```

## How To Reproduce

Install dependencies:

```bash
pip install -r requirements.txt
```

Download the public dataset:

```bash
python scripts/download_data.py
```

Clean the raw transactions and create a SQLite database:

```bash
python scripts/prepare_data.py
```

Run the growth analysis and generate reports:

```bash
python scripts/run_analysis.py
```

If the UCI workbook is unavailable, regenerate only the dashboard and corrected derivative outputs from the committed aggregate CSVs:

```bash
python scripts/refresh_cached_outputs.py
```

This cached path cannot independently revalidate transaction cleaning or customer-level eligibility. Use the full pipeline for that. Run the automated tests with `python -m unittest discover -s tests -v`.

## Methods

- Data cleaning: removed missing customer IDs, cancellations, returns, non-positive quantities, invalid prices, and invalid dates.
- KPI tree: decomposed revenue into active customers, order frequency, and average order value.
- Cohort retention: measured repeat purchasing by first purchase month.
- RFM segmentation: scored customers by recency, frequency, and monetary value.
- Opportunity sizing: estimated revenue impact from win-back, AOV lift, and repeat-customer revenue lift scenarios.
- Experiment design: estimated baseline reactivation and required sample size for a coupon win-back A/B test.

## Suggested Resume Summary

Built an end-to-end growth analytics portfolio project using Python, SQL, and Plotly to analyze 805,549 clean e-commerce line items, cohort retention, RFM segments, customer win-back opportunities, and A/B test design; delivered an executive dashboard and actionable growth recommendations.
