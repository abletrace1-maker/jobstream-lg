import threading
import time

def my_task():
    print("Task started")
    time.sleep(2)
    print("Task finished")

t = threading.Thread(target=my_task)
t.start()
print("Thread alive:", t.is_alive())
time.sleep(3)
print("Thread alive:", t.is_alive())
