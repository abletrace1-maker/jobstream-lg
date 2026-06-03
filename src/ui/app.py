import streamlit as st
import sqlite3
import os
import sys
import json
import pandas as pd
import threading
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.schemas import ClarificationQuestion
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph import parent_graph
from src.child_graph import child_graph
from src.state import JobStatus

# T-1: Create src/ui/app.py with Streamlit page config and layout structure
st.set_page_config(
    page_title="JobStream Application Tracker",
    page_icon="🌊",
    layout="wide"
)

DB_PATH = "data/checkpoints.sqlite"
TRACKER_PATH = "data/job_tracker.json"

# T-2: Implement get_checkpointer() using SqliteSaver connecting to data/checkpoints.sqlite
def get_checkpointer():
    """
    Creates and returns a SqliteSaver checkpointer connected to data/checkpoints.sqlite.
    Also returns the underlying sqlite3 connection so we can manage its lifecycle if needed,
    or we can just return the checkpointer.
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    
    saver = SqliteSaver(conn)
    saver.setup()
    return saver, conn

def read_job_tracker():
    """T-1: Implement function to read data/job_tracker.json"""
    try:
        with open(TRACKER_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_latest_graph_state(job_id):
    """
    Queries SqliteSaver for the latest state of the child graph for a given job.
    Since the child graph is executed via the Send API, its state is stored in a namespace
    under the parent's thread_id. We search for it here.
    """
    saver, _ = get_checkpointer()
    
    # Search through recent checkpoints to find the latest state for this job_id
    for snapshot in saver.list(None, limit=200):
        ns = snapshot.config["configurable"].get("checkpoint_ns", "")
        if ns.startswith("child_graph:"):
            state_dict = snapshot.checkpoint.get("channel_values", {})
            job_details = state_dict.get("job_details")
            
            current_job_id = None
            if hasattr(job_details, "job_id"):
                current_job_id = job_details.job_id
            elif isinstance(job_details, dict):
                current_job_id = job_details.get("job_id")
                
            if current_job_id == job_id:
                # Add the actual config so we can resume it later
                state_dict["_config"] = snapshot.config
                return state_dict
                
    return None

def write_job_tracker(jobs):
    """T-3: Implement write-back function to update job_tracker.json with the latest graph statuses"""
    with open(TRACKER_PATH, "w") as f:
        json.dump(jobs, f, indent=2)

def render_clarification_questions(questions):
    """
    US-001 T-1, T-2: Streamlit rendering function for ClarificationQuestion objects.
    Returns a dictionary of answers.
    """
    answers = {}
    for q in questions:
        st.markdown(f"**{q.question}**")
        if q.type == "multiple_choice":
            # multiple choice
            ans = st.radio(
                f"Select an option for {q.id}",
                options=q.options,
                key=f"q_{q.id}",
                label_visibility="collapsed"
            )
            answers[q.id] = ans
        elif q.type == "text":
            # text input
            ans = st.text_area(
                f"Your answer for {q.id}",
                key=f"q_{q.id}",
                label_visibility="collapsed"
            )
            answers[q.id] = ans
    return answers

def run_parent_graph_bg():
    """Background thread function to invoke the parent_graph"""
    try:
        import uuid
        saver, conn = get_checkpointer()
        graph_with_memory = parent_graph.builder.compile(checkpointer=saver)
        
        # T-2: Invoke parent_graph with config
        thread_id = f"batch_ingestion_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        print(f"Starting new batch ingestion with thread_id: {thread_id}")
        graph_with_memory.invoke({"config": {}}, config)
        print("Parent graph invocation finished!")
    except Exception as e:
        print(f"Error in background parent_graph thread: {e}")

def main():
    st.title("🌊 JobStream Application Tracker")
    st.markdown("Welcome to the JobStream AI Agent Dashboard. This system manages your job applications via LangGraph.")

    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # US-002: Start Job Processing Button in Sidebar
    with st.sidebar:
        st.header("Actions")
        if st.button("Start Job Processing", type="primary"):
            # T-3: Wire button to trigger background thread
            st.session_state.is_processing = True
            st.session_state.bg_thread = threading.Thread(target=run_parent_graph_bg, daemon=True)
            st.session_state.bg_thread.start()
            st.success("Job processing started in the background!")
            st.rerun()

    # Poll while the background thread is running
    if st.session_state.is_processing:
        if "bg_thread" in st.session_state and st.session_state.bg_thread.is_alive():
            import time
            with st.spinner("Processing jobs in background..."):
                time.sleep(2)
                st.rerun()
        else:
            st.session_state.is_processing = False
            st.rerun()

    # T-3: Add UI element to display database connection status
    st.subheader("System Status")
    
    try:
        saver, conn = get_checkpointer()
        
        # Test connection by running a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.commit()
        
        st.success("✅ Successfully connected to LangGraph checkpoint database.")
        
    except Exception as e:
        st.error(f"❌ Failed to connect to LangGraph checkpoint database: {e}")

    # US-002 Dashboard sync
    st.subheader("Job Applications Dashboard")
    
    jobs = read_job_tracker()
    updated = False
    
    for job in jobs:
        # Check LangGraph state for this job
        graph_state_dict = get_latest_graph_state(job["job_id"])
        graph_status = graph_state_dict.get("status") if graph_state_dict else None
        
        # Sync if there's a graph status and it differs from the tracker status
        if graph_status:
            # Handle Enum serialization
            if hasattr(graph_status, "value"):
                graph_status_str = graph_status.value
            else:
                graph_status_str = str(graph_status)
                
            if graph_status_str != job.get("status"):
                job["status"] = graph_status_str
                updated = True
            
    if updated:
        write_job_tracker(jobs)
        
    # T-4: Display the merged job data in a Streamlit dataframe or UI list on the main page
    if jobs:
        df = pd.DataFrame(jobs)
        # Optionally reorder columns or style dataframe
        st.dataframe(df, width='stretch')
        
        # US-001 Action Required Section
        paused_jobs = [j for j in jobs if j.get("status") == JobStatus.NEEDS_CLARIFICATION.value]
        if paused_jobs:
            st.subheader("⚠️ Action Required: Clarifications Needed")
            
            selected_job_title = st.selectbox(
                "Select a job to provide clarifications for",
                options=[f"{j['title']} at {j['company']} ({j['job_id']})" for j in paused_jobs]
            )
            
            if selected_job_title:
                selected_job_id = selected_job_title.split("(")[-1].strip(")")
                
                # Extract clarification_questions
                # US-001 T-3: Read the paused graph state via SqliteSaver checkpointer to extract clarification_questions
                state_dict = get_latest_graph_state(selected_job_id)
                if state_dict and "clarification_questions" in state_dict:
                    raw_questions = state_dict["clarification_questions"]
                    
                    # Convert to ClarificationQuestion objects if they are dicts
                    questions = []
                    for q in raw_questions:
                        if isinstance(q, dict):
                            questions.append(ClarificationQuestion(**q))
                        else:
                            questions.append(q)
                            
                    st.write("Please answer the following questions so the AI can proceed to draft your tailored resume:")
                    with st.form(key=f"clarification_form_{selected_job_id}"):
                        answers = render_clarification_questions(questions)
                        
                        submit_button = st.form_submit_button(label="Submit Answers")
                        
                        if submit_button:
                            # US-002 T-2: Inject answers into the paused Child Sub-Graph
                            # We use the _config we found from the state search
                            actual_config = state_dict.get("_config")
                            if actual_config:
                                saver, conn = get_checkpointer()
                                from src.graph import parent_graph
                                graph_with_memory = parent_graph.builder.compile(checkpointer=saver)
                                
                                graph_with_memory.update_state(actual_config, {"user_clarification_answers": answers})
                                
                                # US-002 T-3: Trigger the resumption of the graph
                                parent_config = {
                                    "configurable": {
                                        "thread_id": actual_config["configurable"]["thread_id"]
                                    }
                                }
                                graph_with_memory.invoke(None, parent_config)
                                st.success("Answers submitted and job resumed!")
                                st.rerun()
                            
        # US-001: Review Drafted Strategies Section
        strategy_drafted_jobs = [j for j in jobs if j.get("status") == JobStatus.STRATEGY_DRAFTED.value]
        if strategy_drafted_jobs:
            st.subheader("📝 Action Required: Review Drafted Strategies")
            
            selected_strategy_title = st.selectbox(
                "Select a job to review the drafted strategy",
                options=[f"{j['title']} at {j['company']} ({j['job_id']})" for j in strategy_drafted_jobs],
                key="strategy_selectbox"
            )
            
            if selected_strategy_title:
                selected_job_id = selected_strategy_title.split("(")[-1].strip(")")
                
                # Extract strategy_markdown and resume_diffs
                state_dict = get_latest_graph_state(selected_job_id)
                if state_dict:
                    strategy_markdown = state_dict.get("strategy_markdown", "No strategy drafted yet.")
                    resume_diffs = state_dict.get("resume_diffs", None)
                    
                    st.write("### Strategy")
                    st.markdown(strategy_markdown)
                    
                    st.write("### Resume Diffs")
                    if resume_diffs:
                        if isinstance(resume_diffs, dict):
                            st.json(resume_diffs)
                        elif hasattr(resume_diffs, "model_dump"):
                            st.json(resume_diffs.model_dump())
                        else:
                            st.json(resume_diffs)
                    else:
                        st.info("No resume diffs generated.")
                        
                    # US-002: Approve or Provide Feedback
                    st.write("### Review Action")
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        if st.button("✅ Approve Strategy", key=f"approve_{selected_job_id}"):
                            actual_config = state_dict.get("_config")
                            if actual_config:
                                saver, conn = get_checkpointer()
                                from src.graph import parent_graph
                                graph_with_memory = parent_graph.builder.compile(checkpointer=saver)
                                
                                graph_with_memory.update_state(actual_config, {"user_feedback": ""})
                                
                                parent_config = {
                                    "configurable": {
                                        "thread_id": actual_config["configurable"]["thread_id"]
                                    }
                                }
                                graph_with_memory.invoke(None, parent_config)
                                st.success("Strategy approved! Resuming workflow...")
                                st.rerun()
                            
                    with col2:
                        with st.form(key=f"feedback_form_{selected_job_id}"):
                            feedback_text = st.text_area(
                                "Provide feedback to revise the strategy", 
                                placeholder="E.g., Please emphasize my Python skills more..."
                            )
                            submit_feedback = st.form_submit_button("Submit Feedback")
                            
                            if submit_feedback:
                                if not feedback_text.strip():
                                    st.warning("Please enter feedback before submitting.")
                                else:
                                    actual_config = state_dict.get("_config")
                                    if actual_config:
                                        saver, conn = get_checkpointer()
                                        from src.graph import parent_graph
                                        graph_with_memory = parent_graph.builder.compile(checkpointer=saver)
                                        
                                        graph_with_memory.update_state(actual_config, {"user_feedback": feedback_text.strip()})
                                        
                                        parent_config = {
                                            "configurable": {
                                                "thread_id": actual_config["configurable"]["thread_id"]
                                            }
                                        }
                                        graph_with_memory.invoke(None, parent_config)
                                        st.success("Feedback submitted! Resuming workflow...")
                                        st.rerun()
                        
    else:
        st.info("No jobs found in the tracker. Add jobs to `data/job_tracker.json` to begin.")

if __name__ == "__main__":
    main()
