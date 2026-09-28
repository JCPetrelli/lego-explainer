---
name: brickwise
description: Use when the user wants a target explained as an interactive 3D brick model — a codebase, subsystem, architecture, pipeline, or any complicated topic. Triggers on "/brickwise", "brickwise this", "explain X as bricks", "brick model of X", "build me a brick model of this repo", "show X as bricks", "toy-brick explainer". Output is a self-contained HTML page (orbit, two-stage explode, hover labels, click popups) plus a gallery of all builds; optionally published as a shareable claude.ai Artifact.
---

# Brickwise

Turn a target into a brick model: every concept is a brick, groups of bricks are sub-assemblies, the whole build is the whole topic. **Brick size = complexity.** You write a JSON build spec; the engine validates it and renders it with a fixed, tested viewer. Never hand-write three.js.

**Engine location.** The engine is the repository this skill ships in: two directories above this `SKILL.md`. Resolve it once, following symlinks, and use it for every command below:

```bash
ENGINE="$(cd "$(dirname "$(realpath "<this skill's base directory>/SKILL.md")")/../.." && pwd)"
```

Builds go to `$BRICKWISE_BUILDS` if set, otherwise to `builds/` inside a git clone of the engine, otherwise to `~/brickwise-builds/`. Each build folder has an `index.html` gallery.

Invocation: `/brickwise <path or topic> [publish]`. Requires `python3` (3.10 or later).

## Workflow

1. **Understand the target.**
   - Path → read the README/entry points, list modules and what depends on what. Large repo → dispatch an Explore agent for the map; you only need concepts and dependencies, not code.
   - Topic → own knowledge; web search if recent or niche.
   - Too big for ~35 bricks (monorepo, whole OS) → build the top level only, then offer reruns on named subsystems.

2. **Decompose.** 4–8 groups (sub-assemblies), 2–6 pieces each, 12–35 pieces total. Every piece is one concept a reader should leave knowing. Score each piece's complexity 1–5 honestly: leaf dependency / trivial helper = 1, central engine the rest leans on = 5. Use the whole range.

3. **Choose the mode.**
   - **themed** — only if ONE real object fits and *every* group maps to a recognisable part of it (train: locomotive → wagons; castle: gate, walls, keep, treasury; house: foundation, walls, rooms, roof; ship; rocket stages). The object's order/position must mean something (flow direction, protection layers, support).
   - **stack** — otherwise. Don't strain a metaphor.
   - Write `metaphor` as one sentence that starts with the object (or "Stack:") and says what position means.

4. **Lay out the bricks** on the stud grid (read the specs in `$ENGINE/examples/` first: they are the reference patterns).
   - Coordinates: `x`, `z`, `w`, `d` in studs, `level` in plates. brick/slope = 3 plates tall, plate/tile = 1. `x`, `z` is the brick's min corner; all ≥ 0. No rotation: turn a brick by swapping `w`/`d`. Slopes fall toward +z (use for noses, roofs, ramps).
   - Every piece at `level > 0` must rest on studs: at least one footprint cell directly on top of another piece. Tiles have no studs, and a slope only has studs on its back row (`z == slope.z`), so nothing can rest on a tile or on a sloped face. No overlaps. Only the documented fields are allowed; typos like `colour` are rejected.
   - **Stack mode:** foundations (runtime, storage, platform) at level 0; each layer sits on what it depends on; dependents touch their dependencies; the thing the user touches goes on top.
   - **Themed mode:** place parts where they belong on the object; flow runs along one axis (e.g. train along z, front at high z).
   - Tiny pieces (complexity 1) make good details on top: chimneys, flags, tiles.

5. **Complexity fixes the footprint** (area = w × d; the validator enforces this):

   | complexity | area | shapes |
   |---|---|---|
   | 1 | 1–2 | plate, tile |
   | 2 | 2–4 | brick, plate, slope |
   | 3 | 6–8 | brick, plate, slope |
   | 4 | 12–16 | brick, plate, slope |
   | 5 | ≥ 24 | brick, plate |

6. **Write text.** No hedging, no marketing, no "robust/seamless/powerful".
   - `title`: 1–3 words.
   - `description` (groups and pieces, ≤ 40 words): terse and direct: what it is, what it does, one concrete fact. Fragments are fine. It appears **bold** at the top of the popup.
   - `details` (pieces, required, ≤ 120 words): explains it properly in 2–5 plain sentences. How it works, why it exists, what it connects to, the one gotcha worth knowing. Write for a smart newcomer and define any jargon you use. For a codebase, name the real files, functions and flags.
   - `example` (pieces, optional but expected, ≤ 60 words): one simple concrete case: a real input and output, a command, a number, or an everyday analogy. Don't restate `details`. Skip it only when no example would help.

7. **Colours.** Palette: red, blue, yellow, green, dark-green, orange, white, light-grey, dark-grey, black, tan, azure. One colour per group (`groups[].color`); a piece may override (`pieces[].color`) to stand out inside its group. Avoid light-grey (baseplate colour).

8. **Build.** Write the spec to a temporary file (the session scratchpad if there is one), then:
   ```bash
   cd "$ENGINE" && python3 -m brickwise.build <spec.json> --open
   ```
   `--open` uses macOS `open`; on other systems drop it and give the user the printed path.
   Errors come back as a list (`piece 'x' overlaps 'y' at x=… z=… level=…`, `… is floating`, `complexity 3 needs footprint area 6-8`). Fix them all and rerun — **max 3 attempts**, then stop and show the user the remaining errors.

9. **Report**, briefly: the HTML path, mode + why, group and piece counts, and controls: drag = orbit, scroll = zoom, right-drag = pan, `E`/button = explode, click a group when exploded = take it apart, `Esc` = back.

10. **Publish** (only when asked: "publish", "share", "link"). If an Artifact tool is available, publish the built HTML as a private Artifact (`icon: "blocks"`) and give the link. The page loads three.js from cdn.jsdelivr.net, which Artifacts allow. Otherwise say the HTML file is self-contained and can be hosted anywhere static (GitHub Pages, Netlify).

## Spec shape

```json
{
  "title": "…", "target": "path or topic", "mode": "themed | stack",
  "metaphor": "Train: …",
  "groups": [{"id": "net", "title": "Network", "description": "…", "color": "blue"}],
  "pieces": [{"id": "dns", "group": "net", "title": "DNS lookup", "description": "…",
              "details": "…", "example": "shop.example.com resolves to 93.184.216.34.",
              "complexity": 2, "shape": "brick", "x": 0, "z": 12, "level": 1, "w": 2, "d": 2}]
}
```

Limits: ≤ 8 groups, ≤ 40 pieces, every group has pieces, ids unique.

## Engine maintenance

See `$ENGINE/CONTRIBUTING.md` and `$ENGINE/CLAUDE.md`. Short version: `just test`, `just smoke <page.html> <piece-id>`, and keep the `PALETTE` in `viewer/viewer.js` in sync with `brickwise/schema.py`.
