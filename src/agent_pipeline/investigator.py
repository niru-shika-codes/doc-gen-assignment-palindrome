"""Investigation agent: reads client files and extracts structured facts."""

import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from document_formatter.loading import read_docx, read_file
from utils.callbacks import on_investigation_complete, on_pre_process_complete
from utils.logging_config import get_logger

logger = get_logger(__name__)


INVESTIGATION_PROMPT = """
Read the meeting notes and report request and extract the following as JSON only.

Return this exact JSON shape:

{
  "accounts_in_scope": [],
  "disposal": false,
  "source_of_funds": "",
  "destination_account": "",
  "amount": 0,
  "risk_profile": 0,
  "client_circumstances": "",
  "objectives_changed": false,
  "review_reason": "",
  "income_required": false
}

Guidelines:
- accounts_in_scope: list only accounts mentioned in the report request
- disposal: true only if existing investments are being sold
- source_of_funds: where the money is coming from
- destination_account: where the money is being invested
- amount: the investment amount in GBP as a number
- risk_profile: the agreed risk profile number
- client_circumstances: short high-level summary only (e.g. retired)
- objectives_changed: true only if objectives have changed since the last review
- review_reason: high-level reason for the review without recommendation details
- income_required: true only if the client currently requires income from the portfolio
"""


def pre_process(client_dir: Path) -> dict[str, Any]:
    """Extract facts from structured files without using the LLM."""
    logger.debug("Pre-processing client files from %s", client_dir)

    client_data_path = client_dir / "client_data_db.json"
    meeting_notes_path = client_dir / "meeting_notes.docx"
    report_request_path = client_dir / "report_request.docx"

    for path in [client_data_path, meeting_notes_path, report_request_path]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

    client_data = json.loads(read_file(client_data_path))
    holders = client_data["holders"]["client"]

    facts = {
        "client_name": holders["name"],
        "accounts": holders["accounts"],
        "snapshot_date": client_data["snapshot_date"],
        "meeting_notes": read_docx(meeting_notes_path),
        "report_request": read_docx(report_request_path),
    }

    on_pre_process_complete(facts)
    return facts


def investigate(
    pre_processed: dict[str, Any],
    openai_client: OpenAI,
    model: str,
) -> dict[str, Any]:
    """Use the LLM to extract facts from unstructured client documents."""
    logger.debug("Running investigation LLM call")

    context = {
        "meeting_notes": pre_processed["meeting_notes"],
        "report_request": pre_processed["report_request"],
    }

    response = openai_client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": INVESTIGATION_PROMPT},
            {"role": "user", "content": json.dumps(context)},
        ],
    )

    raw = response.choices[0].message.content or "{}"

    try:
        llm_facts = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Investigation agent returned invalid JSON: %s", raw)
        raise

    required_keys = {
        "accounts_in_scope",
        "disposal",
        "source_of_funds",
        "destination_account",
        "amount",
        "risk_profile",
        "client_circumstances",
        "objectives_changed",
        "review_reason",
        "income_required",
    }

    missing_keys = required_keys - llm_facts.keys()

    if missing_keys:
        raise ValueError(
            f"Investigation output missing keys: {missing_keys}"
        )

    # Investigation agent returns a flat dict of structured facts, which we combine with the pre-processed facts
    # only structured facts go into generation
    facts = {
        "client_name": pre_processed["client_name"],
        "accounts": pre_processed["accounts"],
        "snapshot_date": pre_processed["snapshot_date"],
        "accounts_in_scope": llm_facts["accounts_in_scope"],
        "disposal": llm_facts["disposal"],
        "source_of_funds": llm_facts["source_of_funds"],
        "destination_account": llm_facts["destination_account"],
        "amount": llm_facts["amount"],
        "risk_profile": llm_facts["risk_profile"],
        "client_circumstances": llm_facts["client_circumstances"],
        "objectives_changed": llm_facts["objectives_changed"],
        "review_reason": llm_facts["review_reason"],
        "income_required": llm_facts["income_required"],
    }

    on_investigation_complete(facts)

    return facts