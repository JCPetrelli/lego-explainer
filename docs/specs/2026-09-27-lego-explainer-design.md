# LEGO Explainer — Design

Date: 2026-09-27
Status: approved in brainstorming, pending written-spec review

## Purpose

A global Claude Code skill that explains any target — a codebase, a subsystem, or an abstract topic — as an interactive 3D LEGO model. Each concept is a brick; the whole build is the whole topic. The user orbits the model, explodes it apart in two stages, hovers bricks for titles and clicks them for terse descriptions.

Success: opening a build gives a correct, memorable mental model of the target in a few minutes, and every build behaves identically because the viewer is fixed and tested.

## Decisions

| Question | Decision |
|---|---|
| Meaning of the shape | Hybrid: **themed** model (castle, train, house…) when the metaphor maps cleanly, otherwise **structural stack**. Claude states which and why. |
| Depth | Two levels: 4–8 **groups** (sub-assemblies), each 2–6 **pieces**. ~12–35 pieces total. |
| Brick size | Encodes **complexity** (1–5). Trivial concept / leaf dependency = small plate; heavy central concept = big brick. |
| Output | Central gallery folder; optional publish as private claude.ai Artifact on request. |
| Architecture | Fixed tested viewer + per-target JSON build spec written by Claude + Python validator/builder. |

## Layout

```
~/.claude/skills/lego-explainer/SKILL.md      global skill: workflow + rules for Claude
~/Documents/Scripts/lego_explainer/           engine (git repo)
├── viewer/            viewer.html template, viewer.js (three.js via CDN)
├── lego_explainer/    schema.py, validate.py, build.py, gallery.py
├── samples/           themed.json, stack.json (fixtures + examples for Claude)
├── tests/
├── justfile           `just run` serves/opens the gallery
└── builds/            <YYYY-MM-DD>-<slug>.json + .html, index.html
```

The skill stays thin; all logic lives in the engine. The engine is registered in `jc_secretary/repos.md`.

## Build spec

```json
{
  "title": "home_guard architecture",
  "target": "~/Documents/Scripts/home_guard",
  "mode": "themed",
  "metaphor": "A castle: the gate checks who enters, the walls watch traffic.",
  "groups": [
    {"id": "gate", "title": "Alerting", "description": "…", "color": "red"}
  ],
  "pieces": [
    {"id": "mailer", "group": "gate", "title": "Mail sender",
     "description": "Sends alert emails. Uses shared mail-lib. Retries 3x.",
     "complexity": 2, "shape": "brick",
     "x": 4, "z": 2, "level": 3, "w": 2, "d": 2, "color": "red"}
  ]
}
```

- `mode`: `"themed"` or `"stack"`.
- Units: `x`, `z`, `w` (width along x), `d` (depth along z) in studs; `level` in plate heights. A `brick` is 3 plates tall; `plate`, `tile`, `slope` are 1 plate tall except `slope`, which is 3 (brick height, sloped top). `tile` has no studs.
- `x`, `z` are the brick's minimum corner; the baseplate occupies levels < 0 and has its origin at (0, 0). Baseplate size is computed from the build extent plus a 2-stud margin.
- No rotation field: orientation is expressed by swapping `w`/`d`. Slopes descend toward +z.
- Colours: a fixed palette of 12 named LEGO colours (red, blue, yellow, green, dark-green, orange, white, light-grey, dark-grey, black, tan, azure). Pieces default to their group's colour; a piece may override within the palette.
- Descriptions (groups and pieces): non-empty, at most 40 words.
- `details` (pieces, required): longer explanation, at most 120 words. `example` (pieces, optional): one concrete example, at most 60 words, non-empty when present. *(Added 2026-09-27 after first release.)*

### Complexity → footprint

Footprint area = `w × d`.

| complexity | allowed area | allowed shapes |
|---|---|---|
| 1 | 1–2 | plate, tile |
| 2 | 2–4 | brick, plate, slope |
| 3 | 6–8 | brick, plate, slope |
| 4 | 12–16 | brick, plate, slope |
| 5 | ≥ 24 | brick, plate |

## Validator

`python -m lego_explainer.build <spec.json>` validates, then builds. It rejects, with one precise message per error (e.g. `piece 'mailer' overlaps 'queue' at x=4 z=2 level=3`):

- Schema errors: missing/unknown fields, bad types, unknown `mode`, `shape`, `color`, `group`; duplicate ids.
- Group without pieces; group count outside 1–8; piece count above 40.
- **Overlap**: two pieces share any unit cell (x, z, level).
- **Floating**: a piece at `level > 0` with no piece occupying a cell directly beneath any of its footprint cells.
- **Complexity/size mismatch** per the table above.
- Description empty or over 40 words.

Exit code non-zero on any error; errors printed as a list.

## Builder and gallery

- `build.py` injects the validated spec JSON into `viewer.html` (inline `<script type="application/json">`) and inlines `viewer.js`, producing one self-contained HTML file (three.js + OrbitControls still from cdn.jsdelivr.net) at `builds/<date>-<slug>.html`; the spec is copied beside it as `.json`.
- `gallery.py` regenerates `builds/index.html`: one card per build (title, mode, date, piece count), newest first.
- `just run` serves `builds/` locally and opens the gallery.

## Viewer

**Scene.** Grey baseplate with studs, soft key light + ambient, light shadows. Bricks are glossy plastic with studs and slightly beveled edges. OrbitControls: left-drag orbit, scroll zoom, right-drag pan. Slow auto-rotate until first interaction.

**Explode (button + `E` key), three states:**
1. **Assembled** — full model.
2. **Groups apart** — each group translates as a unit outward from the model centroid (direction = group centroid − model centroid, horizontal, with a vertical lift for stacked groups), eased ~0.6 s. Group titles float above each cluster.
3. **Group disassembled** — clicking a group in state 2 spreads its pieces vertically and outward; other groups fade to ~20% opacity. `Esc`/Back returns to state 2.

Button label cycles: *Explode → Pick a group → Reassemble*.

**Hover.** Thin white outline on the brick; a leader line (line + end dot) from the brick to a title label placed off-model (screen-space, on the side away from the model centre), tracking during orbit. In states 1–2 the label reads `Group › Piece`.

**Click.** Popup card beside the brick: title, complexity dots (●●○○○), group name, the description in bold, the `details` paragraph, and an "Example" box when `example` is set. The card scrolls if taller than the viewport. Closes on outside click or `Esc`. In state 2, clicking selects the group (enters state 3) instead of opening a piece popup; in states 1 and 3 it opens the piece popup.

**Chrome.** Header: title, mode label (`Themed: castle` / `Stack`), metaphor line. Legend: group colours; brick-size-means-complexity note.

**Errors.** If three.js fails to load, show a visible message instead of a blank canvas.

**Out of scope.** In-browser editing, search, dedicated mobile layout (must not break, nothing more).

## Skill workflow (SKILL.md)

Invocation: `/lego-explainer <path or topic> [publish]`.

1. **Understand the target.** Path → explore entry points, modules, dependencies (Explore agent for large repos). Topic → own knowledge, plus web research if recent/niche.
2. **Decompose** into 4–8 groups × 2–6 pieces; score each piece's complexity 1–5.
3. **Choose mode.** Themed only if every group maps to a recognisable part of one object; else stack. Record the reason in `metaphor`.
4. **Lay out.** Stack: foundations (runtime, storage) on the baseplate, layers upward, dependents touching what they depend on. Themed: parts where they belong on the object. Consult `samples/` for patterns.
5. **Write spec, run build.** On validator errors, fix and rerun, max 3 attempts; then stop and show the errors.
6. **Report.** Open the HTML; report path, mode + reason, piece count. If `publish` was requested, publish the HTML as a private Artifact and return the link.

Description style: terse, direct, what it is and what it does, ≤ 40 words, no hedging, no marketing.

Too-large target: stay at top level and suggest a rerun on a named subsystem.

## Testing

- `pytest`: validator (each rejection rule, plus both samples pass), builder round-trip (HTML contains spec, gallery lists build).
- Viewer smoke test in Chrome via DevTools MCP on a sample: no console errors, hover label appears, click popup appears, both explode stages animate.
