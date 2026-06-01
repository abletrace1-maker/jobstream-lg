import streamlit as st
import sqlite3
import os
import json
import pandas as pd
from langgraph.checkpoint.sqlite import SqliteSaver
from src.child_graph import child_graph

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
        return state.values.get("status")
    return None

def write_job_tracker(jobs):
    """T-3: Implement write-back function to update job_tracker.json with the latest graph statuses"""
    with open(TRACKER_PATH, "w") as f:
        json.dump(jobs, f, indent=2)

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
        graph_status = get_latest_graph_state(job["job_id"])
        
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
    else:
        st.info("No jobs found in the tracker. Add jobs to `data/job_tracker.json` to begin.")

if __name__ == "__main__":
    main()
