"""Start the ttsclient REST API server (Zundamon voice) in the background.

Launches ttsclient on http://localhost:19000 using the dedicated Python 3.10
virtual environment inside the bundled ttsclient directory, then waits for
the API to become ready. Idempotent: if a server is already responding on the
target port, this returns immediately.
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

TTS_CLIENT_DIR = Path(__file__).resolve().parent / "ttsclient"
VENV_PYTHON = TTS_CLIENT_DIR / ".venv" / "Scripts" / "python.exe"
PORT = 19000
API_URL = f"http://127.0.0.1:{PORT}"
READY_TIMEOUT = 600
LOG_FILE = TTS_CLIENT_DIR / "server.log"


def server_ready(timeout=5):
    try:
        with urllib.request.urlopen(API_URL + "/docs", timeout=timeout) as response:
            return response.status == 200
    except OSError:
        return False


def start():
    if not VENV_PYTHON.is_file():
        raise RuntimeError(f"ttsclient runtime not found: {VENV_PYTHON}")
    if server_ready():
        print(f"ttsclient server already running at {API_URL}")
        return
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write("\n=== starting ttsclient server ===\n")
        log.flush()
        process = subprocess.Popen(
            [str(VENV_PYTHON), "-m", "ttsclient.main", "cui", "--launch_client", "False", "--no_cui", "False"],
            cwd=str(TTS_CLIENT_DIR),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    print(f"Launching ttsclient server at {API_URL} ...")
    deadline = time.monotonic() + READY_TIMEOUT
    while time.monotonic() < deadline:
        if server_ready():
            print(f"ttsclient server ready at {API_URL}")
            return
        if process.poll() is not None:
            raise RuntimeError(f"ttsclient server exited early (code {process.returncode}). See {LOG_FILE}")
        time.sleep(3)
    process.terminate()
    raise RuntimeError(f"ttsclient server did not become ready within {READY_TIMEOUT}s. See {LOG_FILE}")


if __name__ == "__main__":
    start()
