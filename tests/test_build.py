import json
import re
from datetime import date

import pytest

from lego_explainer import build as build_mod
from lego_explainer.build import BuildError, build, render_html, slugify
from tests.test_validate import base_spec

DAY = date(2026, 9, 27)


def spec_file(tmp_path, spec=None, name="spec.json"):
    path = tmp_path / name
    path.write_text(json.dumps(spec if spec is not None else base_spec()))
    return path


def embedded_json(html):
    m = re.search(r'<script type="application/json" id="lego-spec">(.*?)</script>', html, re.S)
    assert m, "spec block missing"
    return m.group(1)


def test_slugify():
    assert slugify("How a Web Request is Served!") == "how-a-web-request-is-served"
    assert slugify("   ") == "build"


def test_render_embeds_spec_and_viewer_js():
    html = render_html(base_spec())
    assert json.loads(embedded_json(html))["title"] == "Tiny"
    assert "__lego" in html  # viewer.js was inlined
    assert "/*__" not in html  # no marker left behind
    assert "<title>Tiny</title>" in html


def test_script_close_in_description_is_escaped():
    spec = base_spec()
    spec["pieces"][0]["description"] = "evil </script><script>alert(1)</script>"
    spec["title"] = "<b>T</b>"
    html = render_html(spec)
    block = embedded_json(html)
    assert "</script>" not in block
    assert json.loads(block)["pieces"][0]["description"].startswith("evil </script>")
    assert "<title>&lt;b&gt;T&lt;/b&gt;</title>" in html


def test_build_writes_html_json_and_gallery(tmp_path):
    out = tmp_path / "builds"
    html_path = build(spec_file(tmp_path), out, today=DAY)
    assert html_path == out / "2026-09-27-tiny.html"
    assert (out / "2026-09-27-tiny.json").exists()
    index = (out / "index.html").read_text()
    assert "2026-09-27-tiny.html" in index and "Tiny" in index


def test_rebuild_same_day_overwrites(tmp_path):
    out = tmp_path / "builds"
    build(spec_file(tmp_path), out, today=DAY)
    build(spec_file(tmp_path), out, today=DAY)
    assert len(list(out.glob("*.html"))) == 2  # the build + index
    assert (out / "index.html").read_text().count('class="card"') == 1


def test_gallery_newest_first(tmp_path):
    out = tmp_path / "builds"
    build(spec_file(tmp_path), out, today=date(2026, 1, 1))
    other = base_spec()
    other["title"] = "Newer"
    build(spec_file(tmp_path, other), out, today=DAY)
    index = (out / "index.html").read_text()
    assert index.index("Newer") < index.index("Tiny")


def test_invalid_spec_raises_with_all_errors(tmp_path):
    spec = base_spec()
    spec["mode"] = "tower"
    spec["pieces"][1]["level"] = 5
    with pytest.raises(BuildError) as exc:
        build(spec_file(tmp_path, spec), tmp_path / "builds", today=DAY)
    assert len(exc.value.errors) >= 2
    assert not (tmp_path / "builds").exists()


def test_cli_success(tmp_path, capsys):
    code = build_mod.main([str(spec_file(tmp_path)), "--out", str(tmp_path / "b")])
    assert code == 0
    assert "tiny.html" in capsys.readouterr().out


def test_cli_invalid_spec_exits_1(tmp_path, capsys):
    spec = base_spec()
    spec["mode"] = "tower"
    assert build_mod.main([str(spec_file(tmp_path, spec)), "--out", str(tmp_path / "b")]) == 1
    assert "mode" in capsys.readouterr().err


def test_cli_bad_json_exits_1(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    assert build_mod.main([str(bad), "--out", str(tmp_path / "b")]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_cli_missing_file_exits_1(tmp_path, capsys):
    assert build_mod.main([str(tmp_path / "nope.json"), "--out", str(tmp_path / "b")]) == 1
    assert "not found" in capsys.readouterr().err


def test_html_comment_script_sequence_cannot_escape():
    spec = base_spec()
    spec["pieces"][0]["description"] = "<!-- <script> & more >"
    block = embedded_json(render_html(spec))
    assert "<" not in block and ">" not in block and "&" not in block
    assert json.loads(block)["pieces"][0]["description"] == "<!-- <script> & more >"


def test_cli_rejects_nan(tmp_path, capsys):
    bad = tmp_path / "nan.json"
    bad.write_text(json.dumps(base_spec()).replace('"a topic"', "NaN"))
    assert build_mod.main([str(bad), "--out", str(tmp_path / "b")]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_default_builds_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("LEGO_EXPLAINER_BUILDS", str(tmp_path / "mine"))
    assert build_mod.default_builds_dir() == tmp_path / "mine"


def test_default_builds_dir_clone_vs_install(tmp_path, monkeypatch):
    monkeypatch.delenv("LEGO_EXPLAINER_BUILDS", raising=False)
    monkeypatch.setattr(build_mod, "ROOT", tmp_path)
    monkeypatch.setattr(build_mod.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert build_mod.default_builds_dir() == tmp_path / "home" / "lego-explainer-builds"
    (tmp_path / ".git").mkdir()
    assert build_mod.default_builds_dir() == tmp_path / "builds"


def test_cli_html_writes_single_page_without_gallery(tmp_path, capsys):
    out = tmp_path / "page.html"
    assert build_mod.main([str(spec_file(tmp_path)), "--html", str(out)]) == 0
    assert "__lego" in out.read_text()
    assert not (tmp_path / "index.html").exists()


def test_gallery_omits_date_for_undated_files(tmp_path):
    from lego_explainer.gallery import write_gallery
    (tmp_path / "relativity.json").write_text(json.dumps(base_spec()))
    (tmp_path / "relativity.html").write_text("x")
    index = write_gallery(tmp_path).read_text()
    assert "relativity &middot;" not in index and "stack &middot; 2 pieces" in index
