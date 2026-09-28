"""Validate a build spec and render it into a self-contained viewer HTML in builds/."""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from .gallery import write_gallery
from .meta import check_url, head_tags
from .validate import validate

ROOT = Path(__file__).resolve().parent.parent
VIEWER_DIR = ROOT / "viewer"


def default_builds_dir():
    """$BRICKWISE_BUILDS, else builds/ inside a git clone, else ~/brickwise-builds
    (a plugin install lives in a cache directory that is replaced on update)."""
    env = os.environ.get("BRICKWISE_BUILDS")
    if env:
        return Path(env).expanduser()
    if (ROOT / ".git").exists():
        return ROOT / "builds"
    return Path.home() / "brickwise-builds"


class BuildError(Exception):
    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = errors


def _reject_constant(name):
    raise ValueError(f"{name} is not allowed in a spec")


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].rstrip("-") or "build"


def render_html(spec, source_link=None, og_image=None):
    """Page HTML for a validated spec. source_link adds a "GitHub" button pointing at it;
    og_image (absolute URL) gives link previews a picture."""
    check_url(source_link, "source link")
    template = (VIEWER_DIR / "viewer.html").read_text()
    viewer_js = (VIEWER_DIR / "viewer.js").read_text()
    # No raw < > & inside the <script> block: "</script>" or "<!--" in a description
    # would otherwise end it early. The \\u escapes are plain JSON string escapes.
    spec_json = (
        json.dumps(spec, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )
    # Insert the viewer before the spec, one occurrence each, so text inside a
    # spec can never be mistaken for a template marker.
    page = template.replace("__TITLE__", html.escape(spec["title"]))
    page = page.replace("__SOURCE_LINK__", html.escape(source_link or ""), 1)
    page = page.replace("__HEAD_META__", head_tags(spec["title"], spec["metaphor"], og_image), 1)
    page = page.replace("/*__VIEWER_JS__*/", viewer_js, 1)
    return page.replace("/*__SPEC_JSON__*/", spec_json, 1)


def load_spec(spec_path):
    """Read and validate a spec file. Raises BuildError listing every problem."""
    spec = json.loads(Path(spec_path).read_text(), parse_constant=_reject_constant)
    errors = validate(spec)
    if errors:
        raise BuildError(errors)
    return spec


def build(spec_path, builds_dir=None, today=None, source_link=None, og_image=None):
    """Validate the spec at spec_path and write <date>-<slug>.html/.json. Returns the HTML path."""
    spec = load_spec(spec_path)
    builds_dir = Path(builds_dir) if builds_dir else default_builds_dir()
    builds_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{(today or date.today()).isoformat()}-{slugify(spec['title'])}"
    html_path = builds_dir / f"{stem}.html"
    html_path.write_text(render_html(spec, source_link, og_image))
    (builds_dir / f"{stem}.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    write_gallery(builds_dir)
    return html_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Brickwise build spec and render it.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, help="builds directory (default: see default_builds_dir)")
    parser.add_argument("--html", type=Path,
                        help="write just this one HTML file: no JSON copy, no gallery")
    parser.add_argument("--open", action="store_true", help="open the result in the browser")
    parser.add_argument("--source-link", metavar="URL",
                        help="show a GitHub button linking to URL (used for the published examples)")
    parser.add_argument("--og-image", metavar="URL",
                        help="absolute image URL for link previews (LinkedIn, Slack, ...)")
    args = parser.parse_args(argv)

    try:
        check_url(args.source_link, "source link")
        check_url(args.og_image, "og image")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        if args.html:
            args.html.parent.mkdir(parents=True, exist_ok=True)
            args.html.write_text(render_html(load_spec(args.spec), args.source_link, args.og_image))
            html_path = args.html
        else:
            html_path = build(args.spec, args.out, source_link=args.source_link, og_image=args.og_image)
    except FileNotFoundError:
        print(f"error: spec file not found: {args.spec}", file=sys.stderr)
        return 1
    except ValueError as exc:  # includes json.JSONDecodeError
        print(f"error: {args.spec} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    except BuildError as exc:
        print(f"spec has {len(exc.errors)} error(s):", file=sys.stderr)
        for err in exc.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(html_path)
    if args.open:
        subprocess.run(["open", str(html_path)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
