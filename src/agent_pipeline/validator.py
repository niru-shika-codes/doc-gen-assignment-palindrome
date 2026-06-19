"""Validation agent: checks the generated report against source facts."""

from utils.callbacks import on_validation_complete
from utils.logging_config import get_logger

logger = get_logger(__name__)


def validate(report: str, facts: dict) -> list[str]:
    """
    Run deterministic checks against the generated report.
    Returns a list of issues found. Empty list means all checks passed.
    """
    logger.info("Starting validation checks")

    issues: list[str] = []

    issues.extend(_check_client_name(report, facts))
    issues.extend(_check_risk_warning(report))
    issues.extend(_check_fca_line(report))
    issues.extend(_check_tbc_markers(report))
    issues.extend(_check_tax_section(report, facts))
    issues.extend(_check_account_values(report, facts))
    issues.extend(_check_scoped_account_values(report, facts))
    issues.extend(_check_unsupported_claims(report))

    on_validation_complete(issues)

    return issues


def _check_client_name(report: str, facts: dict) -> list[str]:
    name = facts.get("client_name", "")
    if name and name not in report:
        return [f"Client name '{name}' not found in report"]
    return []


def _check_risk_warning(report: str) -> list[str]:
    warning = (
        "The value of investments can fall as well as rise "
        "and you may get back less than you invest. "
        "Past performance is not a guide to future returns."
    )

    if warning not in report:
        return ["Risk warning missing - please include the exact wording in the report"]

    return []


def _check_fca_line(report: str) -> list[str]:
    fca_line = "This firm is authorised and regulated by the Financial Conduct Authority."

    if fca_line not in report:
        return ["FCA authorisation line missing - please include the exact wording in the report"]

    return []


def _check_tbc_markers(report: str) -> list[str]:
    if "[TBC - REQUIRES HUMAN REVIEW]" not in report:
        return ["No TBC markers found — please ensure all fees are marked for human review"]
    return []


def _check_tax_section(report: str, facts: dict) -> list[str]:
    issues: list[str] = []

    disposal = facts.get("disposal", False)
    has_tax_section = "## Tax Implications" in report

    if not disposal and has_tax_section:
        issues.append("Tax Implications section present but no disposal involved")

    if disposal and not has_tax_section:
        issues.append("Tax Implications section missing but disposal is involved")

    return issues


def _check_account_values(report: str, facts: dict) -> list[str]:
    """All scoped account values should appear in the report."""
    issues: list[str] = []

    accounts = facts.get("scoped_accounts") or facts.get("accounts", [])

    for account in accounts:
        value = account.get("value")

        if value is None:
            continue

        formatted = f"£{int(value):,}"

        if formatted not in report:
            issues.append(f"Account value {formatted} not found in report")

    return issues


def _check_scoped_account_values(report: str, facts: dict) -> list[str]:
    """Accounts outside the report scope should not appear in the accounts table."""
    issues: list[str] = []

    scoped_ids = {
        account.get("account_id")
        for account in facts.get("scoped_accounts", [])
    }

    for account in facts.get("accounts", []):
        account_id = account.get("account_id")
        value = account.get("value")

        if account_id in scoped_ids or value is None:
            continue

        formatted = f"£{int(value):,}"

        if formatted in report:
            issues.append(
                f"Out-of-scope account value {formatted} appears in report"
            )

    return issues


def _check_unsupported_claims(report: str) -> list[str]:
    """Detect risky claims that are commonly hallucinated by LLMs."""
    issues: list[str] = []
    report_lower = report.lower()

    unsupported_phrases = [
        # Charges / fees
        "no initial charge",
        "no initial charges",
        "there are no charges",
        "no charges",
        "0% charge",
        "0% initial charge",
        "free of charge",

        # Performance / guarantees
        "guaranteed return",
        "guaranteed returns",
        "capital guaranteed",
        "risk-free",
        "risk free",
        "will grow",
        "will increase",
        "will perform",
        "outperform",
        "enhanced returns",
        "strong returns",

        # Tax overclaims
        "no tax liability",
        "will not trigger tax",
        "no capital gains tax",

        # Overconfident advice language
        "best option",
        "perfectly suited",
        "no downside",
    ]

    for phrase in unsupported_phrases:
        if phrase in report_lower:
            issues.append(f"Possible unsupported claim detected: '{phrase}'")

    return issues