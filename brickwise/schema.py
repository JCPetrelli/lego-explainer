"""Build-spec vocabulary: palette, shapes, and the complexity-to-size rules."""

PALETTE = {
    "red": "#c91a09",
    "blue": "#0055bf",
    "yellow": "#f2cd37",
    "green": "#237841",
    "dark-green": "#184632",
    "orange": "#fe8a18",
    "white": "#f4f4f4",
    "light-grey": "#a0a5a9",
    "dark-grey": "#6c6e68",
    "black": "#1b2a34",
    "tan": "#e4cd9e",
    "azure": "#36aebf",
}

# Height of each shape, in plates (a brick is three plates tall).
SHAPE_HEIGHT = {"brick": 3, "slope": 3, "plate": 1, "tile": 1}
STUDLESS = {"tile"}

# complexity -> (min footprint area, max area or None, allowed shapes)
COMPLEXITY_RULES = {
    1: (1, 2, {"plate", "tile"}),
    2: (2, 4, {"brick", "plate", "slope"}),
    3: (6, 8, {"brick", "plate", "slope"}),
    4: (12, 16, {"brick", "plate", "slope"}),
    5: (24, None, {"brick", "plate"}),
}

MODES = {"themed", "stack"}
MAX_WORDS = 40          # short description (bold line in the popup)
MAX_DETAIL_WORDS = 120  # longer explanation
MAX_EXAMPLE_WORDS = 60  # optional concrete example
MAX_GROUPS = 8
MAX_PIECES = 40
