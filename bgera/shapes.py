#!/usr/bin/env python
# coding: utf-8
"""
Every shape the student can make, and the OpenSCAD code behind it.

A shape is described by:
    words     the plain words the student may type for it
    needs     the measurements it uses, in the order they are spoken
    defaults  a sensible size, so a shape always appears even before the
              student has given any numbers
    scad      a function that turns the measurements into OpenSCAD code

Adding a new shape means adding one entry to SHAPES.  Nothing else in the
app has to change.
"""

import math

from . import braille as braille_mod

SMOOTH = 96          # segments used for round things
SMOOTH_SMALL = 48


def _f(value):
    """Format a number for OpenSCAD without a trailing .0 everywhere."""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------------------
# The shape catalogue
# ---------------------------------------------------------------------------

def _cube(p):
    return f"cube([{_f(p['width'])},{_f(p['length'])},{_f(p['height'])}], center=true);"


def _ball(p):
    return f"sphere(d={_f(p['across'])}, $fn={SMOOTH});"


def _rod(p):
    return f"cylinder(h={_f(p['height'])}, d={_f(p['across'])}, $fn={SMOOTH}, center=true);"


def _cone(p):
    top = p.get("top", 0)
    return (f"cylinder(h={_f(p['height'])}, d1={_f(p['across'])}, d2={_f(top)}, "
            f"$fn={SMOOTH}, center=true);")


def _pyramid(p):
    sides = max(3, int(p["sides"]))
    # Turn it so one flat face points forward, which is easier to feel.
    return (f"rotate([0,0,{180.0 / sides:.3f}])"
            f"cylinder(h={_f(p['height'])}, d1={_f(p['across'])}, d2=0, "
            f"$fn={sides}, center=true);")


def _prism(p):
    sides = max(3, int(p["sides"]))
    return (f"rotate([0,0,{180.0 / sides:.3f}])"
            f"cylinder(h={_f(p['height'])}, d={_f(p['across'])}, "
            f"$fn={sides}, center=true);")


def _tube(p):
    outer = p["across"]
    inner = max(0.2, outer - 2 * p["thick"])
    return ("difference(){"
            f"cylinder(h={_f(p['height'])}, d={_f(outer)}, $fn={SMOOTH}, center=true);"
            f"cylinder(h={_f(p['height'] + 2)}, d={_f(inner)}, $fn={SMOOTH}, center=true);"
            "}")


def _donut(p):
    # The ring has to sit clear of the middle, or the shape turns itself
    # inside out.  If the student asks for a fatter ring than will fit, the
    # ring is thinned rather than refused.
    across = p["across"]
    thick = min(p["thick"], across / 2.0 * 0.98)
    ring = max(thick / 2.0 + 0.05, across / 2.0 - thick / 2.0)
    return ("rotate_extrude($fn=%d)translate([%s,0,0])circle(d=%s, $fn=%d);"
            % (SMOOTH, _f(round(ring, 3)), _f(round(thick, 3)), SMOOTH_SMALL))


def _wedge(p):
    w, l, h = p["width"], p["length"], p["height"]
    return ("translate([%s,%s,%s])"
            "polyhedron(points=[[0,0,0],[%s,0,0],[%s,%s,0],[0,%s,0],[0,0,%s],[%s,0,%s]],"
            "faces=[[0,1,2,3],[0,4,5,1],[1,5,2],[2,5,4,3],[3,4,0]]);"
            % (_f(-w / 2.0), _f(-l / 2.0), _f(-h / 2.0),
               _f(w), _f(w), _f(l), _f(l), _f(h), _f(w), _f(h)))


def _star(p):
    points = max(3, int(p["points"]))
    outer = p["across"] / 2.0
    inner = outer * 0.45
    step = 360.0 / points
    coords = []
    for i in range(points):
        a_out = i * step
        a_in = a_out + step / 2.0
        for radius, angle in ((outer, a_out), (inner, a_in)):
                        coords.append("[%.3f,%.3f]" % (radius * math.cos(math.radians(angle)),
                                           radius * math.sin(math.radians(angle))))
    return (f"linear_extrude(height={_f(p['height'])}, center=true)"
            "polygon(points=[" + ",".join(coords) + "]);")


def _plate(p):
    return f"cube([{_f(p['width'])},{_f(p['length'])},{_f(p['height'])}], center=true);"


def _ring(p):
    outer = p["across"]
    inner = max(0.2, outer - 2 * p["thick"])
    return ("difference(){"
            f"cylinder(h={_f(p['height'])}, d={_f(outer)}, $fn={SMOOTH}, center=true);"
            f"cylinder(h={_f(p['height'] + 2)}, d={_f(inner)}, $fn={SMOOTH}, center=true);"
            "}")


def _text(p):
    words = str(p.get("words", "")).replace('"', "")
    size = p.get("height", 10)
    thick = p.get("thick", 3)
    # No font is named on purpose.  OpenSCAD then uses whatever the
    # computer has, which works on every machine in the classroom.  Naming
    # a font that is missing gives an empty model and a puzzled student.
    return (f'linear_extrude(height={_f(thick)}, center=true)'
            f'text("{words}", size={_f(size)}, halign="center", '
            f'valign="center", $fn={SMOOTH_SMALL});')


def _braille(p):
    words = str(p.get("words", ""))
    plate = bool(p.get("plate", True))
    plate_height = p.get("thick", 2)
    code, cells, width, skipped = braille_mod.scad_line(
        words, plate=plate, plate_height=plate_height,
        capitals=bool(p.get("capitals", False)))
    p["_braille_cells"] = cells
    p["_braille_width"] = width
    p["_braille_skipped"] = skipped
    # Centre it, so it behaves like every other shape.
    dx = -width / 2.0
    dy = braille_mod.DOT_GAP
    return f"translate([{dx:.2f},{dy:.2f},{-plate_height / 2.0:.2f}]){{{code}}}"


SHAPES = {
    "cube": {
        "words": ["cube", "box", "brick", "block"],
        "needs": ["width", "length", "height"],
        "defaults": {"width": 20, "length": 20, "height": 20},
        "scad": _cube,
        "hint": "shape_hint_cube",
    },
    "ball": {
        "words": ["ball", "sphere", "globe"],
        "needs": ["across"],
        "defaults": {"across": 20},
        "scad": _ball,
        "hint": "shape_hint_ball",
    },
    "rod": {
        "words": ["rod", "cylinder", "stick", "pole"],
        "needs": ["across", "height"],
        "defaults": {"across": 20, "height": 20},
        "scad": _rod,
        "hint": "shape_hint_rod",
    },
    "cone": {
        "words": ["cone"],
        "needs": ["across", "height"],
        "defaults": {"across": 20, "height": 20, "top": 0},
        "scad": _cone,
        "hint": "shape_hint_cone",
    },
    "pyramid": {
        "words": ["pyramid"],
        "needs": ["across", "height", "sides"],
        "defaults": {"across": 20, "height": 20, "sides": 4},
        "scad": _pyramid,
        "hint": "shape_hint_pyramid",
    },
    "prism": {
        "words": ["prism", "hexagon", "nut"],
        "needs": ["across", "height", "sides"],
        "defaults": {"across": 20, "height": 20, "sides": 6},
        "scad": _prism,
        "hint": "shape_hint_prism",
    },
    "tube": {
        "words": ["tube", "pipe", "straw"],
        "needs": ["across", "height", "thick"],
        "defaults": {"across": 20, "height": 20, "thick": 2},
        "scad": _tube,
        "hint": "shape_hint_tube",
    },
    "donut": {
        "words": ["donut", "doughnut", "torus", "hoop"],
        "needs": ["across", "thick"],
        "defaults": {"across": 30, "thick": 8},
        "scad": _donut,
        "hint": "shape_hint_donut",
    },
    "wedge": {
        "words": ["wedge", "ramp", "slope", "triangle"],
        "needs": ["width", "length", "height"],
        "defaults": {"width": 20, "length": 30, "height": 15},
        "scad": _wedge,
        "hint": "shape_hint_wedge",
    },
    "star": {
        "words": ["star"],
        "needs": ["across", "height", "points"],
        "defaults": {"across": 40, "height": 5, "points": 5},
        "scad": _star,
        "hint": "shape_hint_star",
    },
    "plate": {
        "words": ["plate", "slab", "tile", "card"],
        "needs": ["width", "length", "height"],
        "defaults": {"width": 80, "length": 30, "height": 3},
        "scad": _plate,
        "hint": "shape_hint_plate",
    },
    "ring": {
        "words": ["ring", "washer", "bangle"],
        "needs": ["across", "height", "thick"],
        "defaults": {"across": 20, "height": 4, "thick": 2},
        "scad": _ring,
        "hint": "shape_hint_ring",
    },
    "text": {
        "words": ["text", "word", "letters", "name", "writing"],
        "needs": ["height", "thick"],
        "defaults": {"height": 10, "thick": 3, "words": ""},
        "scad": _text,
        "takes_words": True,
        "hint": "shape_hint_text",
    },
    "braille": {
        "words": ["braille", "dots"],
        "needs": ["thick"],
        "defaults": {"thick": 2, "words": "", "plate": True},
        "scad": _braille,
        "takes_words": True,
        "hint": "shape_hint_braille",
    },
}

# word -> shape key
SHAPE_WORDS = {}
for _key, _info in SHAPES.items():
    SHAPE_WORDS[_key] = _key
    for _word in _info["words"]:
        SHAPE_WORDS[_word] = _key


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------
# The plain word a student says, and the measurement it sets.

MEASURE_WORDS = {
    "width": "width", "wide": "width", "w": "width",
    "length": "length", "long": "length", "deep": "length", "depth": "length", "l": "length",
    "height": "height", "tall": "height", "high": "height", "h": "height",
    "across": "across", "wide across": "across", "diameter": "across", "d": "across",
    "radius": "radius", "r": "radius",
    "thick": "thick", "thickness": "thick", "wall": "thick", "t": "thick",
    "sides": "sides", "faces": "sides", "n": "sides",
    "points": "points", "p": "points",
    "top": "top",
}

# Measurements that must stay above zero, and their sensible limits.
LIMITS = {
    "width": (0.2, 500), "length": (0.2, 500), "height": (0.2, 500),
    "across": (0.2, 500), "radius": (0.1, 250), "thick": (0.1, 100),
    "sides": (3, 64), "points": (3, 40), "top": (0, 500),
}


def measurement_for(word):
    """Which measurement does this word set?  None if it is not one."""
    return MEASURE_WORDS.get(word.lower())


def shape_for(word):
    """Which shape does this word make?  None if it is not one."""
    return SHAPE_WORDS.get(word.lower())


def scad_for(shape_key, params):
    """The OpenSCAD code for one shape, before it is moved or turned."""
    info = SHAPES[shape_key]
    values = dict(info["defaults"])
    values.update({k: v for k, v in params.items() if v is not None})
    if "radius" in values and values.get("radius"):
        values["across"] = values["radius"] * 2
    return info["scad"](values)


def describe_size(shape_key, params):
    """A short spoken description of a shape's measurements."""
    info = SHAPES[shape_key]
    values = dict(info["defaults"])
    values.update({k: v for k, v in params.items() if v is not None})
    if shape_key == "braille":
        words = values.get("words", "")
        cells, skipped = braille_mod.to_cells(str(words))
        width = round(braille_mod.cells_width(cells)
                      + 2 * braille_mod.PLATE_MARGIN, 1)
        return (f'saying "{words}" in braille, {len(cells)} cells, '
                f'{_f(width)} millimetres wide')
    if shape_key == "text":
        words = values.get("words", "")
        return (f'saying "{words}", letters {_f(values.get("height", 10))} '
                f'millimetres tall, standing {_f(values.get("thick", 3))} '
                f'millimetres up')
    bits = []
    for need in info["needs"]:
        value = values.get(need)
        if value is None:
            continue
        if need == "sides":
            bits.append(f"{int(value)} sides")
        elif need == "points":
            bits.append(f"{int(value)} points")
        else:
            bits.append(f"{need} {_f(value)}")
    return ", ".join(bits) + " millimetres" if bits else "no size yet"
