# Contributing

Issues and pull requests are welcome.

## Setup

```bash
git clone https://github.com/JCPetrelli/lego-explainer.git && cd lego-explainer
just install    # symlink the skill into ~/.claude/skills so Claude Code uses your checkout
just test
```

Python uses only the standard library. The smoke test needs Node.js and a local Chrome (`CHROME_PATH` outside macOS).

## Before opening a pull request

- `just test` passes.
- If you touched `viewer/`, run `just smoke` on at least one example and look at the screenshots in `tests/smoke/shots/`. The pytest suite does not execute the viewer.
- If an example changed, run `just examples` and commit the rebuilt pages.

## Changing the spec format

A rule lives in several places. Change them together:

1. `lego_explainer/schema.py`: constants such as the palette, shape heights, the complexity table and word limits.
2. `lego_explainer/validate.py`: `SPEC_KEYS`, `GROUP_KEYS` or `PIECE_KEYS` for a new field, plus its check.
3. `viewer/viewer.js`: its own copies of `PALETTE` and `SHAPE_HEIGHT`, and anything it renders.
4. `skills/lego-explainer/SKILL.md`: what Claude is told to write.
5. `README.md`: the spec reference.
6. `examples/*.json`: they are test fixtures and must still validate.

## Commit messages

Use the imperative mood and keep the subject short, e.g. "Add slope support check".
