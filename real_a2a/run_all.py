"""Launch all 4 A2A services (Admin + 3 children) as subprocesses."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


SERVICES = [
    ("text2sql", "real_a2a.children.text2sql_crewai.server"),
    ("rag", "real_a2a.children.langgraph_rag.server"),
    ("deepresearch", "real_a2a.children.google_adk_research.server"),
    ("admin", "real_a2a.admin.server"),
]


def main() -> None:
    procs: list[tuple[str, subprocess.Popen]] = []
    env = os.environ.copy()

    print(f"Launching {len(SERVICES)} services from {REPO_ROOT}\n")
    for name, module in SERVICES:
        print(f"  starting {name} ({module})")
        proc = subprocess.Popen(
            [PYTHON, "-m", module],
            cwd=REPO_ROOT,
            env=env,
        )
        procs.append((name, proc))
        time.sleep(2.0)

    print("\nAll services started. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"[!] Service '{name}' exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for name, proc in procs:
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                    else:
                        proc.terminate()
                except Exception:
                    proc.kill()
        for name, proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
