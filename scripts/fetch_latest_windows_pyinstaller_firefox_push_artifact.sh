#!/usr/bin/env bash
set -euo pipefail

WORKFLOW_FILE="${WORKFLOW_FILE:-windows_pyinstaller_firefox_push.yml}"
ARTIFACT_NAME="${ARTIFACT_NAME:-windows-pyinstaller-firefox-push-debug}"
BRANCH="${BRANCH:-dev}"
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

RUNS_JSON="$(gh run list \
  --repo "$REPO" \
  --workflow "$WORKFLOW_FILE" \
  --branch "$BRANCH" \
  --limit 1 \
  --json databaseId,status,conclusion,createdAt,updatedAt,headSha,headBranch,url)"

RUN_ID="$(jq -r '.[0].databaseId // empty' <<<"$RUNS_JSON")"
if [[ -z "$RUN_ID" ]]; then
  echo "No runs found for workflow '$WORKFLOW_FILE' on branch '$BRANCH' in $REPO." >&2
  exit 1
fi

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

gh run download "$RUN_ID" \
  --repo "$REPO" \
  --name "$ARTIFACT_NAME" \
  --dir "$OUTPUT_DIR"

SUMMARY_PATH="$OUTPUT_DIR/_download_summary.json"
jq -n \
  --arg repo "$REPO" \
  --arg workflow "$WORKFLOW_FILE" \
  --arg artifact "$ARTIFACT_NAME" \
  --arg branch "$BRANCH" \
  --argjson run "$(jq '.[0]' <<<"$RUNS_JSON")" \
  '{
    repo: $repo,
    workflow: $workflow,
    artifact: $artifact,
    branch: $branch,
    run: $run
  }' >"$SUMMARY_PATH"

echo "Downloaded artifact '$ARTIFACT_NAME' from run $RUN_ID to: $OUTPUT_DIR"
echo
echo "Files:"
find "$OUTPUT_DIR" -maxdepth 3 -type f | sed "s#^$OUTPUT_DIR/##" | sort
