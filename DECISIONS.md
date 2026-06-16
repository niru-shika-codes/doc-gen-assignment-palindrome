# Decisions Log

## 1. Hardcoded risk warning as static template text
**Decision:** Moved the risking warning from an llm generated placeholder to hardcoded static text in the template_config.json. 
**Why:** The template_spec.md states the wording to be eact (word-to-word). Keeping it as a prompt means that there a risk of model
         pharaphasing it. Regualatory lines should NEVER be rewritten. 
**Trade-off:**: Less creative and flexible but legal lines should never be comprised, it should always be controlled manually for safety / legal reasons. 

## 2. Human review markers defined in global_instructions
