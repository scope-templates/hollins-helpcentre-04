"""Weekly themes from the desk, the quick way.

Pulls fifty tickets at random from the last seven days (or from the whole history with --all), sends them to
the model in one go and prints the themes it finds with rough counts. Set OPENAI_API_KEY; the model is
REVIEW_MODEL or gpt-4o-mini. Run it on a Monday and paste the output into the desk channel.
"""
import argparse
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "hollins.json"
SAMPLE = 50


def main(argv=None):
    parser = argparse.ArgumentParser(description="Themes in a sample of this week's tickets.")
    parser.add_argument("--all", action="store_true", help="sample from the whole history, not the last seven days")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)

    history = json.loads(DATA.read_text(encoding="utf-8"))
    tickets = history["tickets"]
    if not args.all:
        latest = max(datetime.fromisoformat(t["opened_at"].replace("Z", "+00:00")) for t in tickets)
        since = latest - timedelta(days=args.days)
        tickets = [t for t in tickets if datetime.fromisoformat(t["opened_at"].replace("Z", "+00:00")) >= since]
    picked = random.sample(tickets, min(SAMPLE, len(tickets)))

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("set OPENAI_API_KEY", file=sys.stderr)
        return 2
    text = "\n\n".join(f"#{t['number']} [{t['subject']}] {t['message']}" for t in picked)
    prompt = (
        "These are support tickets from a staff rota product. Group them into the main themes, give each theme a "
        "name, a count and one example ticket number, and list them from most to least common.\n\n" + text
    )
    body = json.dumps({"model": os.environ.get("REVIEW_MODEL", "gpt-4o-mini"),
                       "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode())
    print(f"{len(picked)} tickets sampled from {len(tickets)}\n")
    print(out["choices"][0]["message"]["content"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
