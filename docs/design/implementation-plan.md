# LEGO Explainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A global Claude skill that turns any target into an interactive 3D LEGO model (orbit, two-stage explode, hover labels, click popups), built from a validated JSON spec.

**Architecture:** Claude writes a JSON build spec; a Python engine validates it (overlap, floating, complexity↔size) and injects it into a fixed three.js viewer template, producing one self-contained HTML per build plus a gallery index. The skill file only holds the workflow and rules.

**Tech Stack:** Python 3.12 stdlib + pytest; three.js 0.160 (ES modules via cdn.jsdelivr.net importmap); just.

**Spec:** `docs/design/design-spec.md`

> Historical record of the first implementation. Paths and names reflect that moment (`samples/` is now `examples/`).

## Global Constraints

- Groups 1–8, each with ≥ 1 piece; total pieces ≤ 40.
- Descriptions non-empty, ≤ 40 words.
- Shapes: brick (3 plates tall), slope (3), plate (1), tile (1, no studs). Slopes descend toward +z.
- Palette (12): red, blue, yellow, green, dark-green, orange, white, light-grey, dark-grey, black, tan, azure.
- Complexity → area/shapes: 1: 1–2 plate/tile · 2: 2–4 brick/plate/slope · 3: 6–8 brick/plate/slope · 4: 12–16 brick/plate/slope · 5: ≥ 24 brick/plate.
- Output: `builds/<YYYY-MM-DD>-<slug>.html` + `.json`, gallery `builds/index.html`.
- External scripts only from cdn.jsdelivr.net/npm/.
- Commit messages: no Claude attribution (user rule).

## Review Focus

1. A description containing `</script>` must not break the page → JSON is escaped on injection (test in Task 3).
2. Validation must report *all* errors in one run with piece ids and coordinates, not stop at the first (test in Task 2).
3. Malformed JSON file / missing file → clear CLI error, exit 1, no traceback (test in Task 3).
4. Rebuilding the same spec the same day overwrites rather than duplicating gallery entries (test in Task 3).
5. Explode direction when a group centroid coincides with the model centroid → falls back to an index-based angle, never NaN (viewer code, Task 4; smoke-checked in Task 6).

---

### Task 1: Schema constants + project scaffold

**Files:**
- Create: `lego_explainer/__init__.py`, `lego_explainer/schema.py`, `justfile`, `.gitignore`, `tests/__init__.py`

**Interfaces — Produces:**
- `PALETTE: dict[str, str]` name → hex
- `SHAPE_HEIGHT: dict[str, int]` shape → plates
- `STUDLESS: set[str]` = {"tile"}
- `COMPLEXITY_RULES: dict[int, tuple[int, int | None, set[str]]]` → (min_area, max_area or None, shapes)
- `MAX_WORDS=40, MAX_GROUPS=8, MAX_PIECES=40`

- [ ] Write `schema.py` with the constants above (values from Global Constraints).
- [ ] `justfile`: `run` (serve `builds/` on port 5733 and open gallery), `test` (`python3 -m pytest -q`), `build SPEC`.
- [ ] `.gitignore`: `__pycache__/`, `.pytest_cache/`, `builds/*` except samples are in `samples/`.
- [ ] Commit.

### Task 2: Validator

**Files:** Create `lego_explainer/validate.py`, `tests/test_validate.py`

**Interfaces — Produces:**
- `validate(spec: dict) -> list[str]` — empty list = valid.
- `cells(piece: dict) -> set[tuple[int,int,int]]` — (x, z, level) unit cells.

Tests (each builds a minimal valid spec via a `base_spec()` helper and mutates it):

```python
def test_valid_spec_has_no_errors(): assert validate(base_spec()) == []
def test_samples_are_valid(): for f in SAMPLES: assert validate(json.load(f)) == []
def test_overlap_reported(): ... two bricks sharing a cell → error mentions both ids and "overlaps"
def test_floating_reported(): ... brick at level 5 with nothing below → "floating"
def test_level0_on_baseplate_ok()
def test_complexity_size_mismatch(): complexity 1 on a 2x4 brick → "complexity 1"
def test_shape_not_allowed_for_complexity(): complexity 1 brick 1x1 → error
def test_unknown_group_color_shape_mode()
def test_duplicate_ids()
def test_description_too_long_and_empty()
def test_group_without_pieces_and_limits()
def test_collects_all_errors(): spec with 3 distinct problems → len(errors) >= 3
def test_bad_types_do_not_crash(): x="a", w=0, pieces missing → errors, no exception
```

- [ ] Write tests, run → fail (ImportError).
- [ ] Implement: field/type checks first (pieces with type errors are excluded from geometry checks), then refs, then complexity, then overlap via a `dict[cell] -> id` map, then floating (level > 0 needs any footprint cell at `level-1` occupied by another piece).
- [ ] Run → pass. Commit.

### Task 3: Builder + gallery + CLI

**Files:** Create `lego_explainer/build.py`, `lego_explainer/gallery.py`, `viewer/viewer.html` (template stub with markers), `tests/test_build.py`

**Interfaces:**
- Consumes: `validate(spec)`.
- Produces: `slugify(text) -> str`; `render_html(spec: dict) -> str`; `build(spec_path: Path, builds_dir: Path, today: date | None = None) -> Path`; `write_gallery(builds_dir: Path) -> Path`; CLI `python3 -m lego_explainer.build SPEC [--out DIR] [--open]`, exit 1 on errors.
- Template markers: `/*__SPEC_JSON__*/` inside `<script type="application/json" id="lego-spec">`, `/*__VIEWER_JS__*/` inside `<script type="module">`, `__TITLE__` in `<title>`.

Tests:

```python
def test_render_embeds_spec_and_js()
def test_script_close_in_description_is_escaped(): "</script>" not present raw inside the JSON block
def test_build_writes_html_json_and_gallery(tmp_path)
def test_rebuild_same_day_overwrites(tmp_path): two builds → one gallery card
def test_invalid_spec_raises_with_errors(tmp_path)
def test_cli_bad_json_exits_1(tmp_path, capsys)
def test_cli_missing_file_exits_1(tmp_path, capsys)
```

- [ ] Write tests, run → fail.
- [ ] Implement. JSON escaping: `json.dumps(spec).replace("</", "<\\/")`; title HTML-escaped. Gallery reads every `builds/*.json` with a sibling `.html`, sorts by filename desc, cards show title, mode, date, piece count.
- [ ] Run → pass. Commit.

### Task 4: Viewer — scene, bricks, orbit, explode

**Files:** Create `viewer/viewer.js`; fill in `viewer/viewer.html` (layout, CSS tokens, light/dark).

Units: 1 stud = 1.0, plate = 0.4, stud r 0.3 h 0.18. Model centred on the origin; baseplate = extent + 2 margin, with InstancedMesh studs.

- Brick/plate/tile: `RoundedBoxGeometry(w-0.02, h, d-0.02, 2, 0.04)`; studs as child meshes (not on tile).
- Slope: `ExtrudeGeometry` of the profile (0,0)→(d,0)→(d,0.4)→(min(1,d-…)…): back row flat at full height with studs, falling to a 0.4 lip at +z; d = 1 → wedge without studs.
- Each piece → `THREE.Group` with `userData = {id, group, home: Vector3}`, plus an `EdgesGeometry` outline (hidden until hover).
- State machine: `setState(1|2|3, groupId?)`. Offsets: state 2 = group dir × spread + lift; state 3 adds a per-piece spread of `(pieceCentre − groupCentre) × 1.2 + level lift`. Tween 600 ms, easeInOutCubic. Zero-length direction → angle `2π·i/n`.
- State 3: other groups fade to opacity 0.2 (materials are per piece).
- OrbitControls with damping, autoRotate until the first `start` event.
- CDN guard: an inline non-module script shows `#load-error` if `window.__legoReady` is not set within 6 s.
- Test hook: `window.__lego = {state, setState, screenPos(id), pieceIds}`.

- [ ] Implement, build `samples/stack.json`, open, confirm visually. Commit.

### Task 5: Viewer — hover leader line, popup, group labels, chrome

- Raycast on pointermove → top piece. Outline visible; SVG `<line>` + dot from the piece's top-centre in screen space to the label, which sits 150 px toward the side away from the model's screen centre and 60 px up, clamped to the viewport. Recomputed every frame while hovered. Label text: `Group › Piece` in states 1–2, `Piece` in 3.
- Click (pointerup with < 5 px movement): state 2 → `setState(3, group)`; states 1/3 → popup card (title, ●●●○○, group, description) near the piece, clamped. Empty click closes the popup. `Esc`: close the popup, else state 3 → 2. `E`: 1→2, 2→1, 3→1.
- Buttons: state 1 `[Explode]`; state 2 `[Reassemble]` + hint "Click a group to take it apart"; state 3 `[Back] [Reassemble]`.
- Group labels (HTML) above each group's bbox top in states 2–3.
- Header: title, mode badge (`Themed: <metaphor object>` / `Stack`), metaphor line. Legend: group colour swatches + "Bigger brick = more complex".

- [ ] Implement, rebuild the samples, check by hand. Commit.

### Task 6: Samples, smoke test, skill, registration

**Files:** `samples/stack.json` (lego_explainer's own architecture), `samples/themed.json` (a web request as a train), `~/.claude/skills/lego-explainer/SKILL.md`, `README.md`.

- [ ] Both samples pass `validate` (already covered by the Task 2 test).
- [ ] Smoke test in Chrome via DevTools MCP: load the themed build; no console errors; `__lego.screenPos` → dispatch pointermove → label visible; dispatch click → popup visible; `setState(2)`, then click a group → state 3; no NaN positions.
- [ ] SKILL.md: triggers, the 6-step workflow, layout rules for stack/themed, the brick-size table, description style, the retry limit, the publish option (Artifact tool, private).
- [ ] README, repos.md entry. Commit.
