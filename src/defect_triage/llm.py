"""Optional OpenAI-backed triage. Offline rules remain available without it."""

from __future__ import annotations

import json
import os
from typing import Any

from .models import DefectReport, TriageResult


SYSTEM_PROMPT = """You are a quality engineering defect triage assistant. Recommend, do not decide: human owners retain severity and priority authority. Distinguish customer/business severity from response urgency. Do not infer impact that the report does not state; flag missing facts and lower confidence when evidence is weak. Return only a JSON object with: severity (Critical/High/Medium/Low), priority (P1/P2/P3/P4), owner_team, rationale, evidence (array of strings), reproduction_completeness (integer 0-100), confidence (number 0-1), recommended_next_action. Use P1 for urgent broad production/customer/security/data-loss impact; otherwise choose a reasoned priority."""


def triage_with_llm(report: DefectReport, api_key: str | None = None, model: str | None = None) -> TriageResult:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY to use the optional LLM mode.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('Install the optional dependency with: pip install -e ".[llm]"') from exc

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(report.__dict__, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The LLM returned an empty triage response.")
    payload: dict[str, Any] = json.loads(content)
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        raise ValueError("LLM evidence must be an array of strings.")
    try:
        confidence = float(payload.get("confidence", 0.0))
        completeness = int(payload.get("reproduction_completeness", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("LLM confidence and completeness must be numeric.") from exc
    return TriageResult(
        severity=str(payload.get("severity", "")),
        priority=str(payload.get("priority", "")),
        owner_team=str(payload.get("owner_team", "QE Triage")),
        rationale=str(payload.get("rationale", "")),
        evidence=evidence,
        reproduction_completeness=completeness,
        confidence=confidence,
        recommended_next_action=str(payload.get("recommended_next_action", "Review with the owning team.")),
        source="OpenAI LLM",
    )

