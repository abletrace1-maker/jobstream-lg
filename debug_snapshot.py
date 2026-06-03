import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import sys

def main():
    conn = sqlite3.connect("data/checkpoints.sqlite", check_same_thread=False)
    saver = SqliteSaver(conn)
    
    snapshot = next(saver.list(None, limit=1))
    print(dir(snapshot))
    print("snapshot.values =", type(snapshot.values))
    print("Is channel_values in checkpoint?", "channel_values" in getattr(snapshot, "checkpoint", {}))
    
    print("Does snapshot have checkpoint?", hasattr(snapshot, "checkpoint"))
    
    # Let's see what values contains
    if hasattr(snapshot, "values"):
        job_details = snapshot.values.get("job_details")
        print("job_details type:", type(job_details))
        
if __name__ == "__main__":
    main()
