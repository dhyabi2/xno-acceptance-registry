#!/usr/bin/env python3
"""request_count.py - how many DISTINCT accounts have asked for XNO at each seller (the live count to link in a follow-up).

Reads public GitHub issues labelled `wanted-in-xno` on this repo (no token needed for a public repo; GITHUB_TOKEN is
used if set, for rate limits). A requester is a GitHub login that opened such an issue or reacted +1 to one, counted
ONCE per seller host. The project's own accounts and bots are excluded, and nothing is seeded: with no issues the
count is 0 and the page says 0.

    python3 request_count.py                 # prints WANTED-IN-XNO.md to stdout
    python3 request_count.py --json          # machine-readable
    python3 request_count.py --repo OWNER/REPO --exclude login ...
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request

REPO = "dhyabi2/xno-acceptance-registry"
EXCLUDE = {"dhyabi2"}


def get(path, repo_api="https://api.github.com"):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "xno-request-count"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    h["Accept"] = "application/vnd.github+json, application/vnd.github.squirrel-girl-preview+json"
    with urllib.request.urlopen(urllib.request.Request(repo_api + path, headers=h), timeout=30) as r:
        return json.load(r)


def seller_host(body):
    m = re.search(r"###\s*Seller URL\s*\n+\s*(\S+)", body or "")
    if not m:
        return None
    u = m.group(1).strip().strip("<>")
    if "://" not in u:
        u = "https://" + u
    h = urllib.parse.urlparse(u).hostname
    return h.lower().removeprefix("www.") if h else None


def is_bot(user):
    return (user or {}).get("type") == "Bot" or (user or {}).get("login", "").endswith("[bot]")


def count(issues, reactions_for, exclude=EXCLUDE):
    """issues: list of GitHub issue dicts; reactions_for(number) -> list of reaction dicts."""
    out = {}
    for i in issues:
        if "pull_request" in i or "wanted-in-xno" not in {l["name"] for l in i.get("labels", [])}:
            continue
        host = seller_host(i.get("body"))
        if not host:
            continue
        d = out.setdefault(host, {"requesters": set(), "issues": []})
        d["issues"].append(i["html_url"])
        who = [i["user"]]
        who += [r["user"] for r in reactions_for(i["number"]) if r.get("content") == "+1"]
        for u in who:
            if u and u.get("login") and u["login"].lower() not in {e.lower() for e in exclude} and not is_bot(u):
                d["requesters"].add(u["login"])
    return {h: {"distinct_requesters": len(v["requesters"]), "issues": v["issues"]} for h, v in sorted(out.items())}


def render(c, repo=REPO):
    t = sum(v["distinct_requesters"] for v in c.values())
    L = ["# Wanted in XNO: sellers people asked to take Nano", "",
         "Distinct GitHub accounts that asked for XNO at each seller, counted from public issues. One account counts once per seller. "
         "Nothing here is seeded, paid for or promised; the project's own account is excluded. Count today: **%d** across **%d** sellers." % (t, len(c)), "",
         "| Seller host | Distinct requesters | Requests |", "|---|---|---|"]
    for h, v in c.items():
        L.append("| %s | %d | %s |" % (h, v["distinct_requesters"], ", ".join("[#%s](%s)" % (u.rsplit("/", 1)[1], u) for u in v["issues"])))
    if not c:
        L.append("| (none yet) | 0 | |")
    L += ["", "Ask for XNO at a seller: [open a request](https://github.com/%s/issues/new?template=request-xno-at-seller.yml). "
          "Already asked for? React +1 on that issue." % repo]
    return "\n".join(L) + "\n"


def fetch(repo):
    issues, page = [], 1
    while True:
        b = get("/repos/%s/issues?state=all&labels=wanted-in-xno&per_page=100&page=%d" % (repo, page))
        issues += b
        if len(b) < 100:
            return issues
        page += 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--exclude", action="append", default=[])
    a = ap.parse_args()
    c = count(fetch(a.repo), lambda n: get("/repos/%s/issues/%d/reactions?per_page=100" % (a.repo, n)), EXCLUDE | set(a.exclude))
    print(json.dumps(c, indent=1) if a.json else render(c, a.repo), end="")
