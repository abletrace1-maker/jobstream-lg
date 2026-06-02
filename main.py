import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph import parent_graph


def main():
    print("🚀 Starting JobStream pipeline...")
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    db_path = "data/checkpoints.sqlite"
    
    # Configure SQLite Checkpointer
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        memory = SqliteSaver(conn)
        
        # We recompile the parent_graph's builder with the checkpointer 
        # because parent_graph was compiled without one in src.graph
        graph_with_memory = parent_graph.builder.compile(checkpointer=memory)
        
        # Configure the thread
        config = {"configurable": {"thread_id": "jobstream_run_test_1"}}
        
        # Provide an initial empty state
        initial_state = {}
        
        print("⏳ Invoking parent_graph...")
        graph_with_memory.invoke(initial_state, config)
        
        print("✅ JobStream pipeline completed successfully!")


if __name__ == "__main__":
    main()
