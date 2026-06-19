# Decisions Log

## OVERALL VIEW
1. I start of by running the client_clean_01 data on the initial pipeline. I noticed the output and made changes to the template config accoridngly. I have explained each change in detail including trade-offs as we are working wuth financial data and PII is important.
2. I have suggested a simple agentic work flow which includes a diagram explaining what agents I will have and how they will interact with each other. 

## Prompt improvements 
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

## Pipeline Improvements

