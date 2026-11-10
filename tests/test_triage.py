from defect_triage.models import DefectReport
from defect_triage.triage import find_similar_defects, triage_defect


def test_production_payment_failure_gets_urgent_recommendation():
    report = DefectReport(
        title="Checkout times out after payment authorization",
        description="Multiple customers in production cannot complete checkout; payment may already be authorized.",
        component="Payments",
        customer_impact="Revenue impact, no workaround",
        environment="Production",
    )

    result = triage_defect(report)

    assert result.severity in {"Critical", "High"}
    assert result.priority == "P1"
    assert result.owner_team == "Payments"
    assert result.confidence > 0.5


def test_cosmetic_issue_is_low_priority():
    result = triage_defect(DefectReport("Avatar alignment typo", "Minor spacing and alignment issue on profile page."))

    assert result.severity == "Low"
    assert result.priority == "P4"


def test_missing_steps_are_called_out():
    result = triage_defect(DefectReport("Sign in fails", "Users cannot sign in.", environment="Unknown"))

    assert result.reproduction_completeness < 60
    assert "Request missing reproduction steps" in result.recommended_next_action


def test_related_defect_suggestion_uses_text_similarity():
    report = DefectReport("Checkout payment timeout", "Payment authorization completes but checkout returns a timeout.", "Payments")

    matches = find_similar_defects(report)

    assert matches
    assert matches[0]["defect_id"] == "DEF-1042"

