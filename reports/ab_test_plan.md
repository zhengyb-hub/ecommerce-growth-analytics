# A/B Test Plan

## Hypothesis

Offering a targeted coupon to at-risk customers will increase 30-day reactivation without reducing revenue per treated customer after discount.

## Population

Customers inactive 60-180 days before anchor date as of 2011-09-10.

## Design

- Randomization unit: customer_id.
- Control: no coupon or existing lifecycle message.
- Treatment: personalized win-back coupon.
- Primary metric: 30-day reactivation rate.
- Guardrail metric: Revenue per treated customer after discount.
- Observation window: 30 days after assignment.

## Power Estimate

- Eligible historical customers: 1,293.
- Observed baseline 30-day reactivation: 23.7%.
- Target rate: 28.5%.
- Minimum detectable effect: 4.7% absolute.
- Sample size: 1,343 customers per variant.

## Decision Rule

Ship the campaign if the treatment improves 30-day reactivation with statistical significance and does not reduce revenue per treated customer after discount.
