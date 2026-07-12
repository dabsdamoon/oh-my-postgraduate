#!/bin/bash
# Daily: fetch new arXiv candidates, then let the agent triage them.
# Schedule via launchd/cron, e.g.: 0 7 * * * /path/to/repo/scripts/watch.sh
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/arxiv_watch.py
claude -p "/triage" --permission-mode acceptEdits
