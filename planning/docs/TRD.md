# JobStream Agent Technical Requirements Document (TRD)

## 1. System Architecture

JobStream uses a **Parent-Child (Map-Reduce) LangGraph Architecture** to concurrently process multiple job applications while enforcing strict LLM context isolation.

### High-Level Components
1. **Batch Coordinator (Parent Graph):** Loads global configuration, user base resumes, and the `job_tracker.json` queue. It iterates over pending jobs, parses job descriptions (handling both URLs and fallback text files), and dispatches isolated Child Sub-Graphs.
2. **Job Processor (Child Sub-Graph):** An isolated graph handling exactly one job application. It performs fit evaluation, gathers human clarification (HITL), generates strategy/JSON diffs, gathers human approval (HITL), and orchestrates PDF generation.
3. **Streamlit Frontend:** Serves as the UI for Human-in-the-Loop (HITL) interrupts. It reads the LangGraph SQLite checkpoints to resume paused threads and syncs graph statuses back to the portable `job_tracker.json` queue.
4. **State Persistence:** `SqliteSaver` (from `langgraph.checkpoint.sqlite`) persists execution state for long-running sub-graphs at `data/checkpoints.sqlite`.

### Data Flow
`job_tracker.json` -> Parent Graph -> Job Parsing -> Sub-Graph Dispatch -> Evaluate Fit -> Clarification (HITL) -> Strategy Generation -> Review (HITL) -> Diff Application -> PDF Compilation.

---

## 2. State & Data Models

### Graph State Definitions (TypedDict / Pydantic)

**ParentGraphState:**
- `base_resumes`: `Dict[str, BaseResumeSchema]` (Category mapped to parsed JSON)
- `config`: `dict` (Loaded from config.yaml)
- `prompts`: `dict` (Loaded from prompts.yaml)
- `pending_jobs`: `List[JobTrackerEntry]`
- `scraped_jobs`: `List[JobDetailsSchema]`
- `failed_jobs`: `List[JobTrackerEntry]`

**ChildGraphState:**
- `base_resume`: `BaseResumeSchema`
- `job_details`: `JobDetailsSchema`
- `status`: `Enum` (EVALUATING, NEEDS_CLARIFICATION, STRATEGY_DRAFTED, APPROVED, REJECTED, MANUAL_INPUT_REQUIRED)
- `clarification_questions`: `List[ClarificationQuestion]`
- `user_clarification_answers`: `Dict[str, str]`
- `strategy_markdown`: `str`
- `resume_diffs`: `ResumeDiffSchema`
- `user_feedback`: `str`
- `tailored_resume`: `BaseResumeSchema`
- `cover_letter_markdown`: `str`
- `resume_pdf_path`: `str`
- `cover_letter_pdf_path`: `str`

### Strict Application Schemas

- **JobTrackerEntry**: `job_id`, `title`, `company`, `source_type` (url/file), `source`, `category`, `user_score`, `notes`, `status`.
- **BaseResumeSchema**: `name`, `contact_info`, `professional_summary`, `skills` (dict of lists), `professional_experience` (list of objects with highlights), `educational_experience`, `other_points`.
- **JobDetailsSchema**: `job_title`, `company`, `location`, `job_id`, `category`, `salary_range`, `requirements`, `nice_to_haves`, `responsibilities`, `raw_text`.
- **ClarificationQuestion**: `id`, `type` (multiple_choice/text), `question`, `options` (Must include "Let LLM decide").
- **ResumeDiffSchema**: List of objects containing `action` (e.g., replace), `section` (JSON path), `old_value`, `new_value`, `reason`.

*(Note: Exact schemas match the definitions in `templates.MD`).*

---

## 3. Interfaces & APIs

### Internal APIs
- **Diff Applier:** Deterministic Python script (non-LLM) using the `resume_diffs` JSON to patch the `base_resume` dictionary.
- **PDF Generator:** Programmatic conversion from strictly formatted JSON/Markdown into ATS-friendly PDFs using WeasyPrint.

### External APIs
- **OpenAI API:**
  - `gpt-4o-mini`: Cheap parsing for resume-to-JSON and raw HTML-to-Job Details.
  - `gpt-4o`: Heavy reasoning for `EvaluateFitNode`, `StrategyGeneratorNode`, and `CoverLetterGeneratorNode`.
- **Web Scraper:** A scraping utility that handles rate-limiting and retrieves raw HTML from URLs (e.g., LinkedIn).

---

## 4. Node & Edge Definitions

### Parent Graph
- **`LoadConfigAndResumeNode`**: Reads configurations, prompts, base resumes, and `job_tracker.json`.
- **`JobIngestionNode`**: Processes `pending_jobs`. Routes `source_type=="url"` to scraper, `source_type=="file"` to local read. Utilizes LLM to parse text into `JobDetailsSchema` and auto-generates `job_id`.
- **`DispatchJobSubgraphs`** (Edge/Mapper): Uses LangGraph `Send` API to map `scraped_jobs` to individual Child Sub-Graphs. Passes the `category`-matching base resume.

### Child Sub-Graph
- **`EvaluateFitNode`**: Compares `base_resume` to `job_details`. Outputs fit status and `clarification_questions`.
- **`ClarificationNode`**: Triggers a HITL interrupt. Pauses execution until Streamlit frontend supplies `user_clarification_answers`.
- **`StrategyGeneratorNode`**: Drafts targeted updates based on config constraints. Outputs synchronized `strategy_markdown` and `resume_diffs`.
- **`HumanReviewNode`**: Triggers a HITL interrupt. Presents the strategy/diff to the user. Awaits approval or `user_feedback`.
- **`ReviseStrategyNode`**: Processes `user_feedback` to update `strategy_markdown` and `resume_diffs`. Loops back to `HumanReviewNode`.
- **`ApplyChangesNode`**: Deterministic patching of `resume_diffs` onto `base_resume` to produce `tailored_resume`.
- **`CoverLetterGeneratorNode`**: Generates a targeted cover letter markdown.
- **`PDFCompilerNode`**: Wraps WeasyPrint to render `tailored_resume` and `cover_letter_markdown` into PDFs.

---

## 5. Security & Error Handling

- **Anti-Bot & Scraping Failures:** If `JobIngestionNode` hits a 403 or CAPTCHA, it does not retry infinitely. It sets the job status to `MANUAL_INPUT_REQUIRED`, triggering the frontend to request raw text pasting from the user.
- **Hallucination Prevention:** The architecture strictly separates LLM strategy from document generation. By enforcing a JSON Diff (`resume_diffs`) mapped to specific fields, we avoid having the LLM silently modify immutable data (names, dates, companies) or drop layout context.
- **State Synchronization Race Conditions:** Streamlit acts as the UI state synchronizer. It iterates over SQLite graph checkpoints and performs write-backs to `job_tracker.json` to keep the portable queue accurate without causing file I/O collisions in the agent threads.
- **API Configuration & Secrets:** All secrets (OpenAI keys, etc.) should be managed via `.env` files and never hardcoded in `config.yaml`.

---

## 6. Testing Strategy

All tests will be written using the `pytest` framework.

### Unit Tests
- **Parsing Nodes:** Ensure `JobIngestionNode` accurately maps raw HTML text into `JobDetailsSchema` without dropping requirement points.
- **Diff Application:** `ApplyChangesNode` must correctly process the custom `ResumeDiffSchema` (as defined in `templates.MD` - strictly RFC 6902 is not required) on nested JSON paths and raise errors on invalid paths.
- **Schema Validation:** Verify all JSON configurations and outputs strictly conform to their Pydantic/TypedDict schemas.

### Integration Tests
- **End-to-End Pipeline Mocked:** Run a job from `job_tracker.json` through the Parent graph, spawning the Child graph, and mocking the HITL inputs (Clarification and Approval) to verify state progresses correctly.
- **SQLite Checkpoint Restoration:** Ensure a paused graph can be rehydrated from the `.db` file and correctly resumes execution from `ClarificationNode` or `HumanReviewNode` upon receiving input.
