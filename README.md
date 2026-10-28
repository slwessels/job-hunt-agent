# Job Hunt Agent

A Claude skill that runs a job search from start to finish. It reads your CV, interviews you for criteria, crawls job boards on a schedule, removes duplicates, tailors your CV, fills application forms in Chrome, and logs every step. It also draws a timeline of your applications.

**You always click Submit.** The agent never submits, never sends messages for you, never types passwords and never solves CAPTCHAs.

## What is in this repo

| Path | Purpose |
|---|---|
| `job-hunt-agent/SKILL.md` | The skill. Contains the process only. It holds no personal data. |
| `SETUP-PROMPT.md` | A prompt to paste into Claude. It sets up everything for a new user. |
| `INSTALL.md` | Step-by-step install for claude.ai, Claude Desktop and Claude Code. |
| `install.sh` | Installs the skill for Claude Code (`~/.claude/skills`). |
| `examples/job-hunt/` | Fake sample data that shows the file layout. |

## Quick start

1. Open Claude. Paste the text in `SETUP-PROMPT.md`. Attach your CV.
2. Answer the questions. Claude installs the skill, builds your private workspace and schedules the daily search.

Your CV and job data are never stored in this repo. Claude keeps them in a private place that you choose. `INSTALL.md` has manual steps for people who prefer them.

## The seven modes

A Setup, B Crawl, C Digest, D Review a listing, E Apply, F Track, G Timeline. The skill file describes each one.

## Design choices

- **Skill and data are separate.** The skill is shared. Your data lives in your own private repo.
- **Append-only history.** `history/events.jsonl` is never edited. Corrections are new events.
- **Frozen submissions.** Each application keeps a copy of exactly what you sent, with file hashes.
- **No invented facts.** A tailored CV only rewords facts from your master CV or facts you confirm.

## Limits

- Scheduled runs in the cloud cannot use your Chrome. They use web search and fetch. Deep reading and form filling happen when you are present.
- Job-board terms of service differ. Use the agent for personal job search only.

## Licence

MIT.
