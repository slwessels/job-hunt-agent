---
name: linkedin-scan
description: Search LinkedIn (and a user's watch list) for new roles, check each against the criteria, and present safe ones for approval before they go into the ledger. Read-only on LinkedIn; never applies.
---

# LinkedIn scan

Use when the user asks for new roles from LinkedIn or for a scan of a list of companies. Work in a fresh tab (call `tabs_context_mcp` first; tab ids change between sessions). Read only: do not apply, save, message or change profile settings.

## Steps
1. Search `https://www.linkedin.com/jobs/search/?keywords=<terms>&location=<country>&f_TPR=r604800&sortBy=DD`. Rotate the titles in `criteria.json`. The page loads slowly: wait about 3 seconds, then `get_page_text`. For a company list, search by company name plus seniority words; also read the company's own careers page or ATS board when it has one.
2. Open each plausible card (use `find`, then click) and read the description, closing date, applicant count and employer. The job id is in the page URL (`currentJobId`).
3. A role is **safe** when the employer is named and real, the posting is live and under 45 days old (or has a future closing date), and it is not in an excluded sector. Recruiter ads with an unnamed client are added with `legit_flag` = `client unnamed`.
4. Skip anything already in `ledger.csv` (match by URL or employer plus title).
5. **Show the user the candidates first** (title, employer, age, one-line fit, main gap) and add only the ones they keep. Unless the user said to add everything, never write unreviewed roles to the ledger.
6. For each kept role: status `new`, score by the rubric, closing date in the reason, a `found` event, then `python3 dashboard/build.py`.
7. Report by score and closing date. Flag anything closing within 3 days first.
