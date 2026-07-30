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


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def local_images(markdown: str, md_path: Path) -> list[tuple[str, Path]]:
    """Every local image the post references, resolved against the POST FILE.

    Resolving against the post rather than the cwd is the whole point. Our posts write
    `assets/foo.png`, which is relative to the post; the substack library passes the
    string straight to os.path.exists() and wraps the upload in
    `except Exception: pass`. Run from the repo root, that path does not exist, the
    failure was swallowed, and the 2026-07-29 essay reached Substack with both images
    invisible. Aaron found it in the draft, which is exactly the wrong place to find it.
    """
    out = []
    for alt, src in IMAGE_RE.findall(markdown):
        src = src.strip()
        if re.match(r"^(https?:)?//", src) or src.startswith("data:"):
            continue
        out.append((src, (md_path.parent / src).resolve()))
    return out


def upload_images(markdown: str, md_path: Path) -> tuple[str, int]:
    """Upload local images OURSELVES, then rewrite the markdown to hosted URLs.

    Not just a path fix. api.get_image() hardcodes `data:image/jpeg;base64`
    regardless of the file, and a JPEG round-trip visibly softens small text, which
    is most of what our charts are: axis labels, a monospace receipt strip, direct
    series labels. substack_notes.upload_image already derives the mime from the
    extension for exactly this reason, so reuse it and hand the library an http URL
    it will leave alone.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from substack_notes import upload_image

    replacements: dict[str, str] = {}
    for src, path in local_images(markdown, md_path):
        if src in replacements:
            continue
        hosted = upload_image(path)
        if not str(hosted).startswith("http"):
            sys.exit(f"upload of {path.name} returned no usable URL: {hosted!r}")
        print(f"  uploaded {path.name} ({path.stat().st_size / 1024:.0f}KB) "
              f"as {path.suffix.lstrip('.').upper()}")
        replacements[src] = hosted

    def repl(m):
        alt, src = m.group(1), m.group(2).strip()
        return f"![{alt}]({replacements.get(src, src)})"

    return IMAGE_RE.sub(repl, markdown), len(replacements)


def check_inline_fidelity(markdown: str) -> list[tuple[int, str]]:
    """Find lines the library's inline parser would duplicate.

    Emphasis wrapping any other inline construct is broken upstream: for
    `*text with a [link](url)*` parse_inline emits the whole span ONCE as raw
    markdown and then emits the inner tokens AGAIN, so the sentence appears twice in
    the published post. Verified 2026-07-29 across italic+code, italic+link and
    bold+link; emphasis around plain text is fine, and code plus a link with no
    emphasis is fine.

    Cheaper to detect than to fix in the library, and the failure is silent
    otherwise: it looks correct in the markdown and wrong only in the draft.
    """
    from substack.post import parse_inline

    bad = []
    for i, line in enumerate(markdown.split("\n"), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("!") or s.startswith("```"):
            continue
        try:
            rendered = "".join(t.get("content", "") for t in parse_inline(s))
        except Exception:
            continue
        if len(rendered) > len(s):
            bad.append((i, s))
    return bad


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

    md_path = Path(args.markdown_file).resolve()
    markdown = md_path.read_text(encoding="utf-8")

    # PREFLIGHT. Both classes of bug below shipped silently once; neither is visible
    # in the markdown, only in the finished draft.
    problems = check_inline_fidelity(markdown)
    if problems:
        print("Refusing to push: these lines would be DUPLICATED by Substack's "
              "inline parser.\nEmphasis cannot wrap a link or `code`. Unwrap the "
              "emphasis, or drop the link.\n")
        for line_no, text in problems:
            print(f"  line {line_no}: {text[:100]}")
        sys.exit(1)

    missing = [p for _, p in local_images(markdown, md_path) if not p.exists()]
    if missing:
        print("Refusing to push: image(s) referenced by the post do not exist, and "
              "the library would silently publish a dead link.\n")
        for p in missing:
            print(f"  {p}")
        sys.exit(1)

    markdown, n_uploaded = upload_images(markdown, md_path)

    title, body = extract_title(markdown)
    if args.title:
        title, body = args.title, markdown
    if not title:
        sys.exit("No --title given and no '# ' heading found in the file.")

    api = get_api()
    post = Post(title=title, subtitle=args.subtitle, user_id=api.get_user_id())
    post.from_markdown(body, api=api)

    # Confirm every image in the built body really points at a hosted URL. The src
    # lives at content[0].attrs.src on a captionedImage, NOT at the top level, so
    # walk for it rather than guessing the shape. Checked BEFORE the draft is
    # created, so a failure leaves nothing behind to clean up.
    def srcs(node):
        if isinstance(node, dict):
            if node.get("type") == "image2":
                yield (node.get("attrs") or {}).get("src")
            for v in node.values():
                yield from srcs(v)
        elif isinstance(node, list):
            for v in node:
                yield from srcs(v)

    found = list(srcs(post.draft_body))
    unhosted = [s for s in found if not str(s).startswith("http")]
    if unhosted:
        print("Refusing to push: image(s) did not become hosted URLs:\n")
        for src in unhosted:
            print(f"  {src!r}")
        sys.exit(1)
    if len(found) != n_uploaded:
        print(f"Refusing to push: uploaded {n_uploaded} image(s) but the built body "
              f"contains {len(found)}. An image reference was dropped, most likely "
              f"because it is not on its own line.")
        sys.exit(1)
    print(f"  {len(found)} image(s) present in the draft body")

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
