from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_EXCEL_CANDIDATES = [
    PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx",
    PROJECT_ROOT.parent.parent / "work" / "data_raw" / "online_retail_II.xlsx",
]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TRANSACTIONS_CSV = PROCESSED_DIR / "transactions_clean.csv"
SQLITE_PATH = PROCESSED_DIR / "growth_analytics.sqlite"


def find_raw_excel(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Raw Excel file not found: {path}")
        return path

    for path in RAW_EXCEL_CANDIDATES:
        if path.exists():
            return path

    searched = "\n".join(str(path) for path in RAW_EXCEL_CANDIDATES)
    raise FileNotFoundError(
        "Could not find online_retail_II.xlsx. Run scripts/download_data.py first, "
        "or pass --raw-excel.\nSearched:\n" + searched
    )


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Invoice": "invoice_no",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "InvoiceDate": "invoice_date",
        "Price": "unit_price",
        "UnitPrice": "unit_price",
        "Customer ID": "customer_id",
        "CustomerID": "customer_id",
        "Country": "country",
    }
    normalized = frame.rename(columns=rename_map)
    required = [
        "invoice_no",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
    ]
    missing = [column for column in required if column not in normalized.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return normalized[required + [column for column in normalized.columns if column == "source_sheet"]]


def read_raw_excel(path: Path) -> pd.DataFrame:
    workbook = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []
    for sheet_name in workbook.sheet_names:
        print(f"Reading sheet: {sheet_name}")
        frame = pd.read_excel(path, sheet_name=sheet_name)
        frame["source_sheet"] = sheet_name
        frames.append(standardize_columns(frame))
    return pd.concat(frames, ignore_index=True)


def clean_transactions(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    data = raw.copy()
    data["invoice_no"] = data["invoice_no"].astype("string").str.strip()
    data["stock_code"] = data["stock_code"].astype("string").str.strip()
    data["description"] = data["description"].astype("string").str.strip()
    data["country"] = data["country"].astype("string").str.strip()
    data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    data["unit_price"] = pd.to_numeric(data["unit_price"], errors="coerce")
    data["customer_id"] = pd.to_numeric(data["customer_id"], errors="coerce")
    data["invoice_date"] = pd.to_datetime(data["invoice_date"], errors="coerce")

    invoice_text = data["invoice_no"].fillna("").str.upper()
    data["is_cancellation"] = invoice_text.str.startswith("C") | (data["quantity"] < 0)
    data["line_revenue"] = data["quantity"] * data["unit_price"]

    quality_summary = {
        "raw_rows": int(len(data)),
        "missing_customer_rows": int(data["customer_id"].isna().sum()),
        "cancellation_or_return_rows": int(data["is_cancellation"].sum()),
        "non_positive_quantity_rows": int((data["quantity"] <= 0).sum()),
        "non_positive_price_rows": int((data["unit_price"] <= 0).sum()),
        "invalid_date_rows": int(data["invoice_date"].isna().sum()),
    }

    valid = (
        data["customer_id"].notna()
        & data["invoice_date"].notna()
        & (~data["is_cancellation"])
        & (data["quantity"] > 0)
        & (data["unit_price"] > 0)
    )
    clean = data.loc[valid].copy()
    clean["customer_id"] = clean["customer_id"].astype("int64")
    clean["quantity"] = clean["quantity"].astype("int64")
    clean["invoice_month"] = clean["invoice_date"].dt.to_period("M").dt.to_timestamp()
    clean["invoice_date"] = clean["invoice_date"].dt.floor("s")
    clean = clean.sort_values(["invoice_date", "invoice_no", "stock_code"]).reset_index(drop=True)

    output_columns = [
        "invoice_no",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "invoice_month",
        "unit_price",
        "line_revenue",
        "customer_id",
        "country",
        "source_sheet",
    ]
    return clean[output_columns], quality_summary


def write_sqlite(transactions: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_frame = transactions.copy()
    sqlite_frame["invoice_date"] = sqlite_frame["invoice_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    sqlite_frame["invoice_month"] = sqlite_frame["invoice_month"].dt.strftime("%Y-%m-%d")

    with sqlite3.connect(path) as connection:
        sqlite_frame.to_sql("transactions", connection, if_exists="replace", index=False, chunksize=50000)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_transactions_invoice ON transactions(invoice_no)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_transactions_month ON transactions(invoice_month)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_transactions_country ON transactions(country)")


def write_data_dictionary(path: Path, quality_summary: dict[str, int], clean_rows: int) -> None:
    lines = [
        "# Data Dictionary",
        "",
        "Source: UCI Machine Learning Repository, Online Retail II.",
        "",
        "Cleaning rules:",
        "- Removed rows without customer_id.",
        "- Removed cancellations and returns, identified by invoice numbers beginning with C or negative quantity.",
        "- Removed rows with non-positive quantity or unit price.",
        "- Created line_revenue as quantity * unit_price.",
        "- Created invoice_month as the first day of the invoice month.",
        "",
        "Row quality summary:",
    ]
    for key, value in quality_summary.items():
        lines.append(f"- {key}: {value:,}")
    lines.append(f"- clean_rows: {clean_rows:,}")
    lines.extend(
        [
            "",
            "Core fields:",
            "- invoice_no: order or invoice identifier.",
            "- stock_code: product identifier.",
            "- description: product name.",
            "- quantity: units purchased on the invoice line.",
            "- invoice_date: timestamp of the transaction.",
            "- invoice_month: month bucket used for cohort and KPI analysis.",
            "- unit_price: product unit price in GBP.",
            "- line_revenue: quantity multiplied by unit_price.",
            "- customer_id: anonymized customer identifier.",
            "- country: customer country.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Online Retail II and create analysis-ready files.")
    parser.add_argument("--raw-excel", help="Path to online_retail_II.xlsx.")
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_excel = find_raw_excel(args.raw_excel)
    print(f"Using raw data: {raw_excel}")

    raw = read_raw_excel(raw_excel)
    transactions, quality_summary = clean_transactions(raw)

    print(f"Writing clean transactions: {TRANSACTIONS_CSV}")
    transactions.to_csv(TRANSACTIONS_CSV, index=False)

    print(f"Writing SQLite database: {SQLITE_PATH}")
    write_sqlite(transactions, SQLITE_PATH)

    write_data_dictionary(PROCESSED_DIR / "data_dictionary.md", quality_summary, clean_rows=len(transactions))
    print("Data preparation complete.")


if __name__ == "__main__":
    main()
