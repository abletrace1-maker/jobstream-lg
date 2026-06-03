import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
import sys

def main():
    conn = sqlite3.connect("data/checkpoints.sqlite", check_same_thread=False)
    saver = SqliteSaver(conn)
    
    count = 0
    for snapshot in saver.list(None, limit=10):
        print("-----")
        print("Config:", snapshot.config)
        # Check channel_values
        print("Channel Values Keys:", snapshot.values.keys() if hasattr(snapshot, "values") else snapshot.checkpoint.get("channel_values", {}).keys())
        
        # also print namespace
        ns = snapshot.config["configurable"].get("checkpoint_ns", "")
        print("Namespace:", ns)
        
        count += 1
        
    print(f"Total snapshots printed: {count}")

if __name__ == "__main__":
    main()
