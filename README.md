# Data Validation and Schema Enforcement Service

This project demonstrates a lightweight data validation and schema enforcement workflow using Python, pandas, and Great Expectations. It validates a CSV against a small expectation suite, writes a cleaned CSV with only valid rows, and generates a self-contained HTML validation report.

## Tech
- Python 3.10+
- pandas
- great-expectations (legacy dataset API)
- pytest

## Rules (Expectation Suite)
- `age`: not null, between 0 and 120
- `email`: not null, matches a basic email regex
- `salary`: not null, greater than or equal to 0

## Quick Start

```bash
# From the project root
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run the ETL on the sample CSV
python etl_pipeline.py  # Opens a web page with raw vs cleaned reports

# Outputs
# - data/output_clean.csv: cleaned rows only
# - validation_report.html: raw dataset HTML summary with charts
# - validation_report_clean.html: cleaned dataset HTML summary with charts
# - index.html: website showing both reports side-by-side
# - great_expectations/expectations/my_suite.json: raw suite JSON
# - great_expectations/expectations/my_suite_clean.json: cleaned suite JSON
# - great_expectations/expectations/suites_index.json: pointers to both suites

# Run tests
pytest -q
```

## Notes
- This project uses Great Expectations' legacy `PandasDataset` wrapper for simple, direct expectations and access to `unexpected_index_list` for row-level filtering.
- For larger projects, consider a full Great Expectations Data Context + Checkpoint to produce rich Data Docs, data assets, and broader orchestration.
 - Running with custom input/output is supported via `run_etl()` parameters.
