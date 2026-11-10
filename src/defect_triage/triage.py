"""Transparent rules-based defect triage and duplicate suggestion helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DefectReport, TriageResult


SEVERITY_RULES = [
    ("Critical", re.compile(r"data loss|data corruption|security breach|unauthori[sz]ed|production outage|all users|service unavailable", re.I)),
    ("High", re.compile(r"crash|cannot|can't|unable to|blocked|checkout|payment|sign[ -]?in|login", re.I)),
    ("Medium", re.compile(r"incorrect|wrong|fail(?:s|ed|ure)?|error|timeout|slow|intermittent|degraded", re.I)),
    ("Low", re.compile(r"typo|cosmetic|spacing|alignment|color|colour|minor", re.I)),
]

TEAM_RULES = [
    ("Payments", re.compile(r"payment|checkout|billing|charge|refund|invoice", re.I)),
    ("Identity", re.compile(r"login|sign[ -]?in|password|session|authentication|account", re.I)),
    ("API Platform", re.compile(r"api|endpoint|http|service|backend|response code", re.I)),
    ("Mobile", re.compile(r"android|ios|mobile app|push notification", re.I)),
    ("Web Experience", re.compile(r"browser|web page|frontend|front-end|layout|button|screen", re.I)),
]

STOP_WORDS = {"the", "and", "for", "with", "that", "this", "from", "when", "then", "user", "users", "into", "after", "before", "does", "not", "are", "was", "has", "have", "can", "will", "should", "could", "would", "issue", "bug", "error"}


@dataclass(frozen=True)
class KnownDefect:
    defect_id: str
    title: str
    description: str
    component: str

    def searchable_text(self) -> str:
        return " ".join((self.title, self.description, self.component))


KNOWN_DEFECTS = [
    KnownDefect("DEF-1042", "Checkout times out after payment authorization", "Some shoppers see a timeout after a payment is authorized and may retry checkout.", "Payments"),
    KnownDefect("DEF-1088", "Session expires during account sign-in", "A subset of users are returned to the login screen while signing in after a long idle period.", "Identity"),
    KnownDefect("DEF-1116", "Profile avatar is incorrectly aligned on mobile", "The profile image is shifted on smaller Android and iOS screens. No data is affected.", "Mobile"),
    KnownDefect("DEF-1170", "Order API intermittently returns a server error", "The order endpoint occasionally returns HTTP 500 under high request volume.", "API Platform"),
]


def triage_defect(report: DefectReport) -> TriageResult:
    """Return an explainable severity, priority, ownership, and completeness score."""

    text = report.searchable_text()
    matched = [(severity, pattern.search(text)) for severity, pattern in SEVERITY_RULES]
    evidence = [severity_match.group(0) for _, severity_match in matched if severity_match]
    severity = next((level for level, match in matched if match), "Medium")

    impact_text = f"{report.customer_impact} {report.description}".lower()
    production_scope = any(term in impact_text for term in ("production", "all customers", "all users", "multiple customers", "revenue", "data loss"))
    workaround = any(term in impact_text for term in ("workaround", "temporary fix", "alternate path"))
    if severity == "Critical":
        priority = "P1"
    elif severity == "High":
        priority = "P1" if production_scope else "P2"
    elif severity == "Medium":
        priority = "P2" if production_scope and not workaround else "P3"
    else:
        priority = "P3" if production_scope else "P4"

    owner_team = report.component.strip() if report.component.strip().lower() not in {"", "unknown", "other"} else next(
        (team for team, pattern in TEAM_RULES if pattern.search(text)), "QE Triage"
    )
    completeness = _reproduction_completeness(report)
    filled_context = sum(value.strip().lower() not in {"", "unknown", "n/a"} for value in (report.component, report.customer_impact, report.environment))
    confidence = min(0.92, 0.42 + (0.10 * len(evidence)) + (0.07 * filled_context) + (0.001 * completeness))
    rationale = _rationale(severity, priority, production_scope, workaround, evidence)
    next_action = _next_action(severity, priority, completeness)

    return TriageResult(
        severity=severity,
        priority=priority,
        owner_team=owner_team,
        rationale=rationale,
        evidence=evidence or ["No strong impact keyword detected; severity defaults to Medium pending review."],
        reproduction_completeness=completeness,
        confidence=round(confidence, 2),
        recommended_next_action=next_action,
    )


def _reproduction_completeness(report: DefectReport) -> int:
    text = report.description.lower()
    score = 0
    if re.search(r"steps to reproduce|reproduction steps|\bsteps?:\s*\n?\s*(?:1[.)]|-)", text):
        score += 40
    if any(marker in text for marker in ("expected:", "expected result", "actual:", "actual result")):
        score += 25
    if report.environment.strip().lower() not in {"", "unknown", "n/a"} or any(term in text for term in ("chrome", "firefox", "safari", "android", "ios", "staging", "production")):
        score += 20
    if report.customer_impact.strip().lower() not in {"", "unknown", "n/a"}:
        score += 15
    return min(100, score)


def _rationale(severity: str, priority: str, production_scope: bool, workaround: bool, evidence: list[str]) -> str:
    signal_text = ", ".join(evidence) if evidence else "limited impact detail"
    scope = "Production or broad customer impact is indicated" if production_scope else "Broad production impact is not clearly stated"
    recovery = "A workaround is mentioned" if workaround else "No workaround is identified"
    return f"{severity} severity is suggested from: {signal_text}. {scope}; {recovery}. Set {priority} priority for the proposed response urgency."


def _next_action(severity: str, priority: str, completeness: int) -> str:
    if severity == "Critical" or priority == "P1":
        action = "Confirm customer scope and engage the owning team for immediate incident assessment."
    elif severity == "High":
        action = "Reproduce with the owning team and assess the next release or hotfix window."
    else:
        action = "Confirm expected behavior and schedule with the owning team using customer impact and release risk."
    if completeness < 60:
        action += " Request missing reproduction steps, actual/expected results, and environment details."
    return action


def find_similar_defects(report: DefectReport, known_defects: list[KnownDefect] | None = None, limit: int = 3) -> list[dict[str, str | float]]:
    """Return simple token-overlap suggestions, not automatic duplicate decisions."""

    query_tokens = _tokens(report.searchable_text())
    matches = []
    for defect in known_defects if known_defects is not None else KNOWN_DEFECTS:
        candidate_tokens = _tokens(defect.searchable_text())
        union = query_tokens | candidate_tokens
        score = len(query_tokens & candidate_tokens) / len(union) if union else 0.0
        if score >= 0.08:
            matches.append({"defect_id": defect.defect_id, "title": defect.title, "component": defect.component, "similarity": round(score, 3)})
    return sorted(matches, key=lambda item: float(item["similarity"]), reverse=True)[:limit]


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in STOP_WORDS}

