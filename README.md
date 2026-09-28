# Brickwise

[![tests](https://github.com/JCPetrelli/brickwise/actions/workflows/test.yml/badge.svg)](https://github.com/JCPetrelli/brickwise/actions/workflows/test.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![latest release](https://img.shields.io/github/v/release/JCPetrelli/brickwise)](https://github.com/JCPetrelli/brickwise/releases)

A [Claude Code](https://claude.com/claude-code) skill that explains a codebase, an architecture, or any complicated topic as an interactive 3D brick model.

Each concept is a brick, and related bricks form a sub-assembly. The finished model is the whole topic. **A brick's size shows how complex its concept is**, so you can see at a glance where the weight of the subject sits.

![Clicking a brick opens its explanation](docs/images/popup.jpg)

**Live demos:** [Web Request Lifecycle](https://jcpetrelli.github.io/brickwise/examples/web-request.html) · [Brickwise Internals](https://jcpetrelli.github.io/brickwise/examples/brickwise.html) · [Theory of Relativity](https://jcpetrelli.github.io/brickwise/examples/relativity.html) · [all examples](https://jcpetrelli.github.io/brickwise/examples/)

## What you get

One self-contained HTML page per explanation, about 40 KB, that runs in any modern browser:

| To | Do |
|---|---|
| Look at the model from any side | drag to orbit, scroll to zoom, right-drag to pan |
| Pull the sub-assemblies apart | **Explode** button or `E` |
| Take one sub-assembly apart, brick by brick | click it while exploded |
| See a brick's name | hover it: a leader line points to its title |
| Read what it is | click it: a one-line summary in bold, a fuller explanation, and a concrete example |
| Go back | `Esc`, **Back**, or **Reassemble** |

Claude chooses between two kinds of model:
- **Themed:** a real object whose parts map onto the topic, for example an HTTP request as a train (browser locomotive, network, server and data wagons). Used only when every group maps cleanly to a part of the object.
- **Stack:** layers where height means dependency. Foundations sit at the bottom and whatever depends on them sits on top.

## Examples

| | |
|---|---|
| **[Web Request Lifecycle](https://jcpetrelli.github.io/brickwise/examples/web-request.html)** (themed: a train)<br>spec: [`examples/web-request.json`](examples/web-request.json) | **[Theory of Relativity](https://jcpetrelli.github.io/brickwise/examples/relativity.html)** (stack)<br>spec: [`examples/relativity.json`](examples/relativity.json) |
| **[Brickwise Internals](https://jcpetrelli.github.io/brickwise/examples/brickwise.html)** (stack: this repo explaining itself)<br>spec: [`examples/brickwise.json`](examples/brickwise.json) | ![The relativity model exploded into its five groups](docs/images/exploded.jpg) |

Each title opens the live page. The `.json` spec it was built from is linked underneath, and [all examples](https://jcpetrelli.github.io/brickwise/examples/) are in one gallery.

**Host the examples** (optional). Every page is a single static file, so any static host works. On GitHub Pages:
1. Open **Settings → Pages** and set the source to **Deploy from a branch**, branch `main`, folder `/ (root)`.
2. The gallery is then at `https://<user>.github.io/brickwise/examples/`, and each page at `…/examples/relativity.html` and so on.

| Hover a brick | Take one group apart |
|---|---|
| ![Hover label with leader line](docs/images/hover.jpg) | ![General relativity group taken apart, others faded](docs/images/group.jpg) |

## Install

Requirements:
- [Claude Code](https://claude.com/claude-code)
- `python3` 3.10 or later (standard library only, nothing to pip install)
- a browser with WebGL; pages load three.js from cdn.jsdelivr.net, so opening one needs internet
- optional: [`just`](https://github.com/casey/just) for the shortcut commands below (every recipe has a plain-shell equivalent in the `justfile`)
- optional, for contributors: Node.js and Google Chrome, to run the browser smoke test

**As a plugin** (recommended):

```
/plugin marketplace add JCPetrelli/brickwise
/plugin install brickwise@brickwise
```

**Manually**, from a clone:

```bash
git clone https://github.com/JCPetrelli/brickwise.git
cd brickwise
just install      # or: ln -s "$(pwd)/skills/brickwise" ~/.claude/skills/brickwise
```

Start a new Claude Code session after installing so the skill is picked up.

**Update:**

| Install | Command |
|---|---|
| Plugin | `claude plugin update brickwise@brickwise`, then restart Claude Code |
| Manual | `git pull` in the clone; the symlink picks up the change |

**Uninstall:**

| Install | Command |
|---|---|
| Plugin | `claude plugin uninstall brickwise@brickwise`, and optionally `claude plugin marketplace remove brickwise` |
| Manual | `rm ~/.claude/skills/brickwise` (removes only the symlink), then delete the clone |

Your builds are never deleted by either route. They stay in the builds folder described below.

## Use

Ask Claude in plain words, or call the skill directly:

```
explain this repo as a brick model
build me a brick model of how OAuth works
/brickwise ~/code/my-service          # manual install
/brickwise:brickwise photosynthesis   # plugin install (namespaced)
```

Add "publish" to the request to also get a shareable claude.ai link, when your Claude Code session has the Artifact tool.

Claude reads the target, breaks it into 4–8 groups of 2–6 concepts, scores each concept's complexity, picks themed or stack, places the bricks, writes the text, and builds the page. It opens the page and gives you the path.

**Where builds go:** `$BRICKWISE_BUILDS` if you set it. Otherwise `builds/` inside a git clone, or `~/brickwise-builds/` for a plugin install, since the plugin cache is replaced on update. Each builds folder has an `index.html` gallery; from a clone, `just run` serves it at http://localhost:5733.

## How it works

```
target ──► Claude (skills/brickwise/SKILL.md) ──► build spec (JSON)
                                                          │
                                  brickwise.build ◄──┘
                                  ├─ validate.py   every rule, all errors in one pass
                                  ├─ viewer.html + viewer.js   fixed, tested three.js viewer
                                  └─ one self-contained HTML page + gallery
```

Claude never writes 3D code. It writes only a spec, which a validator checks strictly:
- no overlapping bricks
- no floating bricks
- brick size must match complexity
- no unknown fields
- word limits on all text

If the spec fails, Claude gets a precise error list (for example `piece 'db' overlaps 'cache' at x=0 z=9 level=1`), fixes it, and rebuilds. It gets up to three attempts. Every build behaves the same because the viewer never changes.

## Build spec

You can also write specs yourself and build them without Claude:

```bash
python3 -m brickwise.build my-spec.json --open        # into the builds folder + gallery
python3 -m brickwise.build my-spec.json --html out.html   # just one page
python3 -m brickwise.build my-spec.json --html out.html --source-link https://github.com/you/repo
                                                    # adds a GitHub button, as on the example pages
```

`--open` uses the macOS `open` command. On Linux or Windows, leave it out and open the printed path in your browser; the same goes for pages Claude builds.

```json
{
  "title": "Web Request Lifecycle",
  "target": "HTTP request lifecycle",
  "mode": "themed",
  "metaphor": "Train: the browser locomotive pulls the request through the network, server and data wagons.",
  "groups": [
    { "id": "network", "title": "Network", "description": "Finds the server and opens a secure channel.", "color": "blue" }
  ],
  "pieces": [
    {
      "id": "dns", "group": "network", "title": "DNS lookup",
      "description": "Turns the host name into an IP address.",
      "details": "Computers find each other by IP address, not by name. DNS asks a chain of servers…",
      "example": "shop.example.com resolves to 93.184.216.34.",
      "complexity": 2, "shape": "brick",
      "x": 0, "z": 12, "level": 1, "w": 2, "d": 2
    }
  ]
}
```

**Top level:**

| Field | Rules |
|---|---|
| `title` | required; a short name, used as the page title |
| `target` | optional; what the model explains |
| `mode` | `themed` or `stack` |
| `metaphor` | required; one sentence saying what position means |

**Groups** (1–8):

| Field | Rules |
|---|---|
| `id` | unique |
| `title` | required |
| `description` | at most 40 words |
| `color` | a palette colour |

**Pieces** (at most 40; every group needs at least one):

| Field | Rules |
|---|---|
| `id` | unique |
| `group` | an existing group id |
| `title` | required |
| `description` | at most 40 words, shown in bold |
| `details` | at most 120 words |
| `example` | optional, at most 60 words |
| `complexity` | 1–5, sets the footprint (see below) |
| `shape` | `brick` or `slope` (3 plates tall), `plate` or `tile` (1 plate tall) |
| `x`, `z` | brick's corner, in studs, ≥ 0 |
| `level` | height, in plates, ≥ 0 |
| `w`, `d` | footprint, in studs, ≥ 1 |
| `color` | optional override of the group colour |

**Complexity fixes the footprint** (`w × d`):

| complexity | area | shapes |
|---|---|---|
| 1 | 1–2 | plate, tile |
| 2 | 2–4 | brick, plate, slope |
| 3 | 6–8 | brick, plate, slope |
| 4 | 12–16 | brick, plate, slope |
| 5 | ≥ 24 | brick, plate |

**Placement:**
- There is no rotation field; to turn a brick, swap `w` and `d`.
- Slopes fall toward +z.
- Every piece above level 0 must sit on studs. Tiles have no studs, and a slope has studs only on its back row, so nothing can rest on a tile or on a sloped face.

**Palette:** red, blue, yellow, green, dark-green, orange, white, light-grey, dark-grey, black, tan, azure.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "The 3D viewer could not start" after a few seconds | three.js could not be downloaded from cdn.jsdelivr.net. Check the internet connection, or a firewall or ad-blocker blocking jsDelivr, then reload. |
| "WebGL is not available in this browser" | Hardware acceleration is off or unsupported. Enable it in the browser settings, or try another browser. |
| Claude answers in text and builds nothing | The skill isn't loaded. Start a new session after installing, check that `~/.claude/skills/brickwise` exists (manual) or run `claude plugin list` (plugin), and ask explicitly: "build a brick model of …". |
| `/brickwise` is not recognised after a plugin install | Plugin skills are namespaced: use `/brickwise:brickwise`, or ask in plain words. |
| The build fails and Claude shows a list of errors | Claude stops after three repair attempts. Ask it to keep fixing, or narrow the target, e.g. one subsystem instead of a whole monorepo. |
| The page opened from `examples/` on GitHub shows source code | GitHub displays HTML files as code. Use the live demo links at the top, or host your own copy as described under Examples. |

## Repository layout

```
skills/brickwise/SKILL.md   the skill Claude follows
.claude-plugin/                  plugin + marketplace manifests
brickwise/                  schema.py · validate.py · build.py (CLI) · gallery.py
viewer/                          viewer.html template · viewer.js
examples/                        example specs, their built pages, index.html
tests/                           pytest suite · smoke/ headless-Chrome check
docs/                            design spec, implementation plan, screenshots
```

## Development

```bash
just test                                   # pytest, standard library only
just examples                               # rebuild examples/*.html and examples/index.html
just smoke examples/relativity.html gps     # hover, click, explode in headless Chrome
```

These use `just`; without it, run the matching lines from the `justfile` directly. `just smoke` needs Node.js: it installs `puppeteer-core` into `tests/smoke/` on first run and drives your local Chrome. Set `CHROME_PATH` outside macOS. See [CONTRIBUTING.md](CONTRIBUTING.md) before changing the spec format or the viewer.

## Credits

- 3D rendering: [three.js](https://threejs.org) (MIT), loaded from [jsDelivr](https://www.jsdelivr.com).
- Built with [Claude Code](https://claude.com/claude-code).

## License

[MIT](LICENSE) © 2026 Jacopo Castellano

Brickwise is an independent project. It is not affiliated with, sponsored by or endorsed by the LEGO Group or any toy-brick manufacturer. LEGO® is a trademark of the LEGO Group.
