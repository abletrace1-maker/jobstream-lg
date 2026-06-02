# JobStream Agent Guide

This document provides a comprehensive overview of the JobStream LangGraph agent, including its workflow, execution instructions, file system architecture, and development status.

## 1. Workflow Breakdown & Node Architecture

The JobStream agent is built on a **Parent-Child (Map-Reduce) Architecture** to ensure context isolation across multiple job applications concurrently. 

### The Parent Graph (Batch Coordinator)
Defined in `src/graph.py`, this graph orchestrates the ingestion of all pending jobs.

*   **`load_config_and_resume` (in `src/nodes/parent_nodes.py`)**
    *   **Action:** Reads the job queue from `data/job_tracker.json` and loads the base user resumes from `data/json_resumes/*.json`.
    *   **State Impact:** Updates `pending_jobs` and `base_resumes` in the `ParentGraphState`. 
*   **`job_ingestion` (in `src/nodes/parent_nodes.py`)**
    *   **Action:** Iterates over the `pending_jobs`. It parses and normalizes the job description based on the `source_type`:
        *   **Path A (Web URL):** Uses `src/utils/scraper.py` (undetected_chromedriver) and `src/utils/html_parser.py` (BeautifulSoup) to stealthily scrape the webpage and extract the job details (title, responsibilities, requirements).
        *   **Path B (Text File):** Uses `_load_file_source` to read raw text from a provided local file path.
    *   **State Impact:** Outputs parsed jobs into `scraped_jobs` or `failed_jobs`.
*   **`map_to_job_processor` (Edge routing)**
    *   **Action:** For every successfully scraped job, this matches the job's category to the corresponding base resume and uses the LangGraph `Send` API to spawn a separate instance of the `child_graph`.

### The Child Sub-Graph (Job Processor)
Defined in `src/child_graph.py`, this graph executes the tailoring logic for a **single** job application.

*   **`evaluate_fit` (in `src/nodes/evaluate_fit_node.py`)**
    *   **Action:** Calls `gpt-4o` to compare the `base_resume` JSON and the `job_details` JSON. Formulates questions if the LLM needs missing context (e.g., "Do you have AWS experience?").
    *   **State Impact:** Outputs a `status` (either `NEEDS_CLARIFICATION` or `EVALUATING`) and a list of `clarification_questions`.
*   **`clarification` (in `src/nodes/child_nodes.py`)**
    *   **Action:** **Interrupt Node.** If the status is `NEEDS_CLARIFICATION`, execution pauses here. The Streamlit UI surfaces these questions. Once the user submits answers, the UI resumes the graph.
*   **`strategy_generator` (in `src/nodes/strategy_generator_node.py`)**
    *   **Action:** Calls `gpt-4o` to generate two items based on the job details and clarification answers: a human-readable `strategy_markdown` and programmatic JSON `resume_diffs` targeting specific sections of your resume.
*   **`human_review` (in `src/nodes/child_nodes.py`)**
    *   **Action:** **Interrupt Node.** The graph pauses. The Streamlit UI displays the `strategy_markdown` and `resume_diffs`. The user can either "Approve" or provide written feedback to revise the strategy.
*   **`revise_strategy` (in `src/nodes/revise_strategy_node.py`)**
    *   **Action:** If the user provides feedback, this node calls `gpt-4o` to adjust the strategy and JSON diffs based strictly on the user's notes, then routes back to `human_review`.
*   **`apply_changes` (in `src/nodes/child_nodes.py`)**
    *   **Action:** Once approved, this node uses `src/utils/diff_applier.py` (a deterministic python function, no LLMs involved) to overwrite the target fields in the base resume JSON, outputting a `tailored_resume`.
*   **`cover_letter` (in `src/nodes/cover_letter_generator_node.py`)**
    *   **Action:** Calls `gpt-4o` to generate a tailored cover letter using the newly tailored resume and job details. Outputs `cover_letter_markdown`.
*   **`pdf_compiler` (in `src/nodes/child_nodes.py`)**
    *   **Action:** Utilizes `weasyprint` and `jinja2` (via `src/utils/pdf_compiler.py`) to convert the `tailored_resume` JSON and cover letter markdown into ATS-friendly PDFs using HTML templates (`src/templates/`).
    *   **State Impact:** Saves the files to `data/output/` and updates `resume_pdf_path` and `cover_letter_pdf_path`.


---

## 2. Test Run Walkthrough

To run a test with both a web URL and a local text file, follow these steps:

### Setup Your Base Resumes
The LangGraph agent **strictly requires JSON** formatted base resumes to execute safely without hallucinations. It does **not** automatically parse docx/pdf files during the graph execution. 
However, there is a built-in utility (`src/resume_converter.py`) to convert your documents:
1. Place your base resume (e.g., `resume.pdf`, `resume.docx`, or `resume.txt`) into `data/starter_resumes/`. It must be named in the format `starter_[category].[ext]` (e.g., `starter_software_engineering.pdf`).
2. You must manually execute the converter in Python to generate the JSON file (since it is not currently wired to a CLI command):
   ```python
   from src.resume_converter import convert_starter_resumes_to_json
   convert_starter_resumes_to_json()
   ```
3. This creates `data/json_resumes/base_resume_software_engineering.json`. This is what the agent actually reads.

### Prepare the Job Tracker Queue
Open `data/job_tracker.json`. This is the queue the agent reads to find jobs. Add your URL job and your text-file job:
*(Note: If you use a text file, place the text file anywhere accessible, such as `data/job2_description.txt`)*

```json
[
  {
    "job_id": "job-1-url",
    "title": "Software Engineer",
    "company": "Tech Corp",
    "source_type": "url",
    "source": "https://www.linkedin.com/jobs/view/example-job",
    "category": "software_engineering",
    "user_score": "high",
    "notes": "Testing URL extraction",
    "status": "PENDING"
  },
  {
    "job_id": "job-2-file",
    "title": "Backend Developer",
    "company": "Data Inc",
    "source_type": "file",
    "source": "data/job2_description.txt",
    "category": "software_engineering",
    "user_score": "high",
    "notes": "Testing file extraction",
    "status": "PENDING"
  }
]
```

### Environment Config
- Make sure your `OPENAI_API_KEY` is set in your environment variables. 
- **Configuration Note:** The `config` folder is completely empty. The agent currently has the models hardcoded to `gpt-4o` directly in the node files (e.g., `src/nodes/evaluate_fit_node.py`). It does **not** pull from a `config.yaml` file as originally specified in the design docs.

### Execution
Right now, there is **no entry-point script** to trigger the Parent Graph (see section 4). To actually start the pipeline, you need to create a temporary script (e.g., `run.py`):
```python
from src.graph import parent_graph
# This triggers the process
parent_graph.invoke({"config": {}})
```
Execute it: `uv run python run.py`. It will parse the jobs and pause at the Child Graph interrupts.

---

## 3. Launching the Streamlit Front-End

The Streamlit UI is responsible for the Human-in-the-loop (HITL) interactions—specifically answering clarification questions and approving resume strategies. It is functionally complete for this purpose.

To launch the UI, run:
```bash
uv run streamlit run src/ui/app.py
```

**Is it ready to go?**
Yes, for interacting with paused graphs. It correctly connects to the `data/checkpoints.sqlite` database, reads the `job_tracker.json` state, displays questions, and has functional buttons to inject state (Approve/Feedback) back into the graph to resume execution. However, it lacks a button to *start* the initial batch ingestion process.

---

## 4. What Still Needs to be Developed?

While the core agent architecture and node logic are highly advanced and strictly adhere to the Parent/Child Map-Reduce design, the following integration pieces are incomplete:

1. **No Application Entry Point (Trigger):**
   There is currently no `main.py` CLI script, nor is there a "Run Batch Ingestion" button in the Streamlit UI to invoke `parent_graph`. The graphs are compiled, but you have to write a custom Python script to invoke them.
2. **Configuration Architecture is Missing:**
   The `config/` directory is empty. In `src/nodes/parent_nodes.py` and the various LLM nodes, `ChatOpenAI(model="gpt-4o")` is hardcoded. The system ignores the originally planned `config.yaml` and `prompts.yaml`. 
3. **Dummy File Generation:**
   In `src/nodes/parent_nodes.py`, if `data/job_tracker.json` is missing, the code has a fallback to generate a fake "dummy-123" dummy job to prevent crashing. This should eventually be removed in favor of a clean Streamlit onboarding flow.
4. **Resume Converter Integration:**
   The `src/resume_converter.py` logic successfully turns PDFs/DOCXs into the required JSON schema, but it is totally disconnected from the pipeline. Users have to run it manually. 

---

## 5. Actionable Upgrades & Fixes Needed (For AI PM / Coding Agents)

Based on a detailed review of the codebase against the original design specifications, the following tasks should be specced into Epics/Features by the Project Manager Agent and executed by the Coding Agent:

### 1. Fix `EVALUATE_FIT_PROMPT` Misalignment
The current prompt in `src/nodes/evaluate_fit_node.py` has poor conformance to the guidelines established in `agent-design-documents/prompt_details.md`.
**Requirements for the Coding Agent:**
- Update the `EVALUATE_FIT_PROMPT` string to explicitly request a 1-10 fit score.
- Instruct the LLM to output a boolean `should_apply` flag based on a defined threshold (e.g., if score < 3).
- Add explicit instructions telling the LLM to include a "Let the LLM decide the best approach" option for every multiple-choice clarification question generated.
- Ensure the `EvaluateFitOutput` Pydantic schema in `src/schemas.py` is updated to accept the `fit_score` and `should_apply` variables.

### 2. Migration to Google Gemini Models
The system currently hardcodes OpenAI (`gpt-4o`). It needs to be migrated to use Google Gemini (`gemini-2.5-pro`) across all nodes.
**Requirements for the Coding Agent:**
- Run `uv add langchain-google-genai` to install the correct provider package.
- In all four LLM node files (`evaluate_fit_node.py`, `strategy_generator_node.py`, `cover_letter_generator_node.py`, `revise_strategy_node.py`), replace `from langchain_openai import ChatOpenAI` with `from langchain_google_genai import ChatGoogleGenerativeAI`.
- Update the LLM instantiations from `llm = ChatOpenAI(model="gpt-4o", ...)` to `llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)`.
- Note that the environment variable used will switch from `OPENAI_API_KEY` to `GOOGLE_API_KEY`.

### 3. Persist Ephemeral JSON Data
Currently, the extracted `JobDetailsSchema` and the `tailored_resume` JSONs are only stored ephemerally within the LangGraph SQLite `checkpoints.sqlite` database. 
**Requirements for the Coding Agent:**
- Add file I/O logic to save the `job_details.json` and `tailored_resume.json` directly into the `data/output/` directory alongside their PDF counterparts, preferably organized into job-specific sub-folders (e.g., `data/output/{job_id}/`).

### 4. Fix Streamlit ModuleNotFoundError (`No module named 'src'`)
When launching `src/ui/app.py` directly via Streamlit (`uv run streamlit run src/ui/app.py`), the Python path (`sys.path`) does not automatically include the project root. This causes the internal relative imports (e.g., `from src.schemas import ...`) to fail with a `ModuleNotFoundError`.
**Requirements for the Coding Agent:**
- The best fix is to inject a path append at the very top of `src/ui/app.py` (before any `src` imports occur):
  ```python
  import sys
  import os
  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
  ```
- Alternatively, ensure the project is installed as an editable package using `uv` (via a valid `pyproject.toml` or `setup.py`) or provide an execution wrapper script that sets `PYTHONPATH=.`.
- Once implemented, the agent should test launching the Streamlit app to confirm the import error is resolved.

---

## 6. File System Breakdown

### 📂 `src/` (Agent Source Code)
- `graph.py`: Defines the Parent Graph (Batch Coordinator) and the Map-Reduce dispatch logic.
- `child_graph.py`: Defines the isolated Sub-Graph (Job Processor) handling a single application.
- `state.py`: Defines the typed dictionaries for `ParentGraphState` and `ChildGraphState`, and the `JobStatus` enums.
- `schemas.py`: Contains strict Pydantic schemas (`BaseResumeSchema`, `JobDetailsSchema`, `ResumeDiffSchema`) used to enforce structured LLM output.
- `resume_converter.py`: A disconnected utility to convert raw resumes (.pdf, .docx, .txt) into JSON.
- **`nodes/`**: Contains the logic for all LangGraph nodes (LLM calls, prompts, API interactions).
- **`utils/`**: Helper utilities for scraping (Selenium/UC), HTML parsing (BeautifulSoup), deterministic JSON diff patching, and PDF compiling (WeasyPrint/Jinja2).
- **`ui/`**: Contains `app.py`, the Streamlit frontend.
- **`templates/`**: HTML templates (`resume_template.html`, `cover_letter_template.html`) utilized by Jinja2 to generate the final PDFs.

### 📂 `data/` (Agent Working Environment)
- **`starter_resumes/`**: **[User Input]** The folder where you place your raw PDFs or Word Docs for conversion.
- **`json_resumes/`**: **[Agent Input]** The converted JSON resumes that the Parent Graph actively reads during execution.
- **`job_tracker.json`**: **[User Input / UI Update]** The main queue containing jobs to process, updated continuously by Streamlit.
- **`checkpoints.sqlite`**: **[Agent Memory]** The LangGraph SQLite database holding thread states and interrupts.
- **`output/`**: **[Agent Output]** Where the final, tailored PDF resumes and cover letters are saved.

### 📂 `config/` (Configuration)
- **[Currently Empty]**: Intended to hold global agent configuration (e.g., `config.yaml`, `prompts.yaml`) rather than hardcoding models.

### 📂 `planning/` & `agent-design-documents/`
- Documentation and specification trackers used by the initial developer agents to build the system (PRDs, TRDs). 

---

## 7. Tips & Suggestions Discovered During Deep Dive

1. **Add a "Start Job Processing" Button to Streamlit:** To make the app truly full-stack, add a button on the Streamlit sidebar that invokes `parent_graph.invoke(...)` in a background thread. Currently, the UI only works *after* the graph has been started manually.
2. **Fix the Configuration Hardcoding:** Move the hardcoded `model="gpt-4o"` instances into a centralized `config.yaml` as specified in the original TRD. This will save significant costs by allowing you to swap in `gpt-4o-mini` for basic extraction tasks.
3. **Automate Resume Conversion:** Inside `parent_nodes.py`, you can add a quick check to scan `data/starter_resumes/`. If a new PDF is found that hasn't been converted to JSON yet, you can trigger `convert_starter_resumes_to_json()` programmatically before starting the job loop.