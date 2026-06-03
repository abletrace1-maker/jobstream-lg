# JobStream Agent PRD

## 1. Executive Summary
JobStream is a Parent-Child (Map-Reduce) LangGraph-based AI agent designed to automate the customization of resumes and cover letters for multiple job applications concurrently. By isolating each job application into its own sub-graph, the system prevents LLM context pollution and hallucinations. It integrates a Streamlit-based Human-in-the-Loop (HITL) UI, allowing the user to provide clarification on missing context and approve strategic resume changes before generating final ATS-friendly PDFs. This system drastically reduces the manual effort required to tailor applications while maintaining strict control over the final output.

## 2. Problem Statement
### Who has this problem?
Technical job seekers who apply to multiple roles simultaneously (e.g., Project Management vs. Software Engineering) and need to tailor their resumes for each specific job description.

### What is the problem?
Applying to 10-15 jobs requires extreme resume tailoring to pass ATS and impress recruiters. Doing this manually is overwhelmingly slow. Using standard LLM chat interfaces to manage multiple applications leads to "context pollution"—the LLM mixes up requirements from Job A into the resume for Job B, or hallucinates skills and experiences that the candidate does not possess.

### Why is it painful?
- **User impact:** Wastes hours of time manually tweaking resumes and writing cover letters for each application. Context pollution reduces the quality of the resume, potentially introducing false claims or irrelevant skills.
- **Business impact (Personal):** Low volume of applications or low-quality tailored applications leads to a poor interview conversion rate.

### Evidence
- Standard LLM chat sessions lose context isolation when evaluating multiple jobs.
- The need to preserve strict resume JSON schemas and prevent hallucinations (like inventing jobs or changing dates) is difficult to enforce without programmatic diffs and HITL review.

## 3. Target Users & Personas
### Primary Persona: The Strategic Job Seeker
- **Role:** Technical Professional (e.g., Engineer, PM) applying to multiple categories of roles.
- **Goals:** Apply to numerous jobs with highly tailored, accurate resumes and cover letters without spending hours on manual edits.
- **Pain points:** Context pollution in ChatGPT, formatting issues when converting LLM output to PDF, and the risk of the LLM hallucinating skills.
- **Current behavior:** Manually copying/pasting job descriptions into an LLM, manually checking for hallucinations, and manually updating a Word/PDF document.

## 4. Strategic Context
### Business Goals
- Increase the volume of highly targeted job applications that can be submitted per week.
- Improve interview conversion rates by ensuring resumes directly match job description requirements.
- Maintain a single source of truth for all pending applications via a programmatic tracking queue.

### Why now?
The current job market demands hyper-specific, tailored applications to stand out. At the same time, AI tools (like LangGraph and structured LLM outputs) are mature enough to reliably automate this process, provided the architecture strictly enforces context isolation and human review.

## 5. Solution Overview
We are building the **JobStream Agent**, a workflow orchestration tool that ingests job descriptions and produces customized resume and cover letter PDFs.

**How it works:**
1. User adds job URLs or text files to a `job_tracker.json` queue.
2. The **Parent Graph (Batch Coordinator)** reads the queue and scrapes/parses the job details into a strict JSON schema, bypassing simple anti-bot protections.
3. For each job, it spawns an isolated **Child Sub-Graph (Job Processor)**.
4. The Child Graph compares the job against the user's base resume (JSON) and identifies missing context.
5. The graph pauses and uses Streamlit to ask the user clarification questions (HITL).
6. Upon receiving answers, it generates a Markdown strategy and a programmatic JSON Diff of the proposed resume changes.
7. The graph pauses again for Human Review via Streamlit. The user can approve or request revisions.
8. Once approved, changes are programmatically applied to the base JSON resume.
9. A cover letter is generated, and both documents are compiled into ATS-friendly PDFs.

**Key features:**
- Map-Reduce architecture for total context isolation.
- Dual-source ingestion (LinkedIn URLs or raw text fallbacks).
- Strict programmatic constraints (e.g., cannot modify dates, names, or companies).
- Human-in-the-Loop (HITL) checkpoints for clarification and approval.

## 6. Success Metrics
### Primary Metric
- **Time saved per tailored application:** Reduce the manual hours spent tailoring resumes to minutes per job.

### Secondary Metrics
- **[PENDING USER INPUT: What other metrics should we track? e.g., Number of applications processed per week?]**

### Guardrail Metrics
- **Cost:** API cost per application must remain sustainable.
- **Accuracy:** Zero hallucinated skills, jobs, or experiences.

## 7. Epics & High-Level Requirements

**Epic 1: Batch Coordinator & Context Isolation Architecture**
- We believe that using a LangGraph Parent-Child Map-Reduce architecture will allow us to process multiple applications simultaneously without LLM context pollution between different job descriptions.

**Epic 2: Unified Job Ingestion & Parsing**
- We believe that building a resilient ingestion node capable of handling both URLs (with randomized delays) and raw text fallbacks will ensure we never get completely blocked by CAPTCHAs, resulting in a structured Job Details JSON every time.

**Epic 3: AI Fit Evaluation & Strategy Generation**
- We believe that by comparing the structured job requirements against a base resume and generating programmatic JSON diffs (alongside human-readable Markdown), we can safely tailor a resume without risking hallucinations in immutable fields.

**Epic 4: Streamlit Human-in-the-Loop (HITL) UI**
- We believe that implementing execution interrupts using `SqliteSaver` and exposing them through a Streamlit UI will give the user ultimate control over clarification answers and final strategic approvals before PDF generation.

**Epic 5: Programmatic PDF Document Generation**
- We believe that programmatically applying the approved JSON diffs to the base resume and passing it to a templating engine (like WeasyPrint or Typst) will guarantee a consistent, ATS-friendly PDF output every time.

## 8. Out of Scope
- **Fully autonomous application submission:** The system will not click "Apply" or fill out forms on LinkedIn/Workday. The user handles submission manually.
- **Automated job searching:** The system does not scrape job boards to find jobs. The user must manually curate and populate the `job_tracker.json`.
- **Modifying base factual data:** The system will not alter core immutable fields such as names, dates of employment, education degrees, or previous company names.

## 9. Dependencies & Risks
### Dependencies
- **Technical:** `langgraph`, `streamlit`, a programmatic PDF generator (`weasyprint` or `typst`), and OpenAI API access.
- **External:** Reliance on LinkedIn or other job board HTML structures for scraping (mitigated by the raw text fallback).

### Risks & Mitigations
- **Risk:** High LLM API costs from parallel processing.
  - **Mitigation:** Use `gpt-4o-mini` for cheap parsing tasks and reserve `gpt-4o` only for heavy reasoning (evaluation and strategy).
- **Risk:** Streamlit state falling out of sync with LangGraph SQLite checkpoints.
  - **Mitigation:** The Streamlit frontend actively handles write-backs to the `job_tracker.json` to ensure the portable tracking list matches the SQLite graph state.

## 10. Open Questions
- **No pending open questions.** Requirements are currently aligned.