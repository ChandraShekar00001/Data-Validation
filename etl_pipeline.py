from __future__ import annotations

import json
from pathlib import Path
import webbrowser
from typing import Dict, List, Tuple

import pandas as pd

# Great Expectations (legacy dataset API kept for simple, programmatic expectations)
try:
    import great_expectations as ge
    from great_expectations.dataset import PandasDataset  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Great Expectations is required. Please install via requirements.txt"
    ) from e


EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _apply_expectations(dataset: PandasDataset) -> List[Tuple[str, Dict]]:
    """Apply expectation rules and return list of (name, result) dicts.

    Expectations implemented:
    - age: not null, between 0 and 120
    - email: not null, matches email regex
    - salary: not null, >= 0
    """
    results: List[Tuple[str, Dict]] = []

    results.append((
        "age_not_null",
        dataset.expect_column_values_to_not_be_null("age", result_format="COMPLETE"),
    ))
    results.append((
        "age_between",
        dataset.expect_column_values_to_be_between(
            "age", min_value=0, max_value=120, result_format="COMPLETE"
        ),
    ))
    results.append((
        "email_not_null",
        dataset.expect_column_values_to_not_be_null("email", result_format="COMPLETE"),
    ))
    results.append((
        "email_regex",
        dataset.expect_column_values_to_match_regex(
            "email", EMAIL_REGEX, result_format="COMPLETE"
        ),
    ))
    results.append((
        "salary_not_null",
        dataset.expect_column_values_to_not_be_null("salary", result_format="COMPLETE"),
    ))
    results.append((
        "salary_non_negative",
        dataset.expect_column_values_to_be_between(
            "salary", min_value=0, max_value=None, strict_min=False, result_format="COMPLETE"
        ),
    ))

    return results


def _collect_failing_indices(expectation_results: List[Tuple[str, Dict]]) -> List[int]:
    failing: set[int] = set()
    for name, res in expectation_results:
        idxs = (
            res.get("result", {}).get("unexpected_index_list")
            if isinstance(res, dict)
            else None
        )
        if idxs:
            failing.update(int(i) for i in idxs)
    return sorted(failing)


def _write_expectation_suite(dataset: PandasDataset, suite_path: Path) -> None:
    suite = dataset.get_expectation_suite(discard_failed_expectations=False)
    # GE suites provide JSON serialization helpers; keep fallback for versions
    try:
        payload = suite.to_json_dict()  # type: ignore[attr-defined]
    except Exception:
        payload = json.loads(suite.to_json())  # type: ignore[attr-defined]
    suite_path.parent.mkdir(parents=True, exist_ok=True)
    suite_path.write_text(json.dumps(payload, indent=2))


def _render_html_report(
    expectation_results: List[Tuple[str, Dict]],
    total_rows: int,
    output_html: Path,
) -> None:
    """Write a polished, self-contained HTML report with clear percentages.

    Visualization shows invalid% (red) and valid% (green) per expectation,
    plus a summary header with totals.
    """
    if total_rows <= 0:
        total_rows = 1  # avoid division by zero; will render 0% invalid

    # Summaries
    total_expectations = len(expectation_results)
    passed_count = sum(1 for _, r in expectation_results if r.get("success", False))
    failed_count = total_expectations - passed_count
    overall_passed = failed_count == 0

    rows = []
    total_unexpected_all = 0
    for name, res in expectation_results:
        success = res.get("success", False)
        uc = int(res.get("result", {}).get("unexpected_count", 0) or 0)
        total_unexpected_all += uc
        invalid_pct = max(0.0, min(100.0, (uc / total_rows) * 100.0))
        valid_pct = 100.0 - invalid_pct
        rows.append((name, success, uc, invalid_pct, valid_pct))

    html_parts = [
        "<html><head><meta charset='utf-8'><title>Validation Report</title>",
        "<style>body{font-family:'Segoe UI',Arial;margin:16px;color:#222} h2{margin-top:0} .summary{display:flex;gap:18px;flex-wrap:wrap;margin:8px 0 12px} .chip{background:#f5f5f5;border:1px solid #e5e5e5;border-radius:18px;padding:6px 10px;font-size:13px} .ok{color:#0a0} .fail{color:#a00} table{border-collapse:collapse;margin-top:12px;width:900px;max-width:100%} th,td{border:1px solid #ddd;padding:10px} th{background:#f5f5f5;text-align:left} .bar{height:14px;background:#f0f0f0;border-radius:7px;overflow:hidden;position:relative} .seg-invalid{background:#ff6b6b;height:100%;display:inline-block} .seg-valid{background:#30b15a;height:100%;display:inline-block} .pct{font-size:12px;color:#444;margin-left:8px}</style>",
        "</head><body>",
        f"<h2>Great Expectations Validation Report</h2>",
        "<div class='summary'>",
        f"<span class='chip'>Rows: <b>{total_rows}</b></span>",
        f"<span class='chip'>Expectations: <b>{total_expectations}</b></span>",
        f"<span class='chip'>Passed: <b class='ok'>{passed_count}</b></span>",
        f"<span class='chip'>Failed: <b class='fail'>{failed_count}</b></span>",
        f"<span class='chip'>Unexpected total: <b>{total_unexpected_all}</b></span>",
        f"<span class='chip'>Overall: <b class='{ 'ok' if overall_passed else 'fail' }'>{'PASSED' if overall_passed else 'FAILED'}</b></span>",
        "</div>",
        "<table><thead><tr><th>Expectation</th><th>Status</th><th>Unexpected</th><th>Invalid %</th><th>Valid %</th><th>Visualization</th></tr></thead><tbody>",
    ]
    for name, success, uc, inv_pct, val_pct in rows:
        cls = "ok" if success else "fail"
        html_parts.append(
            f"<tr><td>{name}</td><td class='{cls}'>{'PASSED' if success else 'FAILED'}</td><td>{uc}</td>"
            f"<td>{inv_pct:.1f}%</td><td>{val_pct:.1f}%</td>"
            f"<td><div class='bar'><span class='seg-invalid' style='width:{inv_pct:.1f}%'></span><span class='seg-valid' style='width:{val_pct:.1f}%'></span></div></td></tr>"
        )

    html_parts.extend([
        "</tbody></table>",
        "</body></html>",
    ])
    output_html.write_text("\n".join(html_parts), encoding="utf-8")


def _create_index_page(
    report_html: Path,
    clean_report_html: Path,
    input_path: Path,
    output_path: Path,
    index_path: Path,
) -> None:
    index_html = f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Data Validation Reports</title>
<style>body{{font-family:'Segoe UI',Arial;margin:0;background:#f7f7f9}}header{{padding:16px 20px;background:#fff;border-bottom:1px solid #e5e5e5}}header h1{{margin:0 0 6px 0;font-size:22px}}header p{{margin:4px 0;color:#444}}.links a{{margin-right:12px;color:#0366d6;text-decoration:none}}.links a:hover{{text-decoration:underline}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}}section{{background:#fff;border:1px solid #e5e5e5;border-radius:6px}}section h2{{margin:10px 12px;font-size:18px}}iframe{{width:100%;height:78vh;border:0;border-top:1px solid #eee}}</style>
</head><body>
<header>
  <h1>Data Validation Reports</h1>
  <p>Left: Raw dataset. Right: Cleaned dataset.</p>
  <p class=\"links\">
    <a href=\"{report_html.name}\" target=\"_blank\">Raw Report</a>
    <a href=\"{clean_report_html.name}\" target=\"_blank\">Cleaned Report</a>
    <a href=\"{input_path.as_posix()}\" target=\"_blank\">Input CSV</a>
    <a href=\"{output_path.as_posix()}\" target=\"_blank\">Clean CSV</a>
  </p>
</header>
<div class=\"grid\">
  <section>
    <h2>Raw Validation</h2>
    <iframe src=\"{report_html.name}\"></iframe>
  </section>
  <section>
    <h2>Cleaned Validation</h2>
    <iframe src=\"{clean_report_html.name}\"></iframe>
  </section>
</div>
</body></html>"""
    index_path.write_text(index_html, encoding="utf-8")


def run_etl(
    input_path: str | Path,
    output_path: str | Path,
    report_html: str | Path = "validation_report.html",
    suite_save_path: str | Path = "great_expectations/expectations/my_suite.json",
    clean_report_html: str | Path = "validation_report_clean.html",
    suite_clean_save_path: str | Path = "great_expectations/expectations/my_suite_clean.json",
    suites_index_path: str | Path = "great_expectations/expectations/suites_index.json",
    open_browser: bool = False,
) -> Path:
    """Run ETL: read CSV, validate with Great Expectations, write clean data.

    - Generates an HTML validation report at `report_html`.
    - Exports the created expectation suite JSON to `suite_save_path`.

    Returns the output CSV path.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    report_html = Path(report_html)
    suite_save_path = Path(suite_save_path)

    df = pd.read_csv(input_path)

    # Use GE PandasDataset wrapper
    dataset = PandasDataset(df)

    expectation_results = _apply_expectations(dataset)

    # Save suite for traceability
    _write_expectation_suite(dataset, suite_save_path)

    # Compute row-level validity using explicit pandas rules
    email_regex = EMAIL_REGEX
    mask = (
        df["age"].notna()
        & (df["age"] >= 0)
        & (df["age"] <= 120)
        & df["email"].notna()
        & df["email"].astype(str).str.match(email_regex)
        & df["salary"].notna()
        & (df["salary"] >= 0)
    )
    clean_df = df[mask]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False)

    # Emit a simple HTML report summarizing validation results (raw dataset)
    _render_html_report(expectation_results, total_rows=len(df), output_html=report_html)

    # Produce a second report for the cleaned dataset to demonstrate the effect
    dataset_clean = PandasDataset(clean_df)
    expectation_results_clean = _apply_expectations(dataset_clean)
    _write_expectation_suite(dataset_clean, Path(suite_clean_save_path))
    _render_html_report(
        expectation_results_clean, total_rows=len(clean_df), output_html=Path(clean_report_html)
    )

    # Write a combined suites index for convenience
    suites_index = {
        "raw_suite": str(Path(suite_save_path)),
        "clean_suite": str(Path(suite_clean_save_path)),
    }
    Path(suites_index_path).parent.mkdir(parents=True, exist_ok=True)
    Path(suites_index_path).write_text(json.dumps(suites_index, indent=2), encoding="utf-8")

    # Create an index page to view both reports side-by-side
    index_path = Path("index.html")
    _create_index_page(Path(report_html), Path(clean_report_html), Path(input_path), Path(output_path), index_path)

    if open_browser:
        # Open the index page after execution
        webbrowser.open(index_path.resolve().as_uri())

    return output_path


if __name__ == "__main__":
    base = Path(__file__).parent
    run_etl(
        base / "data" / "input.csv",
        base / "data" / "output_clean.csv",
        report_html=base / "validation_report.html",
        clean_report_html=base / "validation_report_clean.html",
        suite_clean_save_path=base / "great_expectations" / "expectations" / "my_suite_clean.json",
        suites_index_path=base / "great_expectations" / "expectations" / "suites_index.json",
        open_browser=True,
    )
