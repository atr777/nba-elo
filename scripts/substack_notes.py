"""Substack Notes client: post ONE note to secondbounce.substack.com.

Substack has no official Notes API. Notes are "comments" with no parent post;
the working endpoint is POST /api/v1/comment/draft with a TipTap-style bodyJson.
Auth is the same cookie the draft pusher uses (SUBSTACK_COOKIES_STRING in .env).

SAFETY: posting is public and irreversible. Nothing is sent without --live.
Without it you get the exact payload printed and nothing leaves the machine.

Usage:
    python scripts/substack_notes.py --text "A note." --dry-run
    python scripts/substack_notes.py --text "A note." --live

Normally you do not call this directly. `drip_notes.py` is the scheduled path;
it adds the approval gate, rate limits and the posting window.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Notes are published on substack.com itself, not the publication subdomain, and the
# path is /comment/feed. Posting to the subdomain's /comment/draft answered HTTP 500
# with an empty error body (2026-07-26). `attachmentIds` must be present even when
# empty; omitting it was the other half of that 500.
NOTE_ENDPOINT = "https://substack.com/api/v1/comment/feed"

# Brand rules that are cheap to enforce mechanically (docs/growth/BRAND.md).
EM_DASH = "—"
PLACEHOLDER = re.compile(r"\[[^\]]{2,40}\]")  # [TEAM], [FA post URL], ...
MAX_CHARS = 2800  # Notes have no hard cap; this catches runaway input.


class NoteRejected(Exception):
    """Content failed a house rule. Never auto-fix; a human rewrites it."""


class NotePostFailed(Exception):
    """A send did not complete. `certainly_not_posted` distinguishes the two cases
    that matter for a public, irreversible action:

      True  -> Substack answered with an error, so nothing was published and the
               note is safe to retry.
      False -> we never saw a usable answer (connection dropped, timeout). The note
               MAY be live. Never retry automatically; a human checks the feed.
    """

    def __init__(self, msg: str, certainly_not_posted: bool):
        super().__init__(msg)
        self.certainly_not_posted = certainly_not_posted


def validate(text: str) -> None:
    t = (text or "").strip()
    if not t:
        raise NoteRejected("empty note")
    if len(t) > MAX_CHARS:
        raise NoteRejected(f"note is {len(t)} chars (limit {MAX_CHARS})")
    if EM_DASH in t:
        raise NoteRejected("contains an em dash (house rule: never)")
    hit = PLACEHOLDER.search(t)
    if hit:
        raise NoteRejected(f"unfilled placeholder {hit.group(0)!r}")
    if "73.5" in t:
        raise NoteRejected("mentions 73.5% (the retracted number; never quote it)")


def build_body_json(text: str) -> dict:
    """TipTap doc. Blank lines separate paragraphs; single newlines are kept as
    hard breaks so a note reads on Substack the way it reads in the bank."""
    content = []
    for block in text.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        nodes = []
        for i, line in enumerate(block.split("\n")):
            if i:
                nodes.append({"type": "hardBreak"})
            if line:
                nodes.append({"type": "text", "text": line})
        content.append({"type": "paragraph", "content": nodes})
    if not content:
        raise NoteRejected("note produced no paragraphs")
    return {"type": "doc", "attrs": {"schemaVersion": "v1"}, "content": content}


def build_payload(text: str) -> dict:
    return {
        "bodyJson": build_body_json(text),
        "attachmentIds": [],  # required field; images/links would populate it
        "tabId": "for-you",
        "surface": "feed",
        "replyMinimumRole": "everyone",
    }


def get_session():
    load_dotenv(ROOT / ".env")
    cookies = os.getenv("SUBSTACK_COOKIES_STRING")
    if not cookies:
        sys.exit("SUBSTACK_COOKIES_STRING missing from .env")
    from substack import Api

    api = Api(cookies_string=cookies,
              publication_url="https://secondbounce.substack.com")
    return api._session


def post_note(text: str, live: bool = False) -> dict:
    """Validate, then (only if live) publish. Returns a result dict.

    On success returns {"posted": True, "id": ..., "url": ...}.
    """
    validate(text)
    payload = build_payload(text)
    if not live:
        return {"posted": False, "dry_run": True, "payload": payload}

    import requests

    try:
        r = get_session().post(NOTE_ENDPOINT, json=payload, timeout=45)
    except requests.RequestException as e:
        # No usable response. The request may or may not have reached Substack.
        raise NotePostFailed(f"no response: {type(e).__name__}: {e}",
                             certainly_not_posted=False)

    if r.status_code >= 400:
        raise NotePostFailed(f"HTTP {r.status_code}: {r.text[:200]}",
                             certainly_not_posted=True)

    # From here the note IS published. Nothing below may raise, or a caller could
    # conclude the send failed and post it a second time.
    data = {}
    try:
        if r.content:
            data = r.json() or {}
    except ValueError:
        data = {}
    nid = data.get("id") or (data.get("comment") or {}).get("id")
    url = f"https://substack.com/@secondbounce/note/c-{nid}" if nid else None
    return {"posted": True, "id": nid, "url": url,
            "http_status": r.status_code, "raw": data}


def main() -> None:
    p = argparse.ArgumentParser(description="Post one Substack Note")
    p.add_argument("--text", required=True)
    p.add_argument("--live", action="store_true",
                   help="actually publish (default is dry run)")
    p.add_argument("--dry-run", action="store_true", help="explicit no-op default")
    a = p.parse_args()

    try:
        res = post_note(a.text, live=a.live and not a.dry_run)
    except NoteRejected as e:
        sys.exit(f"REJECTED: {e}")

    if res.get("dry_run"):
        print("DRY RUN, nothing sent. Payload:")
        print(json.dumps(res["payload"], indent=2)[:1500])
        print("\nAdd --live to publish.")
    else:
        print(f"POSTED: {res.get('url') or res.get('id')}")


if __name__ == "__main__":
    main()
