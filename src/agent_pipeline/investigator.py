"""Investigation agent: reads client files and extracts structured facts."""

import json
from pathlib import Path

from openai import OpenAI

from document_formatter.loading import read_docx, read_file
from utils.callbacks import on_investigation_complete, on_pre_process_complete
from utils.logging_config import get_logger

logger = get_logger(__name__)


def pre_process(client_dir: Path) -> dict:
    """Extract what we can directly from structured data — no LLM needed."""
    logger.debug("Pre-processing client files from %s", client_dir)

    client_data = json.loads(read_file(client_dir / "client_data_db.json"))
    holders = client_data["holders"]["client"]

    facts = {
        "client_name": holders["name"],
        "accounts": holders["accounts"],
        "snapshot_date": client_data["snapshot_date"],
        "meeting_notes": read_docx(client_dir / "meeting_notes.docx"),
        "report_request": read_docx(client_dir / "report_request.docx"),
    }

    on_pre_process_complete(facts)
    return facts


def investigate(pre_processed: dict, openai_client: OpenAI, model: str) -> dict:
    """Single LLM call to extract facts that require reading the docx files."""
    logger.debug("Running investigation LLM call")

    prompt = """
    Read the meeting notes and report request and extract the following as JSON only.
    Return JSON only — no markdown backticks, no other text.

    {
        "accounts_in_scope": [],
        "disposal": false,
        "source_of_funds": "",
        "amount": 0,
        "risk_profile": 0
    }

    Guidelines:
    - accounts_in_scope: list only accounts mentioned in the report request
    - disposal: true only if existing investments are being sold
    - source_of_funds: where the money is coming from
    - amount: the investment amount in GBP as a number
    - risk_profile: the agreed risk profile number
    """

    context = {
        "meeting_notes": pre_processed["meeting_notes"],
        "report_request": pre_processed["report_request"],
    }

    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(context)},
        ],
    )

    raw = response.choices[0].message.content.strip()
    llm_facts = json.loads(raw)

    facts = {**pre_processed, **llm_facts}
    on_investigation_complete(facts)
    return facts