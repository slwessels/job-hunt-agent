#!/usr/bin/env bash
# Creates your private job-hunt workspace from templates/workspace.
# usage: ./init-workspace.sh <target-folder>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${1:?usage: init-workspace.sh <target-folder>}"
if [ -e "$dest" ] && [ -n "$(ls -A "$dest" 2>/dev/null)" ]; then
  echo "refusing: $dest exists and is not empty" >&2; exit 1
fi
mkdir -p "$dest"
cp -R "$here/templates/workspace/." "$dest/"
git -C "$dest" init -q
git -C "$dest" config core.hooksPath .githooks
echo "Workspace created in $dest."
echo "Next: create a PRIVATE GitHub repo, add it as origin, edit profile/profile.json and criteria.json,"
echo "then ask Claude to run 'job-hunt-agent setup' inside this folder. See docs/WORKSPACE.md."
