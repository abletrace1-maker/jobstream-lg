# LangGraph Agent Architectural Guidelines & Specification Checklist

This document serves as a comprehensive guide for designing, architecting, and specifying LangGraph agents. It is built upon the lessons learned from previous agent developments (e.g., JobStream) and provides a robust framework to ensure that when you pass a specification to an AI coder, the resulting system is resilient, correctly stateful, and integrated properly.

---

## Part 1: Post-Mortem – What We Learned from JobStream

During the development of the JobStream agent, several critical architectural oversights caused the application to hang, crash, or fail to complete. Understanding *why* these happened is key to preventing them in future agents.

### 1. Sub-graph State & Checkpoint Namespaces
**The Issue:** The Streamlit UI attempted to read the state of a specific job by querying the database for a `thread_id` equal to the `job_id`. However, because the agent used LangGraph's Map-Reduce (`Send`) API, the sub-graphs didn't have their own isolated root `thread_id`. Instead, they were saved under the **Parent's** `thread_id` using a nested **Checkpoint Namespace** (e.g., `child_graph:1234-5678`).
**The Fix:** The state retrieval function had to be rewritten to query the parent thread and iterate over its checkpoints to find the specific `checkpoint_ns` that contained the child's state. 
**The Lesson:** When designing systems with Sub-graphs or Map-Reduce architectures, you must explicitly design how external systems (like UIs) will locate and access nested states.

### 2. Streamlit Thread Blocking & State Loss
**The Issue:** When a user clicked "Submit Answers", the Streamlit UI called `graph_with_memory.invoke()` directly in the button's execution path. Because LangGraph processing is synchronous and computationally heavy, this blocked the entire Streamlit UI thread. Streamlit appeared to "do nothing" or freeze. Additionally, when the process finally finished and called `st.rerun()`, any success messages or active states were instantly wiped out before the user could see them.
**The Fix:** We moved the `graph.invoke()` call into a background daemon thread (`threading.Thread`). We then stored persistent UI messages in `st.session_state` (e.g., `st.session_state.success_msg = "Answers submitted!"`) so that they survived the `st.rerun()` boundary and rendered correctly on the next loop.
**The Lesson:** **Never block the main UI thread with agent execution.** LangGraph invocations must be handled asynchronously or in background threads. Always use session state mechanisms to pass UI flags and success messages across reruns.

### 3. Schema Rigidity vs. LLM Unpredictability
**The Issue:** The JSON Diff schema strictly defined `new_value` and `old_value` as `str` (strings). When the LLM decided to replace an entire list (e.g., `skills: ["Python", "AWS"]`), it was forced by the Pydantic schema to stringify the list. Later, the PDF compiler (Jinja2) crashed because it tried to iterate over a string.
**The Fix:** Changed the schema types to `Any` to allow polymorphic JSON structures.
**The Lesson:** While strict schemas are great, you must identify which fields are polymorphic. If an LLM might return a string, list, or dict for a specific field, type it as `Any` or `Union[str, List, Dict]` to prevent downstream crashes.

### 4. LLM Structured Outputs & Nested Arrays (Dot Notation vs. JSON Paths)
**The Issue:** The LLM was instructed to output a `section` string to target where changes should happen (e.g., updating a specific bullet point in an array). Because our prompt loosely said `experience.highlights`, the LLM outputted exactly `experience.highlights`. When our Python code tried to apply this update to an array, it failed because it had no index (e.g., `experience.highlights` instead of `professional_experience[0].highlights[2]`).
**The Fix:** 
1. Updated the prompt to explicitly demonstrate exact JSON paths with array indices: `professional_experience[i].highlights`.
2. Updated the Pydantic schema field with `Field(description="The exact path... e.g., 'professional_experience[0].highlights[2]'")`.
**The Lesson:** When asking an LLM to generate paths for programmatic JSON updates (especially arrays), you **must** be hyper-explicit in your Pydantic `Field` descriptions and prompt examples. Loose dot-notation works for objects, but destroys arrays.

### 5. Defensive Handling of LLM Enums/Actions
**The Issue:** The system expected the LLM to output `action: "replace"`. The LLM logically outputted `action: "update"`. Because the code strictly checked for `"replace"` and ignored anything else, the agent silently skipped making changes.
**The Fix:** Broadened the accepted actions to `("replace", "update")`.
**The Lesson:** Always instruct the AI coder to implement **Defensive Parsing**. If the LLM returns an unexpected synonym, the code should log a warning or map it correctly, not silently fail.

### 6. Terminal State Updates
**The Issue:** The graph successfully generated PDFs and finished its execution, but the UI was stuck waiting because the agent's internal `status` state was never updated from `STRATEGY_DRAFTED` to `APPROVED`.
**The Fix:** Explicitly updated the terminal node to yield a final `{"status": "APPROVED"}` state.
**The Lesson:** State transitions must be mapped out exhaustively. Every end-node must be responsible for setting a final "completed" or "failed" status so the rest of the application knows the thread is closed.

---

## Part 2: Core LangGraph Concepts to Master

Before designing your next agent (e.g., an Audit Agent or PDF Ingestion Pipeline), ensure you understand these LangGraph mechanics:

1. **Checkpointers and Threads (`SqliteSaver`, `PostgresSaver`)**
   - **How it works:** LangGraph saves the state at every step using a `thread_id`. 
   - **What to know:** You must define how `thread_id`s are generated and passed around. If a UI needs to resume a graph, it *must* have the exact `thread_id` (and config) used to start it.
2. **Sub-graphs vs. The `Send` API (Map-Reduce)**
   - **How it works:** Standard sub-graphs act as single nodes. The `Send` API allows you to map over a list and spawn multiple isolated sub-graphs dynamically.
   - **What to know:** `Send` API executions share the parent's `thread_id` but exist in separate `checkpoint_ns` (namespaces). Resuming a paused `Send` execution often requires invoking the *parent* graph with the parent's config.
3. **Reducers (State Merging)**
   - **How it works:** In `TypedDict` state definitions, you can define `Annotated[list, operator.add]` to append to a list instead of overwriting it.
   - **What to know:** If you don't use a reducer, yielding `{"messages": [new_msg]}` will overwrite all previous messages. Design your state with clear overwrite vs. append rules.
4. **Human-in-the-Loop (HITL) Interrupts**
   - **How it works:** `interrupt_before` or `interrupt_after` pauses execution. You resume by calling `graph.update_state(config, updates)` and then `graph.invoke(None, config)`.
   - **What to know:** Designing a HITL workflow requires two parts: the LangGraph pause logic, and the UI polling logic to detect the pause, gather input, and trigger the resume.

---

## Part 3: Architectural Recommendations for Resilient Agents

1. **State Completeness & Transition Matrices:**
   - Always define an Enum for your Agent Statuses (e.g., `QUEUED`, `PROCESSING`, `AWAITING_INPUT`, `COMPLETED`, `FAILED`).
   - Map exactly which Node is responsible for transitioning the state. Never rely on implicit completion.
2. **Decouple LLM Output from System State:**
   - Do not let the LLM directly overwrite core state (like `job_id`, `original_document_text`). 
   - Use the LLM to generate *deltas* or *diffs*, and use deterministic Python code to validate and apply those changes to the state.
3. **Graceful Degradation & Fallbacks:**
   - If an LLM returns a hallucinated schema, the node should catch the `ValidationError` and transition to a `FAILED_PARSING` state, or return a safe default, rather than crashing the Python process.
4. **Database State vs. Application State:**
   - LangGraph's SQLite checkpoint is hard to query analytically (it stores pickled blobs/JSON). 
   - If you need a dashboard (like Streamlit), maintain a secondary, lightweight database or JSON file (e.g., `tracker.json`) and sync it with LangGraph's state upon node completion.

---

## Part 4: The AI Coder Specification Checklist

When you write a TRD/PRD for your AI coder to build your next agent, copy this checklist and ensure every point is explicitly answered in your specification document.

### 1. State Definition
- [ ] What is the exact schema of the Graph State? (Provide Pydantic models or TypedDicts).
- [ ] Which fields are overwritten, and which are appended to (Reducers)?
- [ ] What is the Enum of all possible Statuses? What are the exact terminal statuses?

### 2. Sub-graph & Concurrency Design
- [ ] Does this agent process items one-by-one, or does it map over a list concurrently?
- [ ] If using the `Send` API, explicitly instruct the AI: *"State polling and resumption must account for LangGraph `checkpoint_ns` (namespaces) under the parent thread."*
- [ ] Do sub-graphs need their own checkpointers (`checkpointer=True`), or do they inherit the parent's?

### 3. Schema & LLM Output Design
- [ ] Provide the exact prompt instructions. 
- [ ] Are there fields where the LLM might return varying data types (e.g., string vs list)? Explicitly instruct the AI: *"Use `Any` or `Union` for these fields to prevent Pydantic serialization crashes."*
- [ ] Provide strict instructions on LLM fallbacks: *"If the LLM returns an action like 'update' instead of 'replace', map it defensively. If parsing fails, fall back to the original state—do not crash the node."*

### 4. Human-in-the-Loop (HITL) Integration
- [ ] Which nodes have `interrupt_before` or `interrupt_after`?
- [ ] What exact data is the UI expected to inject back into the state to resume?
- [ ] Explicitly instruct the AI on resumption: *"To resume, use `graph.update_state()` followed by invoking the parent graph with the original parent configuration."*

### 5. UI and System Integration
- [ ] How does the UI know the graph is done? (e.g., *"The final node MUST update the state to `status: COMPLETED`"*).
- [ ] How is the UI fetching state? Explicitly instruct the AI: *"Write a DB helper function that safely iterates over `SqliteSaver.list()` to extract values, handling unpickling or JSON extraction gracefully."*
- [ ] Does the UI trigger agent execution natively? Explicitly instruct the AI: *"Do not block the UI thread. Use background daemon threads for graph `invoke()` calls, and manage transient UI states (like success messages) using `st.session_state` to survive reruns."*

### 6. Testing Strategy Requirements
Instruct the AI coder to write tests covering:
- [ ] **State Transitions:** Assert that reaching the `END` node sets the status to a terminal state.
- [ ] **Defensive Parsing:** Pass a malformed LLM response into the node and assert that the graph gracefully falls back instead of throwing an exception.
- [ ] **HITL Resumption:** Mock an interrupted state, inject a dummy user response, and assert that the graph successfully transitions to the next node.
