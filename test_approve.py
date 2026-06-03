import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.ui.app import get_latest_graph_state
from src.graph import parent_graph
from src.ui.app import get_checkpointer

state = get_latest_graph_state("dummy-123")
if state:
    actual_config = state.get("_config")
    print(f"Found config: {actual_config}")
    
    saver, conn = get_checkpointer()
    graph_with_memory = parent_graph.builder.compile(checkpointer=saver)
    
    print("Resuming graph...")
    parent_config = {
        "configurable": {
            "thread_id": actual_config["configurable"]["thread_id"]
        }
    }
    try:
        # We need to simulate the UI approve button.
        # It updates the child state with user_feedback="" and then resumes parent graph.
        graph_with_memory.update_state(actual_config, {"user_feedback": ""})
        graph_with_memory.invoke(None, parent_config)
        print("Graph invoked successfully!")
    except Exception as e:
        print(f"Graph invoke failed: {e}")
