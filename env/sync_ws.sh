#!/bin/sh
# Sync the local code to the WS dev copy (~/jsw-dev) and stamp its revision (OPTIONS_PLAN.md §5, S5).
# Usage: env/sync_ws.sh        (run from the repo root)
set -e
WS=saisandeshk@10.24.32.174
REV="$(git describe --always --dirty) $(date -u +%Y-%m-%dT%H:%M:%SZ)"
rsync -a --exclude __pycache__ jsw env analysis tests "$WS":~/jsw-dev/
ssh "$WS" "echo '$REV' > ~/jsw-dev/REVISION"
echo "synced: $REV"
