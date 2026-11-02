#!/usr/bin/env bash
# Installs the job-hunt-agent skill for Claude Code, or builds a ZIP for claude.ai.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "--zip" ]; then
  (cd "$here" && rm -f job-hunt-agent.zip && zip -r job-hunt-agent.zip job-hunt-agent >/dev/null)
  echo "Created $here/job-hunt-agent.zip. Upload it in Claude settings."
  exit 0
fi
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/job-hunt-agent"
if [ "${1:-}" = "--link" ]; then
  # Link instead of copy, so a `git pull` of this repo updates the installed skill.
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  ln -s "$here/job-hunt-agent" "$dest"
  echo "Linked $dest to $here/job-hunt-agent. Start a new Claude Code session."
  exit 0
fi
mkdir -p "$dest"
cp -R "$here/job-hunt-agent/." "$dest/"
echo "Installed to $dest. Start a new Claude Code session."
