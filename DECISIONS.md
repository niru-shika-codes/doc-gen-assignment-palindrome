# Decisions Log

## OVERALL VIEW
1. As suggested, ran client_01_clean to understand the baseline behaviout on the clean data to identify the weaknesses. The generated report (which i have copied and called client_01_clean_baselined.md in outputs folder) highlighted the following issues:
    - Verbose sections
    - Repeated information
    - LLM adding wording not aligned with the domain, esp around fee's/charges. 

2. After reviewing the client files and the guidance in template_spec.md and fde_notes.md, I decided to treat the prompts as code and iteratively improve them. Rather than relying on a single large prompt over all documents, I restructured the pipeline into separate stages for investigation, generation, validation and evaluation.

## PROMPT IMPROVEMENTS (ITERATIVE)
### 1. Hardcoded risk warning as static template text
**Issue:** The original prompt asked the model to generate the risk warning, risking paraphrasing of a legally required line.
**Decision:** Moved the risking warning from an llm generated placeholder to hardcoded static text in the template_config.json. 
**Why:** The template_spec.md states the wording to be eact (word-to-word). Keeping it as a prompt means that there a risk of model
         pharaphasing it. Regualatory lines should NEVER be rewritten. 
**Trade-off:**: Less creative and flexible but legal lines should never be comprised, it should always be controlled manually for safety / legal reasons. 

### 2. Human review markers defined in global_instructions
**Issue:** Fee rates and CGT figures had no protection against the model inventing them. There was no consistent way to flag them for human review across sections.
**Decision:** Added a consistent [TBC - REQUIRES HUMAN REVIEW] marker defined once in global_instructions.
**Why:** FDE notes say fee rates and CGT figures must never be invented. Defining the marker globally ensures consistency across all sections.
**Trade-off:** Could be a Python code instead for production level, but for now global_instructions keeps it in config alongside the prompts. 

### 3. Tightened tax_implications use_if and prompt
**Issue:** The original use_if condition was too vague and the prompt actively instructed the model to estimate CGT figures, directly violating the FDE notes rules mentioned.
**Decision:** Made the inclusion condition explicit and removed the instruction to estimate CGT.
**Why:** The original prompt told the model to estimate CGT which directly violates FDE notes rules.

### 4. Fees & Charges Prompt changes
**Issue:** The original prompt was too vague and the model invented fee descriptions such as "there may be an ongoing platform fee" and "a standard ongoing advice charge" with no actual rates. Neither of these figures exist anywhere in the source data (client_data_db.json, meeting_notes.docx, or report_request.docx).
**Decision:** Rewrote the fees prompt to explicitly forbid inventing or estimating fee rates, using the [TBC - REQUIRES HUMAN REVIEW] marker instead.
**Why:** The original prompt was too vague — the model invented vague fee descriptions such as "there may be an ongoing platform fee" and "a standard ongoing advice charge" with no actual rates. Neither of these figures exist anywhere in the source data (client_data_db.json, meeting_notes.docx, or report_request.docx). A made-up fee rate must never reach the client per the FDE notes.
**Trade-off:** The model still generates text. However, in production, fee rates would be pulled directly from a fees database and injected into the prompt using f-string templating. This approach removes the model from that decision entirely and guarantees the correct figures appear every time. A python assertion could check the fees generated match the fees in the database. 

### 5. Fixing scope prompt - Introduction
**Issue:** There are two issues that can be decuded from the inital generated report. 
           1. The LLM model repeated "This report relates to" because the template already has "in relation to" before the slot
           2. It added extra sentences make it messy, grammatically incorrect and the flow unatural. 
**Decision:**: Decided to format the sentence and give concreate example as LLMs prefer this. 
**Why:** The prompt needs to know it's completing a sentence, not starting one. The model had no context that the template already had words before the slot.
**Trade-off:** A concrete example was included to improve model clarity but explicitly marked as illustrative to prevent the model copying client-specific values onto other clients. This balances clarity with generalisability across the palindrone test set.

### 6. Summary Prompt Changes
**Issue:** The summary is not high level and does to adhere to spec requirements - it is too detailed (which is not required). For example, it provided transaction amounts which is not needed. 
**Decision:**: Rewrote the prompt to explicitly forbid mentioning specific transaction amounts, top-up figures, or investment amounts in the summary. Instructed the model to focus only on who the client is, their risk profile, and their general financial situation.
**Why:** The template_spec.md states Background & Objectives should be high level only. Specific amounts belong in Recommendations. Mixing them makes the report repetitive and harder to read.
**Trade-off:** The model still generates surrounding text but is now restricted to specific fields from the source data (client name, retirement status, risk profile, and change of circumstances.) This reduces ambiguity while remaining flexible enough for other clients on the test set.

### 7. Recommendation prompt changes 
**Issue:** Recommedation prompt is too vague, does not have clear guidance on what needs to be icluded. Does not mention platform charges, does not specify the amount or source funds which is needed as mentioned in the template_spec.md.
**Decision:**: Rewrote the prompt to to include more details which inclue platform charges and amounts. Also included TBC-HUMAN REVIEW NEEDED as it is needed. 
**Why:** The spec says recommendations should include amounts involved and relevant platform charges. The original prompt gave the model no structure so it generated vague outputs.
**Trade-off:** We are telling the model exactly what to include which is good for consistency but assumes every recommendation will have these components. More complex clients may need additional fields. Essentially in producting, I would recommend creating a Pydantic schema definition. Why? This forces the model to return a structured JSON that is validated before rendering into the report. It will catch any missing feilds early and make the pipeline robust across different client data on test tests.

## DATA DECISIONS

1. The client folders contained both structured and unstructured data, and not all files are equally trustworthy. I established a source hierarchy with the knowlege I had. 
    - client_data_db.json -> ecord for account existence, ownership and account types 
    - meeting_notes.docx -> Client conversations / objectives and risk profile 
    - report_request.docx -> Scope of the report + advisor notes
    - fde_notes.md -> Used to source metadata and relationship between docs
    - Additional file -> platform market updates was not used as it it says "his note is general market commentary and does not relate to any individual client's accounts or recommendations"

2. This was done to avoid feeding everyfile into every prompy and reduce hallucinations / irrelevant information appearing in the report.

3. Overall, I tried to move deterministic decisions into Python and reserve the LLM for tasks that required reasoning or natural language generation. This reduced hallucination risk and should generalise better to the held-out client set.

4. I deliberately avoided hardcoding client-specific rules. Instead, I focused on generic behaviours such as account deduplication, scoped account resolution and source trust rules so that the pipeline would generalise to unseen clients.

## HLD 

1. Initially we had the following: 

                     ALL FILES
                           │
                           ▼
                ┌─────────────────┐
                │    Single LLM   │
                │      Prompt     │
                └─────────────────┘
                           │
                           ▼
                     Final Report

2. Now we have the following agentic design:

                ┌─────────────────┐
                │ Investigation   │
                │ Agent           │
                └─────────────────┘
                         │
                   structured facts
                         │
                         ▼
                ┌─────────────────┐
                │ Generation      │
                │ Agent           │
                └─────────────────┘
                         │
                    markdown report
                         │
                         ▼
                ┌─────────────────┐
                │ Validation      │
                │ Agent           │
                └─────────────────┘
                         │
                  issues / pass
                         │
                         ▼
                ┌─────────────────┐
                │ Evaluation      │
                │ Layer           │
                └─────────────────┘

## Agent design Overview

### 1. Investigation Agent
**Issue:** The original pipeline fed every source document directly into every generation prompt. This increased cost, latency and the risk of irrelevant information contaminating the output.
**Decision:** Added an Investigation Agent responsible for extracting structured facts from the source documents before generation.
**Why:** Separating fact extraction from report writing reduces context size and allows the Generation Agent to operate only on structured facts.
**Trade-off:** This introduces an extra LLM call but significantly improves reliability and makes debugging easier.

### 2. Generation Agent
**Issue:** The original pipeline used one large context string and relied on the model to both understand the data and write the report at the same time. This made outputs harder to debug and increased the chance of section bleed, repetition and hallucinated details.
**Decision:** Added a Generation Agent responsible only for filling report sections from structured facts and `template_config.json`.
**Why:** Once the Investigation Agent has extracted clean facts, the Generation Agent can focus on producing readable report wording without needing access to raw source documents. This reduces context size and keeps generation aligned to the report template.
**Trade-off:** The generated wording depends heavily on the quality of the extracted facts and the placeholder prompts. If the Investigation Agent misses a fact, the Generation Agent cannot recover it from the raw documents.

### 3. Validation Agent
**Issue:** The starter pipeline produced a report but had no automated way to check whether required wording, account values or conditional sections were correct.
**Decision:** Added a deterministic Validation Agent that checks the generated report against the structured facts and report specification.
**Why:** Some checks should not be left to the LLM. Mandatory FCA wording, risk warnings, account values, tax section inclusion and unsupported claims can be checked reliably in code.
**Trade-off:** Rule-based validation cannot catch every subtle quality issue, but it catches important failures quickly and provides a repeatable baseline for evaluation.

### Prompt Injection Protection
**Issue:** Source documents should be treated as untrusted input and may contain instructions or irrelevant content.
**Decision:** Added instructions telling the Investigation Agent to treat source documents as data rather than instructions.
**Why:** This prevents instructions embedded inside documents from influencing the pipeline or causing unintended behaviour.
**Trade-off:** Slightly longer prompts, but stronger guardrails and reduced risk of prompt injection.

### Account Deduplication
**Issue:** Joint accounts appeared under both holders and some accounts were closed.
**Decision:** Added deterministic preprocessing to collect open accounts and remove duplicate joint accounts.
**Why:** This prevents duplicated valuations and ensures that only active accounts appear in the report.
**Trade-off:** More Python logic is required, but less reliance is placed on the LLM for deterministic decisions.

## Evaluation Layer 
**Issue:** Prompt changes were difficult to compare because there was no quantitative record of whether the pipeline improved or regressed.
**Decision:** Added an evaluation layer that converts validation issues into a score and records each run in `outputs/evaluation_log.csv`.
**Why:** This makes prompt and pipeline changes measurable. The log records the client, pass/fail result, score, issues, latency and LLM call count, which helps compare effectiveness, speed and cost. You can also use .csv to conduct analysis which can be later looped back to the product or the agent itself. 
**Trade-off:** The score is only as good as the validation checks behind it. It is useful for regression testing, but manual review is still needed for nuanced advice quality. Needs better versioning metrics too.

## Callbacks and Observability

**Issue:** The original pipeline provided little visibility into what stage of the process was currently executing, making debugging and monitoring difficult.

**Decision:** Introduced callbacks at key stages of the pipeline to record progress and provide structured logging.

**Why:** Callbacks improve observability and make it easier to understand where failures occur. They also separate logging concerns from the business logic, making the code cleaner and easier to maintain.

Examples include:

- `on_pre_process_complete()`
- `on_investigation_complete()`
- `on_validation_complete()`
- `on_report_written()`

**Trade-off:** Additional plumbing code is required, but it improves debugging, monitoring and maintainability. In production, these callbacks could be extended to integrate with tracing or observability platforms.

## Metrics

The evaluation layer records:

- score
- pass/fail status
- issues
- latency
- number of LLM calls

This allows prompt iterations to be compared quantitatively and helps evaluate cost, speed and effectiveness. The evaluation results are stored in `outputs/evaluation_log.csv`.

## What I deliberately avoided

1. Feeding every source document into every prompt.
2. Allowing the LLM to invent fee rates or tax figures.
3. Hardcoding client-specific rules that would not generalise to the held-out set.
4. Adding unnecessary agents and complexity.
5. Letting the LLM decide deterministic logic such as account deduplication or scoped account resolution.


## Future Work Philosophy

I intentionally stopped after introducing three agents. Additional agents could be added, but I felt the extra complexity would not be justified for the current requirements. I preferred to focus on correctness, source trust and evaluation rather than maximising the number of agents. Below i have listed what improvements I can make: 

###  Future Work

1. Pydantic Models
Currently the Investigation Agent returns JSON and checks required keys manually. I would introduce Pydantic models to provide stronger typing, earlier validation and easier debugging. This would improve reliability rather than reducing LLM calls.

2. Image Processing for Statement Summaries
Statement images are currently ignored because the structured database was sufficient for the provided clients. With more time, I would introduce an OCR or multimodal extraction stage to convert statement images into structured data. Deterministic source-resolution rules could then use statement values to supplement missing database values or prefer newer valuations. This would improve robustness when sources disagree or contain incomplete information.

3. Better Document Normalisation
Currently `.docx` files are read into plain text before being passed to the Investigation Agent. With more time, I would add a document normalisation step that converts `.docx` files into clean markdown, preserving headings, bullets and tables. This would provide more structured input to the LLM and make extraction more reliable.

4. Observability
Add additional metrics such as token usage, cost per report and section-level latency to better understand speed, cost and effectiveness trade-offs.

5. Self-Correction Loop
Introduce a retry mechanism where failed validation checks trigger regeneration of only the affected sections. This would reduce manual review but would increase cost and latency.

6. LLM-as-a-Judge
Add an evaluation agent capable of assessing clarity, tone, completeness and factual consistency. This would complement the deterministic evaluation framework.

7. User Acceptance Testing
Incorporate human feedback and user acceptance criteria into the evaluation process to ensure reports meet adviser expectations.

8. Retrieval-Augmented Generation (RAG)
Introduce chunking and retrieval to reduce token usage and improve scalability. Given the relatively small document sizes in this exercise, I considered this lower priority than source trust and evaluation.
