"""Launch server_left.py and server_right.py together, synchronized.

Each child script runs in its own subprocess and has its own BLE scan,
so connection timing varies. This wrapper waits until BOTH children
have printed "Connected", then sends the play command ('y') to both
stdins back-to-back. The two writes are sub-millisecond apart, so the
hands' wall-clock starts are effectively simultaneous.

Both subprocesses' stdout is relayed to this terminal with [LEFT] /
[RIGHT] prefixes so you see what's happening on each hand without
having to juggle multiple windows.

Usage:
  python play_both.py
"""
import os
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable  # use the same Python this script runs under
SCRIPTS = ["server_left.py", "server_right.py"]
CONNECT_TIMEOUT_SECONDS = 30


def relay_stdout(proc, label, ready_event):
    """Stream subprocess stdout to this console with a [LABEL] prefix.

    Sets `ready_event` the first time the line "Connected" is seen,
    which is the cue that the BLE handshake to that ESP32 succeeded.
    """
    for raw in iter(proc.stdout.readline, b""):
        text = raw.decode(errors="replace").rstrip()
        print(f"[{label}] {text}", flush=True)
        if not ready_event.is_set() and "Connected" in text:
            ready_event.set()


def main():
    procs = []
    readies = []

    for script in SCRIPTS:
        label = script.replace("server_", "").replace(".py", "").upper()
        # -u forces unbuffered stdout so we see "Connected" as soon as
        # the child prints it, not whenever Python decides to flush.
        proc = subprocess.Popen(
            [PYTHON, "-u", script],
            cwd=HERE,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        ready = threading.Event()
        threading.Thread(
            target=relay_stdout, args=(proc, label, ready), daemon=True
        ).start()
        procs.append(proc)
        readies.append(ready)

    print("[orchestrator] Waiting for both ESP32s to connect...", flush=True)
    for ready, script in zip(readies, SCRIPTS):
        if not ready.wait(timeout=CONNECT_TIMEOUT_SECONDS):
            print(
                f"[orchestrator] Timed out waiting for {script} to connect. Aborting.",
                flush=True,
            )
            for proc in procs:
                proc.terminate()
            return 1

    print("[orchestrator] Both connected. Sending 'y' to both NOW.", flush=True)
    # Back-to-back stdin writes. The gap between these two flush() calls
    # is sub-millisecond, well below BLE write latency, so the hands'
    # perf_counter() start times line up tightly.
    # Sending 'q' after 'y' so each script auto-quits when its song ends
    # (the prompt loop reads 'q' after play_song returns).
    for proc in procs:
        proc.stdin.write(b"y\nq\n")
        proc.stdin.flush()

    for proc in procs:
        proc.wait()
    print("[orchestrator] Both processes finished.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
