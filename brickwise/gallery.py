"""Write builds/index.html: one card per build, newest first."""

import html
import json
import re
from pathlib import Path

from .meta import head_tags

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{head}
<style>
  :root {{ --bg: #f3f1ea; --card: #fff; --ink: #1b2a34; --muted: #6c6e68; --accent: #c91a09; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #16181c; --card: #22252b; --ink: #eceae4; --muted: #9a9c96; --accent: #f2cd37; }}
  }}
  body {{ margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  main {{ max-width: 920px; margin: 0 auto; padding: 32px 16px; }}
  h1 {{ font-size: 22px; margin: 0 0 20px; }}
  h1 span {{ color: var(--accent); }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
  .card {{ display: block; background: var(--card); border-radius: 10px; padding: 16px;
           color: inherit; text-decoration: none; border-top: 5px solid var(--accent); }}
  .card:hover {{ transform: translateY(-2px); }}
  .card h2 {{ font-size: 16px; margin: 0 0 6px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .empty {{ color: var(--muted); }}
</style>
</head>
<body>
<main>
<h1><span>&#9632;</span> {title}</h1>
<div class="grid">
{cards}
</div>
</main>
</body>
</html>
"""

CARD = """<a class="card" href="{href}">
  <h2>{title}</h2>
  <div class="meta">{meta}</div>
</a>"""


def write_gallery(builds_dir, title="Brickwise builds", og_image=None):
    builds_dir = Path(builds_dir)
    cards = []
    for spec_path in sorted(builds_dir.glob("*.json"), reverse=True):
        html_path = spec_path.with_suffix(".html")
        if not html_path.exists():
            continue
        try:
            spec = json.loads(spec_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        meta = [html.escape(str(spec.get("mode", "?"))), f"{len(spec.get('pieces', []))} pieces"]
        if re.match(r"\d{4}-\d{2}-\d{2}-", spec_path.stem):
            meta.insert(0, spec_path.stem[:10])
        cards.append(CARD.format(
            href=html.escape(html_path.name),
            title=html.escape(str(spec.get("title", html_path.stem))),
            meta=" &middot; ".join(meta),
        ))
    body = "\n".join(cards) or '<p class="empty">No builds yet.</p>'
    index = builds_dir / "index.html"
    head = head_tags(title, "Codebases and topics explained as explorable 3D brick models.", og_image)
    index.write_text(PAGE.format(cards=body, title=html.escape(title), head=head))
    return index
