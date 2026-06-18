"""Callbacks / Hooks for automation at specific points in the report generation process."""

from utils.logging_config import get_logger

logger = get_logger(__name__)


def on_pre_process_complete(facts: dict) -> None:
    logger.info("Pre-processing complete: client=%s, accounts=%d",
                facts["client_name"], len(facts["accounts"]))


def on_investigation_complete(facts: dict) -> None:
    logger.info("Investigation complete: disposal=%s, amount=%s, risk_profile=%s",
                facts.get("disposal"), facts.get("amount"), facts.get("risk_profile"))


def on_section_complete(title: str, content: str) -> None:
    logger.info("Section generated: '%s' (%d chars)", title, len(content))


def on_section_skipped(title: str) -> None:
    logger.info("Section skipped: '%s'", title)


def on_validation_complete(issues: list) -> None:
    if issues:
        logger.warning("Validation failed with %d issue(s) — review before sending", len(issues))
        for issue in issues:
            logger.warning("  - %s", issue)
    else:
        logger.info("Validation passed — report is clean")


def on_report_written(path: str) -> None:
    logger.info("Report written to: %s", path)