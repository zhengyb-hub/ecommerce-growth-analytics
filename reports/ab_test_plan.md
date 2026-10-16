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
- Available with an equal split: 646 per variant.
- Feasibility: original effect assumption is not feasible with the historical pool.
- Approximate detectable effect with the available pool: 6.9% absolute (target 30.7%).
- If the smaller effect matters, expand recruitment or run across additional independent eligible cohorts; do not count repeated exposure of the same customer as new participants.

## Decision Rule

Use an intention-to-treat analysis with a two-sided 5% test and report confidence intervals. Consider launch only if reactivation improves and revenue per assigned customer after discount does not decline. Net contribution margin is the preferred guardrail, but product cost and campaign cost are not in this dataset, so margin cannot be evaluated here. Check balance, exclusions, and sample-ratio mismatch before interpreting results. This is a design, not a completed experiment.
