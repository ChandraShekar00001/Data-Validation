import pandas as pd
from pathlib import Path

from etl_pipeline import run_etl


def test_run_etl_creates_clean_data(tmp_path: Path):
    # Prepare a small CSV with mixed validity
    input_csv = tmp_path / "input.csv"
    input_csv.write_text(
        """id,age,email,salary
1,25,test@example.com,50000
2,-1,bademail,-100
3,130,none@invalid,30000
4,40,,70000
5,30,valid.user@domain.com,0
""",
        encoding="utf-8",
    )

    output_csv = tmp_path / "output.csv"
    report_html = tmp_path / "report.html"
    suite_json = tmp_path / "suite.json"

    out_path = run_etl(input_csv, output_csv, report_html, suite_json)

    assert out_path.exists()
    assert report_html.exists()
    assert suite_json.exists()

    clean = pd.read_csv(out_path)

    # Only rows 1 and 5 should be valid according to rules
    assert len(clean) == 2
    assert clean["age"].between(0, 120).all()
    assert (clean["salary"] >= 0).all()
    assert clean["email"].str.contains("@").all()
