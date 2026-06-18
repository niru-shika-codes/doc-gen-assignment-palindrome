"""Generation agent: fills report sections using structured facts."""

import json
from typing import Any

from openai import OpenAI

from utils.callbacks import on_section_complete, on_section_skipped
from utils.logging_config import get_logger

logger = get_logger(__name__)


class GenerationAgent:
    """Generates each report section using structured facts from the investigation agent."""

    def __init__(self, openai_client: OpenAI, model: str) -> None:
        self._openai = openai_client
        self._model = model

    def section_applies(
        self,
        section: dict[str, Any],
        facts: dict[str, Any],
        instructions: str,
    ) -> bool:
        """Decide whether a section should be included."""
        rule = section.get("use_if", "always")
        title = section.get("title", "Untitled section")

        if rule == "always":
            return True

        verdict = self._ask(
            instruction=(
                f"{instructions}\n\n"
                f"Decide whether this section applies based on the client facts.\n"
                f"Section title: {title}\n"
                f"Rule: {rule}\n\n"
                f"Reply with only 'yes' or 'no'."
            ),
            facts=facts,
        )

        applies = verdict.lower().strip().startswith("y")

        if not applies:
            on_section_skipped(title)

        return applies

    def build_section(
        self,
        section: dict[str, Any],
        facts: dict[str, Any],
        instructions: str,
    ) -> str:
        """Fill all placeholders in a section template."""
        title = section.get("title", "Untitled section")
        logger.debug("Generating section: %s", title)

        content = section["template"]

        for name, spec in section.get("placeholders", {}).items():
            section_instruction = (
                f"{instructions}\n\n"
                f"You are writing ONLY the '{title}' section.\n"
                f"Do NOT include content that belongs in other sections.\n"
                f"Output only the text for this placeholder, nothing else.\n\n"
                f"Placeholder name: {name}\n"
                f"Placeholder instruction:\n{spec['prompt']}"
            )

            value = self._ask(section_instruction, facts)
            content = content.replace(f"<<{name}>>", value)

        on_section_complete(title, content)
        return content

    def _ask(self, instruction: str, facts: dict[str, Any]) -> str:
        """Make a single LLM call with structured facts as context."""
        response = self._openai.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(facts)},
            ],
        )

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("Generation agent received an empty response from the LLM")

        return content.strip()