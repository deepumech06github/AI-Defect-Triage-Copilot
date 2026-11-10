"""Serialization helpers for individual and batch defect triage results."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Iterable

from .models import DefectReport, TriageResult


def report_to_json(report: DefectReport, result: TriageResult, similar: list[dict] | None = None) -> str:
    return json.dumps({
        "schema_version": "1.0",
        "project": "AI-Defect-Triage-Copilot",
        "human_review_required": True,
        "defect": asdict(report),
        "triage_recommendation": asdict(result),
        "similar_defect_suggestions": similar or [],
    }, indent=2, ensure_ascii=False)


def results_to_csv(rows: Iterable[dict]) -> str:
    output = io.StringIO(newline="")
    fields = ["title", "description", "component", "customer_impact", "environment", "severity", "priority", "owner_team", "confidence", "reproduction_completeness", "rationale", "recommended_next_action", "source"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()

