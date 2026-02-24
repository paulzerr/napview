# Self-Healing Loop Log (Windows PyInstaller Firefox Push)

- 2026-02-24: Investigated run `22361764981` failure (`Timed out waiting for napview web UI on localhost ports 8145-8205`).
- 2026-02-24: Confirmed `NAPVIEW.exe` launched, but both redirected stdout/stderr logs were empty in artifact.
- 2026-02-24: Applied workflow changes: `NAPVIEW_NO_AUTO_BROWSER=1`, host probing (`127.0.0.1`, `localhost`, `[::1]`), process-owned port discovery, and high-verbosity diagnostics (transcript, probe logs, netstat/tasklist/process snapshots, copied local app logs).
- 2026-02-24: Starting next automated cycle.
- 2026-02-24: Run `22365435477` canceled while stuck in `Download NIDRA model files`; no app-launch diagnostics produced.
- 2026-02-24: Added deterministic NIDRA download logging (`nidra_download.log`), per-file timeout, SHA256/size logging, early artifact-dir preparation, and meaningful workflow `run-name`.
- 2026-02-24: Run `22365676316` canceled during NIDRA download after instrumentation: file 1 completed (`ez6.onnx`, 12,224,923 bytes, 17.26s), file 2 started (`ez6moe.onnx`) but run was canceled before completion.
- 2026-02-24: Next step is an uncanceled run with current workflow to reach the Napview launch stage and validate localhost detection fixes.
- 2026-02-24: Run `22365895948` reached launch step but failed before probing with PowerShell parser error `InvalidVariableReferenceWithDrive` in URI interpolation.
- 2026-02-24: Patched URI construction to `http://${targetHost}:$port/` and rerunning.
