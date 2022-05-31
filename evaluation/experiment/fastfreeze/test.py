import os
import subprocess
import signal
import sys


def signal_handler(sig, frame):
    subprocess.check_call(('ps', '-aef', '--forest'))
    print(f"========================================================deleting {os.getpid()}")
    # with open(f'/tmp/log-{os.getpid()}', 'w') as f:
    #     f.write(str(sig))
    sys.exit(0)

pid = os.fork()
pid2 = os.fork()
signal.signal(signal.SIGTERM, signal_handler)
if pid != 0 and pid2 != 0:  # parent
    print(f'Main process has PID {os.getpid()}. Its children have PID {pid} and {pid2}')
signal.pause()
