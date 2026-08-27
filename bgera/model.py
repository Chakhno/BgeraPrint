#!/usr/bin/env python
# coding: utf-8
"""
The model the student is building.

A model is a list of named parts.  Each part knows its shape, its
measurements, where it sits, how it is turned, and any extra treatment such
as rounded edges or copies.

Everything that changes the model goes through Model.change(), which keeps a
history so that undo and redo always work.  A student who cannot see the
screen must be able to step back safely.
"""

import copy
import json
import time
from pathlib import Path

from . import shapes as shapes_mod

# The words used to talk about directions, and what they do to x, y, z.
DIRECTIONS = {
    "right": (1, 0, 0), "left": (-1, 0, 0),
    "forward": (0, 1, 0), "back": (0, -1, 0), "backward": (0, -1, 0),
    "up": (0, 0, 1), "down": (0, 0, -1),
    "east": (1, 0, 0), "west": (-1, 0, 0),
    "north": (0, 1, 0), "south": (0, -1, 0),
}

# Which line you turn around.  Students hear "the up line", not "the z axis".
TURN_AXES = {
    "flat": "z", "around": "z", "z": "z", "up": "z", "upright": "z",
    "forward": "y", "y": "y", "over": "y",
    "sideways": "x", "x": "x", "tip": "x",
}

AXIS_NAMES = {"x": "sideways", "y": "forward", "z": "upright"}


def _f(value):
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(round(value, 4) if isinstance(value, float) else value)


def _tidy(value):
    """A number fit to be read aloud: 30 rather than 30.0."""
    value = round(value, 1)
    return int(value) if value == int(value) else value


class Part:
    """One shape in the model."""

    def __init__(self, name, shape, params=None):
        self.name = name
        self.shape = shape
        self.params = dict(params or {})
        self.pos = [0.0, 0.0, 0.0]
        self.turn = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]
        self.mirror = None          # "x", "y" or "z"
        self.round_by = 0.0         # rounded edges, in millimetres
        self.smooth = False         # smooth skin (hull)
        self.hollow = 0.0           # wall thickness if hollowed out
        self.repeat = None          # {"count":n, "gap":mm, "dir":"right"}
        self.circle_repeat = None   # {"count":n, "across":mm}
        self.role = "solid"         # "solid" or "hole"

    # -- OpenSCAD ---------------------------------------------------------

    def body_scad(self):
        code = shapes_mod.scad_for(self.shape, self.params)

        if self.hollow:
            code = self._hollow_scad(code)
        if self.round_by:
            code = (f"minkowski(){{ {code} "
                    f"sphere(r={_f(self.round_by)}, $fn=24); }}")
        if self.smooth:
            code = f"hull(){{ {code} }}"
        return code

    def _hollow_scad(self, code):
        """Shell the shape: keep only a wall of the given thickness."""
        inner = shapes_mod.scad_for(self.shape, self._shrunk_params())
        return f"difference(){{ {code} {inner} }}"

    def _shrunk_params(self):
        smaller = dict(self.params)
        for key in ("width", "length", "across"):
            if key in smaller and smaller[key]:
                smaller[key] = max(0.2, smaller[key] - 2 * self.hollow)
        if "height" in smaller and smaller["height"]:
            # Leave the bottom closed and open the top, which prints well.
            smaller["height"] = smaller["height"]
        return smaller

    def placed_scad(self):
        code = self.body_scad()

        if self.mirror:
            vec = {"x": "[1,0,0]", "y": "[0,1,0]", "z": "[0,0,1]"}[self.mirror]
            code = f"mirror({vec}){{ {code} }}"

        if self.scale != [1.0, 1.0, 1.0]:
            code = (f"scale([{_f(self.scale[0])},{_f(self.scale[1])},"
                    f"{_f(self.scale[2])}]){{ {code} }}")

        if any(self.turn):
            code = (f"rotate([{_f(self.turn[0])},{_f(self.turn[1])},"
                    f"{_f(self.turn[2])}]){{ {code} }}")

        code = (f"translate([{_f(self.pos[0])},{_f(self.pos[1])},"
                f"{_f(self.pos[2])}]){{ {code} }}")

        if self.repeat:
            dx, dy, dz = DIRECTIONS.get(self.repeat["dir"], (1, 0, 0))
            gap = self.repeat["gap"]
            copies = []
            for i in range(int(self.repeat["count"])):
                copies.append(
                    f"translate([{_f(dx * gap * i)},{_f(dy * gap * i)},"
                    f"{_f(dz * gap * i)}]){{ {code} }}")
            code = "union(){" + "".join(copies) + "}"

        if self.circle_repeat:
            count = int(self.circle_repeat["count"])
            radius = self.circle_repeat["across"] / 2.0
            copies = []
            for i in range(count):
                angle = 360.0 * i / count
                copies.append(
                    f"rotate([0,0,{angle:.3f}])translate([{_f(radius)},0,0])"
                    f"{{ {code} }}")
            code = "union(){" + "".join(copies) + "}"

        return code

    # -- size -------------------------------------------------------------

    def rough_size(self):
        """
        A quick estimate of how big this part is, in millimetres.
        Used for talking to the student and for stacking parts.
        The exact size always comes from the slicer after the model is built.
        """
        info = shapes_mod.SHAPES[self.shape]
        values = dict(info["defaults"])
        values.update({k: v for k, v in self.params.items() if v is not None})

        if self.shape in ("cube", "plate", "wedge"):
            size = [values["width"], values["length"], values["height"]]
        elif self.shape == "ball":
            size = [values["across"]] * 3
        elif self.shape in ("rod", "cone", "pyramid", "prism", "tube", "ring"):
            size = [values["across"], values["across"], values["height"]]
        elif self.shape == "donut":
            outer = values["across"] + values["thick"]
            size = [outer, outer, values["thick"]]
        elif self.shape == "star":
            size = [values["across"], values["across"], values["height"]]
        elif self.shape == "text":
            words = str(values.get("words", ""))
            size = [max(1, len(words)) * values["height"] * 0.62,
                    values["height"], values["thick"]]
        elif self.shape == "braille":
            from . import braille as braille_mod
            cells, _ = braille_mod.to_cells(str(values.get("words", "")))
            size = [braille_mod.cells_width(cells) + 2 * braille_mod.PLATE_MARGIN,
                    2 * braille_mod.DOT_GAP + braille_mod.DOT_ACROSS
                    + 2 * braille_mod.PLATE_MARGIN,
                    values["thick"] + braille_mod.DOT_HEIGHT]
        else:
            size = [20.0, 20.0, 20.0]

        size = [s + 2 * self.round_by for s in size]
        size = [s * f for s, f in zip(size, self.scale)]

        if self.repeat:
            dx, dy, dz = DIRECTIONS.get(self.repeat["dir"], (1, 0, 0))
            span = self.repeat["gap"] * (int(self.repeat["count"]) - 1)
            size = [size[0] + abs(dx) * span,
                    size[1] + abs(dy) * span,
                    size[2] + abs(dz) * span]
        if self.circle_repeat:
            across = self.circle_repeat["across"]
            size = [size[0] + across, size[1] + across, size[2]]

        return size

    # -- saving -----------------------------------------------------------

    def to_dict(self):
        return {
            "name": self.name, "shape": self.shape, "params": self.params,
            "pos": self.pos, "turn": self.turn, "scale": self.scale,
            "mirror": self.mirror, "round_by": self.round_by,
            "smooth": self.smooth, "hollow": self.hollow,
            "repeat": self.repeat, "circle_repeat": self.circle_repeat,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, data):
        part = cls(data["name"], data["shape"], data.get("params"))
        part.pos = list(data.get("pos", [0, 0, 0]))
        part.turn = list(data.get("turn", [0, 0, 0]))
        part.scale = list(data.get("scale", [1, 1, 1]))
        part.mirror = data.get("mirror")
        part.round_by = data.get("round_by", 0.0)
        part.smooth = data.get("smooth", False)
        part.hollow = data.get("hollow", 0.0)
        part.repeat = data.get("repeat")
        part.circle_repeat = data.get("circle_repeat")
        part.role = data.get("role", "solid")
        return part


class Group:
    """
    Two or more parts combined into one: joined, cut or overlapped.
    A group behaves like a part, so groups can be combined again.
    """

    OPERATIONS = {"join": "union", "cut": "difference", "overlap": "intersection"}

    def __init__(self, name, operation, members):
        self.name = name
        self.operation = operation     # join, cut, overlap
        self.members = list(members)   # names of the parts inside
        self.round_by = 0.0
        self.smooth = False
        self.role = "solid"
        self.pos = [0.0, 0.0, 0.0]
        self.turn = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]
        self.mirror = None
        self.repeat = None
        self.circle_repeat = None
        self.shape = "group"
        self.params = {}
        self.hollow = 0.0

    def to_dict(self):
        return {"kind": "group", "name": self.name, "operation": self.operation,
                "members": self.members, "round_by": self.round_by,
                "smooth": self.smooth, "pos": self.pos, "turn": self.turn,
                "scale": self.scale, "mirror": self.mirror,
                "repeat": self.repeat, "circle_repeat": self.circle_repeat,
                "role": self.role}

    @classmethod
    def from_dict(cls, data):
        group = cls(data["name"], data["operation"], data["members"])
        group.round_by = data.get("round_by", 0.0)
        group.smooth = data.get("smooth", False)
        group.pos = list(data.get("pos", [0, 0, 0]))
        group.turn = list(data.get("turn", [0, 0, 0]))
        group.scale = list(data.get("scale", [1, 1, 1]))
        group.mirror = data.get("mirror")
        group.repeat = data.get("repeat")
        group.circle_repeat = data.get("circle_repeat")
        group.role = data.get("role", "solid")
        return group


class Model:
    """Everything the student has made so far."""

    def __init__(self):
        self.items = {}      # name -> Part or Group, in the order made
        self.order = []      # names, oldest first
        self.history = []    # for undo
        self.future = []     # for redo
        self.last_action = ""
        self.name = "model"

    # -- history ----------------------------------------------------------

    def snapshot(self):
        # A deep copy, not the live objects.  to_dict() hands back the very
        # dictionaries and lists the parts are using, so without this the
        # snapshot changes along with the model and undo does nothing.
        return copy.deepcopy({
            "items": {n: i.to_dict() for n, i in self.items.items()},
            "order": list(self.order),
            "name": self.name,
        })

    def restore(self, snap):
        self.items = {}
        for name, data in snap["items"].items():
            if data.get("kind") == "group":
                self.items[name] = Group.from_dict(data)
            else:
                self.items[name] = Part.from_dict(data)
        self.order = list(snap["order"])
        self.name = snap.get("name", "model")

    def change(self, description):
        """Call before every change, so undo has something to go back to."""
        self.history.append((description, self.snapshot()))
        if len(self.history) > 100:
            self.history.pop(0)
        self.future.clear()
        self.last_action = description

    def undo(self):
        if not self.history:
            return None
        description, snap = self.history.pop()
        self.future.append((description, self.snapshot()))
        self.restore(snap)
        return description

    def redo(self):
        if not self.future:
            return None
        description, snap = self.future.pop()
        self.history.append((description, self.snapshot()))
        self.restore(snap)
        return description

    # -- parts ------------------------------------------------------------

    def free_name(self, base):
        if base not in self.items:
            return base
        number = 2
        while f"{base}{number}" in self.items:
            number += 1
        return f"{base}{number}"

    def add_part(self, shape, params=None, name=None):
        name = self.free_name(name or shape)
        part = Part(name, shape, params)
        self.items[name] = part
        self.order.append(name)
        return part

    def add_group(self, operation, members, name=None):
        # Not named after the operation: "joined plate and braille into
        # join" is a mouthful. A combined part is a piece.
        name = self.free_name(name or "piece")
        group = Group(name, operation, members)
        self.items[name] = group
        self.order.append(name)
        return group

    def remove(self, name):
        if name not in self.items:
            return False
        # Anything built from it goes too, otherwise the model makes no sense.
        doomed = {name}
        changed = True
        while changed:
            changed = False
            for item in list(self.items.values()):
                if isinstance(item, Group) and set(item.members) & doomed:
                    if item.name not in doomed:
                        doomed.add(item.name)
                        changed = True
        for gone in doomed:
            self.items.pop(gone, None)
            if gone in self.order:
                self.order.remove(gone)
        return True

    def rename(self, old, new):
        if old not in self.items or new in self.items:
            return False
        item = self.items.pop(old)
        item.name = new
        self.items[new] = item
        self.order[self.order.index(old)] = new
        for other in self.items.values():
            if isinstance(other, Group):
                other.members = [new if m == old else m for m in other.members]
        return True

    def find(self, word):
        """
        The part a student means when they say a word.

        An exact name always counts, but so does a shape word: after making
        two plates, "plate" means the one you just made, not the first one.
        Otherwise a student who follows a worksheet ends up quietly cutting
        a hole in something they finished ten minutes ago.
        """
        if not word:
            return None
        word = str(word)
        found = None
        for name in self.order:
            item = self.items[name]
            if item.name == word or getattr(item, "shape", None) == word:
                found = item
        if found is not None:
            return found
        # Last chance: a word that means the same shape, such as "box".
        shape = shapes_mod.shape_for(word)
        if shape:
            for name in self.order:
                if getattr(self.items[name], "shape", None) == shape:
                    found = self.items[name]
        return found

    def current(self):
        """The part the student is working on: the newest top-level one."""
        tops = self.top_level()
        return self.items[tops[-1]] if tops else None

    def top_level(self):
        """Names that are not inside a group."""
        used = set()
        for item in self.items.values():
            if isinstance(item, Group):
                used.update(item.members)
        return [n for n in self.order if n not in used]

    def is_empty(self):
        return not self.items

    def clear(self):
        self.items = {}
        self.order = []

    # -- OpenSCAD ---------------------------------------------------------

    def scad(self):
        """The whole model as one OpenSCAD program."""
        lines = ["// Made with BgeraPrint", "$fa = 2; $fs = 0.4;", ""]
        for name in self.order:
            item = self.items[name]
            lines.append(f"module {self._safe(name)}() {{")
            lines.append("  " + self._item_scad(item))
            lines.append("}")
        tops = self.top_level()
        if not tops:
            lines.append("// nothing to show")
        elif len(tops) == 1:
            lines.append(f"{self._safe(tops[0])}();")
        else:
            lines.append("union() {")
            for name in tops:
                lines.append(f"  {self._safe(name)}();")
            lines.append("}")
        return "\n".join(lines)

    def _item_scad(self, item):
        if isinstance(item, Group):
            op = Group.OPERATIONS[item.operation]
            inner = " ".join(f"{self._safe(m)}();" for m in item.members)
            code = f"{op}(){{ {inner} }}"
            if item.round_by:
                code = (f"minkowski(){{ {code} "
                        f"sphere(r={_f(item.round_by)}, $fn=24); }}")
            if item.smooth:
                code = f"hull(){{ {code} }}"
            if item.mirror:
                vec = {"x": "[1,0,0]", "y": "[0,1,0]", "z": "[0,0,1]"}[item.mirror]
                code = f"mirror({vec}){{ {code} }}"
            if item.scale != [1.0, 1.0, 1.0]:
                code = (f"scale([{_f(item.scale[0])},{_f(item.scale[1])},"
                        f"{_f(item.scale[2])}]){{ {code} }}")
            if any(item.turn):
                code = (f"rotate([{_f(item.turn[0])},{_f(item.turn[1])},"
                        f"{_f(item.turn[2])}]){{ {code} }}")
            if any(item.pos):
                code = (f"translate([{_f(item.pos[0])},{_f(item.pos[1])},"
                        f"{_f(item.pos[2])}]){{ {code} }}")
            if item.repeat:
                dx, dy, dz = DIRECTIONS.get(item.repeat["dir"], (1, 0, 0))
                gap = item.repeat["gap"]
                copies = [f"translate([{_f(dx*gap*i)},{_f(dy*gap*i)},{_f(dz*gap*i)}])"
                          f"{{ {code} }}" for i in range(int(item.repeat["count"]))]
                code = "union(){" + "".join(copies) + "}"
            if item.circle_repeat:
                count = int(item.circle_repeat["count"])
                radius = item.circle_repeat["across"] / 2.0
                copies = []
                for i in range(count):
                    copies.append(f"rotate([0,0,{360.0*i/count:.3f}])"
                                  f"translate([{_f(radius)},0,0]){{ {code} }}")
                code = "union(){" + "".join(copies) + "}"
            return code
        return item.placed_scad()

    @staticmethod
    def _safe(name):
        """
        A module name OpenSCAD is happy with.

        Everything gets the part_ prefix.  Without it a part the student
        called "cube" becomes `module cube(){ cube(...); }`, which calls
        itself forever, and OpenSCAD gives up.  Since "cube" is the very
        first thing anybody types, this matters.
        """
        clean = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        return "part_" + clean

    # -- talking about the model -----------------------------------------

    def rough_size(self):
        """Overall size of everything on the bed, in millimetres."""
        if not self.items:
            return [0, 0, 0]
        lo = [1e9, 1e9, 1e9]
        hi = [-1e9, -1e9, -1e9]
        for name in self.top_level():
            item = self.items[name]
            size = self._item_size(item)
            centre = item.pos
            for axis in range(3):
                lo[axis] = min(lo[axis], centre[axis] - size[axis] / 2.0)
                hi[axis] = max(hi[axis], centre[axis] + size[axis] / 2.0)
        # Whole numbers stay whole: a screen reader saying "thirty point
        # zero" instead of "thirty" is one more thing to wade through.
        return [_tidy(hi[a] - lo[a]) for a in range(3)]

    def _item_size(self, item):
        if isinstance(item, Group):
            members = [self.items[m] for m in item.members if m in self.items]
            if not members:
                return [0, 0, 0]
            if item.operation == "cut":
                # Cutting can only take material away, never add any.
                members = members[:1]
            lo = [1e9, 1e9, 1e9]
            hi = [-1e9, -1e9, -1e9]
            for member in members:
                size = self._item_size(member)
                for axis in range(3):
                    lo[axis] = min(lo[axis], member.pos[axis] - size[axis] / 2.0)
                    hi[axis] = max(hi[axis], member.pos[axis] + size[axis] / 2.0)
            size = [hi[a] - lo[a] for a in range(3)]
            size = [s + 2 * item.round_by for s in size]
            return [s * f for s, f in zip(size, item.scale)]
        return item.rough_size()

    def describe(self):
        """A short spoken description of the whole model."""
        if not self.items:
            return []
        lines = []
        for index, name in enumerate(self.top_level(), start=1):
            item = self.items[name]
            lines.append(self.describe_item(item, index))
        size = self.rough_size()
        lines.append(f"Altogether it is {size[0]} wide, {size[1]} long "
                     f"and {size[2]} tall, in millimetres.")
        return lines

    def describe_item(self, item, index=None):
        head = f"{index}. " if index else ""
        if isinstance(item, Group):
            verb = {"join": "joined together", "cut": "cut out of each other",
                    "overlap": "overlapped"}[item.operation]
            members = ", ".join(item.members)
            size = self._item_size(item)
            text = (f"{head}{item.name}: {members}, {verb}, "
                    f"{_tidy(size[0])} by {_tidy(size[1])} by {_tidy(size[2])} "
                    f"millimetres")
        else:
            text = (f"{head}{item.name}: a {item.shape}, "
                    f"{shapes_mod.describe_size(item.shape, item.params)}")
        extras = []
        if any(item.pos):
            extras.append("at " + self.spoken_position(item.pos))
        if any(item.turn):
            turned = ", ".join(f"{_f(v)} degrees {AXIS_NAMES[a]}"
                               for a, v in zip("xyz", item.turn) if v)
            extras.append("turned " + turned)
        if item.round_by:
            extras.append(f"edges rounded by {_f(item.round_by)}")
        if getattr(item, "hollow", 0):
            extras.append(f"hollow, walls {_f(item.hollow)} thick")
        if item.repeat:
            extras.append(f"{int(item.repeat['count'])} copies "
                          f"{_f(item.repeat['gap'])} apart going {item.repeat['dir']}")
        if item.circle_repeat:
            extras.append(f"{int(item.circle_repeat['count'])} copies in a circle")
        if extras:
            text += ", " + ", ".join(extras)
        return text + "."

    @staticmethod
    def spoken_position(pos):
        bits = []
        names = [("right", "left"), ("forward", "back"), ("up", "down")]
        for value, (plus, minus) in zip(pos, names):
            if value:
                bits.append(f"{_f(abs(value))} {plus if value > 0 else minus}")
        return " and ".join(bits) if bits else "the middle"

    # -- saving -----------------------------------------------------------

    def save(self, folder, name):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{name}.bgera"
        data = {
            "app": "BgeraPrint", "version": 2,
            "saved": time.strftime("%Y-%m-%d %H:%M"),
            "name": name,
            "model": self.snapshot(),
        }
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
        self.name = name
        return path

    def load(self, folder, name):
        path = Path(folder) / f"{name}.bgera"
        if not path.exists():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        self.change(f"open {name}")
        self.restore(data["model"])
        self.name = name
        return True

    @staticmethod
    def saved_projects(folder):
        folder = Path(folder)
        if not folder.exists():
            return []
        out = []
        for path in sorted(folder.glob("*.bgera")):
            when = time.strftime("%Y-%m-%d %H:%M",
                                 time.localtime(path.stat().st_mtime))
            out.append((path.stem, when))
        return out
