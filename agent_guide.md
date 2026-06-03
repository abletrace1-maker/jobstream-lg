# JobStream Agent Guide

This document provides a comprehensive how-to guide on using the JobStream LangGraph agent, monitoring its execution, managing its file system, and understanding its current development status.

---

## 1. How to Test Out a Single Job

JobStream uses a Streamlit UI connected to a background LangGraph agent to process jobs. To test out a single job application from start to finish, follow these steps:

### Step 1: Provide a Base Resume
The agent uses your base resume to evaluate your fit and tailor your application.
1. Place your base resume document (e.g., `resume.pdf`, `resume.docx`, or `resume.txt`) into the `data/starter_resumes/` folder.
2. The file must be named using the category format: `starter_[category].[ext]` (e.g., `starter_software_engineering.pdf`).
3. When the agent runs, it will automatically detect new files here and convert them into a structured JSON format in `data/json_resumes/`.

### Step 2: Add the Job to the Tracker
The agent reads from a JSON queue to know which jobs to process.
1. Open `data/job_tracker.json`.
2. Add a new JSON object for your job. To test the **web scraper**, provide a real URL. Set the status to `"PENDING"`.
   ```json
   [
     {
       "job_id": "test-job-001",
       "title": "Software Engineer",
       "company": "Tech Corp",
       "source_type": "url",
       "source": "https://www.linkedin.com/jobs/view/example-job",
       "category": "software_engineering",
       "user_score": "high",
       "notes": "Testing the scraper and single job flow",
       "status": "PENDING"
     }
   ]
   ```

### Step 3: Start the Agent (Restarting for New Jobs)
If you just put a new job in the tracker, you need to trigger the agent to read the queue.
1. Make sure your `.env` file is set up with your `GOOGLE_API_KEY`.
2. Launch the Streamlit application in your terminal:
   ```bash
   uv run streamlit run src/ui/app.py
   ```
3. Open the Streamlit dashboard in your web browser.
4. **To start or restart the agent to read new jobs:** Look at the left sidebar in the Streamlit UI and click the **"Start Job Processing"** button. This will trigger the agent to run in the background, read the `data/job_tracker.json` file, and begin processing any jobs marked as `"PENDING"`.

---

## 2. Monitoring the Agent & Testing the Scraper

### How can I tell what is happening as it works through the nodes?
Since the agent runs as a background thread initiated by Streamlit, the primary way to see real-time node transitions and internal logs is to **look at the terminal where you ran `uv run streamlit run src/ui/app.py`**. 
- You will see logs indicating graph transitions, LLM generations, and scraping updates.
- In the **Streamlit UI**, you will see the job status change. When the agent pauses for your input (e.g., it needs clarification on your experience), the UI will update to show an "Action Required: Clarifications Needed" section.

### How can I test the job scraper, and will I see the browser open?
Yes, you will literally see the browser open! 
- The web scraper uses `undetected_chromedriver` running in **headed mode** (not headless). 
- When the agent reaches the ingestion node for a URL-based job, an actual Chrome browser window will pop up on your screen.
- You will watch the browser navigate to the job URL, wait for a few seconds to bypass bot detection, and then simulate human scrolling before closing.
- Check your terminal output—you will see lines like `Fetching: <URL>` and `Simulating human scrolling...`.

### Can I see if the job details are being saved?
Yes! Once the scraper finishes and parses the HTML, the extracted job information is persisted to your file system. You can verify it worked perfectly by looking at:
`data/output/test-job-001/job_details.json`
*(See Section 3 below for full details on file saving).*

---

## 3. Where Do Files Get Saved? (File System Workflow)

As you run through the nodes, the agent manages your files across a few specific directories. Here is exactly what gets saved and where:

1. **`data/starter_resumes/` (Input)**
   - Where you drop your raw resumes (`.pdf`, `.docx`).
2. **`data/json_resumes/` (Internal Agent Input)**
   - When the pipeline starts, it automatically converts your starter resumes into parsed JSON (e.g., `base_resume_software_engineering.json`). This is what the LLM actually reads.
3. **`data/job_tracker.json` (State & Queue)**
   - The queue file. The Streamlit UI updates the `status` fields here as the graph progresses (e.g., changing from `PENDING` to `NEEDS_CLARIFICATION` to `COMPLETED`).
4. **`data/checkpoints.sqlite` (Agent Memory)**
   - A local database used by LangGraph to pause, resume, and store the internal state of the map-reduce graphs.
5. **`data/output/{job_id}/` (Final Output & Artifacts)**
   - For every processed job, a dedicated folder is created using the `job_id`. 
   - **`job_details.json`**: The clean, structured data scraped from the job URL.
   - **`tailored_resume.json`**: The final JSON structure of your resume after the LLM has applied targeted changes.
   - **`{job_id}_resume.pdf`**: The final, ATS-friendly compiled PDF of your tailored resume.
   - **`{job_id}_cover_letter.pdf`**: The final compiled PDF of your tailored cover letter.

---

## 4. What Still Needs to be Developed?

The v2 upgrade integrated Google Gemini, fixed the Streamlit frontend, and added output persistence. However, a few technical debts remain.

**If nothing else needs to be developed, it would be stated here. However, the following minor architectural items still need to be addressed by the development team:**

1. **Hardcoded Models vs. Config File:**
   - Although `config/config.yaml` exists and defines the Gemini model and temperature settings, the LLM nodes (`src/nodes/evaluate_fit_node.py`, `src/nodes/strategy_generator_node.py`, etc.) are still hardcoding `ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)`. The code needs to be updated to inject the model configuration directly from `state.get("config")`.
2. **Remove Dummy Job Fallback:**
   - In `src/nodes/parent_nodes.py`, if the `data/job_tracker.json` file is completely empty or missing, the `load_config_and_resume` node still creates a fake `"dummy-123"` job to prevent crashing. This fallback should be removed, allowing the system to idle gracefully with an empty queue.
