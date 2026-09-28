"""Validate a build spec: schema, references, complexity-to-size, overlaps and support."""

from .schema import (
    COMPLEXITY_RULES,
    MAX_DETAIL_WORDS,
    MAX_EXAMPLE_WORDS,
    MAX_GROUPS,
    MAX_PIECES,
    MAX_WORDS,
    MODES,
    PALETTE,
    SHAPE_HEIGHT,
    STUDLESS,
)

INT_FIELDS = ("x", "z", "level", "w", "d", "complexity")
SPEC_KEYS = {"title", "target", "mode", "metaphor", "groups", "pieces"}
GROUP_KEYS = {"id", "title", "description", "color"}
PIECE_KEYS = {"id", "group", "title", "description", "details", "example", "complexity", "shape",
              "x", "z", "level", "w", "d", "color"}


def cells(piece):
    """Unit cells (x, z, level) occupied by a piece."""
    height = SHAPE_HEIGHT[piece["shape"]]
    return {
        (x, z, lv)
        for x in range(piece["x"], piece["x"] + piece["w"])
        for z in range(piece["z"], piece["z"] + piece["d"])
        for lv in range(piece["level"], piece["level"] + height)
    }


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _in(value, allowed):
    """Membership test that tolerates unhashable JSON values (lists, objects)."""
    return isinstance(value, str) and value in allowed


def _check_keys(label, obj, allowed, errors):
    for key in sorted(set(obj) - allowed):
        errors.append(f"{label}: unknown field {key!r}")


def _check_text(label, obj, field, errors):
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: {field} is missing or empty")
        return False
    return True


def _check_words(label, obj, field, limit, errors):
    if _check_text(label, obj, field, errors):
        words = len(obj[field].split())
        if words > limit:
            errors.append(f"{label}: {field} has {words} words (max {limit})")


def _check_description(label, obj, errors):
    _check_words(label, obj, "description", MAX_WORDS, errors)


def _check_groups(groups, errors):
    ids = []
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            errors.append(f"group #{i}: must be an object")
            continue
        label = f"group '{g.get('id', f'#{i}')}'"
        _check_keys(label, g, GROUP_KEYS, errors)
        if _check_text(label, g, "id", errors):
            if g["id"] in ids:
                errors.append(f"duplicate group id '{g['id']}'")
            ids.append(g["id"])
        _check_text(label, g, "title", errors)
        _check_description(label, g, errors)
        if not _in(g.get("color"), PALETTE):
            errors.append(f"{label}: unknown color {g.get('color')!r}")
    return set(ids)


def _check_piece(p, group_ids, errors):
    """Field-level checks. Returns True when the piece is sound enough for geometry checks."""
    label = f"piece '{p.get('id', '?')}'"
    _check_keys(label, p, PIECE_KEYS, errors)
    ok = True
    for field in ("id", "group", "title", "shape"):
        ok &= _check_text(label, p, field, errors)
    _check_description(label, p, errors)
    _check_words(label, p, "details", MAX_DETAIL_WORDS, errors)
    if "example" in p:
        _check_words(label, p, "example", MAX_EXAMPLE_WORDS, errors)
    for field in INT_FIELDS:
        value = p.get(field)
        if not _is_int(value):
            errors.append(f"{label}: {field} must be an integer, got {value!r}")
            ok = False
        elif field in ("w", "d") and value < 1:
            errors.append(f"{label}: {field} must be >= 1")
            ok = False
        elif field in ("x", "z", "level") and value < 0:
            errors.append(f"{label}: {field} must be >= 0")
            ok = False

    if isinstance(p.get("group"), str) and p["group"] not in group_ids:
        errors.append(f"{label}: unknown group '{p['group']}'")
    if "color" in p and not _in(p["color"], PALETTE):
        errors.append(f"{label}: unknown color {p['color']!r}")
    if isinstance(p.get("shape"), str) and p["shape"] not in SHAPE_HEIGHT:
        errors.append(f"{label}: unknown shape '{p['shape']}'")
        ok = False
    if not ok:
        return False

    rule = COMPLEXITY_RULES.get(p["complexity"])
    if rule is None:
        errors.append(f"{label}: complexity must be 1-5, got {p['complexity']}")
        return False
    if ok:
        lo, hi, shapes = rule
        area = p["w"] * p["d"]
        c = p["complexity"]
        if area < lo or (hi is not None and area > hi):
            size = f"{lo}-{hi}" if hi else f">= {lo}"
            errors.append(
                f"{label}: complexity {c} needs footprint area {size}, "
                f"got {p['w']}x{p['d']}={area}"
            )
        if p["shape"] not in shapes:
            errors.append(
                f"{label}: complexity {c} cannot be a {p['shape']} "
                f"(allowed: {', '.join(sorted(shapes))})"
            )
    return ok


def _supports(owner, x, z):
    """Whether cell (x, z) on top of piece `owner` can hold a brick: tiles have no studs,
    and a slope has studs only on its back row."""
    if owner["shape"] in STUDLESS:
        return False
    if owner["shape"] == "slope" and owner["d"] > 1:
        return z == owner["z"]
    return True


def _check_geometry(pieces, errors):
    owner = {}
    clashes = {}
    for p in pieces:
        for cell in sorted(cells(p)):
            other = owner.get(cell)
            if other is None:
                owner[cell] = p
            elif other is not p:
                clashes.setdefault((p["id"], other["id"]), cell)
    for (pid, oid), (x, z, lv) in clashes.items():
        errors.append(f"piece '{pid}' overlaps '{oid}' at x={x} z={z} level={lv}")
    for p in pieces:
        if p["level"] == 0:
            continue
        supported = False
        for x in range(p["x"], p["x"] + p["w"]):
            for z in range(p["z"], p["z"] + p["d"]):
                below = owner.get((x, z, p["level"] - 1))
                if below is not None and below is not p and _supports(below, x, z):
                    supported = True
        if not supported:
            errors.append(
                f"piece '{p['id']}' is floating: nothing with studs under it at "
                f"x={p['x']} z={p['z']} level={p['level']} (tiles and slope faces do not hold bricks)"
            )


def validate(spec):
    """Return a list of human-readable errors; an empty list means the spec is valid."""
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    errors = []
    _check_keys("spec", spec, SPEC_KEYS, errors)
    for field in ("title", "metaphor"):
        _check_text("spec", spec, field, errors)
    if not _in(spec.get("mode"), MODES):
        errors.append(f"spec: mode must be one of {sorted(MODES)}, got {spec.get('mode')!r}")

    groups = spec.get("groups")
    pieces = spec.get("pieces")
    if not isinstance(groups, list) or not groups:
        errors.append("spec: groups must be a non-empty list")
        groups = []
    if not isinstance(pieces, list) or not pieces:
        errors.append("spec: pieces must be a non-empty list")
        pieces = []
    if len(groups) > MAX_GROUPS:
        errors.append(f"spec: {len(groups)} groups (max {MAX_GROUPS})")
    if len(pieces) > MAX_PIECES:
        errors.append(f"spec: {len(pieces)} pieces (max {MAX_PIECES})")

    group_ids = _check_groups(groups, errors)
    seen, sound = set(), []
    for i, p in enumerate(pieces):
        if not isinstance(p, dict):
            errors.append(f"piece #{i}: must be an object")
            continue
        pid = p.get("id")
        if isinstance(pid, str):
            if pid in seen:
                errors.append(f"duplicate piece id '{pid}'")
            seen.add(pid)
        if _check_piece(p, group_ids, errors):
            sound.append(p)

    used = {p["group"] for p in pieces if isinstance(p, dict) and isinstance(p.get("group"), str)}
    for gid in sorted(group_ids - used):
        errors.append(f"group '{gid}' has no pieces")

    _check_geometry(sound, errors)
    return errors
