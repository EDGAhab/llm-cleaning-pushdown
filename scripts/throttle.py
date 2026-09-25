#!/usr/bin/env python3
"""throttle.py: CPU quota enforcer via SIGSTOP/SIGCONT duty cycling.

Replaces cpulimit (which was wiped by service restarts). Usage:
  python3 throttle.py <percent> -- <command> [args...]

The child gets <percent>% CPU via periodic SIGSTOP/SIGCONT.
"""
import signal
import subprocess
import sys
import time


def main():
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        print(f"Usage: {sys.argv[0]} <percent> -- <command> [args...]", file=sys.stderr)
        sys.exit(2)
    pct = float(sys.argv[1])
    cmd = sys.argv[3:]
    if not (0 < pct <= 100):
        print("percent must be in (0, 100]", file=sys.stderr)
        sys.exit(2)

    # duty cycle: 100ms period
    period = 0.1
    on_time = period * pct / 100.0
    off_time = period - on_time

    proc = subprocess.Popen(cmd)
    try:
        while proc.poll() is None:
            # run
            try:
                proc.send_signal(signal.SIGCONT)
            except ProcessLookupError:
                break
            time.sleep(on_time)
            if proc.poll() is not None:
                break
            # stop
            try:
                proc.send_signal(signal.SIGSTOP)
            except ProcessLookupError:
                break
            time.sleep(off_time)
    except KeyboardInterrupt:
        proc.terminate()
    # ensure child is running before we exit so it can finish cleanup
    try:
        proc.send_signal(signal.SIGCONT)
    except ProcessLookupError:
        pass
    sys.exit(proc.wait())


if __name__ == "__main__":
    main()
