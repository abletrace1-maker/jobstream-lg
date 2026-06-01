import streamlit as st
import sqlite3
import os
from langgraph.checkpoint.sqlite import SqliteSaver

# T-1: Create src/ui/app.py with Streamlit page config and layout structure
st.set_page_config(
    page_title="JobStream Application Tracker",
    page_icon="🌊",
    layout="wide"
)

DB_PATH = "data/checkpoints.sqlite"

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

def main():
    st.title("🌊 JobStream Application Tracker")
    st.markdown("Welcome to the JobStream AI Agent Dashboard. This system manages your job applications via LangGraph.")

    # T-3: Add UI element to display database connection status
    st.subheader("System Status")
    
    try:
        saver, conn = get_checkpointer()
        
        # Test connection by running a simple query
        cursor = conn.cursor()
        # In newer langgraph-checkpoint-sqlite, table might be 'checkpoints'
        # Just check if we can execute a simple select 1.
        cursor.execute("SELECT 1")
        conn.commit()
        
        st.success("✅ Successfully connected to LangGraph checkpoint database.")
        
    except Exception as e:
        st.error(f"❌ Failed to connect to LangGraph checkpoint database: {e}")

if __name__ == "__main__":
    main()
