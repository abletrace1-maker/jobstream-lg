# Other Design Notes & Architecture (other_design_notes.MD)

## Recommended File Structure

To support spec-driven development, clear separation of concerns, and easy UI integration, the JobStream application should follow this directory structure:

```text
jobstream-langgraph/
├── data/
│   ├── starter_resumes/      # Raw user resumes (PDF/Docx/TXT)
│   ├── json_resumes/         # Resumes converted to the strict Base JSON schema
│   ├── raw_jobs/             # Manually saved .txt files of job descriptions
│   ├── job_tracker.json      # The central queue and status list of jobs
│   └── outputs/              # Final tailored PDFs and Markdown strategies
├── config/
│   ├── config.yaml           # Model settings, immutable constraints, UI toggles
│   └── prompts.yaml          # Centralized LLM system prompts
├── src/
│   ├── __init__.py
│   ├── state.py              # Pydantic/TypedDict definitions for Graph State
│   ├── schemas.py            # Pydantic models for structured LLM outputs (Diffs, Job Details)
│   ├── graph.py              # LangGraph compilation (Edges, Routing, Checkpointing)
│   ├── nodes/                # Individual graph nodes
│   │   ├── __init__.py
│   │   ├── ingestion.py      # Resume conversion and Job Scraping/Parsing
│   │   ├── evaluation.py     # EvaluateFit and Clarification logic
│   │   ├── strategy.py       # Strategy generation and revision logic
│   │   └── document.py       # JSON Patching and PDF Compilation
│   └── utils/
│       ├── pdf_generator.py  # Wrapper for WeasyPrint/Typst logic
│       ├── scraper.py        # Web scraping logic (handles delays to avoid bans)
│       └── diff_applier.py   # Script to safely apply JSON Diffs to Base JSON
├── app.py                    # Streamlit frontend entry point
├── requirements.txt          # Python dependencies (langgraph, streamlit, weasyprint, etc.)
└── README.md
```

## File Naming Conventions & Categories

Because a candidate might apply for different *categories* of jobs (e.g., Project Management vs. Software Engineering), the system supports multiple base resumes.

### 1. Starter Resumes
The user must name their raw starter documents using the prefix `starter_` followed by the category. 
*   **Format:** `starter_[category].[ext]`
*   **Examples:** `starter_project_management.pdf`, `starter_engineering.docx`

### 2. JSON Resumes
When the "Resume to JSON Converter" processes the starter files, it must maintain the category in the output filename.
*   **Format:** `base_resume_[category].json`
*   **Examples:** `base_resume_project_management.json`, `base_resume_engineering.json`

### 3. Generated Output Files
When saving the final PDFs and markdown strategies, the outputs should clearly identify the category, company, and the specific `MM-DD_n_company_name` job ID.
*   **Resume Format:** `[category]_[job_id]_resume.pdf`
*   **Cover Letter Format:** `[category]_[job_id]_cover_letter.pdf`
*   **Example:** `engineering_05-20_1_DataTech-Solutions_resume.pdf`

## System Resiliency & Architecture Notes

### 1. Unified Job Ingestion (URL vs Text)
The system uses a single unified `JobIngestionNode` to handle both LinkedIn URLs and raw `.txt` files. 
*   **Routing Logic:** The node inspects the `source_type` in the `job_tracker.json`.
*   If `url`, it calls the scraper script (with safe delays) and uses the HTML-to-JSON mapping prompt.
*   If `file`, it uses `read_file` on the local path (e.g., `data/raw_jobs/job1.txt`) and uses a standard Text-to-JSON mapping prompt.
*   Regardless of the source, both routes yield the exact same `Parsed Job Details (JSON)` schema to ensure downstream nodes (like `EvaluateFitNode`) don't need to care where the text came from.

### 2. CAPTCHA / Anti-Bot Handling
If the `SequentialScraperNode` hits a block (HTTP 403, known CAPTCHA elements, or LLM detects a paywall wall of text), the node must NOT loop infinitely. 
*   **Action:** Update the job's sub-graph state to `status: MANUAL_INPUT_REQUIRED`.
*   **Result:** The graph yields to the Streamlit UI, presenting a text box saying: *"Failed to scrape [URL]. Please paste the raw job description here."* The user pastes the text, clicks submit, and the node parses the text instead of the URL.

### 3. Context Isolation (The Map-Reduce Pattern)
As requested, LLM context pollution is a major risk when handling 10-15 jobs. 
*   The system uses the LangGraph `Send` API to map the list of parsed jobs into completely distinct Sub-Graphs.
*   The `StrategyGeneratorNode` for Job A will only ever see the State dictionary for Job A. It physically cannot access the requirements for Job B. 

### 4. Database Selection for Checkpointing
*   For local, single-user operation (which this is), `SqliteSaver` (from `langgraph.checkpoint.sqlite`) is the perfect choice. It stores the state as a local `.db` file in the project root. If the Streamlit app is closed and reopened, it queries the SQLite DB to restore all active and paused job processing threads.

### 5. Streamlit Status Syncing (Write-Back)
While LangGraph's SQLite database is the ultimate source of truth for the active workflow state, the user needs a readable, portable `job_tracker.json`. 
*   **The Problem:** The Agent graph should not be responsible for constantly doing file I/O to update the tracker file every time a node completes (this causes race conditions).
*   **The Solution:** The Streamlit frontend handles the Write-Back. As Streamlit iterates over the active Graph threads to render the UI, it checks the `status` of each job (e.g., `PENDING`, `NEEDS_CLARIFICATION`, `APPROVED`). It then compares this to the status in `data/job_tracker.json`. If they differ, Streamlit updates the JSON file and saves it. This guarantees the JSON file is always synchronized with the actual graph execution state.