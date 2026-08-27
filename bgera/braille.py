#!/usr/bin/env python
# coding: utf-8
"""
Grade 1 (uncontracted) braille, turned into printable dots.

Sizes follow the Marburg Medium standard, which is what most braille
readers are used to:

    dot base across        1.5 mm
    dot height             0.6 mm
    dots inside a cell     2.5 mm apart
    cell to cell           6.0 mm
    line to line          10.0 mm

A cell is six dots, numbered like this:

        1  4
        2  5
        3  6

A note on how the dots are made.  The obvious way is a sphere per dot,
squashed and then cut off flat.  That works, but OpenSCAD takes about
twenty seconds over a four letter name and over a minute over a sentence,
because it has to union twenty separate solids and then intersect the lot.
A student typing `braille nino` should not wait twenty seconds.

So the dots are built here instead, as one mesh handed to OpenSCAD as a
single polyhedron, sunk a hair into the plate so the two solids properly
overlap rather than meeting on a shared plane.  Same shape, same standard
sizes, about twenty five times quicker.
"""

import math

DOT_ACROSS = 1.5
DOT_HEIGHT = 0.6
DOT_GAP = 2.5      # between dots inside one cell
CELL_GAP = 6.0     # between the left columns of two cells
LINE_GAP = 10.0    # between the top rows of two lines
PLATE_MARGIN = 4.0

# How finely a dot is drawn, and how far it sinks into the plate.
DOT_SIDES = 16     # around the dot; finer than the printer can manage anyway
DOT_RINGS = 4      # from the top of the dot down to its base
SINK = 0.05        # mm, so the dot and the plate overlap instead of touching

LETTERS = {
    "a": (1,), "b": (1, 2), "c": (1, 4), "d": (1, 4, 5), "e": (1, 5),
    "f": (1, 2, 4), "g": (1, 2, 4, 5), "h": (1, 2, 5), "i": (2, 4),
    "j": (2, 4, 5), "k": (1, 3), "l": (1, 2, 3), "m": (1, 3, 4),
    "n": (1, 3, 4, 5), "o": (1, 3, 5), "p": (1, 2, 3, 4),
    "q": (1, 2, 3, 4, 5), "r": (1, 2, 3, 5), "s": (2, 3, 4),
    "t": (2, 3, 4, 5), "u": (1, 3, 6), "v": (1, 2, 3, 6),
    "w": (2, 4, 5, 6), "x": (1, 3, 4, 6), "y": (1, 3, 4, 5, 6),
    "z": (1, 3, 5, 6),
}

PUNCTUATION = {
    " ": (),
    ",": (2,),
    ";": (2, 3),
    ":": (2, 5),
    ".": (2, 5, 6),
    "?": (2, 3, 6),
    "!": (2, 3, 5),
    "'": (3,),
    "-": (3, 6),
}

NUMBER_SIGN = (3, 4, 5, 6)
CAPITAL_SIGN = (6,)

DIGITS = {
    "1": LETTERS["a"], "2": LETTERS["b"], "3": LETTERS["c"],
    "4": LETTERS["d"], "5": LETTERS["e"], "6": LETTERS["f"],
    "7": LETTERS["g"], "8": LETTERS["h"], "9": LETTERS["i"],
    "0": LETTERS["j"],
}

# Where each dot number sits inside a cell, as (column, row) counted from
# the top left.
DOT_POSITION = {
    1: (0, 0), 2: (0, 1), 3: (0, 2),
    4: (1, 0), 5: (1, 1), 6: (1, 2),
}


# ---------------------------------------------------------------------------
# Words to cells
# ---------------------------------------------------------------------------

def to_cells(words, capitals=False):
    """
    Turn a line of writing into a list of cells.

    Returns (cells, skipped) where cells is a list of dot-number tuples and
    skipped is the characters that have no braille sign here.
    """
    cells = []
    skipped = []
    in_number = False

    for char in words:
        lower = char.lower()

        if char.isdigit():
            if not in_number:
                cells.append(NUMBER_SIGN)
                in_number = True
            cells.append(DIGITS[char])
            continue

        # Any non-digit ends a number run.
        if in_number:
            in_number = False

        if lower in LETTERS:
            if capitals and char.isupper():
                cells.append(CAPITAL_SIGN)
            cells.append(LETTERS[lower])
        elif lower in PUNCTUATION:
            cells.append(PUNCTUATION[lower])
        else:
            if char not in skipped:
                skipped.append(char)

    return cells, skipped


def cells_width(cells):
    """How wide a row of cells is, in millimetres, dots only."""
    if not cells:
        return 0.0
    return (len(cells) - 1) * CELL_GAP + DOT_GAP + DOT_ACROSS


def dot_positions(cells):
    """Where every dot of every cell sits, as (x, y) in millimetres."""
    places = []
    for index, dots in enumerate(cells):
        x0 = index * CELL_GAP
        for dot in sorted(dots):
            col, row = DOT_POSITION[dot]
            places.append((x0 + col * DOT_GAP, -row * DOT_GAP))
    return places


# ---------------------------------------------------------------------------
# Cells to a printable mesh
# ---------------------------------------------------------------------------

def _dome(cx, cy, cz, across=DOT_ACROSS, height=DOT_HEIGHT,
          sides=DOT_SIDES, rings=DOT_RINGS, sink=SINK):
    """
    One braille dot: a rounded dome standing on z = cz.

    Returns (points, faces).  The dome is a closed solid, so many of them
    can be handed to OpenSCAD as one polyhedron.  Faces are wound so their
    outsides face out; get that wrong and the printer hollows out the model
    instead of filling it.
    """
    a = across / 2.0
    radius = (a * a + height * height) / (2 * height)
    centre = height - radius
    widest = math.acos((radius - height) / radius)

    points = [(cx, cy, cz + height)]                 # the very top
    for ring in range(1, rings + 1):
        angle = widest * ring / rings
        out = radius * math.sin(angle)
        up = max(centre + radius * math.cos(angle), 0.0)
        if ring == rings:
            up = -sink                                # a hair into the plate
        for side in range(sides):
            around = 2 * math.pi * side / sides
            points.append((cx + out * math.cos(around),
                           cy + out * math.sin(around),
                           cz + up))

    faces = [[0, 1 + (side + 1) % sides, 1 + side] for side in range(sides)]
    for ring in range(rings - 1):
        upper = 1 + ring * sides
        lower = 1 + (ring + 1) * sides
        for side in range(sides):
            following = (side + 1) % sides
            faces.append([upper + side, upper + following,
                          lower + following, lower + side])
    bottom = 1 + (rings - 1) * sides
    faces.append([bottom + side for side in range(sides)])

    return points, faces


def scad_dots(cells, plate_height=0.0):
    """OpenSCAD for the dots of one line of braille, as a single solid."""
    places = dot_positions(cells)
    if not places:
        return ""

    points = []
    faces = []
    for x, y in places:
        dome_points, dome_faces = _dome(x, y, plate_height)
        offset = len(points)
        points.extend(dome_points)
        faces.extend([[index + offset for index in face] for face in dome_faces])

    listed_points = ",".join(f"[{x:.4f},{y:.4f},{z:.4f}]" for x, y, z in points)
    listed_faces = ",".join("[" + ",".join(str(i) for i in face) + "]"
                            for face in faces)
    return (f"polyhedron(points=[{listed_points}], faces=[{listed_faces}], "
            f"convexity=8);")


def scad_line(words, plate=True, plate_height=2.0, capitals=False):
    """
    OpenSCAD code for one line of braille, optionally on a backing plate.

    Returns (scad_code, cell_count, width_mm, skipped_characters).
    """
    cells, skipped = to_cells(words, capitals=capitals)
    dots_width = cells_width(cells)
    base_height = plate_height if plate else 0.0

    parts = []
    if plate and cells:
        width = dots_width + 2 * PLATE_MARGIN
        depth = 2 * DOT_GAP + DOT_ACROSS + 2 * PLATE_MARGIN
        parts.append(
            f"translate([{-PLATE_MARGIN - radius_offset():.2f},"
            f"{-2 * DOT_GAP - PLATE_MARGIN - radius_offset():.2f},0])"
            f"cube([{width:.2f},{depth:.2f},{plate_height:.2f}]);"
        )

    dots = scad_dots(cells, plate_height=base_height)
    if dots:
        parts.append(dots)

    if not parts:
        return "cube([0.1,0.1,0.1]);", 0, 0.0, skipped

    code = "union(){\n" + "\n".join(parts) + "\n}"
    return code, len(cells), round(dots_width, 1), skipped


def radius_offset():
    return DOT_ACROSS / 2.0
