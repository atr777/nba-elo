"""Scheduled Substack Notes drip. Runs on the VPS from the daily cron.

The approval gate: this script will ONLY post a note whose `status` is exactly
`approved` in data/manual/notes_queue.yaml. Aaron approves; the machine drips.
Nothing else in the queue can go out, and nothing goes out without --live.

    python scripts/drip_notes.py                # dry run, shows the next note
    python scripts/drip_notes.py --live         # post if a slot is due
    python scripts/drip_notes.py --status       # queue summary, posts nothing

Rate limits (docs/growth/CONTENT_SYSTEM.md says 1-3 Notes/day):
  MAX_PER_DAY, MIN_GAP_HOURS, and an ET posting window. The cron fires more
  often than we post; the script decides whether this firing is a slot.

State lives in the queue file itself (status/posted_at/note_url per item), so
the queue is both the plan and the record. No second source of truth.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substack_notes import NoteRejected, post_note, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# NOTES_QUEUE lets tests point at a scratch queue; production uses the default.
QUEUE = Path(os.environ.get("NOTES_QUEUE", ROOT / "data/manual/notes_queue.yaml"))
LOG = ROOT / "logs/notes_drip.log"

MAX_PER_DAY = 2
MIN_GAP_HOURS = 5
# ET hours in which a note may go out. Sports audience peaks 7-10PM ET, with a
# morning slot; ET = UTC-4 in season (EDT).
WINDOW_ET = [(9, 11), (13, 14), (19, 22)]
ET_OFFSET = -4


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def load_queue() -> list:
    if not QUEUE.exists():
        return []
    data = yaml.safe_load(QUEUE.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise SystemExit(f"{QUEUE} must be a YAML list")
    return data


def save_queue(items: list) -> None:
    QUEUE.write_text(
        yaml.safe_dump(items, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def now_et() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ET_OFFSET)


def in_window(dt_et: datetime) -> bool:
    return any(lo <= dt_et.hour < hi for lo, hi in WINDOW_ET)


def posted_items(items: list) -> list:
    out = []
    for it in items:
        ts = it.get("posted_at")
        if it.get("status") == "posted" and ts:
            try:
                out.append(datetime.fromisoformat(str(ts).replace("Z", "+00:00")))
            except ValueError:
                pass
    return out


def gate(items: list, force: bool) -> tuple[bool, str]:
    """Should this firing post? Returns (ok, reason)."""
    et = now_et()
    done = posted_items(items)
    today = [d for d in done if d.astimezone(timezone.utc).date()
             == datetime.now(timezone.utc).date()]
    if force:
        return True, "forced (--force), skipping window and gap checks"
    if not in_window(et):
        return False, f"outside posting window (now {et:%H:%M} ET)"
    if len(today) >= MAX_PER_DAY:
        return False, f"daily cap reached ({len(today)}/{MAX_PER_DAY})"
    if done:
        newest = max(done)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        gap = (datetime.now(timezone.utc) - newest).total_seconds() / 3600
        if gap < MIN_GAP_HOURS:
            return False, f"only {gap:.1f}h since last note (min {MIN_GAP_HOURS}h)"
    return True, "slot is due"


def next_approved(items: list):
    for it in items:
        if it.get("status") == "approved":
            return it
    return None


def summary(items: list) -> str:
    counts = {}
    for it in items:
        counts[it.get("status", "?")] = counts.get(it.get("status", "?"), 0) + 1
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "empty"


def main() -> None:
    p = argparse.ArgumentParser(description="Drip approved Substack Notes")
    p.add_argument("--live", action="store_true", help="actually publish")
    p.add_argument("--force", action="store_true",
                   help="ignore window/gap/cap (still requires approved status)")
    p.add_argument("--status", action="store_true", help="print queue state only")
    a = p.parse_args()

    items = load_queue()
    if a.status:
        print(f"queue: {QUEUE}")
        print(f"counts: {summary(items)}")
        nxt = next_approved(items)
        print(f"next approved: {nxt['id'] if nxt else 'NONE'}")
        et = now_et()
        print(f"now {et:%Y-%m-%d %H:%M} ET, in window: {in_window(et)}")
        ok, why = gate(items, False)
        print(f"would post now: {ok} ({why})")
        return

    if not items:
        log(f"queue empty or missing ({QUEUE}); nothing to do")
        return

    ok, why = gate(items, a.force)
    if not ok:
        log(f"no post this run: {why}")
        return

    item = next_approved(items)
    if not item:
        log(f"no APPROVED notes waiting (queue: {summary(items)})")
        return

    text = str(item.get("text", "")).strip()
    try:
        validate(text)
    except NoteRejected as e:
        item["status"] = "rejected"
        item["rejected_reason"] = str(e)
        save_queue(items)
        log(f"REJECTED {item.get('id')}: {e} (status set to rejected, not posted)")
        return

    if not a.live:
        log(f"DRY RUN ({why}). Would post {item.get('id')}: {text[:90]!r}")
        log("Add --live to publish.")
        return

    try:
        res = post_note(text, live=True)
    except Exception as e:  # network/API failure: leave status alone, retry next cron
        log(f"FAILED to post {item.get('id')}: {type(e).__name__}: {str(e)[:200]}")
        raise SystemExit(1)

    item["status"] = "posted"
    item["posted_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    item["note_url"] = res.get("url")
    save_queue(items)
    log(f"POSTED {item.get('id')} -> {res.get('url') or res.get('id')}")


if __name__ == "__main__":
    main()
