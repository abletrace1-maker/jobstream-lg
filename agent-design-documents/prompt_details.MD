# Prompt Guidelines (prompt_details.MD)

This document outlines the core instructions, context, and expected outputs for every LLM-driven node in the JobStream workflow. Do NOT use these exact words as the prompt, but ensure the system prompts cover these specific requirements.

## 1. Resume to JSON Converter (Setup Phase)
**Objective:** Transform a raw text/PDF resume into the strict `templates.MD` JSON format.
**Key Directives:**
*   **Completeness:** Do not summarize, truncate, or drop any bullet points. Copy the text exactly, just mapping it to the correct JSON schema key.
*   **Formatting Preservation:** Maintain the stylistic intent (e.g., if the user has short, punchy bullets, keep them short and punchy).
*   **Data Extraction:** Accurately separate contact info, skills, and chronological experience.

## 2. Job URL / Text Parser Node
**Objective:** Convert raw scraped HTML text or user-pasted job descriptions into the Job Details JSON schema.
**Key Directives:**
*   **Categorization:** Accurately split the text into "Requirements" vs "Nice-to-haves" vs "Responsibilities".
*   **Noise Reduction:** Ignore equal opportunity statements, generic company boilerplate, and benefits packages unless they represent a specific skill requirement.
*   **Failure Handling:** If the text appears to be a CAPTCHA, a paywall notice, or a "JavaScript required" page, return a specific error flag in the JSON so the graph can pause and ask the user for manual text input.

## 3. Evaluate Fit Node
**Objective:** Compare the parsed Base Resume to the parsed Job Details.
**Key Directives:**
*   **Scoring:** Provide a realistic 1-10 fit score. If the score is below a threshold (e.g., 3/10), flag `should_apply` as false.
*   **Gap Analysis:** Identify key job requirements that are completely missing from the base resume.
*   **Question Generation:** For every missing critical requirement, or ambiguous overlap, generate a clarification question. 
*   **Always Provide LLM Option:** Every multiple-choice question MUST include an option that says "Let the LLM decide the best approach".

## 4. Strategy Generator Node
**Objective:** Create the Markdown strategy document and the programmatic JSON Diff document.
**Key Directives:**
*   **Adhere to Constraints:** Read the `config` context. Do NOT suggest changes to forbidden sections (e.g., Job Titles, Dates, Company Names).
*   **Incorporate User Answers:** If the user answered clarification questions, strictly follow their guidance. If they chose "Let LLM decide", use your best judgment to re-frame existing skills to match the job.
*   **No Hallucinations:** You may reword, reorder, or emphasize existing points. You may NOT invent new jobs, degrees, or measurable metrics (e.g., do not change "increased sales" to "increased sales by 500%").
*   **Dual Output Consistency:** The Markdown document (for the human) and the JSON Diff (for the programmatic applier) must represent the EXACT same changes.

## 5. Revise Strategy Node
**Objective:** Update the Strategy Markdown and JSON Diff based on free-text human feedback.
**Key Directives:**
*   **Feedback Integration:** Treat the `user_feedback` string as absolute priority. If they say "Undo the changes to my first job", remove those changes from the diff.
*   **Maintain Validity:** Ensure the resulting JSON Diff still perfectly matches the `templates.MD` schema and targets valid JSON paths in the base resume.

## 6. PDF Formatting/Review Node (Optional LLM check)
**Objective:** Ensure the applied JSON matches the "look and feel" of the starter resume.
**Key Directives:**
*   Verify that bullets start with action verbs if the starter resume did.
*   Ensure length of sections hasn't ballooned out of proportion to the original.

## 7. Cover Letter Generator Node
**Objective:** Draft a compelling, concise Cover Letter that complements the approved tailored resume.
**Key Directives:**
*   **Targeting:** Explicitly reference the `company_name` and `job_title` from the job details.
*   **Alignment:** Focus strictly on the requirements mentioned in the job description that match the candidate's tailored resume.
*   **Tone:** Maintain a professional, confident tone. Do NOT invent new experiences, hobbies, or traits. Avoid overly generic fluff ("I am a hard worker"). Keep it to 3-4 impactful paragraphs.