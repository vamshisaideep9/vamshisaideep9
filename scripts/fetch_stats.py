#!/usr/bin/env python3
"""Fetches GitHub stats — including private and organisation work — into stats.json.

Needs a token for YOUR account in $GH_TOKEN (classic PAT: repo, read:org, read:user).
Only aggregate numbers are written: no repo names, no code, no commit messages.

Usage:  GH_TOKEN=... python scripts/fetch_stats.py
"""
import datetime as dt, json, os, sys, urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("METRICS_TOKEN")
IGNORE = {"jupyter notebook", "html", "css", "scss", "powershell", "batchfile", "makefile", "dockerfile", "shell", "procfile"}


def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if out.get("errors"):
        sys.exit(f"GraphQL error: {out['errors']}")
    return out["data"]


YEAR_Q = """query($from: DateTime!, $to: DateTime!) { viewer { contributionsCollection(from: $from, to: $to) {
  totalCommitContributions restrictedContributionsCount totalPullRequestContributions
  totalPullRequestReviewContributions totalIssueContributions
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }"""

REPO_Q = """query($after: String) { viewer { repositories(first: 100, after: $after, isFork: false,
  ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
  totalCount pageInfo { hasNextPage endCursor }
  nodes { stargazerCount isPrivate languages(first: 12, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } } } } }"""


def main():
    if not TOKEN:
        sys.exit("Set GH_TOKEN (or METRICS_TOKEN) to a token for your account.")
    me = gql("{ viewer { login createdAt pullRequests(states: MERGED) { totalCount } } }")["viewer"]

    # Contributions, one calendar year at a time (the API caps each window at a year).
    now = dt.datetime.now(dt.timezone.utc)
    start_year = int(me["createdAt"][:4])
    days, totals = {}, Counter()
    for y in range(start_year, now.year + 1):
        frm = dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc)
        to = min(dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc), now)
        c = gql(YEAR_Q, **{"from": frm.isoformat(), "to": to.isoformat()})["viewer"]["contributionsCollection"]
        totals["commits"] += c["totalCommitContributions"] + c["restrictedContributionsCount"]
        totals["prs"] += c["totalPullRequestContributions"]
        totals["reviews"] += c["totalPullRequestReviewContributions"]
        totals["issues"] += c["totalIssueContributions"]
        totals["contributions"] += c["contributionCalendar"]["totalContributions"]
        for w in c["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    ordered = sorted(days.items())
    today = now.date()
    # Streaks: today without a contribution yet doesn't break the current streak.
    longest = run = 0
    for _, n in ordered:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    for date, n in reversed(ordered):
        if n:
            current += 1
        elif date != today.isoformat():
            break

    last_year = [(d, n) for d, n in ordered if d > (today - dt.timedelta(days=371)).isoformat()]
    # Trim to whole weeks ending this week (Sun → Sat), 53 columns.
    while last_year and dt.date.fromisoformat(last_year[0][0]).weekday() != 6:
        last_year.pop(0)

    # Repositories + languages (owned, collaborator and org repos — public and private).
    langs, stars, repos, private, after = Counter(), 0, 0, 0, None
    while True:
        r = gql(REPO_Q, after=after)["viewer"]["repositories"]
        for n in r["nodes"]:
            repos += 1; stars += n["stargazerCount"]; private += n["isPrivate"]
            for e in n["languages"]["edges"]:
                if e["node"]["name"].lower() not in IGNORE:
                    langs[e["node"]["name"]] += e["size"]
        if not r["pageInfo"]["hasNextPage"]:
            break
        after = r["pageInfo"]["endCursor"]
    total = sum(langs.values()) or 1
    top = [{"name": k, "pct": round(v * 100 / total, 1)} for k, v in langs.most_common(7)]

    out = {
        "updated": now.strftime("%Y-%m-%d"),
        "since": start_year,
        "year_contributions": sum(n for _, n in last_year),
        "contributions": totals["contributions"],
        "commits": totals["commits"],
        "prs": totals["prs"],
        "prs_merged": me["pullRequests"]["totalCount"],
        "reviews": totals["reviews"],
        "issues": totals["issues"],
        "repos": repos,
        "private_repos": private,
        "stars": stars,
        "streak_current": current,
        "streak_longest": longest,
        "best_day": max((n for _, n in last_year), default=0),
        "languages": top,
        "calendar": [n for _, n in last_year],
        "calendar_start": last_year[0][0] if last_year else today.isoformat(),
    }
    with open(os.path.join(ROOT, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print({k: v for k, v in out.items() if k != "calendar"})


if __name__ == "__main__":
    main()
