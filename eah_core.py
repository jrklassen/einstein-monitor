"""Einstein@Home monitor core: settings plus nvidia-smi / boinccmd readers.

No Streamlit imports, so the logic can be tested on its own. Every reader
returns an `error` string (instead of silently returning nothing) so the page
can tell "BOINC isn't answering" apart from "no tasks".
"""
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

BOINC_CMD = os.getenv("BOINC_CMD_PATH", r"C:\Program Files\BOINC\boinccmd.exe")
NVIDIA_SMI = os.getenv("NVIDIA_SMI_PATH", "nvidia-smi")
try:
    REFRESH_RATE = max(2, int(os.getenv("REFRESH_INTERVAL", "10")))
except ValueError:
    REFRESH_RATE = 10
try:
    CMD_TIMEOUT = max(2, int(os.getenv("CMD_TIMEOUT", "8")))
except ValueError:
    CMD_TIMEOUT = 8

RAW_LIMIT = 20_000  # characters of raw boinccmd output kept for troubleshooting
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_STATE_LABELS = {
    "EXECUTING": "Running",
    "SUSPENDED": "Suspended",
    "PREEMPTED": "Preempted",
    "UNINITIALIZED": "Ready to run",
}


def _now():
    return datetime.now().strftime("%H:%M:%S")


def _run(cmd, label):
    """Run a command with a timeout. Returns (stdout, error)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=CMD_TIMEOUT,
            creationflags=_NO_WINDOW,
        )
        return result.stdout, None
    except FileNotFoundError:
        return None, f"{label} not found at '{cmd[0]}' (check the path in .env)"
    except subprocess.TimeoutExpired:
        return None, f"{label} did not respond within {CMD_TIMEOUT}s"
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        detail = detail[0][:200] if detail else "no output"
        return None, f"{label} failed (exit code {exc.returncode}): {detail}"
    except OSError as exc:
        return None, f"{label} could not run ({type(exc).__name__}: {exc})"


def _to_int(text):
    try:
        return int(float(text.strip()))
    except (ValueError, AttributeError):
        return None


def get_gpu_stats():
    """GPU temp, utilization and memory via nvidia-smi.

    Returns {"gpu": {...} | None, "error": str | None, "fetched": "HH:MM:SS"}.
    """
    out, err = _run(
        [
            NVIDIA_SMI,
            "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ],
        "nvidia-smi",
    )
    if err:
        return {"gpu": None, "error": err, "fetched": _now()}
    lines = out.strip().splitlines()
    parts = [p for p in lines[0].split(",")] if lines else []
    if len(parts) != 4:
        return {
            "gpu": None,
            "error": f"Unexpected nvidia-smi output: {out.strip()[:100]!r}",
            "fetched": _now(),
        }
    temp, util, mem_used, mem_total = (_to_int(p) for p in parts)
    gpu = {
        "temp": temp,
        "util": util,
        "mem_used": mem_used,
        "mem_total": mem_total,
        "mem_pct": (
            round(mem_used / mem_total * 100, 1)
            if mem_used is not None and mem_total
            else None
        ),
    }
    return {"gpu": gpu, "error": None, "fetched": _now()}


def _split_blocks(raw):
    # Blocks are separated by a long dash line (as the original code assumed)
    # or by numbered headers such as "1) -----------".
    return re.split(r"-{20,}|^\s*\d+\)\s*-+\s*$", raw, flags=re.M)


def _parse_block(block):
    name = re.search(r"^\s*name:\s*(.+)$", block, re.M)
    if not name:
        return None
    pct = re.search(r"fraction done:\s*([\d.]+)", block)
    state = re.search(r"active_task_state:\s*(\S+)", block) or re.search(
        r"^\s*status:\s*(.+)$", block, re.M
    )
    elapsed = re.search(r"elapsed[^:\n]*:\s*([\d.]+)", block)
    time_label = "Elapsed"
    if not elapsed:  # fall back to CPU time when no elapsed time is reported
        elapsed = re.search(r"current CPU time:\s*([\d.]+)", block)
        time_label = "CPU time"

    status = state.group(1).strip() if state else "Ready to run"
    status = _STATE_LABELS.get(status.upper(), status)
    fraction = float(pct.group(1)) if pct else 0.0
    return {
        "name": name.group(1).strip(),
        "progress": round(min(max(fraction, 0.0), 1.0) * 100, 2),
        "status": status,
        "elapsed_min": round(float(elapsed.group(1)) / 60, 1) if elapsed else 0.0,
        "time_label": time_label,
    }


def parse_tasks(raw):
    """Extract Einstein@Home tasks from `boinccmd --get_simple_gui_info` text."""
    einstein = [
        b
        for b in _split_blocks(raw)
        if "einstein.phys.uwm.edu" in b or "einstein@home" in b.lower()
    ]
    # Real task blocks carry "WU name:"; project blocks (which also mention
    # Einstein@Home) carry "master URL:" instead and are skipped.
    task_blocks = [b for b in einstein if re.search(r"WU name:", b)]
    if not task_blocks:  # unfamiliar layout: behave like the original parser
        task_blocks = [b for b in einstein if "master URL:" not in b]
    tasks = [t for t in (_parse_block(b) for b in task_blocks) if t]
    return tasks


def get_boinc_tasks():
    """Einstein@Home tasks via boinccmd.

    Returns {"tasks": [...], "error": str | None, "raw": str, "fetched": "HH:MM:SS"}.
    """
    out, err = _run([BOINC_CMD, "--get_simple_gui_info"], "boinccmd")
    if err:
        return {"tasks": [], "error": err, "raw": "", "fetched": _now()}
    return {
        "tasks": parse_tasks(out),
        "error": None,
        "raw": out[:RAW_LIMIT],
        "fetched": _now(),
    }
