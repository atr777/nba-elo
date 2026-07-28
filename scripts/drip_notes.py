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
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substack_notes import (  # noqa: E402
    NotePostFailed,
    NoteRejected,
    post_note,
    validate,
)

ROOT = Path(__file__).resolve().parent.parent
# Env overrides exist so tests can point at scratch files; production uses defaults.
QUEUE = Path(os.environ.get("NOTES_QUEUE", ROOT / "data/manual/notes_queue.yaml"))
LEDGER = Path(os.environ.get("NOTES_LEDGER", ROOT / "data/exports/notes_posted.json"))
LOG = ROOT / "logs/notes_drip.log"

MAX_PER_DAY = 2
MIN_GAP_HOURS = 5

# THIS RUNS ON AARON'S PC, NOT THE VPS. Substack refuses note-writing POSTs from the
# VPS: verified 2026-07-26, the identical request returns 400 (accepted, needs
# content) from a residential IP and 403 with an HTML error page from the datacenter
# IP, regardless of headers, while GETs from the VPS still return 200. Getting around
# that would mean evading their bot protection and risking the account, so the drip
# moved hosts instead.
#
# The PC is only on intermittently, so this is a broad window with a rate limit
# rather than fixed hour slots: whenever the task fires inside good ET hours, it
# posts if the daily cap and the gap allow. That yields up to MAX_PER_DAY notes a
# day, at least MIN_GAP_HOURS apart, and it self-heals when the PC was off at any
# particular hour. Window is half-open, [lo, hi).
WINDOW_ET = [(9, 21)]
ET_ZONE = "America/New_York"  # zoneinfo handles EDT/EST; the season spans both


def log(msg: str) -> None:
    """Never raises. Logging is bookkeeping, and bookkeeping must not be able to
    stop, or half-finish, a public irreversible action.

    This was not hypothetical. The .bat used to redirect python into this same
    file, cmd's `>>` holds an exclusive write handle, and so every scheduled run
    died here with PermissionError on the first call. 22 crashed runs, no notes
    posted by the scheduler at all. The redirect is fixed in run_notes_drip.bat;
    this is the belt to that braces, because the failure mode is silent and the
    worst version of it lands mid-send.
    """
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as e:
        line += f"   (WARNING: could not write {LOG.name}: {e})"
    try:
        print(line)
    except (OSError, ValueError, AttributeError):
        # No usable stdout: pythonw.exe, or a closed/redirected handle.
        pass


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
    """Real ET, so this behaves the same on the ET server and on Aaron's PC in
    Guatemala, and does not drift an hour when the season crosses EST/EDT."""
    return datetime.now(timezone.utc).astimezone(ZoneInfo(ET_ZONE))


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


def _portrait_warning(image: str) -> str | None:
    """Feed images want 4:5 portrait (1080x1350): it occupies ~25% more mobile screen
    than a square and materially outperforms landscape. Our chart house style is
    landscape because it was built for the newsletter, so flag it rather than block."""
    try:
        from PIL import Image
    except ImportError:
        return None
    path = Path(image)
    if not path.is_absolute():
        path = ROOT / path
    try:
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        return None
    if h and w / h > 1.05:
        return (f"{w}x{h} is landscape (ratio {w/h:.2f}); portrait 4:5 (1080x1350) "
                f"performs better in the feed")
    return None


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
    image = item.get("image") or None
    link = item.get("link") or None

    try:
        if image and link:
            raise NoteRejected("has both an image and a link; pick one")
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
        extra = (f" + image {image}" if image
                 else f" + link card {link}" if link else " (text only)")
        log(f"DRY RUN ({why}). Would post {nid}: {text[:90]!r}{extra}")
        log("Add --live to publish.")
        return

    # Write-ahead: claim the id BEFORE sending. If this process dies mid-send, the
    # claim survives and the next cron skips the note instead of double-posting to
    # a public feed. Posting twice is worse than not posting.
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    led[nid] = {"state": "sending", "at": stamp, "text": text[:120]}
    save_ledger(led)

    if image:
        warn = _portrait_warning(image)
        if warn:
            log(f"NOTE on {nid} image: {warn}")

    try:
        res = post_note(text, live=True, image=image, link=link)
    except NotePostFailed as e:
        if e.certainly_not_posted:
            # Substack rejected it, so nothing is live. Release the claim to retry.
            led.pop(nid, None)
            save_ledger(led)
            log(f"NOT POSTED {nid} (safe to retry): {e}")
        else:
            led[nid] = {"state": "unknown", "at": stamp, "error": str(e)[:200],
                        "text": text[:120]}
            save_ledger(led)
            log(f"UNKNOWN outcome for {nid}: {e}. It may be live. Left claimed so "
                f"it is NOT retried. Check the feed, then delete its entry from "
                f"{LEDGER.name} if it never posted.")
        raise SystemExit(1)
    except Exception as e:  # unexpected: keep the claim, do not risk a repeat
        led[nid] = {"state": "unknown", "at": stamp,
                    "error": f"{type(e).__name__}: {str(e)[:180]}", "text": text[:120]}
        save_ledger(led)
        log(f"UNEXPECTED error posting {nid}: {type(e).__name__}: {str(e)[:200]}. "
            f"Left claimed; check the feed before clearing it.")
        raise SystemExit(1)

    led[nid] = {"posted_at": stamp, "note_url": res.get("url"),
                "http_status": res.get("http_status"), "text": text[:120],
                "image": image, "link": link}
    save_ledger(led)
    log(f"POSTED {nid} -> {res.get('url') or 'live (no id in response)'}")


if __name__ == "__main__":
    main()
