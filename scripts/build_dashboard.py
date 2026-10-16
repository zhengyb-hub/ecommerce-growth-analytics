"""Build the self-contained, source-backed portfolio dashboard from committed aggregates."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


def records(name: str) -> list[dict]:
    return json.loads(pd.read_csv(DATA / name).to_json(orient="records", date_format="iso"))


def build_dashboard() -> Path:
    payload = {
        "overview": records("overview_metrics.csv")[0],
        "monthly": records("monthly_kpis.csv"),
        "cohorts": records("cohort_retention_long.csv"),
        "segments": records("rfm_segment_summary.csv"),
        "countries": records("country_performance.csv")[:10],
        "scenarios": records("growth_scenarios.csv"),
        "experiment": records("ab_test_design.csv")[0],
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    template = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
    html = template.replace("/* PLOTLY_BUNDLE */", get_plotlyjs()).replace("/* DASHBOARD_DATA */", data_json)
    for destination in (ROOT / "dashboard" / "growth_dashboard.html", ROOT / "docs" / "index.html"):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")
    return ROOT / "dashboard" / "growth_dashboard.html"


if __name__ == "__main__":
    print(build_dashboard())
