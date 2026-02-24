# Self-Healing Loop Log (Windows PyInstaller Firefox Push)

- 2026-02-24: Investigated run `22361764981` failure (`Timed out waiting for napview web UI on localhost ports 8145-8205`).
- 2026-02-24: Confirmed `NAPVIEW.exe` launched, but both redirected stdout/stderr logs were empty in artifact.
- 2026-02-24: Applied workflow changes: `NAPVIEW_NO_AUTO_BROWSER=1`, host probing (`127.0.0.1`, `localhost`, `[::1]`), process-owned port discovery, and high-verbosity diagnostics (transcript, probe logs, netstat/tasklist/process snapshots, copied local app logs).
- 2026-02-24: Starting next automated cycle.
