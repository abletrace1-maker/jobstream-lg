import json
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

def main():
    try:
        with open("data/job_tracker.json", "r") as f:
            jobs = json.load(f)
    except Exception as e:
        print("Error reading tracker:", e)
        return
        
    print("Jobs in tracker:", [j["job_id"] for j in jobs])
    
    conn = sqlite3.connect("data/checkpoints.sqlite", check_same_thread=False)
    saver = SqliteSaver(conn)
    
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
                
            status = state_dict.get("status")
            if hasattr(status, "value"):
                status = status.value
            
            print(f"Found in DB: ns={ns}, job_id={current_job_id}, status={status}")
            
if __name__ == "__main__":
    main()
