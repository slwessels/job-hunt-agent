---
name: prepare-application
description: Prepare a tailored CV and cover letter for a job in ledger.csv. Reads the posting, writes the fit analysis, builds the .odt drafts, logs the event and rebuilds the dashboard. Never submits.
---

# Prepare an application

Use when the user asks to review, prepare or "run" one or more roles. Never submit, never enter passwords or ID numbers, never message anyone. The user opens the `.odt` in LibreOffice Writer, edits it, and says when to make PDFs and submit.

## Steps
1. **Read the posting** from the employer or ATS page (job-board pages only to find it) and confirm it is still live. Note closing date, applicant count and posting age. Write `applications/<job_id>/posting.md` (a summary, not the full text).
2. **Check the rules** in `criteria.json`: excluded sectors (confirm with the user, never silently override), postings older than 45 days with no sign they are open, named employer, open on an employer or ATS page. The role track is whatever the user's criteria say: flag blockers, do not skip a role only for being off the main track.
3. **Score** with the rubric: title 30, domain 25, location 20, skills 15, pay 10. Strong 75 and over, Possible 50 to 74, Weak under 50. Apply the `hard_requirement_screen` tiers and show raw and adjusted scores. Record the breakdown in the ledger reason as `[T.. D.. L.. S.. P..]`.
4. **Write `gap-analysis.md`**: main risk, requirement match table (Yes / Partial / No with evidence), and an ASK list of facts only the user can supply. Use only facts in `profile/master-cv.md` and what the user has said. Never claim a certification, a title or an ownership the user has not confirmed. If ASK items matter to the pitch, stop and ask before drafting.
5. **Tailor to this posting only.** Use the posting's own requirements and the user's facts. Never carry a talking point from another application into this one, even if it is a strong point there. If the posting does not mention a topic, the documents do not either.
6. **Write `spec.json`** in the application folder and run `python3 tools/make_application.py <job_id> applications/<job_id>/spec.json`. The spec names a base CV and cover letter (the latest approved pair) and lists paragraph replacements. The tool keeps the email and LinkedIn hyperlinks and refuses to overwrite an existing file.
7. **Check the layout**: convert to PDF in a throwaway directory (`libreoffice -env:UserInstallation=file://$HOME/lo-profile --headless --convert-to pdf --outdir pdfprev ...`), confirm the CV is 2 pages and the letter 1 page, then delete `pdfprev` and `lo-profile`. Previews are not deliverables.
8. **Log it**: write `notes.md`, set the ledger status to `preparing`, append a `prepared` event to `history/events.jsonl`, then run `python3 dashboard/build.py`.
9. **Report**: fit, main risks, the ASK list, and where the drafts are. If Writer has the file open, tell the user to File > Reload.

## Rules that always apply
- The user edits the `.odt` in Writer. Work from the latest saved copy on disk; never regenerate over an existing draft. Before touching a file, check its modified time and read it. Back up before an in-place fix.
- File names the person sees: `<Name> - <Job Title> - CV` and `<Name> - <Job Title> - Cover Letter` (.odt and .pdf).
- Cover letters open warmly: "Thank you for the opportunity to apply for the <role> role." then one concrete sentence on why you fit.
- Email and LinkedIn must be real hyperlinks in every CV and letter.
- Summary is positioning, achievements are outcomes with numbers, and the two do not overlap.
- Understate decisions and ownership; use exact team sizes; do not claim what the user has not confirmed.
- Statuses: new, shortlisted, preparing, submitted, rejected (employer said no), skipped (user decided not to pursue), excluded (fails criteria), expired (listing closed).
- The repo is private and holds personal data. Never make it public.
