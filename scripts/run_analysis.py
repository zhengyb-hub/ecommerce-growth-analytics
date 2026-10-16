from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import norm
from build_dashboard import build_dashboard


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
REPORTS_DIR = PROJECT_ROOT / "reports"
TRANSACTIONS_CSV = PROCESSED_DIR / "transactions_clean.csv"


def money(value: float) -> str:
    return f"GBP {value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1%}"


def load_transactions(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Clean transaction file not found: {path}. Run scripts/prepare_data.py first.")
    data = pd.read_csv(
        path,
        parse_dates=["invoice_date", "invoice_month"],
        dtype={
            "invoice_no": "string",
            "stock_code": "string",
            "description": "string",
            "customer_id": "int64",
            "country": "string",
            "source_sheet": "string",
        },
    )
    data["line_revenue"] = pd.to_numeric(data["line_revenue"], errors="coerce")
    data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    return data


def build_orders(transactions: pd.DataFrame) -> pd.DataFrame:
    orders = (
        transactions.groupby("invoice_no", as_index=False)
        .agg(
            customer_id=("customer_id", "first"),
            order_date=("invoice_date", "min"),
            country=("country", "first"),
            revenue=("line_revenue", "sum"),
            units=("quantity", "sum"),
            unique_skus=("stock_code", "nunique"),
        )
        .sort_values("order_date")
    )
    orders["order_month"] = orders["order_date"].dt.to_period("M").dt.to_timestamp()
    return orders


def overview_metrics(orders: pd.DataFrame) -> pd.DataFrame:
    customer_order_counts = orders.groupby("customer_id")["invoice_no"].nunique()
    total_revenue = orders["revenue"].sum()
    total_orders = orders["invoice_no"].nunique()
    total_customers = orders["customer_id"].nunique()
    repeat_customers = int((customer_order_counts > 1).sum())
    metrics = {
        "date_start": orders["order_date"].min().strftime("%Y-%m-%d"),
        "date_end": orders["order_date"].max().strftime("%Y-%m-%d"),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "avg_order_value": total_revenue / total_orders,
        "orders_per_customer": total_orders / total_customers,
        "repeat_customer_rate": repeat_customers / total_customers,
    }
    return pd.DataFrame([metrics])


def monthly_kpis(orders: pd.DataFrame) -> pd.DataFrame:
    first_month = orders.groupby("customer_id")["order_month"].min().rename("first_order_month")
    enriched = orders.join(first_month, on="customer_id")
    enriched["customer_type"] = np.where(
        enriched["order_month"] == enriched["first_order_month"], "new", "returning"
    )

    monthly = (
        enriched.groupby("order_month")
        .agg(
            revenue=("revenue", "sum"),
            orders=("invoice_no", "nunique"),
            active_customers=("customer_id", "nunique"),
        )
        .reset_index()
    )
    new_customers = (
        enriched.loc[enriched["customer_type"] == "new"]
        .groupby("order_month")["customer_id"]
        .nunique()
        .rename("new_customers")
    )
    returning_customers = (
        enriched.loc[enriched["customer_type"] == "returning"]
        .groupby("order_month")["customer_id"]
        .nunique()
        .rename("returning_customers")
    )
    returning_revenue = (
        enriched.loc[enriched["customer_type"] == "returning"]
        .groupby("order_month")["revenue"]
        .sum()
        .rename("returning_revenue")
    )

    monthly = monthly.join(new_customers, on="order_month").join(returning_customers, on="order_month")
    monthly = monthly.join(returning_revenue, on="order_month")
    monthly[["new_customers", "returning_customers", "returning_revenue"]] = monthly[
        ["new_customers", "returning_customers", "returning_revenue"]
    ].fillna(0)
    monthly["avg_order_value"] = monthly["revenue"] / monthly["orders"]
    monthly["orders_per_active_customer"] = monthly["orders"] / monthly["active_customers"]
    monthly["returning_customer_share"] = monthly["returning_customers"] / monthly["active_customers"]
    return monthly.sort_values("order_month")


def cohort_retention(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    first_month = orders.groupby("customer_id")["order_month"].min().rename("cohort_month")
    cohort_orders = orders.join(first_month, on="customer_id")
    cohort_orders["months_since_first_order"] = (
        (cohort_orders["order_month"].dt.year - cohort_orders["cohort_month"].dt.year) * 12
        + (cohort_orders["order_month"].dt.month - cohort_orders["cohort_month"].dt.month)
    )

    cohort_counts = (
        cohort_orders.groupby(["cohort_month", "months_since_first_order"])["customer_id"]
        .nunique()
        .reset_index(name="active_customers")
    )
    cohort_sizes = cohort_counts.loc[cohort_counts["months_since_first_order"] == 0, ["cohort_month", "active_customers"]]
    cohort_sizes = cohort_sizes.rename(columns={"active_customers": "cohort_size"})
    retention = cohort_counts.merge(cohort_sizes, on="cohort_month", how="left")
    retention["retention_rate"] = retention["active_customers"] / retention["cohort_size"]
    retention = retention.sort_values(["cohort_month", "months_since_first_order"])

    matrix = retention.pivot(index="cohort_month", columns="months_since_first_order", values="retention_rate")
    return retention, matrix


def score_series(values: pd.Series, high_is_good: bool) -> pd.Series:
    percentile_rank = values.rank(method="first", pct=True)
    scores = np.ceil(percentile_rank * 5).clip(1, 5).astype(int)
    if not high_is_good:
        scores = 6 - scores
    return scores


def assign_segment(row: pd.Series) -> str:
    r = row["r_score"]
    f = row["f_score"]
    m = row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 4 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f >= 2:
        return "Potential Loyalists"
    if r >= 4 and f == 1:
        return "New Customers"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Needs Attention"


def rfm_analysis(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshot_date = orders["order_date"].max() + pd.Timedelta(days=1)
    rfm = (
        orders.groupby("customer_id")
        .agg(
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            frequency=("invoice_no", "nunique"),
            monetary=("revenue", "sum"),
            avg_order_value=("revenue", "mean"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (snapshot_date - rfm["last_order_date"]).dt.days
    rfm["r_score"] = score_series(rfm["recency_days"], high_is_good=False)
    rfm["f_score"] = score_series(rfm["frequency"], high_is_good=True)
    rfm["m_score"] = score_series(rfm["monetary"], high_is_good=True)
    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    rfm["segment"] = rfm.apply(assign_segment, axis=1)

    segment_summary = (
        rfm.groupby("segment")
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_order_value=("avg_order_value", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    segment_summary["customer_share"] = segment_summary["customers"] / segment_summary["customers"].sum()
    segment_summary["revenue_share"] = segment_summary["revenue"] / segment_summary["revenue"].sum()
    return rfm, segment_summary


def country_performance(orders: pd.DataFrame) -> pd.DataFrame:
    country = (
        orders.groupby("country")
        .agg(
            revenue=("revenue", "sum"),
            orders=("invoice_no", "nunique"),
            customers=("customer_id", "nunique"),
            avg_order_value=("revenue", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    country["revenue_share"] = country["revenue"] / country["revenue"].sum()
    return country


def product_performance(transactions: pd.DataFrame) -> pd.DataFrame:
    products = (
        transactions.groupby(["stock_code", "description"])
        .agg(
            revenue=("line_revenue", "sum"),
            units=("quantity", "sum"),
            orders=("invoice_no", "nunique"),
            customers=("customer_id", "nunique"),
            avg_unit_price=("unit_price", "mean"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    products["revenue_share"] = products["revenue"] / products["revenue"].sum()
    return products


def growth_scenarios(monthly: pd.DataFrame, rfm_segments: pd.DataFrame, overview: pd.DataFrame) -> pd.DataFrame:
    latest_months = complete_months(monthly, pd.Timestamp(overview.loc[0, "date_end"])).tail(3)
    baseline_revenue = latest_months["revenue"].sum()
    returning_revenue = latest_months["returning_revenue"].sum()
    avg_order_value = float(overview.loc[0, "avg_order_value"])

    segment_lookup = rfm_segments.set_index("segment")
    reactivation_pool = 0
    for segment in ["At Risk", "Hibernating"]:
        if segment in segment_lookup.index:
            reactivation_pool += int(segment_lookup.loc[segment, "customers"])

    scenarios = pd.DataFrame(
        [
            {
                "scenario": "Win back 10% of at-risk and hibernating customers",
                "baseline": reactivation_pool,
                "assumption": "Each reactivated customer places one average order.",
                "estimated_revenue_uplift": reactivation_pool * 0.10 * avg_order_value,
            },
            {
                "scenario": "Increase AOV by 3% in the latest 3 complete months",
                "baseline": baseline_revenue,
                "assumption": "Bundling and merchandising raise average order value.",
                "estimated_revenue_uplift": baseline_revenue * 0.03,
            },
            {
                "scenario": "Increase returning-customer revenue by 5%",
                "baseline": returning_revenue,
                "assumption": "Lifecycle messaging improves repeat-purchase intensity.",
                "estimated_revenue_uplift": returning_revenue * 0.05,
            },
        ]
    )
    return scenarios


def complete_months(monthly: pd.DataFrame, last_observation: pd.Timestamp) -> pd.DataFrame:
    """Exclude the final calendar month when the source ends before month end."""
    result = monthly.sort_values("order_month")
    if last_observation.normalize() < last_observation.to_period("M").end_time.normalize():
        result = result.loc[result["order_month"] < last_observation.to_period("M").start_time]
    return result


def sample_size_two_proportions(p1: float, p2: float, alpha: float = 0.05, power: float = 0.80) -> int:
    if p2 <= p1:
        raise ValueError("p2 must be greater than p1")
    p_bar = (p1 + p2) / 2
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    numerator = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    return int(math.ceil(numerator / ((p2 - p1) ** 2)))


def feasible_mde(p1: float, eligible: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest absolute uplift detectable with an equal split of the available pool."""
    per_arm = eligible // 2
    if per_arm < 2:
        raise ValueError("At least four eligible customers are required")
    low, high = 0.0, 1.0 - p1
    if sample_size_two_proportions(p1, p1 + high, alpha, power) > per_arm:
        raise ValueError("Eligible pool is too small for this power specification")
    for _ in range(60):
        mid = (low + high) / 2
        if sample_size_two_proportions(p1, p1 + mid, alpha, power) <= per_arm:
            high = mid
        else:
            low = mid
    return high


def ab_test_design(orders: pd.DataFrame) -> pd.DataFrame:
    max_date = orders["order_date"].max()
    anchor_date = max_date - pd.Timedelta(days=90)
    inactive_start = anchor_date - pd.Timedelta(days=180)
    inactive_end = anchor_date - pd.Timedelta(days=60)

    historical_orders = orders.loc[orders["order_date"] <= anchor_date]
    last_before_anchor = historical_orders.groupby("customer_id")["order_date"].max()
    eligible_customers = last_before_anchor[
        (last_before_anchor >= inactive_start) & (last_before_anchor <= inactive_end)
    ].index

    future_orders = orders.loc[
        (orders["order_date"] > anchor_date)
        & (orders["order_date"] <= anchor_date + pd.Timedelta(days=30))
        & (orders["customer_id"].isin(eligible_customers))
    ]
    eligible_count = len(eligible_customers)
    reactivated_count = future_orders["customer_id"].nunique()
    baseline_rate = reactivated_count / eligible_count if eligible_count else 0
    baseline_for_power = max(baseline_rate, 0.001)
    mde_abs = max(0.02, baseline_for_power * 0.20)
    target_rate = min(baseline_for_power + mde_abs, 0.95)
    sample_size = sample_size_two_proportions(baseline_for_power, target_rate)
    feasible_effect = feasible_mde(baseline_for_power, eligible_count)

    return pd.DataFrame(
        [
            {
                "experiment": "At-risk customer coupon win-back",
                "anchor_date": anchor_date.strftime("%Y-%m-%d"),
                "target_definition": "Customers inactive 60-180 days before anchor date",
                "eligible_customers": eligible_count,
                "observed_30d_reactivation_rate": baseline_rate,
                "minimum_detectable_effect_abs": target_rate - baseline_for_power,
                "target_30d_reactivation_rate": target_rate,
                "sample_size_per_variant": sample_size,
                "available_per_variant": eligible_count // 2,
                "required_total_sample": sample_size * 2,
                "sample_feasible": sample_size * 2 <= eligible_count,
                "feasible_mde_abs": feasible_effect,
                "primary_metric": "30-day reactivation rate",
                "guardrail_metric": "Revenue per treated customer after discount",
            }
        ]
    )


def write_csv_outputs(
    overview: pd.DataFrame,
    monthly: pd.DataFrame,
    retention: pd.DataFrame,
    rfm: pd.DataFrame,
    segments: pd.DataFrame,
    country: pd.DataFrame,
    products: pd.DataFrame,
    scenarios: pd.DataFrame,
    ab_test: pd.DataFrame,
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    overview.to_csv(PROCESSED_DIR / "overview_metrics.csv", index=False)
    monthly.to_csv(PROCESSED_DIR / "monthly_kpis.csv", index=False)
    retention.to_csv(PROCESSED_DIR / "cohort_retention_long.csv", index=False)
    rfm.to_csv(PROCESSED_DIR / "rfm_customers.csv", index=False)
    segments.to_csv(PROCESSED_DIR / "rfm_segment_summary.csv", index=False)
    country.to_csv(PROCESSED_DIR / "country_performance.csv", index=False)
    products.head(50).to_csv(PROCESSED_DIR / "top_products.csv", index=False)
    scenarios.to_csv(PROCESSED_DIR / "growth_scenarios.csv", index=False)
    ab_test.to_csv(PROCESSED_DIR / "ab_test_design.csv", index=False)


def dashboard_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      <div class="note">{note}</div>
    </div>
    """


def create_dashboard(
    overview: pd.DataFrame,
    monthly: pd.DataFrame,
    retention_matrix: pd.DataFrame,
    segments: pd.DataFrame,
    country: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    metrics = overview.iloc[0]

    fig_kpis = make_subplots(specs=[[{"secondary_y": True}]])
    fig_kpis.add_trace(
        go.Scatter(
            x=monthly["order_month"],
            y=monthly["revenue"],
            name="Revenue",
            mode="lines+markers",
            line=dict(color="#1f77b4", width=3),
        ),
        secondary_y=False,
    )
    fig_kpis.add_trace(
        go.Bar(
            x=monthly["order_month"],
            y=monthly["active_customers"],
            name="Active customers",
            marker_color="#ff7f0e",
            opacity=0.45,
        ),
        secondary_y=True,
    )
    fig_kpis.update_layout(title="Monthly revenue and active customers", height=430, margin=dict(l=50, r=50, t=70, b=40))
    fig_kpis.update_yaxes(title_text="Revenue (GBP)", secondary_y=False)
    fig_kpis.update_yaxes(title_text="Active customers", secondary_y=True)

    heatmap_matrix = retention_matrix.copy()
    heatmap_matrix.index = heatmap_matrix.index.strftime("%Y-%m")
    fig_retention = go.Figure(
        data=go.Heatmap(
            z=heatmap_matrix.iloc[:, :13].values,
            x=[str(column) for column in heatmap_matrix.iloc[:, :13].columns],
            y=heatmap_matrix.index,
            colorscale="YlGnBu",
            zmin=0,
            zmax=1,
            colorbar=dict(tickformat=".0%"),
            hovertemplate="Cohort %{y}<br>Month %{x}<br>Retention %{z:.1%}<extra></extra>",
        )
    )
    fig_retention.update_layout(
        title="Cohort retention by months since first purchase",
        xaxis_title="Months since first purchase",
        yaxis_title="First purchase month",
        height=520,
        margin=dict(l=80, r=50, t=70, b=50),
    )

    fig_segments = go.Figure(
        data=[
            go.Bar(
                x=segments["segment"],
                y=segments["revenue"],
                marker_color="#2ca02c",
                hovertemplate="%{x}<br>Revenue GBP %{y:,.0f}<extra></extra>",
            )
        ]
    )
    fig_segments.update_layout(title="Revenue by RFM segment", yaxis_title="Revenue (GBP)", height=420)

    top_country = country.head(10).sort_values("revenue")
    fig_country = go.Figure(
        data=[
            go.Bar(
                x=top_country["revenue"],
                y=top_country["country"],
                orientation="h",
                marker_color="#9467bd",
                hovertemplate="%{y}<br>Revenue GBP %{x:,.0f}<extra></extra>",
            )
        ]
    )
    fig_country.update_layout(title="Top 10 countries by revenue", xaxis_title="Revenue (GBP)", height=420)

    fig_scenarios = go.Figure(
        data=[
            go.Bar(
                x=scenarios["estimated_revenue_uplift"],
                y=scenarios["scenario"],
                orientation="h",
                marker_color="#d62728",
                hovertemplate="%{y}<br>Estimated uplift GBP %{x:,.0f}<extra></extra>",
            )
        ]
    )
    fig_scenarios.update_layout(title="Growth scenario sizing", xaxis_title="Estimated revenue uplift (GBP)", height=420)

    cards = "\n".join(
        [
            dashboard_card("Total Revenue", money(float(metrics["total_revenue"])), f"{metrics['date_start']} to {metrics['date_end']}"),
            dashboard_card("Customers", f"{int(metrics['total_customers']):,}", "Known customers after cleaning"),
            dashboard_card("Repeat Rate", pct(float(metrics["repeat_customer_rate"])), "Customers with 2+ orders"),
            dashboard_card("AOV", money(float(metrics["avg_order_value"])), "Average order value"),
        ]
    )

    html_parts = [
        "<!doctype html>",
        "<html>",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<title>E-commerce Growth Analytics Dashboard</title>",
        "<style>",
        "body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f7f8fb;color:#172033;}",
        "header{background:#172033;color:white;padding:28px 40px;}",
        "header h1{margin:0;font-size:28px;letter-spacing:0;}",
        "header p{margin:8px 0 0;color:#d7deea;}",
        ".wrap{max-width:1180px;margin:0 auto;padding:28px 24px 48px;}",
        ".cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:20px;}",
        ".card{background:white;border:1px solid #e1e5ee;border-radius:8px;padding:18px;box-shadow:0 1px 2px rgba(20,32,51,.04);}",
        ".label{font-size:13px;color:#5c667a;text-transform:uppercase;}",
        ".value{font-size:26px;font-weight:700;margin-top:8px;}",
        ".note{font-size:13px;color:#69758a;margin-top:6px;}",
        ".panel{background:white;border:1px solid #e1e5ee;border-radius:8px;margin-top:18px;padding:10px;}",
        "@media(max-width:900px){.cards{grid-template-columns:repeat(2,minmax(0,1fr));}}",
        "@media(max-width:560px){.cards{grid-template-columns:1fr;}header{padding:22px 20px;}.wrap{padding:18px 14px;}}",
        "</style>",
        "</head>",
        "<body>",
        "<header><h1>E-commerce Growth Analytics</h1><p>Retention, RFM segmentation, and revenue opportunity sizing from Online Retail II.</p></header>",
        f"<main class=\"wrap\"><section class=\"cards\">{cards}</section>",
        f"<section class=\"panel\">{fig_kpis.to_html(full_html=False, include_plotlyjs=True)}</section>",
        f"<section class=\"panel\">{fig_retention.to_html(full_html=False, include_plotlyjs=False)}</section>",
        f"<section class=\"panel\">{fig_segments.to_html(full_html=False, include_plotlyjs=False)}</section>",
        f"<section class=\"panel\">{fig_country.to_html(full_html=False, include_plotlyjs=False)}</section>",
        f"<section class=\"panel\">{fig_scenarios.to_html(full_html=False, include_plotlyjs=False)}</section>",
        "</main></body></html>",
    ]
    (DASHBOARD_DIR / "growth_dashboard.html").write_text("\n".join(html_parts), encoding="utf-8")


def weighted_retention(retention: pd.DataFrame, month: int) -> float:
    month_data = retention.loc[retention["months_since_first_order"] == month]
    if month_data.empty:
        return float("nan")
    return month_data["active_customers"].sum() / month_data["cohort_size"].sum()


def create_reports(
    transaction_line_count: int,
    overview: pd.DataFrame,
    monthly: pd.DataFrame,
    retention: pd.DataFrame,
    segments: pd.DataFrame,
    country: pd.DataFrame,
    products: pd.DataFrame,
    scenarios: pd.DataFrame,
    ab_test: pd.DataFrame,
) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = overview.iloc[0]
    top_segment = segments.iloc[0]
    top_country = country.iloc[0]
    top_product = products.iloc[0]
    best_scenario = scenarios.sort_values("estimated_revenue_uplift", ascending=False).iloc[0]
    latest_month = complete_months(monthly, pd.Timestamp(metrics["date_end"])).iloc[-1]
    month_1_retention = weighted_retention(retention, 1)
    month_3_retention = weighted_retention(retention, 3)
    ab = ab_test.iloc[0]

    summary = f"""# Executive Summary

## Business Question

How can a non-store e-commerce retailer improve repeat revenue and prioritize growth opportunities across customers, markets, and products?

## Dataset

The analysis uses UCI Online Retail II, a two-year transactional dataset from a UK-based online retailer. After cleaning cancellations, returns, missing customer IDs, and invalid prices, the dataset covers {transaction_line_count:,} clean line items, {int(metrics['total_orders']):,} orders, and {int(metrics['total_customers']):,} known customers between {metrics['date_start']} and {metrics['date_end']}.

## Key Findings

- Total clean revenue is {money(float(metrics['total_revenue']))}, with an average order value of {money(float(metrics['avg_order_value']))}.
- Repeat customer rate is {pct(float(metrics['repeat_customer_rate']))}; this makes lifecycle retention the most direct growth lever.
- Weighted month-1 cohort retention is {pct(month_1_retention)} and weighted month-3 retention is {pct(month_3_retention)}.
- The highest revenue RFM segment is {top_segment['segment']}, contributing {pct(float(top_segment['revenue_share']))} of clean revenue.
- {top_country['country']} is the largest market, contributing {pct(float(top_country['revenue_share']))} of clean revenue.
- The top product by revenue is {top_product['description']} ({top_product['stock_code']}), contributing {money(float(top_product['revenue']))}.

## Growth Recommendations

1. Pilot a consent-compliant win-back campaign for At Risk and Hibernating customers after resolving experiment feasibility. The largest modeled scenario is "{best_scenario['scenario']}", estimated at {money(float(best_scenario['estimated_revenue_uplift']))}; this is not realized revenue.
2. Build a first-90-day lifecycle program because early cohort retention drops quickly after the first purchase.
3. Use product bundles and merchandising around top SKUs to lift average order value without relying only on discounts.
4. Treat country strategy separately: protect the core UK base while testing localized offers in smaller high-AOV markets.

These directional scenarios may overlap and exclude campaign and product costs; do not add their uplifts together as a forecast.

## Experiment Design

Recommended test: {ab['experiment']}.

- Target: {ab['target_definition']}.
- Baseline 30-day reactivation: {pct(float(ab['observed_30d_reactivation_rate']))}.
- Primary metric: {ab['primary_metric']}.
- Guardrail: {ab['guardrail_metric']}.
- The original uplift assumption needs {int(ab['sample_size_per_variant']):,} per arm, exceeding the {int(ab['eligible_customers']):,}-customer historical pool. A feasible equal split has {int(ab['available_per_variant']):,} per arm and can detect roughly {pct(float(ab['feasible_mde_abs']))} absolute uplift at 80% power (normal approximation). Do not claim this historical design is launch-ready.

## Latest Complete Month Snapshot

- Month: {latest_month['order_month'].strftime('%Y-%m')}.
- Revenue: {money(float(latest_month['revenue']))}.
- Active customers: {int(latest_month['active_customers']):,}.
- Returning customer share: {pct(float(latest_month['returning_customer_share']))}.
"""

    resume = f"""# Resume Bullets

Use one of these on your resume or LinkedIn project section.

- Built an end-to-end growth analytics project on {transaction_line_count:,} clean e-commerce line items and {int(metrics['total_orders']):,} orders, using Python and SQL to analyze cohort retention, RFM segmentation, repeat purchase behavior, and revenue drivers.
- Developed a customer lifecycle dashboard covering {int(metrics['total_customers']):,} customers and {money(float(metrics['total_revenue']))} in clean revenue; modeled a directional returning-revenue opportunity of {money(float(best_scenario['estimated_revenue_uplift']))} under explicit assumptions.
- Designed an A/B test for an at-risk customer coupon campaign, defining target population, primary and guardrail metrics, baseline reactivation, MDE, and required sample size.

Short version:

Built a growth analytics portfolio project using Python, SQL, and Plotly to analyze {transaction_line_count:,} clean e-commerce line items, cohort retention, RFM segments, and revenue opportunities; delivered an executive dashboard and experiment plan for customer win-back growth.
"""

    ab_plan = f"""# A/B Test Plan

## Hypothesis

Offering a targeted coupon to at-risk customers will increase 30-day reactivation without reducing revenue per treated customer after discount.

## Population

{ab['target_definition']} as of {ab['anchor_date']}.

## Design

- Randomization unit: customer_id.
- Control: no coupon or existing lifecycle message.
- Treatment: personalized win-back coupon.
- Primary metric: {ab['primary_metric']}.
- Guardrail metric: {ab['guardrail_metric']}.
- Observation window: 30 days after assignment.

## Power Estimate

- Eligible historical customers: {int(ab['eligible_customers']):,}.
- Observed baseline 30-day reactivation: {pct(float(ab['observed_30d_reactivation_rate']))}.
- Target rate: {pct(float(ab['target_30d_reactivation_rate']))}.
- Minimum detectable effect: {pct(float(ab['minimum_detectable_effect_abs']))} absolute.
- Sample size: {int(ab['sample_size_per_variant']):,} customers per variant.
- Available with an equal split: {int(ab['available_per_variant']):,} per variant.
- Feasibility: original effect assumption is {'feasible' if ab['sample_feasible'] else 'not feasible'} with the historical pool.
- Approximate detectable effect with the available pool: {pct(float(ab['feasible_mde_abs']))} absolute (target {pct(float(ab['observed_30d_reactivation_rate'] + ab['feasible_mde_abs']))}).
- If the smaller effect matters, expand recruitment or run across additional independent eligible cohorts; do not count repeated exposure of the same customer as new participants.

## Decision Rule

Use an intention-to-treat analysis with a two-sided 5% test and report confidence intervals. Consider launch only if reactivation improves and revenue per assigned customer after discount does not decline. Net contribution margin is the preferred guardrail, but product cost and campaign cost are not in this dataset, so margin cannot be evaluated here. Check balance, exclusions, and sample-ratio mismatch before interpreting results. This is a design, not a completed experiment.
"""

    (REPORTS_DIR / "executive_summary.md").write_text(summary, encoding="utf-8")
    (REPORTS_DIR / "resume_bullets.md").write_text(resume, encoding="utf-8")
    (REPORTS_DIR / "ab_test_plan.md").write_text(ab_plan, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run growth analytics and generate project outputs.")
    parser.add_argument("--transactions", default=str(TRANSACTIONS_CSV), help="Path to cleaned transactions CSV.")
    args = parser.parse_args()

    transactions = load_transactions(Path(args.transactions))
    orders = build_orders(transactions)

    overview = overview_metrics(orders)
    monthly = monthly_kpis(orders)
    retention, retention_matrix = cohort_retention(orders)
    rfm, segment_summary = rfm_analysis(orders)
    country = country_performance(orders)
    products = product_performance(transactions)
    scenarios = growth_scenarios(monthly, segment_summary, overview)
    ab_test = ab_test_design(orders)

    write_csv_outputs(overview, monthly, retention, rfm, segment_summary, country, products, scenarios, ab_test)
    build_dashboard()
    create_reports(len(transactions), overview, monthly, retention, segment_summary, country, products, scenarios, ab_test)

    print("Analysis complete.")
    print(f"Dashboard: {DASHBOARD_DIR / 'growth_dashboard.html'}")
    print(f"Executive summary: {REPORTS_DIR / 'executive_summary.md'}")


if __name__ == "__main__":
    main()
