import psutil
import os

PROCNAME = "python3.6"


if(os.path.exists('start.done')):
    os.remove('start.done')

if(os.path.exists('start.progress')):
    os.remove('start.progress')

for proc in psutil.process_iter():
    # check whether the process name matches
    if proc.name() == PROCNAME:
        print(proc)
        proc.kill()
