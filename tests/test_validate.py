import copy
import json
from pathlib import Path

from lego_explainer.validate import cells, validate

SAMPLES = sorted((Path(__file__).parent.parent / "samples").glob("*.json"))


def base_spec():
    return {
        "title": "Tiny",
        "target": "a topic",
        "mode": "stack",
        "metaphor": "Two layers.",
        "groups": [
            {"id": "base", "title": "Base", "description": "The ground.", "color": "dark-grey"},
            {"id": "top", "title": "Top", "description": "What sits on it.", "color": "red"},
        ],
        "pieces": [
            {"id": "floor", "group": "base", "title": "Floor", "description": "Holds everything.",
             "complexity": 3, "shape": "brick", "x": 0, "z": 0, "level": 0, "w": 2, "d": 4},
            {"id": "roof", "group": "top", "title": "Roof", "description": "Sits on the floor.",
             "complexity": 2, "shape": "brick", "x": 0, "z": 0, "level": 3, "w": 2, "d": 2},
        ],
    }


def piece(spec, pid):
    return next(p for p in spec["pieces"] if p["id"] == pid)


def test_valid_spec_has_no_errors():
    assert validate(base_spec()) == []


def test_samples_exist_and_are_valid():
    assert SAMPLES, "samples/ must contain example specs"
    for f in SAMPLES:
        assert validate(json.loads(f.read_text())) == [], f.name


def test_cells_counts_footprint_times_height():
    p = {"x": 1, "z": 2, "level": 0, "w": 2, "d": 3, "shape": "brick"}
    assert len(cells(p)) == 2 * 3 * 3
    assert (1, 2, 0) in cells(p) and (2, 4, 2) in cells(p)


def test_overlap_reported():
    s = base_spec()
    piece(s, "roof")["level"] = 2  # sinks into the floor
    errs = validate(s)
    assert any("overlaps" in e and "roof" in e and "floor" in e for e in errs)


def test_floating_reported():
    s = base_spec()
    piece(s, "roof")["level"] = 5
    assert any("floating" in e and "roof" in e for e in validate(s))


def test_level0_rests_on_baseplate():
    s = base_spec()
    piece(s, "roof").update(x=5, level=0)
    assert validate(s) == []


def test_negative_level_rejected():
    s = base_spec()
    piece(s, "roof")["level"] = -1
    assert any("level" in e for e in validate(s))


def test_complexity_size_mismatch():
    s = base_spec()
    piece(s, "roof")["complexity"] = 4  # 2x2 is too small for 4
    assert any("complexity 4" in e for e in validate(s))


def test_shape_not_allowed_for_complexity():
    s = base_spec()
    piece(s, "roof").update(complexity=1, w=1, d=1)  # still a brick
    assert any("complexity 1" in e and "brick" in e for e in validate(s))


def test_unknown_refs():
    s = base_spec()
    s["mode"] = "tower"
    piece(s, "roof").update(group="nope", color="purple", shape="sphere")
    errs = " ".join(validate(s))
    for word in ("mode", "group", "color", "shape"):
        assert word in errs


def test_duplicate_ids():
    s = base_spec()
    s["pieces"].append(dict(piece(s, "roof"), x=5, level=0))
    s["groups"].append(dict(s["groups"][0]))
    errs = validate(s)
    assert any("duplicate piece id 'roof'" in e for e in errs)
    assert any("duplicate group id 'base'" in e for e in errs)


def test_description_rules():
    s = base_spec()
    piece(s, "roof")["description"] = " "
    piece(s, "floor")["description"] = "word " * 41
    errs = validate(s)
    assert any("roof" in e and "description" in e for e in errs)
    assert any("floor" in e and "41 words" in e for e in errs)


def test_group_without_pieces_and_limits():
    s = base_spec()
    s["groups"].append({"id": "empty", "title": "E", "description": "Nothing.", "color": "blue"})
    assert any("group 'empty' has no pieces" in e for e in validate(s))
    s = base_spec()
    s["groups"] += [{"id": f"g{i}", "title": "G", "description": "x", "color": "blue"} for i in range(8)]
    assert any("groups" in e and "8" in e for e in validate(s))


def test_too_many_pieces():
    s = base_spec()
    s["pieces"] = [
        {"id": f"p{i}", "group": "base", "title": "P", "description": "x", "complexity": 1,
         "shape": "tile", "x": i, "z": 0, "level": 0, "w": 1, "d": 1}
        for i in range(41)
    ]
    s["groups"] = s["groups"][:1]
    assert any("41 pieces" in e for e in validate(s))


def test_collects_all_errors():
    s = base_spec()
    s["mode"] = "tower"
    piece(s, "roof")["level"] = 5
    piece(s, "floor")["description"] = ""
    assert len(validate(s)) >= 3


def test_bad_types_do_not_crash():
    s = base_spec()
    piece(s, "roof").update(x="a", w=0)
    del piece(s, "floor")["complexity"]
    errs = validate(s)
    assert any("roof" in e and "x" in e for e in errs)
    assert any("roof" in e and "w" in e for e in errs)
    assert any("floor" in e and "complexity" in e for e in errs)
    assert validate({}) != []
    assert validate([]) != []
    assert validate({"groups": "x", "pieces": None}) != []


def test_non_string_values_do_not_crash():
    for mutate in (
        lambda s: s.update(mode=[]),
        lambda s: s["groups"][0].update(color={}),
        lambda s: piece(s, "roof").update(id=["a"]),
        lambda s: piece(s, "roof").update(group=["a"]),
        lambda s: piece(s, "roof").update(color=["a"]),
    ):
        s = base_spec()
        mutate(s)
        assert validate(s) != []


def test_unknown_keys_rejected():
    s = base_spec()
    s["colour"] = "red"
    s["groups"][0]["colour"] = "red"
    piece(s, "roof")["colour"] = "red"
    errs = validate(s)
    assert sum("unknown field 'colour'" in e for e in errs) == 3


def test_nothing_rests_on_a_tile():
    s = base_spec()
    piece(s, "floor").update(shape="tile", complexity=1, w=1, d=2, level=0)
    piece(s, "roof").update(complexity=2, w=1, d=2, level=1)
    assert any("floating" in e and "roof" in e for e in validate(s))


def test_slope_supports_only_its_back_row():
    s = base_spec()
    piece(s, "floor").update(shape="slope", complexity=3, w=2, d=4)
    piece(s, "roof").update(z=2, level=3, w=2, d=2)  # sits on the slanted face
    assert any("floating" in e and "roof" in e for e in validate(s))
    piece(s, "roof").update(z=0, w=1, d=2)  # half on the stud row: fine
    piece(s, "roof")["w"] = 2
    assert validate(s) == []


def test_overlap_keeps_registering_cells():
    s = base_spec()
    # 'mid' overlaps 'floor' at z=0..3 and also covers z=4..5; 'late' overlaps mid at z=5.
    s["pieces"].append({"id": "mid", "group": "base", "title": "M", "description": "x",
                        "complexity": 3, "shape": "plate", "x": 0, "z": 2, "level": 0, "w": 2, "d": 4})
    s["pieces"].append({"id": "late", "group": "base", "title": "L", "description": "x",
                        "complexity": 2, "shape": "plate", "x": 0, "z": 5, "level": 0, "w": 2, "d": 1})
    errs = validate(s)
    assert any("'late' overlaps 'mid'" in e for e in errs)
    assert sum("'mid' overlaps 'floor'" in e for e in errs) == 1
