# Napview Plan: Bootstrap NIDRA Models at Runtime (Non-Blocking UX)

## 1. Problem Statement

Napview currently fails in clean environments (for example fresh GitHub runners and likely first-time end-user installs) because NIDRA model files are not guaranteed to exist at runtime.

The key issue is path and timing:

- In python-package mode, NIDRA loads models from `user_data_dir()/NIDRA/models`.
- Napview does not currently trigger model download in its runtime path.
- Existing CI workflow hacks downloaded models to repo paths, which does not represent real user behavior.

Goal: make Napview self-sufficient for first run by downloading models to NIDRA's expected location automatically, without blocking the GUI/startup experience.

## 2. Context and Current Flow

### 2.1 Where Napview calls NIDRA

- `napview/data_analyzer.py` creates `NIDRA.scorer(...)` and calls `score()`.
- No model provisioning step exists before `score()`.

### 2.2 Where NIDRA expects models

- `nidra/nidra/NIDRA/utils.py:get_model_path()`
- Non-bundle mode resolves model directory as:
  - `Path(user_data_dir()) / "NIDRA" / "models"`

### 2.3 How startup currently works

- `/start` in `napview/napview_backend.py` launches:
  1. `producer`, `recorder`
  2. then `analyzer`, `visualizer`
- Analyzer runs in a separate process already, so analyzer-internal startup work does not block the GUI HTTP server process.

## 3. Design Decision

Use NIDRA's own downloader (`download_assets("models", logger)`) from Napview's analyzer startup path.

Why this is the right choice:

- Uses authoritative NIDRA behavior and file layout.
- Avoids duplicate download logic and hardcoded model URL handling in Napview.
- Ensures user installs behave correctly without CI-specific workarounds.

## 4. Proposed Runtime Behavior

At analyzer process startup:

1. Analyzer starts.
2. Analyzer calls NIDRA model bootstrap once:
   - `NIDRA.utils.download_assets("models", logger)`
3. If download succeeds or files already exist, analyzer continues.
4. If download fails, analyzer logs a clear fatal message and exits analyzer process (fail-fast).

This occurs during the warmup period where data is still accumulating, so user-perceived impact is minimized.

## 5. Implementation Plan (File-Level)

## 5.1 `napview/data_analyzer.py`

Add a dedicated bootstrap method and call it before analysis loop begins.

Implementation details:

- Add helper method:
  - `_ensure_nidra_models(self) -> None`
- Inside helper:
  1. Log target model dir by calling `NIDRA.utils.get_model_path()`.
  2. Call `NIDRA.utils.download_assets("models", self.logger)`.
  3. If return is falsy (`None`), raise `RuntimeError` with explicit message.
  4. Log completion and resolved directory.
- Call helper once at start of `run()` (before epoch loop).
- Do not add retries/fallback paths in Napview; rely on NIDRA's behavior and fail clearly if unresolved.

Notes:

- This keeps bootstrap in analyzer process only.
- No backend API changes required.
- No GUI flow changes required.

## 5.2 Optional startup ordering tweak (low priority)

Current `/start` launches analyzer and visualizer together. If desired, visualizer can be launched before analyzer to reduce perceived startup latency of charts/UI while analyzer bootstraps models.

This is optional and not required for correctness.

## 6. Failure Handling Strategy

Explicit failure behavior:

- If model download fails:
  - Analyzer process should terminate with clear log context.
  - Napview remains operational (GUI/process manager still up), but analyzer-specific status should show failure in logs.

This is intentional fail-fast behavior for controlled environments.

## 7. Logging Requirements

Add deterministic log markers for debugging:

- `"Analyzer: checking NIDRA models at <path>"`
- `"Analyzer: ensuring NIDRA models are available..."`
- `"Analyzer: NIDRA models ready at <path>"`
- On failure: `"Analyzer: NIDRA model bootstrap failed: <reason>"`

These should appear in session log and help distinguish:

- missing models
- network/download failures
- downstream inference failures

## 8. Validation Plan

## 8.1 Local validation (clean machine/profile)

1. Delete/rename local NIDRA model dir:
   - Windows: `%LOCALAPPDATA%\NIDRA\models`
   - Linux/macOS: corresponding `appdirs.user_data_dir()` location
2. Start Napview and trigger START.
3. Confirm:
   - models are created in NIDRA path
   - analyzer proceeds to analysis
   - no `NO_SUCHFILE` ONNX errors

## 8.2 CI validation (single runner)

Use the Windows python-package debug workflow and confirm:

- model files exist in `%LOCALAPPDATA%\NIDRA\models`
- `/start` succeeds
- logs include analyzer save progress (`Analysis saved for epoch ...`)
- no `Failed to load ONNX model` and no `NO_SUCHFILE`

## 9. Acceptance Criteria

Must meet all:

1. Fresh environment without pre-cached models can run Napview python package and start analysis.
2. Models are downloaded to NIDRA-resolved directory, not repo-local paths.
3. No CI/workflow-only bootstrap dependency is required for app correctness.
4. Failures are explicit in logs and not silently ignored.

## 10. Risks and Tradeoffs

- First run may take longer (model download), especially on slower networks.
- If download host/network is unavailable, analyzer startup fails (intentional fail-fast).
- If multiple analyzers are introduced in future, parallel bootstrap calls may race; current single-analyzer architecture avoids this.

## 11. Rollout Sequence

1. Implement `data_analyzer.py` bootstrap changes.
2. Run local clean-profile test.
3. Run Windows python-package debug workflow.
4. If stable, remove CI-side model path workarounds from matrix workflows for python-package variant.

## 12. Out of Scope

- Reworking NIDRA downloader internals.
- Building custom model mirrors/caches.
- Adding resilient retry/backoff orchestration in Napview.
- Altering installer packaging strategy.

