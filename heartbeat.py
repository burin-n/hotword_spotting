import subprocess
import os
import time
import psutil
import signal

filename = 'client2.py'

while True:
    """However, you should be careful with the '.wait()'"""
    pid = subprocess.Popen(['python', filename, 'test-0003']).pid
    time.sleep(60*30)
    # os.kill(pid, signal.SIGTERM)
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):  # or parent.children() for recursive=False
        child.kill()
    parent.kill()
