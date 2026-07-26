"""Scheduled Substack Notes drip. Runs on the VPS from the daily cron.

The approval gate: this script will ONLY post a note whose `status` is exactly
`approved` in data/manual/notes_queue.yaml. Aaron approves; the machine drips.
Nothing else in the queue can go out, and nothing goes out without --live.

    python scripts/drip_notes.py                # dry run, shows the next note
    python scripts/drip_notes.py --live         # post if a slot is due
    python scripts/drip_notes.py --status       # queue summary, posts nothing

TWO FILES, ON PURPOSE:
  * data/manual/notes_queue.yaml  is the PLAN. Git-tracked, human-owned, and this
    script NEVER writes to it. That is what lets Aaron approve from his phone by
    editing it on GitHub while the VPS keeps pulling.
  * data/exports/notes_posted.json is the RECORD. VPS-local and gitignored. It is
    the single source of truth for what has already gone out, which also means an
    `approved` note is never posted twice even though its status never changes.
Earlier versions wrote status back into the queue; that fought with `git pull` over
the same lines and would have corrupted the phone-approval workflow.

Rate limits (docs/growth/CONTENT_SYSTEM.md says 1-3 Notes/day):
  MAX_PER_DAY, MIN_GAP_HOURS, and an ET posting window. The cron fires more
  often than we post; the script decides whether this firing is a slot.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substack_notes import NoteRejected, post_note, validate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Env overrides exist so tests can point at scratch files; production uses defaults.
QUEUE = Path(os.environ.get("NOTES_QUEUE", ROOT / "data/manual/notes_queue.yaml"))
LEDGER = Path(os.environ.get("NOTES_LEDGER", ROOT / "data/exports/notes_posted.json"))
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


def load_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        # A corrupt ledger must never cause a re-post spree. Fail loudly instead.
        raise SystemExit(f"{LEDGER} is not valid JSON; refusing to run")


def save_ledger(led: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=2, sort_keys=True), encoding="utf-8")


def now_et() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ET_OFFSET)


def in_window(dt_et: datetime) -> bool:
    return any(lo <= dt_et.hour < hi for lo, hi in WINDOW_ET)


def sent_times(led: dict) -> list:
    out = []
    for rec in led.values():
        ts = rec.get("posted_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            out.append(dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))
        except ValueError:
            pass
    return out


def gate(led: dict, force: bool) -> tuple[bool, str]:
    """Should this firing post? Returns (ok, reason)."""
    done = sent_times(led)
    today = [d for d in done
             if d.astimezone(timezone.utc).date() == datetime.now(timezone.utc).date()]
    if force:
        return True, "forced (--force), skipping window and gap checks"
    et = now_et()
    if not in_window(et):
        return False, f"outside posting window (now {et:%H:%M} ET)"
    if len(today) >= MAX_PER_DAY:
        return False, f"daily cap reached ({len(today)}/{MAX_PER_DAY})"
    if done:
        gap = (datetime.now(timezone.utc) - max(done)).total_seconds() / 3600
        if gap < MIN_GAP_HOURS:
            return False, f"only {gap:.1f}h since last note (min {MIN_GAP_HOURS}h)"
    return True, "slot is due"


def next_approved(items: list, led: dict):
    """First approved note not already handled. Ledger, not queue status, is what
    stops a repeat, because the queue is read-only to this script."""
    for it in items:
        if it.get("status") == "approved" and str(it.get("id")) not in led:
            return it
    return None


def summary(items: list, led: dict) -> str:
    counts = {}
    for it in items:
        st = it.get("status", "?")
        if str(it.get("id")) in led:
            st = f"{st}/done"
        counts[st] = counts.get(st, 0) + 1
    return ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "empty"


def main() -> None:
    p = argparse.ArgumentParser(description="Drip approved Substack Notes")
    p.add_argument("--live", action="store_true", help="actually publish")
    p.add_argument("--force", action="store_true",
                   help="ignore window/gap/cap (still requires approved status)")
    p.add_argument("--status", action="store_true", help="print state only")
    a = p.parse_args()

    items = load_queue()
    led = load_ledger()

    if a.status:
        print(f"queue : {QUEUE}")
        print(f"ledger: {LEDGER} ({len(led)} recorded)")
        print(f"counts: {summary(items, led)}")
        nxt = next_approved(items, led)
        print(f"next up: {nxt['id'] if nxt else 'NONE'}")
        et = now_et()
        print(f"now {et:%Y-%m-%d %H:%M} ET, in window: {in_window(et)}")
        ok, why = gate(led, False)
        print(f"would post now: {ok} ({why})")
        return

    if not items:
        log(f"queue empty or missing ({QUEUE}); nothing to do")
        return

    ok, why = gate(led, a.force)
    if not ok:
        log(f"no post this run: {why}")
        return

    item = next_approved(items, led)
    if not item:
        log(f"nothing approved and unsent (queue: {summary(items, led)})")
        return

    nid = str(item.get("id"))
    text = str(item.get("text", "")).strip()

    try:
        validate(text)
    except NoteRejected as e:
        # Record it so a bad note is not retried on all five daily crons.
        led[nid] = {"rejected": str(e),
                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        save_ledger(led)
        log(f"REJECTED {nid}: {e} (recorded, not posted; fix the text and change "
            f"its id to retry)")
        return

    if not a.live:
        log(f"DRY RUN ({why}). Would post {nid}: {text[:90]!r}")
        log("Add --live to publish.")
        return

    try:
        res = post_note(text, live=True)
    except Exception as e:  # network/API failure: no ledger write, retry next cron
        log(f"FAILED to post {nid}: {type(e).__name__}: {str(e)[:200]}")
        raise SystemExit(1)

    led[nid] = {"posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "note_url": res.get("url"), "text": text[:120]}
    save_ledger(led)
    log(f"POSTED {nid} -> {res.get('url') or res.get('id')}")


if __name__ == "__main__":
    main()
