from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from urllib.request import urlretrieve


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ZIP_PATH = RAW_DIR / "online_retail_ii.zip"
EXCEL_PATH = RAW_DIR / "online_retail_II.xlsx"


def download(force: bool = False) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if EXCEL_PATH.exists() and not force:
        print(f"Raw Excel already exists: {EXCEL_PATH}")
        return EXCEL_PATH

    if force or not ZIP_PATH.exists():
        print(f"Downloading {DATA_URL}")
        urlretrieve(DATA_URL, ZIP_PATH)
        print(f"Saved archive to {ZIP_PATH}")

    print(f"Extracting {ZIP_PATH}")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(RAW_DIR)

    if not EXCEL_PATH.exists():
        matches = list(RAW_DIR.glob("*.xlsx"))
        if not matches:
            raise FileNotFoundError("No .xlsx file found after extracting the UCI archive.")
        return matches[0]

    print(f"Raw Excel ready: {EXCEL_PATH}")
    return EXCEL_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the UCI Online Retail II dataset.")
    parser.add_argument("--force", action="store_true", help="Re-download and re-extract the archive.")
    args = parser.parse_args()
    download(force=args.force)


if __name__ == "__main__":
    main()
