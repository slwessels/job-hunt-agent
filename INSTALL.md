# Install

The easy way: paste `SETUP-PROMPT.md` into Claude. These are the manual steps.

You need: a Claude account, a GitHub account, and a CV (DOCX, PDF or Markdown).

## 1. Create your private data repo
On GitHub, create a new **private** repository, for example `my-job-hunt`. Do not add the skill to it. Your CV and application data go here.

## 2. Install the skill

### Claude Code (terminal)
```bash
git clone https://github.com/slwessels/job-hunt-agent.git
cd job-hunt-agent
./install.sh
```
The script copies the skill to `~/.claude/skills/job-hunt-agent/`. Start a new Claude Code session afterwards.

### Claude.ai or Claude Desktop
1. Download this repo as a ZIP (Code, then Download ZIP), or run `./install.sh --zip` to make `job-hunt-agent.zip`.
2. Open Settings, then Capabilities (or Skills). Choose Upload skill.
3. Upload the ZIP. The ZIP must contain the folder `job-hunt-agent/` with `SKILL.md` inside.
4. Switch the skill on.

## 3. Connect tools (optional but useful)
- **GitHub access** for the private data repo (so the agent can commit and push).
- **Claude in Chrome** (browser extension) for reading job pages and filling forms.
- **Google Calendar** for follow-up reminders.
- **Scheduled tasks** for the daily crawl. Without them the agent still works when you ask.

## 4. Start
Open a new chat. Attach your CV. Send: `Run job-hunt-agent setup.` (or paste `SETUP-PROMPT.md`).

## 5. Check it worked
Your private repo should now have `criteria.json`, `ledger.csv`, `history/events.jsonl` and `profile/master-cv.md`. Compare with `examples/job-hunt/`.

## Update
Pull this repo again and run `./install.sh` again.
