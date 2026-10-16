# Executive Summary

## Business Question

How can a non-store e-commerce retailer improve repeat revenue and prioritize growth opportunities across customers, markets, and products?

## Dataset

The analysis uses UCI Online Retail II, a two-year transactional dataset from a UK-based online retailer. After cleaning cancellations, returns, missing customer IDs, and invalid prices, the dataset covers 805,549 clean line items, 36,969 orders, and 5,878 known customers between 2009-12-01 and 2011-12-09.

## Key Findings

- Total clean revenue is GBP 17,743,429, with an average order value of GBP 480.
- Repeat customer rate is 72.4%; this makes lifecycle retention the most direct growth lever.
- Weighted month-1 cohort retention is 23.1% and weighted month-3 retention is 24.5%.
- The highest revenue RFM segment is Champions, contributing 68.1% of clean revenue.
- United Kingdom is the largest market, contributing 83.0% of clean revenue.
- The top product by revenue is REGENCY CAKESTAND 3 TIER (22423), contributing GBP 286,486.

## Growth Recommendations

1. Pilot a consent-compliant win-back campaign for At Risk and Hibernating customers after resolving experiment feasibility. The largest modeled scenario is "Increase returning-customer revenue by 5%", estimated at GBP 143,373; this is not realized revenue.
2. Build a first-90-day lifecycle program because early cohort retention drops quickly after the first purchase.
3. Use product bundles and merchandising around top SKUs to lift average order value without relying only on discounts.
4. Treat country strategy separately: protect the core UK base while testing localized offers in smaller high-AOV markets.

These directional scenarios may overlap and exclude campaign and product costs; do not add their uplifts together as a forecast.

## Experiment Design

Recommended test: At-risk customer coupon win-back.

- Target: Customers inactive 60-180 days before anchor date.
- Baseline 30-day reactivation: 23.7%.
- Primary metric: 30-day reactivation rate.
- Guardrail: Revenue per treated customer after discount.
- The original uplift assumption needs 1,343 per arm, exceeding the 1,293-customer historical pool. A feasible equal split has 646 per arm and can detect roughly 6.9% absolute uplift at 80% power (normal approximation). Do not claim this historical design is launch-ready.

## Latest Complete Month Snapshot

- Month: 2011-11.
- Revenue: GBP 1,161,817.
- Active customers: 1,664.
- Returning customer share: 88.5%.
