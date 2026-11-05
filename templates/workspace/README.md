# My job hunt (private)

Private workspace for the job-hunt-agent skill (https://github.com/slwessels/job-hunt-agent). It holds a CV with personal contact details: never make this repository public.

- `criteria.json`: what to look for and the screening rules. `ledger.csv`: every job seen. `history/events.jsonl`: append-only event log.
- `applications/<job_id>/`: everything for one job. `digests/`: daily digests. `profile/`: master CV and facts.
- `dashboard/index.html`: regenerate with `python3 dashboard/build.py`.
- Once per clone: `git config core.hooksPath .githooks`.
- Start every session with `git pull`; end it with commit and push.
