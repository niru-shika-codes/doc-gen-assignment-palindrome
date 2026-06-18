"""Evaluation helpers for scoring generated reports."""

from typing import Any

from agent_pipeline.validator import validate


def evaluate_report(report: str, facts: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the generated report and return a simple score."""
    issues = validate(report, facts)

    total_checks = 6
    failed_checks = len(issues)
    passed_checks = max(total_checks - failed_checks, 0)

    return {
        "passed": failed_checks == 0,
        "score": passed_checks / total_checks,
        "passed_checks": passed_checks,
        "total_checks": total_checks,
        "issues": issues,
    }