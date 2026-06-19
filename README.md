# doc-gen-assignment

Config-driven advice report generation pipeline for client source material.

This project extends the starter pipeline into a multi-stage agentic workflow with structured fact extraction, deterministic validation, and evaluation logging.

The focus of the solution is correctness, source trust, and generalisation rather than maximising the number of agents.

## Setup

```bash
# clone the repository

cp .env.example .env
# add your OpenAI API key to .env

uv sync
```

Alternatively:

```bash
pip install -e .
```

## Run

Generate a report for a client:

```bash
uv run python -m agent_pipeline.generate --client client_01_clean
```

Generated reports are written to:

```text
outputs/<client>.md
```

Evaluation results are recorded in:

```text
outputs/evaluation_log.csv
```

Available clients:

* client_01_clean
* client_02_medium
* client_03_hard
* client_04_stretch

---

# Architecture

The starter pipeline pushed every file into every prompt.

This solution uses a staged pipeline:

```text
Client source files
        ↓
Pre-processing
        ↓
Investigation Agent
        ↓
Structured facts
        ↓
Generation Agent
        ↓
Markdown report
        ↓
Validation Agent
        ↓
Evaluation Layer
        ↓
outputs/
```

---

# Agents

## 1. Investigation Agent

Responsible for extracting structured facts from the source documents.

Responsibilities:

* applies source trust rules
* extracts client objectives and recommendations
* determines whether disposals are involved
* extracts risk profile and amounts
* resolves account scope
* deduplicates joint accounts
* ignores closed accounts

Output:

```python
{
    "accounts_in_scope": [...],
    "amount": 20000,
    "risk_profile": 4,
    ...
}
```

---

## 2. Generation Agent

Responsible for generating report sections.

Responsibilities:

* fills placeholders defined in `template_config.json`
* generates only from structured facts
* does not receive raw source documents
* respects section-level instructions

Output:

```markdown
## Recommendations
...
```

---

## 3. Validation Agent

Performs deterministic checks against the generated report.

Checks:

* client name appears
* FCA wording appears exactly
* mandatory risk warning appears exactly
* Tax Implications section is included only when required
* account values are present
* fees and unknown values are marked with

```text
[TBC - REQUIRES HUMAN REVIEW]
```

---

## Evaluation Layer

Each report is automatically evaluated.

Metrics recorded:

* score
* pass/fail status
* issues found
* latency
* number of LLM calls

Results are appended to:

```text
outputs/evaluation_log.csv
```

---

# Source Handling

Not every file is treated equally.

## client_data_db.json

Source of truth for:

* account existence
* ownership
* account type
* valuations

---

## meeting_notes.docx

Source of truth for:

* client objectives
* risk profile
* client decisions
* whether a disposal is involved

---

## report_request.docx

Source of truth for:

* report scope
* adviser instruction

---

## fde_notes.md

Used as source guidance only.

It helps explain:

* source hierarchy
* relationships between files
* intended usage

No client facts are extracted from this file.

---

## platform_market_update.docx

Excluded from prompts.

The document explicitly states that it contains general market commentary and illustrative figures rather than client-specific information.

Including it would increase token usage and create a risk that irrelevant figures leak into client reports.

---

# Design Principles

## Source trust

Different files serve different purposes.

Each source is trusted only for the information it owns.

---

## Deterministic where possible

Deterministic logic is implemented in Python.

Examples:

* account deduplication
* exclusion of closed accounts
* scoped account resolution
* validation checks

The LLM is reserved for:

* reasoning
* summarisation
* natural language generation

This reduces hallucination risk and should generalise better to the held-out set.

---

## Prompt injection protection

Source documents are treated as data rather than instructions.

The Investigation Agent is instructed to ignore any embedded instructions that attempt to:

* change output format
* reveal data
* override system rules

---

## Evaluation

Prompt changes are measured quantitatively rather than relying on manual inspection.

Evaluation metrics help balance:

* correctness
* speed
* cost
* effectiveness

---

# Repository Structure

```text
config/
    template_config.json

src/
    agent_pipeline/
        investigator.py
        generator.py
        validator.py
        evaluation.py
        generate.py

    document_formatter/
        formatting.py
        loading.py

data/
    client_01_clean
    client_02_medium
    client_03_hard
    client_04_stretch

outputs/
    *.md
    evaluation_log.csv
utils/
    callbacks.py
    logging_config.py

DECISIONS.md
PROJECT_GUIDANCE.md
```

---

# Future Work

Potential improvements include:

1. Pydantic models for stronger validation.
2. OCR or multimodal extraction for statement images.
3. Converting `.docx` files into structured markdown before prompting.
4. Additional observability such as token usage and cost tracking.
5. Self-correction loops for failed validations.
6. LLM-as-a-Judge evaluation.
7. User acceptance testing.
8. Retrieval-Augmented Generation (RAG).

I intentionally stopped after introducing three agents. Additional agents could be added, but I felt the extra complexity would not be justified for the current requirements. I preferred to focus on correctness, source trust and evaluation rather than maximising the number of agents.

---

# Decisions

See `DECISIONS.md` for:

* prompt iterations
* architectural decisions
* trade-offs
* evaluation approach
* future work

# Tools:
- Github Copilot has been used in someparts of the code. 