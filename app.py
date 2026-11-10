"""Streamlit dashboard for the AI Defect Triage Copilot."""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import asdict

import streamlit as st

from defect_triage.exports import report_to_json, results_to_csv
from defect_triage.llm import triage_with_llm
from defect_triage.models import DefectReport
from defect_triage.triage import find_similar_defects, triage_defect


def _api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "")
    try:
        key = key or st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    return key or None


SAMPLE_TITLE = "Checkout times out after payment authorization"
SAMPLE_DESCRIPTION = "Steps to reproduce:\n1. Add an item to cart.\n2. Submit payment in production.\nExpected: order confirmation appears.\nActual: checkout times out after payment is authorized. Multiple customers report the issue."

st.set_page_config(page_title="AI Defect Triage Copilot", page_icon="🧭", layout="wide")
st.title("🧭 AI Defect Triage Copilot")
st.caption("Explainable defect severity and priority recommendations for quality engineering teams.")

single_tab, batch_tab, about_tab = st.tabs(["Triage a defect", "Batch triage", "About & architecture"])

with single_tab:
    st.subheader("Defect intake")
    title = st.text_input("Defect title", value=SAMPLE_TITLE)
    description = st.text_area("Description, reproduction steps, actual and expected behavior", value=SAMPLE_DESCRIPTION, height=180)
    columns = st.columns(3)
    component = columns[0].text_input("Component", value="Payments")
    customer_impact = columns[1].text_input("Customer or business impact", value="Multiple production customers; no workaround")
    environment = columns[2].text_input("Environment", value="Production · Web")
    mode = st.radio("Recommendation engine", ["Offline explainable rules", "OpenAI LLM"], horizontal=True)

    if st.button("Recommend triage", type="primary"):
        try:
            report = DefectReport(title, description, component, customer_impact, environment)
            result = triage_defect(report) if mode == "Offline explainable rules" else triage_with_llm(report, api_key=_api_key())
            similar = find_similar_defects(report)
            st.session_state["triage_payload"] = (report, result, similar)
        except Exception as exc:
            st.error(str(exc))

    if "triage_payload" in st.session_state:
        report, result, similar = st.session_state["triage_payload"]
        st.divider()
        metric_cols = st.columns(4)
        metric_cols[0].metric("Suggested severity", result.severity)
        metric_cols[1].metric("Suggested priority", result.priority)
        metric_cols[2].metric("Owner team", result.owner_team)
        metric_cols[3].metric("Confidence", f"{result.confidence:.0%}")
        st.caption(f"Source: {result.source} · Recommendations require confirmation by the defect owner.")
        st.markdown(f"**Why:** {result.rationale}")
        st.markdown(f"**Next action:** {result.recommended_next_action}")
        st.progress(result.reproduction_completeness, text=f"Reproduction detail completeness: {result.reproduction_completeness}%")
        st.markdown("**Evidence signals**")
        for signal in result.evidence:
            st.markdown(f"- {signal}")
        st.markdown("**Possible related defects**")
        if similar:
            st.dataframe(similar, use_container_width=True, hide_index=True)
            st.caption("Similarity is a lightweight text overlap hint. Confirm duplicates manually.")
        else:
            st.info("No close match found in the included sample defect list.")
        st.download_button("Download triage JSON", report_to_json(report, result, similar), "defect-triage.json", "application/json")

with batch_tab:
    st.subheader("Triage a CSV backlog")
    st.write("Upload a CSV with `title` and `description` columns. Optional columns: `component`, `customer_impact`, and `environment`. Batch mode uses offline rules so it works without credentials.")
    upload = st.file_uploader("Defect CSV", type=["csv"])
    if upload is not None:
        try:
            text = upload.getvalue().decode("utf-8-sig")
            input_rows = list(csv.DictReader(io.StringIO(text)))
            if not input_rows or "title" not in input_rows[0] or "description" not in input_rows[0]:
                st.error("The CSV needs `title` and `description` column headers and at least one defect row.")
            else:
                results = []
                for row in input_rows:
                    report = DefectReport(
                        title=row.get("title", ""),
                        description=row.get("description", ""),
                        component=row.get("component", "Unknown") or "Unknown",
                        customer_impact=row.get("customer_impact", "Unknown") or "Unknown",
                        environment=row.get("environment", "Unknown") or "Unknown",
                    )
                    result = triage_defect(report)
                    results.append({**asdict(report), **asdict(result)})
                st.dataframe([
                    {"Title": row["title"], "Severity": row["severity"], "Priority": row["priority"], "Owner": row["owner_team"], "Confidence": f"{row['confidence']:.0%}"}
                    for row in results
                ], use_container_width=True, hide_index=True)
                st.download_button("Download triaged CSV", results_to_csv(results), "triaged-defects.csv", "text/csv")
                st.download_button("Download batch JSON", json.dumps({"schema_version": "1.0", "human_review_required": True, "results": results}, indent=2), "triaged-defects.json", "application/json")
        except Exception as exc:
            st.error(f"Could not process CSV: {exc}")

with about_tab:
    st.subheader("A reviewable decision-support workflow")
    st.markdown("""
    This portfolio demo illustrates how an AI-assisted triage workflow can help a QA organization handle a growing defect backlog:

    - Recommend **severity** from customer and product impact signals.
    - Recommend **priority** from urgency, scope, and workaround context.
    - Explain the evidence and expose confidence instead of silently classifying.
    - Measure whether a report contains enough reproduction detail.
    - Suggest possible duplicates from a small sample knowledge base.
    - Export a triage recommendation for human review and downstream systems.

    The offline engine is transparent and deterministic. Optional LLM output is advisory. Neither mode closes, assigns, or reprioritizes real tickets.
    """)
    st.markdown("**Architecture:** Streamlit intake → offline rules or optional LLM → validated triage model → duplicate suggestions and exports. See `docs/architecture.md`.")

