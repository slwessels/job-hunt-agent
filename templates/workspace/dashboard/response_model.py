"""Response-chance model for the dashboard.

Question answered: how likely is it that a company replies at all to this application
(interview, call, request for information or a rejection; automated receipts do not count).

Method (kept simple on purpose, because the history is small):
1. Base rate. Beta prior (PRIOR_A replies, PRIOR_B non-replies, ~20% for senior roles with 100+
   applicants) updated with the user's own applications. A reply counts as 1. A still-silent
   application counts as F(t), the share of replies that normally have arrived by day t, so a
   fresh application does not drag the rate down.
2. Adjustments, added in log-odds (signed numbers shown in the tooltip):
   fit score, posting age, number of applicants, route, connections at the company, sector flag,
   the user's own confidence.
   The sum is clipped so no single case reaches 0% or 100%.
3. Time decay (applied in the browser so it stays live): each day without a reply lowers the
   chance, P_now = P * (1 - F(t)) / (1 - P * F(t)).

Inputs: ledger.csv, history/events.jsonl, response-feedback.json (user's confidence, posting age,
applicants, channel). Re-run dashboard/build.py after changing any of them.
"""
import json
import math
import pathlib
import re
from datetime import datetime, timezone

PRIOR_A, PRIOR_B = 2.0, 8.0
HALF_LIFE_DAYS = 7.0          # half of all replies arrive within a week
CLIP = (-3.0, 2.5)            # limit on total adjustment
CONF = {"low": -0.9, "medium": 0.0, "high": 0.7}
CHANNEL = {"recruiter_message": 0.4, "easy_apply": 0.0, "company_ats": 0.0, "agency": -0.2}
GOV = re.compile(r"government|public sector|public financial|\bPFM\b|state-owned", re.I)
APPLICABLE = {"submitted", "new", "preparing", "shortlisted"}


def F(days):
    return 1 - 0.5 ** (max(days, 0) / HALF_LIFE_DAYS)


def logit(p):
    return math.log(p / (1 - p))


def inv(x):
    return 1 / (1 + math.exp(-x))


def _days_since(ts, now):
    return (now - datetime.fromisoformat(ts)).total_seconds() / 86400


def score(ledger, events, feedback, now=None):
    now = now or datetime.now(timezone.utc).astimezone()
    sub, replied = {}, set()
    for e in events:
        if e["type"] == "submitted":
            sub.setdefault(e["job_id"], e["ts"])
        if e["type"] in ("response", "rejected"):
            replied.add(e["job_id"])
    applied = set(sub) | replied
    n_reply = len(replied)
    n_eff = n_reply
    for j in applied - replied:
        n_eff += F(_days_since(sub[j], now)) if j in sub else 0
    base = (PRIOR_A + n_reply) / (PRIOR_A + PRIOR_B + n_eff)
    out = {}
    for r in ledger:
        j, st = r["job_id"], r["status"]
        fb = feedback.get(j, {})
        if j in replied:
            out[j] = {"state": "replied"}
            continue
        if st not in APPLICABLE:
            out[j] = {"state": "na"}
            continue
        why = []
        if r["score"] != "":
            v = max(-0.8, min(0.8, 0.04 * (float(r["score"]) - 65)))
            why.append(("Fit score " + r["score"], v))
        age = fb.get("posting_age_days")
        if age is not None:
            v = 0.2 if age <= 14 else 0.0 if age <= 30 else -0.3 if age <= 45 else -0.9 if age <= 90 else -1.4
            why.append((f"Posting about {age} days old", v))
        ap = fb.get("applicants")
        if ap is not None:
            v = -0.4 if ap >= 100 else -0.2 if ap >= 50 else 0.0
            why.append((("100+" if ap >= 100 else str(ap)) + " applicants", v))
        ch = fb.get("channel")
        if ch in CHANNEL and CHANNEL[ch]:
            why.append(("Route: " + ch.replace("_", " "), CHANNEL[ch]))
        if GOV.search(" ".join([r.get("gap", ""), r.get("reason", ""), r.get("employer", "")])):
            why.append(("Government / public-sector focus", -0.6))
        nc = fb.get("connections")
        if nc:
            why.append((f"{nc} connection(s) at the company" + (", contacted" if fb.get("contacted") else ", not contacted"), 0.5 if fb.get("contacted") else 0.15))
        c = fb.get("confidence")
        if c in CONF and CONF[c]:
            why.append((f"Your confidence: {c}", CONF[c]))
        adj = max(CLIP[0], min(CLIP[1], sum(v for _, v in why)))
        p0 = inv(logit(base) + adj)
        out[j] = {"state": "est", "p0": round(p0, 4), "why": [[k, round(v, 2)] for k, v in why],
                  "applied": st == "submitted"}
    meta = {"base": round(base, 3), "replies": n_reply, "n_eff": round(n_eff, 2), "applications": len(applied),
            "prior": [PRIOR_A, PRIOR_B], "half_life": HALF_LIFE_DAYS, "clip": CLIP}
    return out, meta


def load_feedback(root):
    p = pathlib.Path(root) / "response-feedback.json"
    return {k: v for k, v in json.loads(p.read_text()).items() if not k.startswith("_")} if p.exists() else {}
