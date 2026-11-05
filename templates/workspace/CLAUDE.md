# Working rules for this workspace

Read this at the start of every session. It is the short version of `docs/PROCESS.md` in the job-hunt-agent repo.

- Start of session: `git pull`. End of session: commit and `git push`. This repo is the only copy of the data.
- The user submits every application and sends every message. You prepare and draft.
- Never type passwords, create accounts, solve CAPTCHAs, or pay for anything.
- Never invent a fact. Use `profile/master-cv.md` and what the user confirms in chat.
- Tailor each application to that job's own posting. Do not carry points over from other applications.
- The user edits `.odt` files in Writer. Read the saved file, never regenerate over it, back up before an in-place fix.
- After any change to the ledger or the events: `python3 dashboard/build.py`. A commit hook does this too (`git config core.hooksPath .githooks`, once per clone).
- Statuses: new, shortlisted, preparing, submitted, rejected (employer said no), skipped (user's choice), excluded (fails criteria), expired (listing closed).
