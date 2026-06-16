# Data

This project uses the UCI Machine Learning Repository Online Retail II dataset.

Source URL: https://archive.ics.uci.edu/dataset/502/online+retail+ii

Raw data is not committed because the Excel file is large. Recreate the raw and processed files with:

```bash
python scripts/download_data.py
python scripts/prepare_data.py
python scripts/run_analysis.py
```

In this Codex workspace, the raw Excel file was downloaded to `../../work/data_raw/online_retail_II.xlsx`, and `scripts/prepare_data.py` can discover it automatically.
