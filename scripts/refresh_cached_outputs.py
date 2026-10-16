"""Refresh derived deliverables when the large raw UCI workbook is unavailable.

Uses only the previously committed aggregate CSVs. It does not recompute cleaning,
customer-level RFM, or the historical eligible pool from source transactions.
"""
from __future__ import annotations

import pandas as pd

from build_dashboard import build_dashboard
from run_analysis import PROCESSED_DIR, create_reports, feasible_mde


def main() -> None:
    read = lambda name: pd.read_csv(PROCESSED_DIR / name)
    overview = read("overview_metrics.csv")
    monthly = read("monthly_kpis.csv")
    monthly["order_month"] = pd.to_datetime(monthly["order_month"])
    retention = read("cohort_retention_long.csv")
    segments = read("rfm_segment_summary.csv")
    country = read("country_performance.csv")
    products = read("top_products.csv")
    ab = read("ab_test_design.csv")

    last_observation = pd.Timestamp(overview.loc[0, "date_end"])
    complete = monthly.loc[monthly["order_month"] < last_observation.to_period("M").start_time].tail(3)
    pool = int(segments.loc[segments["segment"].isin(["At Risk", "Hibernating"]), "customers"].sum())
    aov = float(overview.loc[0, "avg_order_value"])
    scenarios = pd.DataFrame([
        {"scenario": "Win back 10% of at-risk and hibernating customers", "baseline": pool, "assumption": "Each reactivated customer places one average order.", "estimated_revenue_uplift": pool * .10 * aov},
        {"scenario": "Increase AOV by 3% in the latest 3 complete months", "baseline": complete["revenue"].sum(), "assumption": "Bundling and merchandising raise average order value.", "estimated_revenue_uplift": complete["revenue"].sum() * .03},
        {"scenario": "Increase returning-customer revenue by 5%", "baseline": complete["returning_revenue"].sum(), "assumption": "Lifecycle messaging improves repeat-purchase intensity.", "estimated_revenue_uplift": complete["returning_revenue"].sum() * .05},
    ])
    scenarios.to_csv(PROCESSED_DIR / "growth_scenarios.csv", index=False)

    eligible = int(ab.loc[0, "eligible_customers"])
    required = int(ab.loc[0, "sample_size_per_variant"])
    ab["available_per_variant"] = eligible // 2
    ab["required_total_sample"] = required * 2
    ab["sample_feasible"] = required * 2 <= eligible
    ab["feasible_mde_abs"] = feasible_mde(float(ab.loc[0, "observed_30d_reactivation_rate"]), eligible)
    ab.to_csv(PROCESSED_DIR / "ab_test_design.csv", index=False)

    # Line count is the published count from the original full-data run, not
    # something inferable from the aggregate files alone.
    create_reports(805_549, overview, monthly, retention, segments, country, products, scenarios, ab)
    print(build_dashboard())


if __name__ == "__main__":
    main()
