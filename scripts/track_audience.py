"""Record a dated snapshot of audience and engagement to data/exports/audience_history.csv.

WHY THIS EXISTS. After the paid tier was blocked (Stripe does not support Guatemala),
audience size became the only revenue KPI. It was also the one number nobody was
recording, and Substack will not give it to us: as of 2026-07-29
/api/v1/publication/subscriber_count and /api/v1/publication/stats both answer 403
with our cookie, the rendered profile page loads its counts client-side so there is
nothing to scrape, and /api/v1/user/profile/self reports followerCount 0 and
subscriberCountNumber 0, which is not obviously true and not obviously false. So the
subscriber number is HUMAN INPUT, passed with --subscribers, and every row records
where its numbers came from.

What IS machine readable, and is collected automatically:
  * per-note likes / restacks / replies, from the reader profile feed
  * per-post reactions / comments, from the public archive

    python scripts/track_audience.py                      # collect + show the trend
    python scripts/track_audience.py --subscribers 47      # ...and record what Aaron
                                                          #    read off the dashboard
    python scripts/track_audience.py --show               # print history, collect nothing

READ RESTACKS FIRST. Likes are flattery; restacks are the only mechanism by which a
note reaches anyone who does not already follow us. A week of likes with zero
restacks means the drip is talking to the room it already has.
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = ROOT / "data/exports/audience_history.csv"
PROFILE_ID = 104030246          # Second Bounce, from /api/v1/user/profile/self
ARCHIVE = "https://secondbounce.substack.com/api/v1/archive?sort=new&limit=50"
FEED = f"https://substack.com/api/v1/reader/feed/profile/{PROFILE_ID}"

FIELDS = ["date", "subscribers", "subscribers_source", "notes_posted", "note_likes",
          "note_restacks", "note_replies", "posts_published", "post_reactions",
          "post_comments"]


def collect_notes(session) -> dict:
    r = session.get(FEED, timeout=30)
    r.raise_for_status()
    items = (r.json() or {}).get("items") or []
    notes = [it["comment"] for it in items if it.get("comment")]
    return {
        "notes_posted": len(notes),
        "note_likes": sum(int(c.get("reaction_count") or 0) for c in notes),
        "note_restacks": sum(int(c.get("restacks") or 0) for c in notes),
        "note_replies": sum(int(c.get("children_count") or 0) for c in notes),
    }


def collect_posts() -> dict:
    """Public archive, no auth. Deliberately not the authenticated endpoint: this is
    the same view a reader gets, so it cannot flatter us with private numbers."""
    import requests

    r = requests.get(ARCHIVE, timeout=30)
    r.raise_for_status()
    posts = r.json() or []
    return {
        "posts_published": len(posts),
        "post_reactions": sum(sum((p.get("reactions") or {}).values()) for p in posts),
        "post_comments": sum(int(p.get("comment_count") or 0) for p in posts),
    }


def load_history() -> list:
    if not OUT.exists():
        return []
    with OUT.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save_row(row: dict) -> None:
    """One row per date. Re-running on the same day overwrites that day rather than
    appending a duplicate, so a trend never double-counts a day the PC ran twice.

    A same-day re-run KEEPS a subscriber count already recorded for that date. It is
    the one field a human had to read off a dashboard, so silently blanking it on the
    next automated run destroys the only number that cannot be re-collected. Ran into
    exactly that within an hour of writing the script.
    """
    history = load_history()
    prior = next((r for r in history if r.get("date") == row["date"]), None)
    if prior and not row.get("subscribers") and prior.get("subscribers"):
        row["subscribers"] = prior["subscribers"]
        row["subscribers_source"] = prior.get("subscribers_source", "")
    rows = [r for r in history if r.get("date") != row["date"]]
    rows.append({k: row.get(k, "") for k in FIELDS})
    rows.sort(key=lambda r: r["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def show(rows: list) -> None:
    if not rows:
        print("no history yet")
        return
    print(f"\n{'date':12s} {'subs':>6s} {'notes':>6s} {'likes':>6s} {'restk':>6s} "
          f"{'repl':>5s} {'posts':>6s} {'react':>6s}")
    for r in rows:
        print(f"{r['date']:12s} {r['subscribers'] or '?':>6s} {r['notes_posted']:>6s} "
              f"{r['note_likes']:>6s} {r['note_restacks']:>6s} {r['note_replies']:>5s} "
              f"{r['posts_published']:>6s} {r['post_reactions']:>6s}")
    if len(rows) >= 2:
        a, b = rows[0], rows[-1]
        def d(k):
            try:
                return int(b[k] or 0) - int(a[k] or 0)
            except ValueError:
                return 0
        print(f"\nchange over {len(rows)} snapshots ({a['date']} to {b['date']}): "
              f"likes {d('note_likes'):+d}, restacks {d('note_restacks'):+d}, "
              f"replies {d('note_replies'):+d}")
    last = rows[-1]
    if last["note_restacks"] in ("0", "") and int(last["notes_posted"] or 0) >= 5:
        print("\nFLAG: zero restacks across every note posted. Likes do not travel; "
              "restacks are what puts a note in front of someone who does not follow "
              "us yet. Nothing in the feed is currently reaching new people.")


def main() -> None:
    p = argparse.ArgumentParser(description="Snapshot audience + engagement")
    p.add_argument("--subscribers", type=int,
                   help="the number Aaron read off the Substack dashboard")
    p.add_argument("--show", action="store_true", help="print history, collect nothing")
    a = p.parse_args()

    if a.show:
        show(load_history())
        return

    from substack_notes import get_session

    row = {"date": date.today().isoformat()}
    row.update(collect_posts())
    row.update(collect_notes(get_session()))
    if a.subscribers is not None:
        row["subscribers"] = a.subscribers
        row["subscribers_source"] = "dashboard (manual)"
    else:
        # Carry the last known figure forward as blank rather than guessing: a wrong
        # KPI is worse than a missing one, and this is THE KPI.
        row["subscribers_source"] = "not read"

    save_row(row)
    print(f"recorded {row['date']} -> {OUT.relative_to(ROOT)}")
    show(load_history())


if __name__ == "__main__":
    main()
