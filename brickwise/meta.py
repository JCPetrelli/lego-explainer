"""<head> tags shared by build pages and galleries: link previews and the tab icon."""

import html
import re

# A red 2x1 brick with two studs, inline so pages stay self-contained.
FAVICON = (
    "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect x='3' y='12' width='26' height='16' rx='2' fill='%23c91a09'/>"
    "<rect x='7' y='6' width='7' height='7' rx='1.5' fill='%23c91a09'/>"
    "<rect x='18' y='6' width='7' height='7' rx='1.5' fill='%23c91a09'/></svg>"
)


def check_url(url, what):
    if url and not re.match(r"https?://", url):
        raise ValueError(f"{what} must start with http:// or https://, got {url!r}")


def head_tags(title, description, og_image=None):
    """Description, Open Graph and Twitter card tags plus the favicon, one per line."""
    check_url(og_image, "og image")
    t, d = html.escape(title), html.escape(description)
    tags = [
        f'<meta name="description" content="{d}">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        '<meta property="og:type" content="website">',
        f'<meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}">',
        f'<link rel="icon" href="{FAVICON}">',
    ]
    if og_image:
        tags.insert(4, f'<meta property="og:image" content="{html.escape(og_image)}">')
    return "\n".join(tags)
