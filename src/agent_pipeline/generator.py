"""Generation agent: fills report sections using structured facts."""

import json
from openai import OpenAI


class GenerationAgent:
    """Generates each report section using structured facts from the investigation agent."""

    def __init__(self, openai_client: OpenAI, model: str) -> None:
        self._openai = openai_client
        self._model = model
        self.call_count = 0

    def section_applies(self, section: dict, facts: dict, instructions: str) -> bool:
        """Decide whether a section should be included."""
        rule = section.get("use_if", "always")
        if rule == "always":
            return True
        verdict = self._ask(
            f"{instructions}\n\n"
            f"Decide whether this section applies based on the client facts.\n"
            f"Rule: {rule}\n"
            f"Reply with only 'yes' or 'no'.",
            facts,
        )
        return verdict.lower().startswith("y")

    def build_section(self, section: dict, facts: dict, instructions: str) -> str:
        """Fill all placeholders in a section template."""
        content = section["template"]
        for name, spec in section.get("placeholders", {}).items():
            section_instruction = (
                f"{instructions}\n\n"
                f"You are writing ONLY the '{section['title']}' section.\n"
                f"Do NOT include content that belongs in other sections.\n"
                f"Output only the text for this placeholder, nothing else.\n\n"
                f"{spec['prompt']}"
            )
            value = self._ask(section_instruction, facts)
            content = content.replace(f"<<{name}>>", value)
        return content

    def _ask(self, instruction: str, facts: dict) -> str:
        """Make a single LLM call with structured facts as context."""
        self.call_count += 1
        
        response = self._openai.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(facts)},
            ],
        )
        return response.choices[0].message.content.strip()