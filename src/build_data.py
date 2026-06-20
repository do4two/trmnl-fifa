#!/usr/bin/env python3
"""
Fetch FIFA World Cup 2026 data (openfootball), compute group tables +
qualification flags, and emit the JSON payload that the TRMNL plugin consumes.

Usage:
  # write output/trmnl_data.json from the live openfootball feed
  python src/build_data.py

  # use a local cached copy instead of the network
  python src/build_data.py --matches data/worldcup.json --teams data/worldcup.teams.json

  # also POST it to a TRMNL private-plugin webhook (merge_variables)
  python src/build_data.py --webhook https://trmnl.com/api/custom_plugins/<uuid>

  # set the default favourite group baked into the payload (small layouts)
  python src/build_data.py --favorite C

The output shape (top-level keys become Liquid merge variables under polling,
or are wrapped in {"merge_variables": ...} for the webhook strategy):

  {
    "updated_at": "2026-06-19 21:30 UTC",
    "tournament": "World Cup 2026",
    "matches_played": 29, "matches_total": 72,
    "logic": "top2+third-elim",
    "favorite_group": "A",
    "groups": [ {"name":"A","teams":[ {row}, ... ]}, ... 12 ]
  }
"""
import argparse
import json
import shutil
import subprocess
import sys
import os
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import standings as S

OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026"
MATCHES_URL = OPENFOOTBALL + "/worldcup.json"
TEAMS_URL = OPENFOOTBALL + "/worldcup.teams.json"


def _fetch(url):
    """GET a URL via urllib, falling back to curl (some environments block
    Python's sockets but allow curl)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "trmnl-wm2026"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        if shutil.which("curl"):
            out = subprocess.run(
                ["curl", "-sSL", "--fail", "--max-time", "30", url],
                capture_output=True, text=True,
            )
            if out.returncode == 0 and out.stdout:
                return out.stdout
        raise RuntimeError("could not fetch %s: %s" % (url, e))


def _load(path_or_url):
    if path_or_url.startswith(("http://", "https://")):
        return json.loads(_fetch(path_or_url))
    with open(path_or_url, encoding="utf-8") as f:
        return json.load(f)


def build_payload(matches_src, teams_src, favorite="A"):
    matches_doc = _load(matches_src)
    teams = _load(teams_src)
    matches = matches_doc.get("matches", matches_doc) if isinstance(matches_doc, dict) else matches_doc

    groups = S.build_standings(teams, matches)

    gmatches = [m for m in matches if S.group_letter(m)]
    played = sum(1 for m in gmatches if S.is_played(m))

    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "tournament": matches_doc.get("name", "World Cup 2026") if isinstance(matches_doc, dict) else "World Cup 2026",
        "matches_played": played,
        "matches_total": len(gmatches),
        "logic": "top2+third-elim",
        "favorite_group": favorite.upper(),
        "groups": groups,
    }


def post_webhook(url, payload):
    body = json.dumps({"merge_variables": payload}).encode("utf-8")
    size = len(body)
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Webhook %s -> HTTP %s (%d bytes sent)" % (url, r.status, size))
    if size > 2048:
        print("WARNING: payload is %d bytes; free TRMNL webhook limit is 2KB "
              "(5KB for TRMNL+). Prefer the Polling strategy for the full feed."
              % size, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matches", default=MATCHES_URL, help="path or URL to worldcup.json")
    ap.add_argument("--teams", default=TEAMS_URL, help="path or URL to worldcup.teams.json")
    ap.add_argument("--favorite", default="A", help="default favourite group (A-L)")
    ap.add_argument("--out", default="output/trmnl_data.json", help="output JSON path")
    ap.add_argument("--webhook", help="TRMNL private-plugin webhook URL to POST to")
    args = ap.parse_args()

    payload = build_payload(args.matches, args.teams, args.favorite)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    qualified = sum(1 for g in payload["groups"] for t in g["teams"] if t["qualified"])
    eliminated = sum(1 for g in payload["groups"] for t in g["teams"] if t["eliminated"])
    print("Wrote %s  (%d/%d group games played, %d teams clinched top-2, %d eliminated)"
          % (args.out, payload["matches_played"], payload["matches_total"],
             qualified, eliminated))

    if args.webhook:
        post_webhook(args.webhook, payload)


if __name__ == "__main__":
    main()
