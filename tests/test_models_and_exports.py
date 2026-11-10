import json

import pytest

from defect_triage.exports import report_to_json, results_to_csv
from defect_triage.models import DefectReport, TriageResult
from defect_triage.triage import triage_defect


def test_defect_report_requires_title_and_description():
    with pytest.raises(ValueError, match="title"):
        DefectReport("", "Description")


def test_json_export_marks_human_review_required():
    report = DefectReport("Sign-in fails", "Users cannot sign in.")
    result = triage_defect(report)
    payload = json.loads(report_to_json(report, result))

    assert payload["human_review_required"] is True
    assert payload["triage_recommendation"]["priority"] in {"P1", "P2", "P3", "P4"}


def test_csv_export_writes_header_and_result_row():
    report = DefectReport("Sign-in fails", "Users cannot sign in.")
    result = triage_defect(report)
    csv_text = results_to_csv([{**report.__dict__, **result.__dict__}])

    assert "severity,priority" in csv_text
    assert "Sign-in fails" in csv_text

