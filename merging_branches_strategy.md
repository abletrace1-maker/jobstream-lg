# Merging Branches Strategy

This document outlines the current state of the repository's Git branches, the conflicts that exist between them, and the step-by-step strategy to successfully merge all completed features into the `main` branch.

## 1. The Git History Situation

The repository currently has a split history resulting from features being developed in parallel but not merged back into `main` sequentially:

*   **`main` (Current State):** Contains Epics 1 (F-01, F-02, F-03) and F-06 (Resume to JSON Converter). 
*   **The Unmerged Epic 2 Chain (`F-04` & `F-05`):** The Web Scraper (F-04) and Job Ingestion Node (F-05) branches were branched off of `F-03` *before* `F-06` was merged into `main`. The `F-05` branch contains both the F-04 and F-05 commits.
*   **The Unmerged F-07 Branch:** `feature/F-07-Evaluate-Fit-Node` was branched cleanly off of the current `main` (after F-06).

## 2. Conflict Analysis

*   **F-07 Merge:** If you merge `feature/F-07-Evaluate-Fit-Node` into `main` right now, **there will be no conflicts**. It is a direct continuation of `main`.
*   **F-05 Merge:** If you merge `feature/F-05-Job-Ingestion-Node-URL-Text-Handling` into `main`, **you will encounter several merge conflicts**. This is because both F-05 and F-06 (which is in `main`) touched the exact same core files. 

### Expected Conflicts when Merging F-05:
1.  **Dependency Conflicts (`pyproject.toml` and `uv.lock`)**: 
    *   `main` added `python-docx` and `pypdf`.
    *   `F-05` added `beautifulsoup4`, `selenium`, `requests`, etc.
    *   *Resolution:* You must accept **both** sets of additions so all tools have their required dependencies.
2.  **Parent Graph Definition (`src/graph.py`)**:
    *   `main` has `dummy_job_ingestion` stubbed out.
    *   `F-05` imported and swapped the stub for the real `job_ingestion` node.
    *   *Resolution:* Accept the changes from `F-05` to wire up the real node.
3.  **Parent Nodes Logic (`src/nodes/parent_nodes.py`)**:
    *   `main` implemented the `load_config_and_resume` node.
    *   `F-05` implemented the `job_ingestion` node.
    *   *Resolution:* Accept **both** implementations so the file contains both `load_config_and_resume` and `job_ingestion`.
4.  **Test Suite (`tests/test_parent_nodes.py` and `tests/test_child_graph.py`)**:
    *   Both branches added new test functions to these files.
    *   *Resolution:* Accept **both** sets of tests.
5.  **Project Management Board (`planning/trackers/master_board.json`)**:
    *   `main` flipped the F-06 status to "DONE".
    *   `F-05` flipped the F-04 and F-05 statuses to "DONE".
    *   *Resolution:* Manually merge the JSON so F-04, F-05, and F-06 all say "DONE".

## 3. How to Proceed (Step-by-Step)

Follow these terminal commands and instructions to safely merge everything and resolve the conflicts.

**Step 1: Merge F-07 (Clean Merge)**
```bash
git checkout main
git merge feature/F-07-Evaluate-Fit-Node
# This will succeed automatically without conflicts
```

**Step 2: Merge F-05 (Will trigger conflicts)**
```bash
git merge feature/F-05-Job-Ingestion-Node-URL-Text-Handling
```

**Step 3: Resolve the Conflicts**
1.  Open your IDE (like VS Code) and go through the files marked with conflicts (specifically `pyproject.toml`, `src/graph.py`, `src/nodes/parent_nodes.py`, the test files, and `master_board.json`).
2.  Using the VS Code merge tool, choose **"Accept Both Changes"** for the Python files and `pyproject.toml`. 
3.  For `src/graph.py`, ensure the import for `dummy_job_ingestion` is removed and replaced with `job_ingestion`.
4.  **Important for `uv.lock`:** Do not try to resolve the lockfile by hand. Just run `git checkout --ours uv.lock` (to use main's lockfile) and then run `uv lock` in your terminal to safely regenerate a lockfile that includes all the new dependencies from `pyproject.toml`.

**Step 4: Finalize the Merge**
Once all conflicts are resolved and saved:
```bash
# Add the resolved files
git add .
git commit -m "Merge F-05 and F-04 into main, resolving feature conflicts"
```