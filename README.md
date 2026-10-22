# ⚛️ Einstein@Home & GPU Monitor

A small Streamlit dashboard for a machine running [Einstein@Home](https://einsteinathome.org/) through BOINC. It shows:

- **GPU:** temperature, load and VRAM use, read with `nvidia-smi`.
- **Einstein@Home tasks:** name, progress, state and elapsed time, read with `boinccmd`.
- **Honest errors:** if `nvidia-smi` or `boinccmd` is missing, times out or fails, the page says so instead of showing an empty list.

Readings are shared between all open browsers and refreshed at most every few seconds, so extra viewers don't add load.

## Setup

1. Install requirements: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and adjust the paths to `boinccmd.exe` and `nvidia-smi.exe` if yours differ.
3. Start it: `streamlit run app.py`, or double-click `eah_runner.pyw` for a windowless launcher that restarts the dashboard if it crashes (logs go to `eah_runner.log` and `streamlit.log`).

Open `http://127.0.0.1:8502`. The dashboard listens on this computer only unless you set `LISTEN_ADDRESS` in `.env` to the PC's LAN IP.

### BOINC access

The monitor runs `boinccmd` on the same machine, which reads the GUI RPC password from BOINC's own `gui_rpc_auth.cfg`. The monitor has no password setting and stores no credentials.

## Settings (`.env`)

| Setting | Default | Meaning |
|---|---|---|
| `BOINC_CMD_PATH` | `C:\Program Files\BOINC\boinccmd.exe` | Path to `boinccmd` |
| `NVIDIA_SMI_PATH` | `nvidia-smi` | Path to `nvidia-smi` |
| `REFRESH_INTERVAL` | `10` | Seconds between refreshes (minimum 2) |
| `CMD_TIMEOUT` | `8` | Seconds before a command is given up on (minimum 2) |
| `LISTEN_ADDRESS` | `127.0.0.1` | Address the runner listens on |
| `DASHBOARD_PORT` | `8502` | Port the runner listens on |

## Security

The dashboard has **no login**. Run it on a trusted home network only: don't port-forward it or expose it to the internet. `.env` is gitignored.

## Files

| File | Purpose |
|---|---|
| `app.py` | Dashboard |
| `eah_core.py` | Settings and the `nvidia-smi` / `boinccmd` readers |
| `eah_runner.pyw` | Windowless launcher + watchdog |
| `.env.example` | Template for your local `.env` |
