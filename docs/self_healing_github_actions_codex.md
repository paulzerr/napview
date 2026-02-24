# Self-Healing GitHub Actions Loop with Codex (Generalized Guide)

This document describes how to build an automated loop that:

1.  Generates or modifies code
2.  Pushes to GitHub
3.  Triggers a GitHub Actions workflow
4.  Waits for completion
5.  Downloads logs/artifacts
6.  Diagnoses failures using an LLM (e.g., Codex)
7.  Applies fixes
8.  Repeats until success

The design is intentionally generalized so it can be adapted to any
repository, language, or workflow.

------------------------------------------------------------------------

# 1. System Overview

You are building an automated CI/CD repair agent.

Core loop:

generate/edit → commit → push → trigger workflow → wait → download logs
→ analyze → patch → push → repeat until green

This requires:

-   GitHub API access
-   Local git access to repo
-   An LLM capable of editing code
-   A loop orchestrator (Python recommended)

------------------------------------------------------------------------

# 2. Required Components

## 2.1 GitHub Token

Create a GitHub Personal Access Token with:

-   repo
-   workflow
-   actions:read
-   actions:write (optional but useful)

Store as environment variable:

GITHUB_TOKEN=xxxx

------------------------------------------------------------------------

## 2.2 Repository Setup

Your repo must contain:

-   A valid GitHub Actions workflow
-   A dedicated working branch (recommended)

Example branch in this repo: dev

This prevents infinite loops on main.

------------------------------------------------------------------------

## 2.3 Generic GitHub Actions Workflow Template

This works for almost any build/test system.

``` yaml
name: CI

on:
  push:
    branches:
      - dev
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup runtime
        run: |
          echo "Install runtime here"

      - name: Install deps
        run: |
          echo "Install dependencies"

      - name: Build
        run: |
          echo "Run build"

      - name: Test
        run: |
          echo "Run tests"

      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: workflow-logs
          path: .
```

The artifact step ensures logs/files are always retrievable.

------------------------------------------------------------------------

# 3. Orchestrator Design

The orchestrator controls the entire loop.

Recommended: Python daemon or CLI runner.

Core responsibilities:

1.  Modify repo (via Codex)
2.  Commit + push
3.  Trigger workflow
4.  Wait for completion
5.  Fetch logs/artifacts
6.  Send to Codex for analysis
7.  Apply fix
8.  Repeat

------------------------------------------------------------------------

# 4. Git Operations

## Commit + Push

``` bash
git add .
git commit -m "auto: codex attempt"
git push origin dev
```

Use deterministic commit messages for tracking attempts.
Codex should run these git commands directly (including push), not leave
the push as a manual user step.

------------------------------------------------------------------------

# 5. Triggering GitHub Actions

Two methods.

## Method A --- Push Trigger (simplest)

Push to branch: dev

Workflow automatically runs.

## Method B --- Manual Trigger via API

POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches

Python example:

``` python
import requests

def trigger_workflow(repo, workflow_file, branch, token):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.post(url, headers=headers, json={"ref": branch})
    r.raise_for_status()
```

------------------------------------------------------------------------

# 6. Waiting for Workflow Completion

Poll latest run: GET /repos/{owner}/{repo}/actions/runs

``` python
import time, requests

def wait_for_completion(repo, token, branch="dev"):
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/actions/runs",
            headers=headers
        ).json()

        runs = [
            x for x in r["workflow_runs"]
            if x["head_branch"] == branch
        ]

        if not runs:
            time.sleep(5)
            continue

        run = runs[0]

        if run["status"] == "completed":
            return run

        time.sleep(10)
```

------------------------------------------------------------------------

# 7. Downloading Logs

GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs

``` python
def download_logs(repo, run_id, token, out="logs.zip"):
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs",
        headers=headers
    )

    open(out, "wb").write(r.content)
```

------------------------------------------------------------------------

# 8. Downloading Artifacts

GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts

``` python
def download_artifacts(repo, run_id, token):
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts",
        headers=headers
    ).json()

    for art in r["artifacts"]:
        aid = art["id"]
        name = art["name"]

        blob = requests.get(
            f"https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip",
            headers=headers
        ).content

        open(f"{name}.zip", "wb").write(blob)
```

------------------------------------------------------------------------

# 9. Feeding Logs to Codex

Collect:

-   build logs
-   test failures
-   stack traces
-   compiler output

Then send structured prompt to Codex:

Analyze failure\
Identify root cause\
Patch repository\
Return updated files or diff

------------------------------------------------------------------------

# 10. Loop Controller Logic

``` python
while True:
    codex_generate_or_edit()
    git_commit_push()

    trigger_workflow()

    run = wait_for_completion()

    if run["conclusion"] == "success":
        break

    logs = download_logs()
    artifacts = download_artifacts()

    codex_analyze_and_fix(logs)
```

Add: - max attempts - timeout - failure classification

------------------------------------------------------------------------

# 11. Recommended Enhancements

## Failure classification

Have Codex label failure type: - dependency - test - build - lint -
infra

## Persistent memory

Store attempts: attempt_01/ attempt_02/

Include logs, diffs, summaries.

## Parallel strategy

Try multiple fixes simultaneously on separate branches.

## Safety controls

-   max retries
-   stop on repeated identical failure
-   require green tests before merge

------------------------------------------------------------------------

# 12. Minimal Stack

Recommended:

-   Python orchestrator
-   Git CLI
-   GitHub REST API
-   Codex
-   Local repo clone

Optional: - Redis (state) - Postgres (history) - Docker sandbox

------------------------------------------------------------------------

# 13. End State

You now have a self-healing CI loop that can:

-   write code
-   push
-   run builds
-   read logs
-   debug itself
-   retry until success

This architecture works for any GitHub repository or workflow.
