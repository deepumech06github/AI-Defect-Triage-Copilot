"""Validated models for defect reports and triage recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SEVERITIES = {"Critical", "High", "Medium", "Low"}
PRIORITIES = {"P1", "P2", "P3", "P4"}


@dataclass(frozen=True)
class DefectReport:
    title: str
    description: str
    component: str = "Unknown"
    customer_impact: str = "Unknown"
    environment: str = "Unknown"

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("A defect title is required.")
        if not self.description.strip():
            raise ValueError("A defect description is required.")

    def searchable_text(self) -> str:
        return " ".join((self.title, self.description, self.component, self.customer_impact))


@dataclass(frozen=True)
class TriageResult:
    severity: str
    priority: str
    owner_team: str
    rationale: str
    evidence: list[str]
    reproduction_completeness: int
    confidence: float
    recommended_next_action: str
    source: str = "Offline rules"

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unsupported severity: {self.severity}")
        if self.priority not in PRIORITIES:
            raise ValueError(f"Unsupported priority: {self.priority}")
        if not 0 <= self.reproduction_completeness <= 100:
            raise ValueError("Reproduction completeness must be between 0 and 100.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

