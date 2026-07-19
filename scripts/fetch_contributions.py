"""Scrape the public contribution calendar into data/contributions.json.

    python scripts/fetch_contributions.py [username]

Uses https://github.com/users/<user>/contributions, which is public HTML and
needs no token. Falls back to keeping the previous JSON if the fetch fails,
so a flaky network never blanks the README.
"""

import json
import pathlib
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

USER = "bhanuprasadhere"
URL = "https://github.com/users/{user}/contributions"
OUT = pathlib.Path("data/contributions.json")


def fetch(user):
    r = requests.get(
        URL.format(user=user),
        headers={"User-Agent": f"{user}-profile-readme", "Accept": "text/html"},
        timeout=30,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Counts live in <tool-tip for="cell-id">N contributions on ...</tool-tip>.
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}

    days = []
    for td in soup.select("td[data-date]"):
        text = tips.get(td.get("id"), "") or td.get("aria-label", "") or td.get_text(" ", strip=True)
        m = re.search(r"(\d+)\s+contribution", text)
        no = re.search(r"\bNo contributions\b", text, re.I)
        count = 0 if no else (int(m.group(1)) if m else 0)
        days.append({
            "date": td["data-date"],
            "count": count,
            "level": int(td.get("data-level") or 0),
        })

    if not days:
        raise RuntimeError("no contribution cells found - GitHub markup may have changed")

    days.sort(key=lambda d: d["date"])
    return {
        "user": user,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": sum(d["count"] for d in days),
        "days": days,
    }


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else USER
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = fetch(user)
    except Exception as exc:
        if OUT.exists():
            print(f"fetch failed ({exc}); keeping existing {OUT}")
            raise SystemExit(0)
        raise
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT}: {len(data['days'])} days, {data['total']} contributions")
