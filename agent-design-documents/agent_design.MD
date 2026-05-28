# JobStream Agent Design Specification

## 1. System Architecture Overview

The system utilizes a Parent-Child (Map-Reduce) Graph architecture to handle multiple job applications concurrently while maintaining strict context isolation for each job.

1.  **Parent Graph (Batch Coordinator):** Handles the initialization, configuration loading, and sequential scraping of job URLs to avoid bot detection. Once jobs are scraped, it spawns isolated Sub-Graphs for each job.
2.  **Child Sub-Graph (Job Processor):** A fully isolated workflow that processes exactly ONE job against the candidate's base resume. It contains all the Human-in-the-Loop (HITL) nodes, logic, and state necessary to produce a final, tailored PDF resume.

This architecture ensures that LLM contexts are never polluted with information from other job postings.

---

## 2. Parent Graph: Batch Coordinator

**Objective:** Safely ingest multiple jobs and orchestrate parallel processing without triggering anti-bot protections.

### Node: `LoadConfigAndResumeNode`
*   **Objective:** Reads all of the user's base resumes (JSON format) from the `data/json_resumes` folder, the global configuration (YAML), and prompt templates (YAML). It also reads the `job_tracker.json` list to find all jobs marked as `PENDING`.
*   **Inputs:** File paths from graph invocation.
*   **Outputs (to State):** 
    *   `base_resumes` (Dictionary mapping `category` to the parsed JSON Object)
    *   `config`
    *   `prompts`
    *   `pending_jobs` (List of job objects from the tracker)

### Node: `JobIngestionNode` (Formerly SequentialScraper)
*   **Objective:** Iterates through the `pending_jobs` list. It checks the `source_type`. If `url`, it uses the scraping script (with randomized delays). If `file`, it reads the local `.txt` file. 
    *   **Job ID Generation:** It must ensure every job has a `job_id` following the format `MM-DD_n_company_name` (e.g., `05-20_1_MHB-Group-Canada`). The `n` increments based on the batch index. If the `company_name` is missing from the tracker, it uses the LLM to extract it from the parsed text and inject it into the ID.
    *   It then passes the raw text to an LLM to parse into the strict `Job Details JSON` schema. It must pass the user's `user_score` and `notes` into the parsed output so downstream nodes understand the user's intent.
*   **Inputs:** `pending_jobs`, `base_resumes` (keys)
*   **Outputs (to State):** 
    *   `scraped_jobs` (List of parsed JSON Objects)
    *   `failed_jobs` (List of jobs that were blocked or unparseable)

### Node/Edge: `DispatchJobSubgraphs`
*   **Objective:** A mapping function that takes the `scraped_jobs` list and spawns a parallel Sub-Graph execution for each job. It looks at the job's `category` and passes the corresponding `base_resume` from the `base_resumes` dictionary into the Sub-Graph state.

---

## 3. Child Sub-Graph: Job Processor

**Objective:** Handle the end-to-end evaluation, strategy, review, and generation of a tailored resume for a single job posting.

**Core Sub-Graph State Elements:**
*   `base_resume` (JSON)
*   `job_details` (JSON)
*   `status` (Enum: EVALUATING, NEEDS_CLARIFICATION, STRATEGY_DRAFTED, APPROVED, REJECTED)
*   `clarification_questions` (List of Objects: question_text, options, requires_user_input)
*   `user_clarification_answers` (Dictionary)
*   `strategy_markdown` (Markdown string)
*   `resume_diffs` (JSON Object representing Old vs. New changes)
*   `user_feedback` (String)
*   `tailored_resume` (JSON)

### Node: `EvaluateFitNode`
*   **Objective:** Compare the `base_resume` against the `job_details`. Determine if the candidate is a viable fit based on constraints in the `config`. Identify missing context that requires user input.
*   **Inputs:** `base_resume`, `job_details`, `config`, `prompts`
*   **Outputs (to State):** 
    *   `status` (Updates to REJECTED, NEEDS_CLARIFICATION, or moves forward)
    *   `clarification_questions` (If context is missing. Includes options like "Let LLM decide")

### Node: `ClarificationNode` (HITL Interrupt)
*   **Objective:** Pauses the execution to ask the user questions identified in `EvaluateFitNode`. The node formats the questions, triggers an interrupt, and waits. Upon waking, it saves the answers.
*   **Inputs:** `clarification_questions`
*   **Outputs (to State):** 
    *   `user_clarification_answers`

### Node: `StrategyGeneratorNode`
*   **Objective:** Using the base resume, job details, and user clarifications, draft a targeted resume update strategy. It must produce two parallel outputs: a human-readable Markdown summary explaining the "why", and a strict JSON Diff showing exact Before/After changes for specific resume sections.
*   **Inputs:** `base_resume`, `job_details`, `user_clarification_answers`, `config`, `prompts`
*   **Outputs (to State):**
    *   `strategy_markdown`
    *   `resume_diffs`
    *   `status` (Updated to STRATEGY_DRAFTED)

### Node: `HumanReviewNode` (HITL Interrupt)
*   **Objective:** Pauses execution to present the `strategy_markdown` and `resume_diffs` to the user via the frontend. Waits for either an "Approve" signal or text-based "Feedback" (e.g., "Make the summary more aggressive").
*   **Inputs:** `strategy_markdown`, `resume_diffs`
*   **Outputs (to State):**
    *   `user_feedback` (If rejected/modified)
    *   `status` (Updated to APPROVED or loops to REVISE)

### Node: `ReviseStrategyNode`
*   **Objective:** If the user provided feedback in the `HumanReviewNode`, this node reads the feedback, the previous strategy, and the diffs, and generates an updated strategy and diff set.
*   **Inputs:** `strategy_markdown`, `resume_diffs`, `user_feedback`, `prompts`
*   **Outputs (to State):**
    *   `strategy_markdown` (Updated)
    *   `resume_diffs` (Updated)

### Node: `ApplyChangesNode`
*   **Objective:** A deterministic (non-LLM) node that takes the original `base_resume` JSON and applies the approved `resume_diffs` JSON to create the final, strictly-formatted tailored resume JSON.
*   **Inputs:** `base_resume`, `resume_diffs`
*   **Outputs (to State):**
    *   `tailored_resume` (JSON)

### Node: `CoverLetterGeneratorNode`
*   **Objective:** Now that the tailored resume is finalized and approved, this LLM node uses the `tailored_resume`, the `job_details`, and any `user_clarification_answers` to draft a highly targeted Cover Letter.
*   **Inputs:** `tailored_resume`, `job_details`, `user_clarification_answers`, `prompts`
*   **Outputs (to State):**
    *   `cover_letter_markdown` (Markdown string)

### Node: `PDFCompilerNode`
*   **Objective:** Takes the `tailored_resume` JSON and passes it into a programmatic templating engine (e.g., Typst or WeasyPrint) to generate the final ATS-friendly PDF. It also takes the `cover_letter_markdown` and converts it into a separate PDF or appending page. Writes both to the local output directory.
*   **Inputs:** `tailored_resume`, `cover_letter_markdown`, `job_details` (for file naming)
*   **Outputs (to System/Filesystem):**
    *   Outputs `.pdf` files to the filesystem.
    *   Updates state with `resume_pdf_path` and `cover_letter_pdf_path`.