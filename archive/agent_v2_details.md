# JobStream Agent v2 - Details of Changes

This document details all the bugs, fixes, enhancements, and features identified from the `agent_guide.md` that are required to upgrade the JobStream LangGraph agent to v2. 

## 1. Bugs & Fixes
* **Streamlit ModuleNotFoundError:** Direct execution of `src/ui/app.py` causes an import error (`No module named 'src'`). 
  * **Fix:** Inject a Python path append at the top of `src/ui/app.py` (`sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))`) to ensure relative imports resolve correctly.
* **Remove Dummy Job Fallback:** The `load_config_and_resume` node inside `src/nodes/parent_nodes.py` creates a "dummy-123" job if `data/job_tracker.json` is missing.
  * **Fix:** Remove this fallback behavior. The system should rely on a clean Streamlit onboarding flow instead of faking a job.
* **EVALUATE_FIT_PROMPT Misalignment:** The prompt in `src/nodes/evaluate_fit_node.py` fails to conform to design specifications.
  * **Fix:** Update the prompt to request a 1-10 `fit_score`. Include logic to output a boolean `should_apply` based on a threshold. Instruct the LLM to include a "Let the LLM decide the best approach" option for every multiple-choice clarification question.
  * **Dependency Fix:** Update the `EvaluateFitOutput` Pydantic schema in `src/schemas.py` to accept `fit_score` (int) and `should_apply` (bool).

## 2. New Features & Integrations
* **Application Entry Points:** Currently, the agent lacks a formal entry point, requiring temporary run scripts.
  * **Feature:** Create a `main.py` CLI script at the root level to trigger the Parent Graph's batch ingestion easily.
* **Streamlit Job Trigger Button:** The UI only functions after the graph has manually started and paused. 
  * **Feature:** Add a "Run Batch Ingestion" / "Start Job Processing" button in the Streamlit UI (sidebar) to invoke `parent_graph.invoke({"config": {}})` safely via a background thread.
* **Automate Resume Conversion:** The `src/resume_converter.py` utility is disconnected from the workflow.
  * **Feature:** Integrate the conversion logic directly into `src/nodes/parent_nodes.py`. Scan `data/starter_resumes/` for un-converted PDFs/DOCXs and trigger `convert_starter_resumes_to_json()` programmatically before the job loop starts.

## 3. Architecture & Enhancements
* **Configuration Architecture:** The `config/` directory is empty and models are hardcoded.
  * **Enhancement:** Implement a centralized `config/config.yaml` file to control model selection and other global agent settings. Remove all hardcoded model instantiations from the nodes.
* **Migration to Google Gemini Models:** The system currently defaults to OpenAI (`gpt-4o`).
  * **Enhancement:** Migrate all LLM calls to Google Gemini (`gemini-2.5-pro` with `temperature=0`). Install `langchain-google-genai` via `uv`, replace `ChatOpenAI` imports with `ChatGoogleGenerativeAI`, and update the environment variable to `GOOGLE_API_KEY`. The model name should be managed via the new config architecture.
* **Persist Ephemeral JSON Data:** `job_details.json` and `tailored_resume.json` exist only within SQLite checkpoints.
  * **Enhancement:** Update the I/O saving logic (likely near `pdf_compiler` node) to persist the `job_details.json` and `tailored_resume.json` directly into a job-specific folder `data/output/{job_id}/` alongside their PDF counterparts.