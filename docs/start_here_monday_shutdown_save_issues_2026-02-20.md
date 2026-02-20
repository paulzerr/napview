# Shutdown Save Issues Proposal (2026-02-20)

## Observed Issues
- `mne.export.export_raw(..., fmt='edf')` fails during shutdown.
- UI shows:
  - `An error occurred while saving EEG data.`
  - `Staging results file .../temp/results/staging_results.txt does not exist.`

## Root Cause
1. **Dependency mismatch**
- Project pins:
  - `mne==1.11.0`
  - `edfio==0.4.3`
- Runtime behavior:
  - `mne 1.11.0` imports `Bdf` from `edfio` in `mne/export/_edf_bdf.py`.
  - `edfio 0.4.3` does not export `Bdf` (only `Edf`), causing:
    - `ImportError: cannot import name 'Bdf' from 'edfio'`

2. **Staging file warning behavior**
- `staging_results.txt` is read in shutdown (`save_results_files`) but is not created in this repo.
- Missing file is currently appended to shutdown messages, which can make shutdown look problematic even when non-fatal.

## Implementation Options

### 1. Minimal dependency fix (Recommended)
- Update dependency pin from `edfio==0.4.3` to `edfio>=0.4.10,<0.5` in:
  - `requirements.txt`
  - `setup.py`
- Reinstall dependencies.

**Benefits**
- Resolves EDF export crash with minimal code changes.

**Risks**
- Any dependency bump can reveal unrelated compatibility issues.

### 2. Dependency fix + explicit compatibility check
- Apply Option 1.
- Add a startup/runtime check that validates `edfio` version and raises a clear error if incompatible.

**Benefits**
- Fails earlier with a precise message instead of failing late at shutdown.

**Risks**
- Small extra code path to maintain.

### 3. Option 2 + shutdown UX cleanup
- Apply Option 2.
- Treat missing `staging_results.txt` as informational (unless staging is explicitly enabled).

**Benefits**
- Avoids noisy “shutdown with some issues” messaging for expected missing file.

**Risks**
- If staging is expected but misconfigured, warning may be less visible unless gated by config.

## Recommended Path
- Start with **Option 1** for the immediate fix.
- Add **Option 2** if you want stronger diagnostics.
- Add **Option 3** if you want cleaner shutdown UX.
