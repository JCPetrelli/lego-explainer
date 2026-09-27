"""Validate a build spec: schema, references, complexity-to-size, overlaps and support."""

from .schema import (
    COMPLEXITY_RULES,
    MAX_GROUPS,
    MAX_PIECES,
    MAX_WORDS,
    MODES,
    PALETTE,
    SHAPE_HEIGHT,
)

INT_FIELDS = ("x", "z", "level", "w", "d", "complexity")
TEXT_FIELDS = ("id", "group", "title", "description", "shape")


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


def _check_text(label, obj, field, errors):
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: {field} is missing or empty")
        return False
    return True


def _check_description(label, obj, errors):
    if _check_text(label, obj, "description", errors):
        words = len(obj["description"].split())
        if words > MAX_WORDS:
            errors.append(f"{label}: description has {words} words (max {MAX_WORDS})")


def _check_groups(groups, errors):
    ids = []
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            errors.append(f"group #{i}: must be an object")
            continue
        label = f"group '{g.get('id', f'#{i}')}'"
        if _check_text(label, g, "id", errors):
            if g["id"] in ids:
                errors.append(f"duplicate group id '{g['id']}'")
            ids.append(g["id"])
        _check_text(label, g, "title", errors)
        _check_description(label, g, errors)
        if g.get("color") not in PALETTE:
            errors.append(f"{label}: unknown color {g.get('color')!r}")
    return set(ids)


def _check_piece(p, group_ids, errors):
    """Field-level checks. Returns True when the piece is sound enough for geometry checks."""
    label = f"piece '{p.get('id', '?')}'"
    ok = True
    for field in ("id", "group", "title", "shape"):
        ok &= _check_text(label, p, field, errors)
    _check_description(label, p, errors)
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
    if "color" in p and p["color"] not in PALETTE:
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


def _check_geometry(pieces, errors):
    owner = {}
    for p in pieces:
        for cell in sorted(cells(p)):
            other = owner.get(cell)
            if other is not None and other != p["id"]:
                x, z, lv = cell
                errors.append(f"piece '{p['id']}' overlaps '{other}' at x={x} z={z} level={lv}")
                break
            owner[cell] = p["id"]
    for p in pieces:
        if p["level"] == 0:
            continue
        below = [
            owner.get((x, z, p["level"] - 1))
            for x in range(p["x"], p["x"] + p["w"])
            for z in range(p["z"], p["z"] + p["d"])
        ]
        if not any(o is not None and o != p["id"] for o in below):
            errors.append(
                f"piece '{p['id']}' is floating: nothing under it at "
                f"x={p['x']} z={p['z']} level={p['level']}"
            )


def validate(spec):
    """Return a list of human-readable errors; an empty list means the spec is valid."""
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]
    errors = []
    for field in ("title", "metaphor"):
        _check_text("spec", spec, field, errors)
    if spec.get("mode") not in MODES:
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
        if isinstance(pid, str) and pid in seen:
            errors.append(f"duplicate piece id '{pid}'")
        seen.add(pid)
        if _check_piece(p, group_ids, errors):
            sound.append(p)

    used = {p.get("group") for p in pieces if isinstance(p, dict)}
    for gid in sorted(group_ids - used):
        errors.append(f"group '{gid}' has no pieces")

    _check_geometry(sound, errors)
    return errors
