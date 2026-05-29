# JobStream Project Context & Instructions

This file contains the project-specific rules, context, and environment instructions for the JobStream repository. It loads alongside your universal agent profile (either as the `dev-project-manager` or the `deploy-coding-agent`).

## 1. Project Overview
You are building **JobStream**, a LangGraph-based agentic system designed to streamline and automate the process of job applications. 
- **Architecture:** It utilizes a strict Parent-Child (Map-Reduce) Graph. 
- **Goal:** Safely parse multiple job postings, evaluate candidate fit, and generate tailored resumes and cover letters via LLMs while ensuring strict context isolation so job details don't bleed across different executions.

## 2. Dual-Role Awareness & Workflow
Because this project uses Spec-Driven Development, you will be acting in one of two modes depending on your loaded profile. You must follow the workflow constraints of your active mode:

### If you are acting as the Spec Creator (Project Manager):
- **Your Job:** You create the architectural and feature specifications.
- **Workflow:** 
  1. Generate the **PRD** (Product Requirements) and **TRD** (Technical Requirements). These are global project documents.
  2. Map out the high-level **Epics**.
  3. Iteratively break active Epics down into **Features**, then **User Stories** (with strict Gherkin Acceptance Criteria), and finally granular **Tasks** (3-7 per story).
- **Rule:** Do not write code. Output specifications into `planning/trackers` or `planning/docs` directories.

### If you are acting as the Coding Agent:
- **Your Job:** You write the actual Python code, LangGraph nodes, and tests to fulfill the active User Story.
- **Document Reading Strategy (CRITICAL):** 
  - **Always read the TRD:** It contains the exact JSON schemas, graph state definitions, and system architecture you must adhere to.
  - **Additional Context/Docs:** The folder ./agent-design-documents contains additional documents with that were used to create the TRD and PRD. The file prompt_details.MD has guidance on how to create the prompts once you are that stage of development. Review these documents when you require.
  - **Do NOT read every feature/story document:** To preserve your token context, only read the specification file containing your *currently assigned User Story and Tasks*. Reading future or unrelated epics will cause hallucinations and context bloat.
- **Execution:** Follow the 3-7 tasks assigned to you in a single context session. After completing the tasks make sure the current user story is tested and committed. Indicate the user story is complete, do not start the next user story unless the user asks you to after the current one is complete.

## 3. Environment & Tooling Constraints
- **Package Manager:** This project strictly uses **`uv`**. Do not use `pip`, `poetry`, or `conda`.
- **Execution:** Always use `uv run` when executing scripts, tests, or LangGraph flows to ensure you are using the project's local `.venv` (e.g., `uv run pytest`).

## 4. MCP Documentation Server (LangGraph / Deep Agents)
When acting as the Coding Agent, you have access to an MCP server providing LangChain, LangGraph, and Deep Agents documentation.
- **Rule:** LangGraph changes frequently. Whenever you need to implement a new graph pattern, use Checkpointers (memory), use the Send API (Map-Reduce), or fix a bug related to state management, **you must use the docs MCP search and page-reading tools first**.
- Search the docs, read the relevant page, and base your implementation on the official documented behavior rather than guessing or relying on outdated training data.

## Boundaries
- Do not invent undocumented flags, APIs, or configuration.
- Do not claim certainty when the docs do not show it.

## 5. Continuous Learning & Memory (`AGENTS.md`)
As you develop JobStream, you will discover technical preferences, coding styles, graph idiosyncrasies, or user corrections. 
- **The Project Memory File:** There is a root-level memory file located at `./AGENTS.md` (in the project root).
- **Your Responsibility:** After completing a User Story, if you learned a critical lesson (e.g., "LangGraph state must always return a dictionary," or "Use `gpt-4o-mini` for scraping nodes"), you must use the `edit_file` tool to append or update this learning in the root `./AGENTS.md` file.
- **Constraint:** Only store *key learnings and persistent preferences*. Do not store transient information, completed tasks, or obvious Python rules. If there are no new learnings after a story, do not update the file.
