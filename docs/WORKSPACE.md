# Setting up your own workspace

The skill in this repo is shared and holds no personal data. Your CV, search criteria, applications and history live in a separate **private** repository that you own. This page shows how to create it.

## 1. Create the workspace

```bash
git clone https://github.com/slwessels/job-hunt-agent.git
cd job-hunt-agent
./install.sh --link                 # installs the skill for Claude Code
./init-workspace.sh ~/my-job-hunt   # copies templates/workspace and runs git init
```

Then on GitHub create a **private** repository (for example `my-job-hunt`) and connect it:

```bash
cd ~/my-job-hunt
git remote add origin git@github.com:YOU/my-job-hunt.git
git add -A && git commit -m "Create workspace" && git push -u origin main
```

If you prefer the guided route, attach your CV in Claude and say `Run job-hunt-agent setup`. Setup builds the same structure and fills in the files from an interview.

## 2. What you get

```
my-job-hunt/
  CLAUDE.md                  working rules Claude reads each session
  README.md                  what this repo is, and a reminder that it is private
  criteria.json              titles, locations, sectors, screening rules, watch list
  schedule.json              your scheduled task (cron, timezone, where it runs)
  ledger.csv                 every job seen (generated from events when you use jh.py)
  history/events.jsonl       append-only log of everything that happens
  history/checked.jsonl      URLs already found dead or not a fit
  response-feedback.json     your own inputs for the response-chance estimate
  profile/profile.json       name, email, LinkedIn and facts (used by tools/make_application.py)
  profile/master-cv.md       your CV as text (source of truth for every claim)
  applications/<job_id>/     one folder per job
  digests/                   daily digests
  tools/make_application.py  builds tailored .odt CV and letter from a base pair
  dashboard/build.py         builds dashboard/index.html from the ledger and events
  .githooks/pre-commit       rebuilds the dashboard on every commit
  .claude/skills/            prepare-application and linkedin-scan, specific to this workspace
```

## 3. Fill in the three files that matter

1. `profile/profile.json`: set `name`, `email`, `linkedin`. The tool checks that the email and LinkedIn hyperlinks survive in every document it writes, so use the same link text as in your base `.odt`.
2. `profile/master-cv.md`: your CV as plain text. Claude uses only what is written here and what you confirm in chat.
3. `criteria.json`: titles, locations, sectors you prefer or exclude, dealbreakers, and `watch_companies`. For a company with a public job-board API, give `ats` (greenhouse, lever, ashby, smartrecruiters, workable, workday) and `board`.

Put a base CV and cover letter in LibreOffice Writer format (`.odt`) in `profile/` or in your first application folder, with your email and LinkedIn as real hyperlinks. `tools/make_application.py` rewrites these, so every later application keeps your layout.

## 4. Daily use

- `git pull` first, commit and push last.
- Ask Claude to scan (`linkedin-scan`), review a listing, or prepare an application (`prepare-application`).
- Follow `docs/PROCESS.md` for the rules.
- Run `python3 dashboard/build.py` and open `dashboard/index.html`.

## 5. Two machines

The workspace repo is the only copy of your data. Pull before you start, push when you finish, and do not keep CV copies elsewhere.

## 6. Keep it private

The workspace contains your CV, contact details and application history. Keep the repository private and do not copy files from it into the public skill repo.
