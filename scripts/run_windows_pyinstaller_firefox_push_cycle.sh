#!/usr/bin/env bash
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-windows_pyinstaller_firefox_push.yml}"
ARTIFACT_NAME="${ARTIFACT_NAME:-windows-pyinstaller-firefox-push-debug}"
BRANCH="${BRANCH:-dev}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-auto: codex attempt}"
WAIT_FOR_COMPLETION="${WAIT_FOR_COMPLETION:-1}"
WAIT_TIMEOUT_MINUTES="${WAIT_TIMEOUT_MINUTES:-180}"
OUTPUT_DIR="${1:-${TMPDIR:-/tmp}/windows-pyinstaller-firefox-push-latest}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required." >&2
  exit 1
fi

REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
SSH_REMOTE_URL="${SSH_REMOTE_URL:-git@github.com:${REPO}.git}"

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "Current branch is '$CURRENT_BRANCH'; expected '$BRANCH'." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "$COMMIT_MESSAGE"
  git push "$SSH_REMOTE_URL" "$BRANCH"
else
  echo "Working tree clean. Skipping commit/push."
fi

gh workflow run "$WORKFLOW_FILE" --repo "$REPO" --ref "$BRANCH"

RUN_ID=""
DEADLINE_EPOCH="$(( $(date +%s) + WAIT_TIMEOUT_MINUTES * 60 ))"
while [[ -z "$RUN_ID" ]]; do
  if (( $(date +%s) >= DEADLINE_EPOCH )); then
    echo "Timed out waiting for a workflow run to appear." >&2
    exit 1
  fi

  RUN_ID="$(gh run list \
    --repo "$REPO" \
    --workflow "$WORKFLOW_FILE" \
    --branch "$BRANCH" \
    --event workflow_dispatch \
    --limit 1 \
    --json databaseId \
    | jq -r '.[0].databaseId // empty')"

  if [[ -z "$RUN_ID" ]]; then
    sleep 5
  fi
done

if [[ "$WAIT_FOR_COMPLETION" == "1" ]]; then
  WATCH_EXIT_CODE=0
  if ! gh run watch "$RUN_ID" --repo "$REPO" --exit-status; then
    WATCH_EXIT_CODE=$?
  fi
else
  WATCH_EXIT_CODE=0
fi

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

gh run view "$RUN_ID" --repo "$REPO" --log >"$OUTPUT_DIR/workflow.log" || true

if ! gh run download "$RUN_ID" \
  --repo "$REPO" \
  --name "$ARTIFACT_NAME" \
  --dir "$OUTPUT_DIR"; then
  echo "Artifact '$ARTIFACT_NAME' not downloaded for run $RUN_ID." >&2
fi

RUN_JSON="$(gh run view "$RUN_ID" \
  --repo "$REPO" \
  --json databaseId,status,conclusion,createdAt,updatedAt,headSha,headBranch,url)"

jq -n \
  --arg repo "$REPO" \
  --arg workflow "$WORKFLOW_FILE" \
  --arg artifact "$ARTIFACT_NAME" \
  --arg branch "$BRANCH" \
  --argjson run "$RUN_JSON" \
  '{
    repo: $repo,
    workflow: $workflow,
    artifact: $artifact,
    branch: $branch,
    run: $run
  }' >"$OUTPUT_DIR/_download_summary.json"

echo "Downloaded artifact '$ARTIFACT_NAME' from run $RUN_ID to: $OUTPUT_DIR"
echo
echo "Files:"
find "$OUTPUT_DIR" -maxdepth 3 -type f | sed "s#^$OUTPUT_DIR/##" | sort

if [[ "$WATCH_EXIT_CODE" -ne 0 ]]; then
  exit "$WATCH_EXIT_CODE"
fi
