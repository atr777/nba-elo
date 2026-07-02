"""Push a markdown file to Substack as a DRAFT on secondbounce.substack.com.

Drafts only by design — a human reviews and hits Publish in the Substack app.

Auth (in nba-elo-engine/.env or environment):
    SUBSTACK_EMAIL + SUBSTACK_PASSWORD   (set a password: substack.com -> Settings -> Account)
    or SUBSTACK_COOKIES_STRING           (fallback if password login hits a captcha)

Usage:
    python scripts/substack_push_draft.py data/exports/daily_newsletter.md
    python scripts/substack_push_draft.py post.md --title "Season Recap" --subtitle "73.5% in the books"
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from substack import Api
from substack.post import Post

PUBLICATION_URL = "https://secondbounce.substack.com"


def extract_title(markdown: str) -> tuple[str | None, str]:
    """Pull the first H1 out of the markdown to use as the post title."""
    match = re.search(r"^# (.+)$", markdown, flags=re.MULTILINE)
    if not match:
        return None, markdown
    body = markdown[: match.start()] + markdown[match.end() :]
    return match.group(1).strip(), body.strip()


def get_api() -> Api:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    email = os.getenv("SUBSTACK_EMAIL")
    password = os.getenv("SUBSTACK_PASSWORD")
    cookies = os.getenv("SUBSTACK_COOKIES_STRING")
    if cookies:
        return Api(cookies_string=cookies, publication_url=PUBLICATION_URL)
    if email and password:
        return Api(email=email, password=password, publication_url=PUBLICATION_URL)
    sys.exit(
        "No Substack credentials. Add SUBSTACK_EMAIL + SUBSTACK_PASSWORD "
        "(or SUBSTACK_COOKIES_STRING) to nba-elo-engine/.env"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown_file", help="Path to the markdown file to push")
    parser.add_argument("--title", help="Post title (default: first # heading in the file)")
    parser.add_argument("--subtitle", default="", help="Post subtitle")
    args = parser.parse_args()

    markdown = Path(args.markdown_file).read_text(encoding="utf-8")
    title, body = extract_title(markdown)
    if args.title:
        title, body = args.title, markdown
    if not title:
        sys.exit("No --title given and no '# ' heading found in the file.")

    api = get_api()
    post = Post(title=title, subtitle=args.subtitle, user_id=api.get_user_id())
    post.from_markdown(body, api=api)

    draft = api.post_draft(post.get_draft())
    draft_id = draft.get("id")
    print(f"Draft created: \"{title}\" (id {draft_id})")

    for tag in ("NBA", "basketball", "Sports Analytics", "NBA Predictions",
                "Statistics"):
        try:
            api.add_tag_to_post(draft_id, tag)
        except Exception:
            pass
    print("Standard tags applied.")
    print(f"Review and publish at: {PUBLICATION_URL}/publish/posts/drafts")


if __name__ == "__main__":
    main()
