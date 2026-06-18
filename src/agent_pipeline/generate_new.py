"""Generate an advice report for a client from the template config.

Usage:
    python -m agent_pipeline.generate_new --client client_01_clean
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent_pipeline.generator import GenerationAgent
from agent_pipeline.investigator import investigate, pre_process
from agent_pipeline.validator import validate
from document_formatter.formatting import format_document
from utils.callbacks import on_report_written
from utils.logging_config import setup_logging


def build_report(config: dict, facts: dict, generation_agent: GenerationAgent) -> str:
    """Build the report section by section."""
    instructions = config.get("global_instructions", "")

    sections = []

    for section in config["sections"]:
        title = section.get("title", "")

        if not generation_agent.section_applies(section, facts, instructions):
            continue

        content = generation_agent.build_section(section, facts, instructions)

        sections.append(
            {
                "title": title,
                "content": content,
            }
        )

    return format_document(config, sections)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an advice report for a client."
    )
    parser.add_argument("--client", required=True, help="folder name under data/")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/template_config.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))

    args = parser.parse_args()

    load_dotenv()
    setup_logging()

    openai_client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    client_dir = args.data_dir / args.client

    pre_processed = pre_process(client_dir)
    facts = investigate(pre_processed, openai_client, model)

    generation_agent = GenerationAgent(openai_client, model)
    report = build_report(config, facts, generation_agent)

    validate(report, facts)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    out_path = args.output_dir / f"{args.client}.md"
    out_path.write_text(report, encoding="utf-8")

    on_report_written(str(out_path))


if __name__ == "__main__":
    main()