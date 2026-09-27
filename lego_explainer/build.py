"""Validate a build spec and render it into a self-contained viewer HTML in builds/."""

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from .gallery import write_gallery
from .validate import validate

ROOT = Path(__file__).resolve().parent.parent
VIEWER_DIR = ROOT / "viewer"
BUILDS_DIR = ROOT / "builds"


class BuildError(Exception):
    def __init__(self, errors):
        super().__init__("\n".join(errors))
        self.errors = errors


def _reject_constant(name):
    raise ValueError(f"{name} is not allowed in a spec")


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60].rstrip("-") or "build"


def render_html(spec):
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
    page = page.replace("/*__VIEWER_JS__*/", viewer_js, 1)
    return page.replace("/*__SPEC_JSON__*/", spec_json, 1)


def build(spec_path, builds_dir=BUILDS_DIR, today=None):
    """Validate the spec at spec_path and write <date>-<slug>.html/.json. Returns the HTML path."""
    spec = json.loads(Path(spec_path).read_text(), parse_constant=_reject_constant)
    errors = validate(spec)
    if errors:
        raise BuildError(errors)
    builds_dir = Path(builds_dir)
    builds_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{(today or date.today()).isoformat()}-{slugify(spec['title'])}"
    html_path = builds_dir / f"{stem}.html"
    html_path.write_text(render_html(spec))
    (builds_dir / f"{stem}.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    write_gallery(builds_dir)
    return html_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a LEGO build spec and render it.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, default=BUILDS_DIR, help="builds directory")
    parser.add_argument("--open", action="store_true", help="open the result in the browser")
    args = parser.parse_args(argv)

    try:
        html_path = build(args.spec, args.out)
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
