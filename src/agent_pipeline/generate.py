"""Generate an advice report for a client from the template config.

Usage:
    python -m agent_pipeline.generate --client client_01_clean
"""

import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from agent_pipeline.evaluation import evaluate_report
from agent_pipeline.generator import GenerationAgent
from agent_pipeline.investigator import investigate, pre_process
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


def record_evaluation(
    output_dir: Path,
    client: str,
    evaluation: dict,
    llm_calls: int,
    duration_s: float,
) -> None:
    """Append the evaluation result to a CSV log in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / "evaluation_log.csv"
    file_exists = log_path.exists()

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client": client,
        "llm_calls": llm_calls,
        "duration_s": duration_s,
        "score": f"{evaluation['passed_checks']}/{evaluation['total_checks']}",
        "passed": evaluation["passed"],
        "issues": (
            "; ".join(evaluation["issues"])
            if evaluation["issues"]
            else "No issues found"
        ),
    }

    with log_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "client",
                "llm_calls",
                "duration_s",
                "score",
                "passed",
                "issues",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


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

    start_time = time.perf_counter()

    openai_client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    client_dir = args.data_dir / args.client

    pre_processed = pre_process(client_dir)
    facts = investigate(pre_processed, openai_client, model)

    generation_agent = GenerationAgent(openai_client, model)
    report = build_report(config, facts, generation_agent)

    evaluation = evaluate_report(report, facts)

    duration_s = round(time.perf_counter() - start_time, 2)
    llm_calls = 1 + generation_agent.call_count

    print(
        f"Evaluation score: "
        f"{evaluation['passed_checks']}/{evaluation['total_checks']}"
    )
    print(f"LLM calls: {llm_calls}")
    print(f"Duration: {duration_s}s")

    if not evaluation["passed"]:
        print("Evaluation issues:")
        for issue in evaluation["issues"]:
            print(f"- {issue}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    out_path = args.output_dir / f"{args.client}.md"
    out_path.write_text(report, encoding="utf-8")

    record_evaluation(
        args.output_dir,
        args.client,
        evaluation,
        llm_calls,
        duration_s,
    )

    on_report_written(str(out_path))


if __name__ == "__main__":
    main()