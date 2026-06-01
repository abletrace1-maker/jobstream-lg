import streamlit as st
import sqlite3
import os
import json
import pandas as pd
from src.schemas import ClarificationQuestion
from langgraph.checkpoint.sqlite import SqliteSaver
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
    """T-2: Implement function to query SqliteSaver for the latest state of each job (using job_id as thread_id)"""
    config = {"configurable": {"thread_id": job_id}}
    state = child_graph.get_state(config)
    if state and hasattr(state, "values") and state.values:
        return state.values
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

def main():
    st.title("🌊 JobStream Application Tracker")
    st.markdown("Welcome to the JobStream AI Agent Dashboard. This system manages your job applications via LangGraph.")

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
        if graph_status and graph_status != job.get("status"):
            job["status"] = graph_status
            updated = True
            
    if updated:
        write_job_tracker(jobs)
        
    # T-4: Display the merged job data in a Streamlit dataframe or UI list on the main page
    if jobs:
        df = pd.DataFrame(jobs)
        # Optionally reorder columns or style dataframe
        st.dataframe(df, use_container_width=True)
        
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
                            config = {"configurable": {"thread_id": selected_job_id}}
                            child_graph.update_state(config, {"user_clarification_answers": answers})
                            
                            # US-002 T-3: Trigger the resumption of the graph
                            for _ in child_graph.stream(None, config, stream_mode="values"):
                                pass
                                
                            st.success("Answers submitted successfully! Resuming workflow...")
                            st.rerun()
                            
    else:
        st.info("No jobs found in the tracker. Add jobs to `data/job_tracker.json` to begin.")

if __name__ == "__main__":
    main()
