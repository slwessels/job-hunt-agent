#!/usr/bin/env python3
"""Workspace helper for the job-hunt-agent skill.

The model decides; this script does the bookkeeping. It keeps three rules:
- history/events.jsonl is the only source of truth and is append-only.
- ledger.csv is generated from the events (`rebuild`). Never edit it by hand.
- history/checked.jsonl remembers URLs already found closed, stale or blocked.

Standard library only (Python 3.8+). Run `jh.py --help` for the commands.
Every command takes --ws <workspace folder> (default: current folder).
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

COLUMNS = ["job_id", "first_seen", "last_seen", "title", "employer", "recruiter", "location", "mode",
           "salary", "url", "alt_urls", "cluster_id", "tier", "score", "reason", "gap", "status", "legit_flag"]
STATUSES = ["new", "shortlisted", "preparing", "ready", "submitted", "interviewing", "offer",
            "rejected", "withdrawn", "skipped", "closed", "expired", "excluded"]
TYPES = ["setup", "crawl", "criteria_changed", "found", "seen", "job_updated", "snapshot", "shortlisted",
         "user_confirmed", "docs_prepared", "docs_approved", "form_filled", "submitted", "reminder_set",
         "response", "interview_scheduled", "interview_done", "follow_up_drafted", "follow_up_sent",
         "offer", "rejected", "withdrawn", "skipped", "closed", "expired", "note", "correction"]
SOURCES = ["crawl", "user", "chrome", "email", "calendar", "claude"]
FLAGS = ["", "aggregator", "conditional", "mismatch", "data_error", "stale", "date_unverified", "pay_to_apply"]
TIERS = ["", "Strong", "Possible", "Weak", "Excluded"]
CHECK_RESULTS = ["closed", "stale", "filled", "not_fit", "blocked"]
RECHECK_DAYS = {"blocked": 7}  # every other result is final
WORKSPACE_EVENTS = {"setup", "crawl", "criteria_changed", "note", "correction"}
SUFFIXES = r"\b(pty|ltd|limited|inc|llc|plc|gmbh|bv|sa|group holdings)\b"


# ---------- files ----------

def paths(ws):
    return {"events": os.path.join(ws, "history", "events.jsonl"),
            "checked": os.path.join(ws, "history", "checked.jsonl"),
            "ledger": os.path.join(ws, "ledger.csv"),
            "criteria": os.path.join(ws, "criteria.json")}


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    sys.exit("%s line %d is not valid JSON" % (path, n))
    return out


def append_jsonl(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def tz_now(ws):
    """Current time in the workspace time zone (criteria.json schedule.tz), ISO 8601 with offset."""
    try:
        from zoneinfo import ZoneInfo
        tz = json.load(open(paths(ws)["criteria"], encoding="utf-8")).get("schedule", {}).get("tz")
        if tz:
            return dt.datetime.now(ZoneInfo(tz)).isoformat(timespec="seconds")
    except Exception:
        pass
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- ids ----------

def norm(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)                  # "(Pty) Ltd", "(Hybrid)", "(via X)"
    s = re.sub(r"\b[a-z]{1,4}\s?-?\d{3,}\b", " ", s)  # recruiter refs such as "TJ 19600"
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def city_of(location):
    """First place name in a location string; 'remote' when there is none."""
    loc = norm(re.split(r"[,/|;]| or ", location or "")[0])
    loc = re.sub(r"\b(hybrid|onsite|on site|remote|metropolitan area|metro)\b", " ", loc).strip()
    return re.sub(r"\s+", " ", loc) or "remote"


def job_id(employer, title, location):
    key = "%s|%s|%s" % (norm(employer) or "unknown", norm(title), city_of(location))
    return hashlib.md5(key.encode()).hexdigest()[:8], key


def next_event_id(events, ts):
    day = ts[:10].replace("-", "")
    nums = [int(e["event_id"].rsplit("_", 1)[1]) for e in events
            if e.get("event_id", "").startswith("ev_%s_" % day) and e["event_id"].rsplit("_", 1)[1].isdigit()]
    return "ev_%s_%04d" % (day, max(nums, default=0) + 1)


# ---------- ledger from events ----------

def fold(events):
    """Replay the event log into ledger rows, in order of first appearance."""
    rows, order = {}, []
    for e in events:
        # A correction never removes the old event: its details.set and status_after are applied on top.
        jid, d, day = e.get("job_id"), e.get("details") or {}, (e.get("ts") or "")[:10]
        if not jid:
            continue
        if e.get("type") in ("found", "snapshot") and isinstance(d.get("job"), dict):
            row = rows.get(jid) or {c: "" for c in COLUMNS}
            row.update({k: ("" if v is None else str(v)) for k, v in d["job"].items() if k in COLUMNS})
            row["job_id"] = jid
            row["first_seen"] = row["first_seen"] or day
            row["last_seen"] = row["last_seen"] or day
            if jid not in rows:
                order.append(jid)
            rows[jid] = row
        row = rows.get(jid)
        if row is None:
            continue  # legacy event before the job's first snapshot
        if e.get("type") == "seen":
            row["last_seen"] = max(row["last_seen"], day)
            url = d.get("url")
            alts = [u for u in row["alt_urls"].split(" ") if u]
            if url and url != row["url"] and url not in alts:
                row["alt_urls"] = " ".join(alts + [url])
        if e.get("type") in ("job_updated", "correction"):
            for k, v in (d.get("set") or {}).items():
                if k in COLUMNS and k != "job_id":
                    row[k] = "" if v is None else str(v)
        if e.get("status_after"):
            row["status"] = e["status_after"]
    return [rows[j] for j in order]


def write_ledger(ws, events):
    rows = fold(events)
    tmp = paths(ws)["ledger"] + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, paths(ws)["ledger"])
    return rows


def find_matches(events, employer, title, location="", url=""):
    jid, _ = job_id(employer, title, location)
    hits = []
    for r in fold(events):
        why = []
        if r["job_id"] == jid:
            why.append("same job_id")
        if norm(r["employer"]) == norm(employer) and norm(r["title"]) == norm(title):
            why.append("same employer and title")
        if url and (url == r["url"] or url in r["alt_urls"].split(" ")):
            why.append("same url")
        if why:
            hits.append({"job_id": r["job_id"], "status": r["status"], "title": r["title"],
                         "employer": r["employer"], "why": why})
    return jid, hits


# ---------- commands ----------

def make_event(ws, events, job, etype, summary, status=None, source="claude", details=None, files=None, ts=None):
    ts = ts or tz_now(ws)
    ev = {"event_id": next_event_id(events, ts), "ts": ts, "job_id": job, "type": etype, "source": source,
          "summary": summary, "status_after": status, "details": details or {}, "files": files or []}
    problems = check_event(ev)
    if problems:
        sys.exit("refused: " + "; ".join(problems))
    append_jsonl(paths(ws)["events"], ev)
    events.append(ev)
    return ev


def cmd_id(a):
    jid, key = job_id(a.employer, a.title, a.location)
    print(json.dumps({"job_id": jid, "key": key}))


def cmd_find(a):
    events = read_jsonl(paths(a.ws)["events"])
    jid, hits = find_matches(events, a.employer, a.title, a.location, a.url)
    print(json.dumps({"job_id": jid, "matches": hits}, ensure_ascii=False))


def cmd_add_job(a):
    job = json.loads(a.json)
    for k in ("title", "employer"):
        if not job.get(k):
            sys.exit("job JSON needs %s" % k)
    events = read_jsonl(paths(a.ws)["events"])
    jid, hits = find_matches(events, job["employer"], job["title"], job.get("location", ""), job.get("url", ""))
    if hits:
        known = hits[0]["job_id"]
        ev = make_event(a.ws, events, known, "seen", "Seen again: %s, %s" % (job["title"], job["employer"]),
                        source=a.source, details={"url": job.get("url", "")})
        write_ledger(a.ws, events)
        print(json.dumps({"result": "duplicate", "job_id": known, "status": hits[0]["status"],
                          "why": hits[0]["why"], "event_id": ev["event_id"]}))
        return
    status = job.pop("status", None) or "new"
    summary = a.summary or "Found: %s, %s (%s %s)" % (job["title"], job["employer"], job.get("tier", ""), job.get("score", ""))
    ev = make_event(a.ws, events, jid, "found", summary, status=status, source=a.source, details={"job": job})
    write_ledger(a.ws, events)
    print(json.dumps({"result": "new", "job_id": jid, "event_id": ev["event_id"]}))


def cmd_event(a):
    events = read_jsonl(paths(a.ws)["events"])
    known = {r["job_id"] for r in fold(events)}
    if a.job and a.job not in known:
        sys.exit("unknown job_id %s: add the job first" % a.job)
    details = json.loads(a.details) if a.details else {}
    files = [f for f in (a.files or "").split(",") if f]
    missing = [f for f in files if not os.path.exists(os.path.join(a.ws, f))]
    if missing:
        print("warning: files not found: %s" % ", ".join(missing), file=sys.stderr)
    ev = make_event(a.ws, events, a.job, a.type, a.summary, a.status, a.source, details, files, a.ts)
    write_ledger(a.ws, events)
    print(json.dumps({"event_id": ev["event_id"]}))


def cmd_update(a):
    sets = {}
    for pair in a.set:
        k, _, v = pair.partition("=")
        if k not in COLUMNS or k in ("job_id", "status"):
            sys.exit("cannot set %s (status changes need an event with --status)" % k)
        sets[k] = v
    a.type, a.details, a.status, a.files, a.ts = "job_updated", json.dumps({"set": sets}), None, "", None
    a.summary = a.summary or "Updated " + ", ".join(sets)
    cmd_event(a)


def cmd_rebuild(a):
    rows = write_ledger(a.ws, read_jsonl(paths(a.ws)["events"]))
    print("ledger.csv rebuilt: %d rows" % len(rows))


def cmd_migrate(a):
    """One-off: append a snapshot event for each ledger row so the ledger can be rebuilt from events."""
    p = paths(a.ws)
    events = read_jsonl(p["events"])
    with open(p["ledger"], newline="", encoding="utf-8") as f:
        ledger = list(csv.DictReader(f))
    folded = {r["job_id"]: r for r in fold(events)}
    added = 0
    for row in ledger:
        if folded.get(row["job_id"]) == {c: row.get(c, "") for c in COLUMNS}:
            continue
        job = {c: row.get(c, "") for c in COLUMNS if c != "job_id"}
        status = job["status"] if job["status"] in STATUSES else "new"
        if job["status"] not in STATUSES:
            job["reason"] = (job["reason"] + " [old status: %s]" % job["status"]).strip()
        job["status"] = status
        if job["legit_flag"] not in FLAGS:
            job["reason"] = (job["reason"] + " [old flag: %s]" % job["legit_flag"]).strip()
            job["legit_flag"] = ""
        make_event(a.ws, events, row["job_id"], "snapshot", "Migration snapshot of ledger row",
                   status=status, details={"job": job})
        added += 1
    if not a.dry_run:
        write_ledger(a.ws, events)
    print("snapshot events added: %d; ledger rows: %d" % (added, len(ledger)))


def check_event(e):
    p = []
    for k in ("event_id", "ts", "type", "source", "summary"):
        if not e.get(k):
            p.append("missing %s" % k)
    if e.get("type") not in TYPES:
        p.append("type %r not allowed" % e.get("type"))
    if e.get("source") not in SOURCES:
        p.append("source %r not allowed" % e.get("source"))
    if e.get("status_after") and e["status_after"] not in STATUSES:
        p.append("status_after %r not allowed" % e["status_after"])
    if not re.search(r"(Z|[+-]\d\d:?\d\d)$", e.get("ts") or ""):
        p.append("ts needs a time zone offset")
    if e.get("type") not in WORKSPACE_EVENTS and not e.get("job_id"):
        p.append("type %s needs a job_id" % e.get("type"))
    job = (e.get("details") or {}).get("job")
    if isinstance(job, dict):
        if job.get("legit_flag", "") not in FLAGS:
            p.append("legit_flag %r not allowed" % job.get("legit_flag"))
        if job.get("tier", "") not in TIERS:
            p.append("tier %r not allowed" % job.get("tier"))
    return p


def cmd_validate(a):
    p = paths(a.ws)
    events = read_jsonl(p["events"])
    errors, warnings = [], []
    seen = set()
    for e in events:
        if e.get("event_id") in seen:
            errors.append("duplicate event_id %s" % e.get("event_id"))
        seen.add(e.get("event_id"))
        for msg in check_event(e):
            warnings.append("%s: %s" % (e.get("event_id"), msg))
    rows = fold(events)
    if os.path.exists(p["ledger"]):
        with open(p["ledger"], newline="", encoding="utf-8") as f:
            on_disk = list(csv.DictReader(f))
        if [dict(r) for r in on_disk] != rows:
            errors.append("ledger.csv does not match the event log: run `rebuild` (or `migrate` once for an old workspace)")
        if len(on_disk) > len(rows):
            errors.append("%d ledger rows have no found/snapshot event" % (len(on_disk) - len(rows)))
    for c in read_jsonl(p["checked"]):
        if c.get("result") not in CHECK_RESULTS:
            warnings.append("checked %s: result %r not allowed" % (c.get("url"), c.get("result")))
    for w in warnings[:50]:
        print("warning: " + w)
    if len(warnings) > 50:
        print("warning: ... %d more" % (len(warnings) - 50))
    for e in errors:
        print("ERROR: " + e)
    print("%d events, %d ledger rows, %d errors, %d warnings" % (len(events), len(rows), len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


def checked_state(ws, url, today=None):
    today = today or dt.date.today().isoformat()
    last = None
    for c in read_jsonl(paths(ws)["checked"]):
        if c.get("url") == url:
            last = c
    if not last:
        return None
    days = RECHECK_DAYS.get(last["result"])
    if days and (dt.date.fromisoformat(today) - dt.date.fromisoformat(last["date"][:10])).days >= days:
        return None  # due for a re-check
    return last


def cmd_checked(a):
    if a.action == "add":
        if a.result not in CHECK_RESULTS:
            sys.exit("result must be one of " + ", ".join(CHECK_RESULTS))
        append_jsonl(paths(a.ws)["checked"], {"date": tz_now(a.ws)[:10], "url": a.url, "result": a.result,
                                             "note": a.note or ""})
        print("recorded")
    elif a.action == "has":
        state = checked_state(a.ws, a.url)
        print(json.dumps({"skip": bool(state), "last": state}))
    else:
        for c in read_jsonl(paths(a.ws)["checked"]):
            print(json.dumps(c, ensure_ascii=False))


# ---------- public job-board APIs ----------

def http_json(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "job-hunt-agent/1.0",
                                                          "Accept": "application/json",
                                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def ats_postings(c):
    """Return [{title, location, posted, url}] from a company's public board."""
    ats, board = c.get("ats"), c.get("board", "")
    if ats == "greenhouse":
        base = c.get("api_base", "https://boards-api.greenhouse.io")
        js = http_json("%s/v1/boards/%s/jobs" % (base, board))
        return [{"title": j["title"], "location": (j.get("location") or {}).get("name", ""),
                 "posted": (j.get("first_published") or j.get("updated_at") or "")[:10], "url": j["absolute_url"]}
                for j in js.get("jobs", [])]
    if ats == "lever":
        base = c.get("api_base", "https://api.lever.co")
        js = http_json("%s/v0/postings/%s?mode=json" % (base, board))
        return [{"title": j["text"], "location": (j.get("categories") or {}).get("location", ""),
                 "posted": dt.datetime.utcfromtimestamp(j.get("createdAt", 0) / 1000).date().isoformat(),
                 "url": j["hostedUrl"]} for j in js]
    if ats == "ashby":
        js = http_json("https://api.ashbyhq.com/posting-api/job-board/%s" % board)
        return [{"title": j["title"], "location": j.get("location", ""), "posted": (j.get("publishedAt") or "")[:10],
                 "url": j.get("jobUrl", "")} for j in js.get("jobs", [])]
    if ats == "smartrecruiters":
        out, offset = [], 0
        while True:
            js = http_json("https://api.smartrecruiters.com/v1/companies/%s/postings?limit=100&offset=%d" % (board, offset))
            for j in js.get("content", []):
                loc = j.get("location") or {}
                out.append({"title": j["name"], "location": ", ".join(x for x in (loc.get("city"), loc.get("country")) if x),
                            "posted": (j.get("releasedDate") or "")[:10],
                            "url": "https://jobs.smartrecruiters.com/%s/%s" % (board, j["id"])})
            offset += 100
            if offset >= js.get("totalFound", 0) or offset >= 1000:
                return out
    if ats == "workable":
        js = http_json("https://apply.workable.com/api/v1/widget/accounts/%s" % board)
        return [{"title": j["title"], "location": ", ".join(x for x in (j.get("city"), j.get("country")) if x),
                 "posted": (j.get("published_on") or "")[:10], "url": j.get("url", "")} for j in js.get("jobs", [])]
    if ats == "workday":
        m = re.match(r"https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)", c.get("careers_url", ""))
        if not m:
            raise ValueError("workday needs careers_url like https://<tenant>.wd3.myworkdayjobs.com/<site>")
        tenant, wd, site = m.groups()
        root = "https://%s.%s.myworkdayjobs.com" % (tenant, wd)
        out = []
        for term in c.get("search", [""]):
            js = http_json("%s/wday/cxs/%s/%s/jobs" % (root, tenant, site),
                           {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term})
            for j in js.get("jobPostings", []):
                out.append({"title": j.get("title", ""), "location": j.get("locationsText", ""),
                            "posted": j.get("postedOn", ""), "url": "%s/%s%s" % (root, site, j.get("externalPath", ""))})
        return list({o["url"]: o for o in out}.values())
    raise ValueError("no API for ats %r: use web search and the careers_url" % ats)


def cmd_ats(a):
    p = paths(a.ws)
    criteria = json.load(open(p["criteria"], encoding="utf-8"))
    events = read_jsonl(p["events"])
    words = [w.lower() for w in (a.match or "").split(",") if w]
    for c in criteria.get("watch_companies", []):
        if isinstance(c, str):
            c = {"name": c}
        if a.company and a.company.lower() not in c["name"].lower():
            continue
        if not c.get("ats"):
            print(json.dumps({"company": c["name"], "skipped": "no ats set: use web search"}))
            continue
        try:
            posts = ats_postings(c)
        except (urllib.error.URLError, ValueError, KeyError, OSError) as err:
            print(json.dumps({"company": c["name"], "error": str(err)[:200]}))
            continue
        for post in posts:
            if words and not any(re.search(r"\b%s\b" % re.escape(w), post["title"].lower()) for w in words):
                continue
            _, hits = find_matches(events, c["name"], post["title"], post["location"], post["url"])
            state = checked_state(a.ws, post["url"])
            print(json.dumps(dict(post, company=c["name"],
                                  known=hits[0]["job_id"] if hits else None,
                                  checked=state["result"] if state else None), ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ws", default=".", help="workspace folder (default: current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("id", help="print the job_id for employer, title and location")
    s.add_argument("--employer", required=True); s.add_argument("--title", required=True)
    s.add_argument("--location", default=""); s.set_defaults(fn=cmd_id)

    s = sub.add_parser("find", help="look for a job already in the ledger")
    s.add_argument("--employer", required=True); s.add_argument("--title", required=True)
    s.add_argument("--location", default=""); s.add_argument("--url", default=""); s.set_defaults(fn=cmd_find)

    s = sub.add_parser("add-job", help="add a job (or log a 'seen' event if it is a duplicate)")
    s.add_argument("--json", required=True, help="ledger fields as JSON; status defaults to new")
    s.add_argument("--summary"); s.add_argument("--source", default="crawl"); s.set_defaults(fn=cmd_add_job)

    s = sub.add_parser("event", help="append an event, then rebuild the ledger")
    s.add_argument("--job"); s.add_argument("--type", required=True, choices=TYPES)
    s.add_argument("--summary", required=True); s.add_argument("--status", choices=STATUSES)
    s.add_argument("--source", default="claude", choices=SOURCES); s.add_argument("--details")
    s.add_argument("--files", help="comma-separated paths relative to the workspace")
    s.add_argument("--ts", help="when it happened, ISO 8601 with offset (default: now)")
    s.set_defaults(fn=cmd_event)

    s = sub.add_parser("update", help="change ledger fields (not status) through a job_updated event")
    s.add_argument("--job", required=True); s.add_argument("--set", nargs="+", required=True, metavar="FIELD=VALUE")
    s.add_argument("--summary"); s.add_argument("--source", default="claude", choices=SOURCES)
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("rebuild", help="regenerate ledger.csv from the event log"); s.set_defaults(fn=cmd_rebuild)
    s = sub.add_parser("validate", help="check the event log, the ledger and checked.jsonl"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("migrate", help="one-off: snapshot an old hand-edited ledger into the event log")
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_migrate)

    s = sub.add_parser("checked", help="remember URLs already found closed, stale, filled, not a fit or blocked")
    s.add_argument("action", choices=["add", "has", "list"]); s.add_argument("--url")
    s.add_argument("--result", choices=CHECK_RESULTS); s.add_argument("--note"); s.set_defaults(fn=cmd_checked)

    s = sub.add_parser("ats", help="list postings from watch_companies' public job-board APIs")
    s.add_argument("--company"); s.add_argument("--match", help="comma-separated title words, e.g. cto,head,director")
    s.set_defaults(fn=cmd_ats)

    a = ap.parse_args()
    if a.cmd == "checked" and a.action in ("add", "has") and not a.url:
        ap.error("checked %s needs --url" % a.action)
    a.fn(a)


if __name__ == "__main__":
    main()
