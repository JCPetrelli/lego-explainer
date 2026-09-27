# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Engine behind the global `lego-explainer` skill, whose instructions live **outside this repo** at `~/.claude/skills/lego-explainer/SKILL.md`. Claude writes a JSON build spec, `lego_explainer.build` validates it and injects it into a fixed three.js viewer, and the output is a self-contained page in `builds/` (git-ignored). The design spec is at `docs/specs/2026-09-27-lego-explainer-design.md`. If you change a spec rule, update the spec, `SKILL.md` and `README.md` together.

## Commands

```bash
just test                                        # python3 -m pytest -q (stdlib only, no venv)
python3 -m pytest tests/test_validate.py::test_floating_reported -q   # single test
python3 -m lego_explainer.build samples/themed.json --open            # validate + build + open
just run                                         # serve builds/ gallery on :5733
just smoke builds/<file>.html <piece-id>         # headless Chrome check; npm-installs puppeteer-core on first run
```

`just smoke` drives the system Chrome with SwiftShader. It hovers, clicks, explodes, and takes one group apart, then prints JSON with `"problems": []` when clean. Screenshots go to `tests/smoke/shots/`. Run it after any viewer change: the pytest suite does not execute `viewer.js`.

## Architecture

**Rules are duplicated across the Python/JS boundary.** `lego_explainer/schema.py` is the source of truth for the palette, shape heights, complexity→footprint table and word limits. `viewer/viewer.js` hard-codes its own `PALETTE` and `SHAPE_HEIGHT`, which must stay in sync.

**Validator (`validate.py`) runs in two phases.**
1. Field checks per piece, via `_check_piece`. A piece with bad types or ranges is excluded from phase 2, so one bad field never causes a crash or cascading errors.
2. Geometry via `_check_geometry` over the sound pieces only. It works on a cell map `(x, z, level) → piece`:
   - Overlaps are reported once per piece pair.
   - Support: a piece at `level > 0` needs at least one footprint cell directly on top of a stud-bearing cell. Tiles (`STUDLESS`) and the non-back rows of a slope give no support.

It returns *all* errors as strings, because the skill's fix-and-rerun loop is limited to 3 attempts. Every membership test goes through `_in()`, since JSON values may be unhashable lists or dicts. Unknown keys are rejected via `SPEC_KEYS`, `GROUP_KEYS` and `PIECE_KEYS`: add new fields there.

**Builder (`build.py`).**
- `render_html` replaces the markers in `viewer/viewer.html`: `__TITLE__` (HTML-escaped), `/*__VIEWER_JS__*/` (the inlined `viewer.js`), and `/*__SPEC_JSON__*/`. The viewer is inserted before the spec, one occurrence each, so text inside a spec can't be mistaken for a marker.
- The spec JSON has `<`, `>` and `&` escaped as `<` and so on, and NaN is rejected both on load (`parse_constant`) and on dump (`allow_nan=False`).
- Output is `builds/<date>-<slug>.html` plus a `.json` copy. `gallery.py` regenerates `index.html` from those JSON copies.
- `viewer.js` must never contain `</` (it is inlined in a `<script>`) or the `/*__` marker prefix.

**Viewer (`viewer/viewer.js`, a single ES module; three.js 0.160 via a jsDelivr importmap).**
- Units: 1 stud = 1.0, plate = 0.4. A spec `(x, z)` is the brick's min corner, and the model is centred on the origin.
- Slopes are an `ExtrudeGeometry` profile that falls toward +z, with studs only on the back row.
- The state machine is `setState(1|2|3, group)`: assembled, groups apart, one group apart. Every piece tweens its `offset` from `home` over 600 ms. Opacity changes toggle `material.transparent`, which requires `needsUpdate`.
- State-2 group offsets are computed once:
  - vertical lift proportional to the group's height
  - horizontal push proportional to its distance from the model centre
  - then an AABB relaxation loop pushes apart groups that still overlap
- Hover label, leader line (SVG), popup and group labels are DOM overlays, re-projected every frame. Anything whose anchor is behind the camera is hidden.
- `window.__lego` (`state`, `setState`, `screenPos(id)`, `positionsFinite()`) is the test hook used by `tests/smoke/smoke.mjs`. Keep it stable.
- An inline non-module script shows `#load-error` if `window.__legoReady` isn't set within 6 s, which covers a CDN or WebGL failure.

## Samples

`samples/stack.json` and `samples/themed.json` are three things at once:
- test fixtures (`test_samples_exist_and_are_valid`)
- the layout references the skill tells Claude to read
- the smoke-test targets

They must always pass validation after any rule change.
