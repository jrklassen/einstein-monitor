"""Starts the Einstein@Home monitor and keeps it running (windowless).

Runs the Streamlit dashboard, restarting it if it ever crashes.
Logs to eah_runner.log and streamlit.log in this folder.
"""
import os
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# Address and port the dashboard listens on, read from .env (LISTEN_ADDRESS,
# DASHBOARD_PORT). The default, 127.0.0.1, is this computer only; set
# LISTEN_ADDRESS to the machine's LAN IP to reach it from other devices (keep it
# off the internet: the dashboard has no login).
from dotenv import dotenv_values  # noqa: E402

_env = dotenv_values(BASE_DIR / ".env")
ADDRESS = (_env.get("LISTEN_ADDRESS") or os.environ.get("LISTEN_ADDRESS") or "127.0.0.1").strip()
try:
    PORT = int(_env.get("DASHBOARD_PORT") or os.environ.get("DASHBOARD_PORT") or 8502)
except ValueError:
    PORT = 8502  # the Solar app uses 8501

RUNNER_LOG = BASE_DIR / "eah_runner.log"
STREAMLIT_LOG = BASE_DIR / "streamlit.log"
MAX_LOG_BYTES = 1_000_000


def log(message):
    try:
        with open(RUNNER_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}\n")
    except OSError:
        pass


def rotate(path):
    try:
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            old = path.with_suffix(path.suffix + ".old")
            if old.exists():
                old.unlink()
            path.rename(old)
    except OSError:
        pass


def already_running():
    try:
        with socket.create_connection((ADDRESS, PORT), timeout=2):
            return True
    except OSError:
        return False


def run_streamlit():
    rotate(STREAMLIT_LOG)
    with open(STREAMLIT_LOG, "ab") as out:
        proc = subprocess.Popen(
            [
                "pythonw",
                "-m", "streamlit", "run", "app.py",
                "--server.headless", "true",
                "--server.address", ADDRESS,
                "--server.port", str(PORT),
            ],
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return proc.wait()


def main():
    time.sleep(5)  # let the network come up after logon
    rotate(RUNNER_LOG)
    if already_running():
        log(f"something is already listening on {ADDRESS}:{PORT}; exiting")
        return
    log(f"starting (dashboard on http://{ADDRESS}:{PORT})")

    delay = 5
    while True:
        started = time.time()
        try:
            code = run_streamlit()
        except Exception as exc:
            code = f"{type(exc).__name__}: {exc}"
        ran = time.time() - started
        log(f"streamlit exited ({code}) after {ran:.0f}s; restarting in {delay}s")
        time.sleep(delay)
        # Healthy long runs reset the back-off; quick failures back off to 5 min.
        delay = 5 if ran > 120 else min(delay * 2, 300)


main()
