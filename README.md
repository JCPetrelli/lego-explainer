# LEGO Explainer

Explains a codebase, subsystem or topic as an interactive 3D LEGO model. Each concept is a brick, groups of bricks are sub-assemblies, and a brick's size shows its complexity.

This repo is the engine behind the global Claude skill `~/.claude/skills/lego-explainer/SKILL.md`. Claude writes a JSON build spec, and the engine validates it and renders it with a fixed three.js viewer.

## Use

In Claude Code: `/lego-explainer <path or topic>`. Add `publish` to also get a private claude.ai link.

By hand:

```bash
python3 -m lego_explainer.build samples/themed.json --open   # validate + build + open
just run                                                     # gallery at http://localhost:5733
```

## Viewer controls

| Action | Control |
|---|---|
| Orbit / zoom / pan | drag / scroll / right-drag |
| Explode groups | **Explode** button or `E` |
| Take one group apart | click a group while exploded |
| Back / reassemble | `Esc` or **Back** / **Reassemble** |
| Title | hover a brick (leader line + label) |
| Description, details, example | click a brick |

## Spec rules

The full spec is in `docs/specs/2026-09-27-lego-explainer-design.md`. In short:
- Positions are on a stud grid: `x`, `z`, `w`, `d` are in studs and `level` is in plates. A brick or slope is 3 plates tall, a plate or tile is 1.
- Each piece has a bold `description` (≤ 40 words), a longer `details` (≤ 120 words) and an optional `example` (≤ 60 words).
- The validator rejects overlaps, floating bricks, unknown groups, colours or shapes, and descriptions over 40 words.
- Complexity fixes the footprint area: 1 → 1–2 (plate or tile), 2 → 2–4, 3 → 6–8, 4 → 12–16, 5 → ≥ 24.

## Layout

```
lego_explainer/   schema.py (vocabulary) · validate.py · build.py (CLI) · gallery.py
viewer/           viewer.html template · viewer.js (three.js 0.160 via jsDelivr)
samples/          stack.json · themed.json. Test fixtures and layout references.
tests/            pytest suite · smoke/ (headless Chrome check)
builds/           generated pages + index.html (git-ignored)
```

## Develop

```bash
just test                                                    # pytest
just smoke builds/<file>.html <piece-id>                     # hover, popup, explode in headless Chrome
```
