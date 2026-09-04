from fabric_poc_automation.validation import evaluate_run_summary


def test_validation_passes_complete_summary() -> None:
    checks = evaluate_run_summary({
        "input_rows": 10,
        "output_rows": 10,
        "package_version": "0.1.0",
        "executor_import_ok": True,
        "partitions": 4,
    })
    assert {item["status"] for item in checks} == {"PASS"}


def test_validation_reports_failures() -> None:
    checks = evaluate_run_summary({
        "input_rows": 10,
        "output_rows": 9,
        "package_version": None,
        "executor_import_ok": False,
        "partitions": 1,
    })
    assert all(item["status"] == "FAIL" for item in checks)
