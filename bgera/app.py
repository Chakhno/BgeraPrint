#!/usr/bin/env python
# coding: utf-8
"""
BgeraPrint: the part that listens, does things, and says what happened.

The rule that shapes this file: after every single command the student hears
one short sentence telling them what changed.  Nobody using a screen reader
should ever have to wonder whether something worked.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

from . import guided as guided_mod
from . import keys as keys_mod
from . import help as help_mod
from . import menu as menu_mod
from . import parser as parser_mod
from . import printing as printing_mod
from . import shapes as shapes_mod
from . import transfer as transfer_mod
from .model import Group, Model
from .texts import say, set_language, t


# ---------------------------------------------------------------------------
# Where everything lives
# ---------------------------------------------------------------------------

def bundled(relative):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def beside_the_app():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def somewhere_writable():
    """
    Where to keep settings and saved work.

    Next to the app, which is what anybody would expect: the projects
    folder sits beside the program and can be copied about with it.

    But a program dropped into Program Files, or run from a locked-down
    school share or a memory stick, cannot write beside itself. Rather than
    fall over at startup -- which is what it used to do, before any of the
    friendly error handling gets a chance to run -- it quietly moves to the
    usual per-user place instead.
    """
    home = beside_the_app()
    try:
        home.mkdir(parents=True, exist_ok=True)
        probe = home / ".can_write"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return home
    except OSError:
        pass

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA")
                    or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME")
                    or Path.home() / ".local" / "share")
    fallback = Path(base) / "BgeraPrint"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except OSError:
        # Nothing is writable. Use a temporary folder so the app still runs;
        # saved work will not survive, but a lesson is not lost mid-way.
        import tempfile
        return Path(tempfile.gettempdir()) / "BgeraPrint"


ASSETS = bundled("assets")
BIN = ASSETS / "bin"
PRINTER_CONFIGS = ASSETS / "printer_configs"
MODELS = ASSETS / "models"

HOME = somewhere_writable()
CONFIG_PATH = HOME / "config.json"
PROJECTS_DIR = HOME / "projects"
WORK_DIR = HOME / "work"
DOWNLOADS = Path.home() / "Downloads"

OPENSCAD = BIN / ("openscad.exe" if os.name == "nt" else "openscad")
SLICER = BIN / ("prusa-slicer-console.exe" if os.name == "nt" else "prusa-slicer")

# PrusaSlicer and OpenSCAD load their DLLs from the folder they sit in.
# Without this they start and then die with no message at all, which is a
# miserable thing to debug in front of a class.
if BIN.exists() and str(BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(BIN)

# How far parts sink into each other when stacked or placed side by side.
# Enough for OpenSCAD to see one solid, far too little for anyone to feel.
OVERLAP = 0.05

BUILTIN_FILES = {
    "lion": "Lion.stl", "turtle": "Turtle.stl", "giraffe": "Giraffe.stl",
    "wolf": "Wolf.stl", "camel": "Camel.stl", "rocket": "Rocket.stl",
    "pawn": "Pawn.stl", "rook": "Rook.stl", "queen": "Queen.stl",
    "king": "King.stl", "bishop": "Bishop.stl", "knight": "Knight.stl",
}


# ---------------------------------------------------------------------------
# Settings that live between sessions
# ---------------------------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def save_config(config):
    try:
        CONFIG_PATH.write_text(json.dumps(config, indent=1), encoding="utf-8")
    except OSError:
        pass


def known_printer_models():
    if not PRINTER_CONFIGS.exists():
        return []
    return sorted(path.stem for path in PRINTER_CONFIGS.glob("*.ini"))


def _ask(question, default=""):
    """
    Ask something, and survive the answer never coming.

    Piping a file into a fresh copy runs out of input at the first setup
    question. Left alone that ends in a Python traceback, which is a
    horrible thing to hand anybody and a baffling one to hear read out.
    """
    try:
        return input(question).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def ask_setup():
    """First run: language, printer, address.  Kept short and forgiving."""
    print(t("welcome"))

    language = 1
    for _ in range(10):
        answer = _ask(t("choose_language"))
        if not answer:
            break
        if answer in ("1", "2"):
            language = int(answer)
            break
        if answer.lower().startswith("eng"):
            language = 1
            break
        if answer.lower().startswith(("geo", "ქარ")):
            language = 2
            break
        print("Please press 1 or 2.")
    set_language(language)

    models = known_printer_models()
    model = models[0] if models else "xmax3"
    for _ in range(10):
        answer = _ask(t("ask_printer_model")).lower()
        if not answer:
            break
        if answer in models:
            model = answer
            break
        say("unknown_model")
        if models:
            print("Known printers: " + ", ".join(models))

    ip = _ask(t("ask_ip"))
    port = _ask(t("ask_port")) or "7125"

    config = {
        "lan": language,
        "printers": [{"name": model, "model": model, "ip": ip, "port": port}],
        "current_printer": model,
        # the old keys, so an older copy of the app still reads this file
        "printer": model, "ip": ip, "port": port,
    }
    save_config(config)
    return config


def upgrade_config(config):
    """A config file from version 1.3.1 still works."""
    if "printers" not in config:
        config["printers"] = [{
            "name": config.get("printer", "printer"),
            "model": config.get("printer", "xmax3"),
            "ip": config.get("ip", ""),
            "port": config.get("port", "7125"),
        }]
        config["current_printer"] = config["printers"][0]["name"]
        save_config(config)
    return config


# ---------------------------------------------------------------------------
# The app
# ---------------------------------------------------------------------------

class BgeraPrint:

    def __init__(self, config):
        self.config = config
        set_language(config.get("lan", 1))

        self.model = Model()
        self.settings = printing_mod.PrintSettings()
        self.printers = [printing_mod.Printer.from_dict(p)
                         for p in config["printers"]]
        self.printer = self._find_printer(config.get("current_printer")) \
            or (self.printers[0] if self.printers else None)

        self.external_stl = None      # a shape file that did not come from parts
        self.external_name = None
        self.stl_path = DOWNLOADS / "bgeraprint_model.stl"
        self.scad_path = DOWNLOADS / "bgeraprint_model.scad"
        self.gcode_path = DOWNLOADS / "bgeraprint_model.gcode"
        self.prepared = False
        self.last_report = {}

        self.receiver = None
        self.received = []

        self.interface = config.get("interface", "menus")
        menu_mod.set_style(config.get("menu_style", "speak"))
        # Changing a number with the arrow keys needs a keyboard that can be
        # read one key at a time. Fed from a file there is none, so the typed
        # way is the only one that can work, whatever the config remembers.
        menu_mod.set_number_mode(
            config.get("number_mode", "arrows")
            if keys_mod.keyboard_is_there() else "typed")

        self.lesson = None            # (lesson_index, step_index)
        self.confirm = None           # "print" or "stopprint"
        self.last_said = ""
        self.running = True

        try:
            WORK_DIR.mkdir(parents=True, exist_ok=True)
            PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as problem:
            self.plain(f"I cannot make a folder to work in: {problem}")
            self.plain("Try running BgeraPrint from a folder you can "
                       "write to, such as your Desktop.")

    # -- small helpers ----------------------------------------------------

    def _find_printer(self, name):
        for printer in self.printers:
            if printer.name == name:
                return printer
        return None

    def projects_dir(self):
        return PROJECTS_DIR

    def tell(self, key, **kw):
        self.last_said = t(key, **kw)
        print(self.last_said)

    def plain(self, text):
        self.last_said = text
        print(text)

    def target_item(self, name):
        """The part a command applies to: the named one, or the newest."""
        if name:
            item = self.model.find(name)
            if item is not None:
                return item
            self.tell("no_part_named", name=name)
            return None
        item = self.model.current()
        if item is None:
            self.tell("nothing_yet")
        return item

    # -- the loop ---------------------------------------------------------

    def run(self):
        """Run whichever interface is chosen, and swap between them freely."""
        while self.running:
            if self.interface == "menus":
                guided_mod.Guided(self).run()
                # Guided returns when the student asks for typing, or quits.
                if not self.running:
                    break
                if self.interface == "menus":
                    break
            else:
                self.run_typing()
                if self.interface != "menus":
                    break
        self._shutdown()

    def run_typing(self):
        for line in help_mod.INTRO:
            print(line)
        print()

        while self.running and self.interface == "typing":
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.tell("goodbye")
                break

            if not line:
                continue

            expected = self._lesson_expects()
            try:
                self.handle(line)
            except Exception as problem:      # never drop the student out
                self.plain(f"Something went wrong: {problem}")
                self.plain("Nothing was lost. Type list to hear your model.")
            if expected:
                self._lesson_check(line, expected)

    def handle(self, line):
        actions = parser_mod.parse(line, self.model)
        if not actions:
            self.tell("unknown", word=line)
            return
        confirming = self.confirm
        for action in actions:
            self.do(action)
        # A confirmation only lasts for the very next command.
        if self.confirm == confirming and confirming is not None:
            self.confirm = None

    def _shutdown(self):
        if self.receiver:
            self.receiver.stop()

    # -- doing one thing --------------------------------------------------

    def do(self, action):
        what = action["do"]
        method = getattr(self, f"do_{what}", None)
        if method is None:
            self.tell("unknown", word=what)
            return
        method(action)

    # ---- help -----------------------------------------------------------

    def do_help(self, action):
        lines = help_mod.topic(action.get("topic"))
        if lines is None:
            self.plain(f"There is no help topic called {action['topic']}.")
            lines = help_mod.MENU
        for line in lines:
            print(line)

    def do_explain_setting(self, action):
        info = printing_mod.SETTINGS[action["key"]]
        self.plain(f"{action['key']}: {info['help']} "
                   f"It is {self.settings.spoken(action['key'])} now.")

    # ---- making shapes ---------------------------------------------------

    def do_shape(self, action):
        shape = action["shape"]
        self.model.change(f"add a {shape}")
        params = dict(action.get("values") or {})
        if "words" in action:
            words = action["words"]
            if not words:
                self.tell("text_needs_words" if shape == "text"
                          else "braille_needs_words")
                self.model.undo()
                return
            params["words"] = words

        part = self.model.add_part(shape, params, name=action.get("name"))
        self.external_stl = None
        self.prepared = False

        if action.get("quiet"):
            return

        if shape == "braille":
            from . import braille as braille_mod
            cells, skipped = braille_mod.to_cells(params.get("words", ""))
            self.tell("braille_made", words=params["words"], cells=len(cells),
                      width=round(braille_mod.cells_width(cells), 1))
            if skipped:
                self.tell("braille_skipped", chars=" ".join(skipped))
        else:
            self.tell("shape_added", shape=shape, name=part.name)
            # The hint tells you what to type, which is wrong and confusing
            # advice when the menus are about to ask for the same numbers.
            hint = shapes_mod.SHAPES[shape].get("hint")
            if hint and not action.get("values") and self.interface != "menus":
                say(hint)

    def do_builtin(self, action):
        name = action["name"]
        path = MODELS / BUILTIN_FILES[name]
        if not path.exists():
            self.plain(f"The model file for {name} is missing.")
            return
        self.external_stl = path
        self.external_name = name
        self.model.change(f"use the {name}")
        self.model.clear()
        self.prepared = False
        self.plain(f"Using the built in {name}.")
        self._say_external_size()

    def do_openfile(self, action):
        path = Path(action["path"].strip().strip('"').strip("'"))
        if not path.exists():
            self.plain(f"I cannot find a file at {path}.")
            return
        self.external_stl = path
        self.external_name = path.stem
        self.model.change(f"open {path.name}")
        self.model.clear()
        self.prepared = False
        self.plain(f"Opened {path.name}.")
        self._say_external_size()

    def _say_external_size(self):
        size = printing_mod.stl_size(SLICER, self.external_stl)
        if size:
            self.tell("size_report", x=size[0], y=size[1], z=size[2])
            self.plain("Type bigger 2 or smaller 2 to change how big it prints.")

    # ---- measurements -----------------------------------------------------

    def do_measure(self, action):
        if self.external_stl and not self.model.items:
            self.plain("This is a ready made model. "
                       "Use bigger or smaller to change its size.")
            return
        item = self.target_item(action.get("target"))
        if item is None:
            return
        if isinstance(item, Group):
            self.plain(f"{item.name} is made of other parts. "
                       f"Change {', '.join(item.members)} instead.")
            return

        self.model.change(f"change the size of {item.name}")
        for measure, value in action["values"].items():
            low, high = shapes_mod.LIMITS.get(measure, (0.01, 10000))
            if value < low:
                self.tell("number_too_small", word=measure, low=low)
                self.model.undo()
                return
            if value > high:
                self.tell("number_too_big", word=measure, high=high)
                self.model.undo()
                return
            item.params[measure] = value

        self.prepared = False
        self.tell("size_set", name=item.name,
                  dims=shapes_mod.describe_size(item.shape, item.params))

    def do_focus(self, action):
        item = self.model.find(action["name"])
        if item is None:
            self.tell("no_part_named", name=action["name"])
            return
        self.plain(self.model.describe_item(item))

    # ---- moving -----------------------------------------------------------

    def do_move(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        delta = action["delta"]
        self.model.change(f"move {item.name}")
        item.pos = [item.pos[i] + delta[i] for i in range(3)]
        self.prepared = False
        direction, amount = self._spoken_move(delta)
        self.tell("moved", name=item.name, dir=direction, amount=amount)

    @staticmethod
    def _spoken_move(delta):
        pairs = [("right", "left"), ("forward", "back"), ("up", "down")]
        bits = []
        total = 0
        for value, (plus, minus) in zip(delta, pairs):
            if value:
                bits.append(plus if value > 0 else minus)
                total = abs(value)
        return (" and ".join(bits) or "nowhere"), total

    def do_turn(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"turn {item.name}")
        item.turn = [item.turn[i] + action["turn"][i] for i in range(3)]
        self.prepared = False
        axis = "xyz"[max(range(3), key=lambda i: abs(action["turn"][i]))]
        amount = action["turn"]["xyz".index(axis)]
        names = {"x": "sideways", "y": "forward", "z": "upright"}
        self.tell("turned", name=item.name, amount=amount, axis=names[axis])

    def do_center(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"centre {item.name}")
        item.pos = [0.0, 0.0, 0.0]
        self.prepared = False
        self.tell("centred", name=item.name)

    def do_stack(self, action):
        top = self._resolve(action.get("top"), -1)
        bottom = self._resolve(action.get("bottom"), -2)
        if not top or not bottom:
            return
        self.model.change(f"put {top.name} on {bottom.name}")
        bottom_size = self.model._item_size(bottom)
        top_size = self.model._item_size(top)
        # A hair of overlap, not an exact touch. Two solids meeting on a
        # shared plane are slow to join and slice as two separate objects,
        # which is the "not manifold" complaint students hit most.
        top.pos = [bottom.pos[0], bottom.pos[1],
                   bottom.pos[2] + bottom_size[2] / 2.0
                   + top_size[2] / 2.0 - OVERLAP]
        self.prepared = False
        self.tell("stacked", top=top.name, bottom=bottom.name)

    def do_beside(self, action):
        first = self._resolve(action.get("a"), -1)
        second = self._resolve(action.get("b"), -2)
        if not first or not second:
            return
        self.model.change(f"put {first.name} beside {second.name}")
        first_size = self.model._item_size(first)
        second_size = self.model._item_size(second)
        first.pos = [second.pos[0] + second_size[0] / 2.0
                     + first_size[0] / 2.0 - OVERLAP,
                     second.pos[1], second.pos[2]]
        self.prepared = False
        self.tell("beside", a=first.name, b=second.name)

    def _resolve(self, name, fallback_index):
        if name:
            item = self.model.find(name)
            if item is not None:
                return item
            self.tell("no_part_named", name=name)
            return None
        tops = self.model.top_level()
        if len(tops) < abs(fallback_index):
            self.tell("need_two_parts", action="do that")
            return None
        return self.model.items[tops[fallback_index]]

    # ---- combining ---------------------------------------------------------

    def do_combine(self, action):
        operation = action["op"]
        first = self._resolve(action.get("a"), -2)
        second = self._resolve(action.get("b"), -1)
        if not first or not second or first is second:
            return
        self.model.change(f"{operation} {first.name} and {second.name}")
        group = self.model.add_group(operation, [first.name, second.name],
                                     name=action.get("name"))
        self.prepared = False
        key = {"join": "joined", "cut": "cut", "overlap": "overlapped"}[operation]
        self.tell(key, a=first.name, b=second.name, name=group.name)

    def do_join_last(self, action):
        self.do_combine({"do": "combine", "op": "join", "a": None, "b": None})

    # ---- changing ----------------------------------------------------------

    def do_round(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"round {item.name}")
        item.round_by = action["amount"]
        self.prepared = False
        self.tell("rounded", name=item.name, amount=action["amount"])

    def do_hollow(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        if isinstance(item, Group):
            self.plain("Hollow the parts before you join them.")
            return
        self.model.change(f"hollow {item.name}")
        item.hollow = action["amount"]
        self.prepared = False
        self.tell("hollowed", name=item.name, thick=action["amount"])

    def do_smooth(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"smooth {item.name}")
        item.smooth = True
        self.prepared = False
        self.tell("smoothed", name=item.name)

    def do_mirror(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"mirror {item.name}")
        item.mirror = action["axis"]
        self.prepared = False
        names = {"x": "left to right", "y": "front to back", "z": "top to bottom"}
        self.tell("mirrored", name=item.name, dir=names[action["axis"]])

    def do_scale(self, action):
        factor = action["factor"]
        if factor <= 0:
            self.tell("number_too_small", word="scale", low=0.1)
            return
        if self.external_stl and not self.model.items:
            ok, key, extra = self.settings.set("bigger", factor)
            if ok:
                self.prepared = False
                self.tell("setting_changed", setting="size", value=extra["value"])
            return
        item = self.target_item(action.get("target"))
        if item is None:
            return
        self.model.change(f"resize {item.name}")
        item.scale = [s * factor for s in item.scale]
        self.prepared = False
        self.tell("scaled", name=item.name, factor=round(item.scale[0], 3))

    def do_copy(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        count = max(1, int(action["count"]))
        self.model.change(f"copy {item.name}")
        item.repeat = {"count": count, "gap": action["gap"], "dir": action["dir"]}
        self.prepared = False
        self.tell("copied", count=count, name=item.name, gap=action["gap"],
                  dir=action["dir"])

    def do_ring(self, action):
        item = self.target_item(action.get("target"))
        if item is None:
            return
        count = max(2, int(action["count"]))
        self.model.change(f"ring of {item.name}")
        item.circle_repeat = {"count": count, "across": action["across"]}
        self.prepared = False
        self.tell("ringed", count=count, name=item.name, across=action["across"])

    def do_remove(self, action):
        name = action.get("name")
        if not name or name not in self.model.items:
            self.tell("no_part_named", name=name or "that")
            return
        self.model.change(f"remove {name}")
        self.model.remove(name)
        self.prepared = False
        self.tell("part_removed", name=name)

    def do_rename(self, action):
        old, new = action.get("old"), action.get("new")
        if not old or old not in self.model.items:
            self.tell("no_part_named", name=old or "that")
            return
        if not new:
            self.plain("Tell me the new name too, for example: rename ball head.")
            return
        self.model.change(f"rename {old}")
        if not self.model.rename(old, new):
            self.tell("renamed_taken", new=new)
            self.model.undo()
            return
        self.tell("part_renamed", old=old, new=new)

    # ---- listening ---------------------------------------------------------

    def do_list(self, action):
        if self.external_stl and not self.model.items:
            self.plain(f"You are using the ready made model {self.external_name}.")
            return
        tops = self.model.top_level()
        if not tops:
            self.tell("nothing_yet")
            return
        self.tell("list_header", count=len(tops))
        for index, name in enumerate(tops, start=1):
            print("  " + self.model.describe_item(self.model.items[name], index))

    def do_describe(self, action):
        if self.external_stl and not self.model.items:
            self.plain(f"You are using the ready made model {self.external_name}.")
            self._say_external_size()
            return
        lines = self.model.describe()
        if not lines:
            self.tell("describe_empty")
            return
        for line in lines:
            print(line)

    def do_size(self, action):
        if self.external_stl and not self.model.items:
            self._say_external_size()
            return
        if self.model.is_empty():
            self.tell("nothing_yet")
            return
        size = self.model.rough_size()
        self.tell("size_report", x=size[0], y=size[1], z=size[2])
        if self.last_report.get("grams"):
            self.tell("volume_report", grams=self.last_report["grams"])

    def do_what(self, action):
        self.plain(self.model.last_action or "Nothing yet.")

    def do_undo(self, action):
        what = self.model.undo()
        self.prepared = False
        if what is None:
            self.tell("undo_empty")
        else:
            self.tell("undo_done", what=f"That undid: {what}.")

    def do_redo(self, action):
        what = self.model.redo()
        self.prepared = False
        if what is None:
            self.tell("redo_empty")
        else:
            self.tell("redo_done", what=f"That put back: {what}.")

    def do_new(self, action):
        self.model.change("start a new model")
        self.model.clear()
        self.external_stl = None
        self.prepared = False
        if not action.get("quiet"):
            self.tell("new_model")

    # ---- print settings ----------------------------------------------------

    def do_setting(self, action):
        key = action["key"]
        ok, problem, extra = self.settings.set(key, action["value"])
        if not ok:
            self.tell(problem, **extra)
            return
        self.prepared = False
        self.tell("setting_changed", setting=key, value=extra["value"])

    def do_settings(self, action):
        self.tell("settings_header")
        for key, value in self.settings.all_spoken():
            print(f"  {key}: {value}")

    def do_reset_settings(self, action):
        self.settings.reset()
        self.prepared = False
        self.tell("settings_reset")

    # ---- preparing and printing --------------------------------------------

    def _build_stl(self):
        """Turn the model into a shape file.  Returns (ok, message)."""
        if self.external_stl:
            return True, ""
        if self.model.is_empty():
            self.tell("nothing_yet")
            return False, ""
        scad = self.model.scad()
        return printing_mod.run_openscad(OPENSCAD, scad, self.scad_path,
                                         self.stl_path)

    def do_prepare(self, action):
        self.tell("preparing")

        ok, problem = self._build_stl()
        if not ok:
            self.tell("build_failed", reason=problem)
            return

        stl_files = [self.external_stl] if self.external_stl else [self.stl_path]
        if self.received:
            stl_files = list(self.received)

        try:
            profile_source = PRINTER_CONFIGS / f"{self.printer.model}.ini"
            profile = self.settings.write_profile(profile_source, WORK_DIR)
        except OSError as problem:
            self.tell("prepare_failed", reason=str(problem))
            return

        ok, problem = printing_mod.slice_model(
            SLICER, stl_files, profile, self.gcode_path,
            copies=self.settings.values["copies"],
            scale=self.settings.values["bigger"])
        if not ok:
            self.tell("prepare_failed", reason=problem)
            return

        report = printing_mod.gcode_report(self.gcode_path)
        self.last_report = report
        self.prepared = True
        self.tell("prepared", time=report.get("time") or "an unknown time",
                  grams=report.get("grams") or "some")
        if report.get("layers"):
            self.plain(f"It has {report['layers']} layers.")
        self.tell("confirm_print")

    def do_print(self, action):
        if not self.prepared:
            self.tell("prepare_first")
            return
        if self.printer is None:
            self.plain("No printer is set up. Type add printer.")
            return
        if self.confirm != "print":
            self.confirm = "print"
            self.tell("confirm_print")
            return

        self.confirm = None
        self.tell("sending_to_printer")
        ok, problem = self.printer.upload_and_print(self.gcode_path)
        if ok:
            self.tell("print_started")
        elif problem == "offline":
            self.tell("printer_offline", ip=self.printer.ip)
        else:
            self.tell("print_failed", reason=problem)

    def do_status(self, action):
        if self.printer is None:
            self.plain("No printer is set up. Type add printer.")
            return
        state = self.printer.status()
        if state is None:
            self.tell("printer_offline", ip=self.printer.ip)
            return
        if state["state"] == "printing":
            self.tell("status_printing", name=state["file"] or "your model",
                      percent=state["percent"], left=state["left"] or "a while")
        elif state["state"] == "paused":
            self.tell("status_paused")
        else:
            self.tell("status_idle")

    def do_pause(self, action):
        ok, problem = self.printer.pause() if self.printer else (False, "offline")
        self.tell("print_paused" if ok else "printer_offline",
                  ip=self.printer.ip if self.printer else "")

    def do_resume(self, action):
        ok, problem = self.printer.resume() if self.printer else (False, "offline")
        self.tell("print_resumed" if ok else "printer_offline",
                  ip=self.printer.ip if self.printer else "")

    def do_stopprint(self, action):
        if self.confirm != "stopprint":
            self.confirm = "stopprint"
            self.tell("confirm_cancel")
            return
        self.confirm = None
        ok, problem = self.printer.cancel() if self.printer else (False, "offline")
        self.tell("print_cancelled" if ok else "printer_offline",
                  ip=self.printer.ip if self.printer else "")

    # ---- projects ----------------------------------------------------------

    def do_save(self, action):
        name = (action.get("name") or "").strip() or self.model.name
        name = re.sub(r"[^\w -]", "", name).strip() or "model"
        self.model.save(PROJECTS_DIR, name)
        self.tell("saved", name=name)

    def do_open(self, action):
        name = (action.get("name") or "").strip()
        if not name:
            self.do_projects({})
            return
        if not self.model.load(PROJECTS_DIR, name):
            self.tell("no_project", name=name)
            return
        self.external_stl = None
        self.prepared = False
        self.tell("opened", name=name)
        self.do_describe({})

    def do_projects(self, action):
        projects = Model.saved_projects(PROJECTS_DIR)
        if not projects:
            self.tell("projects_none")
            return
        self.tell("projects_header", count=len(projects))
        for index, (name, when) in enumerate(projects, start=1):
            print("  " + t("projects_item", index=index, name=name, when=when))

    def do_export(self, action):
        ok, problem = self._build_stl()
        if not ok:
            self.tell("build_failed", reason=problem)
            return
        target = DOWNLOADS / f"{self.model.name}.stl"
        try:
            target.write_bytes(Path(self.external_stl or self.stl_path).read_bytes())
        except OSError as problem:
            self.plain(f"Could not save the file: {problem}")
            return
        self.tell("exported", path=target)

    # ---- sharing -----------------------------------------------------------

    def do_send(self, action):
        if not self.gcode_path.exists():
            self.tell("prepare_first")
            return
        ip = input(t("send_ask_ip")).strip()
        port = input(t("send_ask_port")).strip() or "5001"
        name = input(t("send_ask_name")).strip()
        ok, result = transfer_mod.send_file(self.gcode_path, ip, port, name)
        if ok:
            self.tell("send_ok", name=result)
        else:
            self.tell("send_failed", reason=result)

    def do_receive(self, action):
        if self.receiver:
            self.plain("You are already receiving. Type done when finished.")
            return
        port = input(t("receive_ask_port")).strip() or "5001"
        self.receiver = transfer_mod.Receiver(port, DOWNLOADS).start()
        time.sleep(0.3)
        if self.receiver.error:
            self.plain(f"Could not listen on port {port}: {self.receiver.error}")
            self.receiver = None
            return
        self.tell("receive_waiting", port=port)

    def do_done(self, action):
        if self.receiver is None:
            if self.lesson:
                self.do_stop({})
            return
        files = self.receiver.stop()
        self.receiver = None
        self.received = list(files)
        if not files:
            self.tell("receive_none")
            return
        self.tell("receive_done", count=len(files))
        self.plain("Type prepare to get them all ready for the printer.")

    # ---- printers -----------------------------------------------------------

    def do_printers(self, action):
        self.tell("printers_header", count=len(self.printers))
        for index, printer in enumerate(self.printers, start=1):
            current = t("printer_current") if printer is self.printer else ""
            print("  " + t("printers_item", index=index, name=printer.name,
                           model=printer.model, ip=printer.ip, current=current))

    def do_addprinter(self, action):
        models = known_printer_models()
        while True:
            model = input(t("ask_printer_model")).strip().lower()
            if model in models:
                break
            say("unknown_model")
            print("Known printers: " + ", ".join(models))
        ip = input(t("ask_ip")).strip()
        port = input(t("ask_port")).strip() or "7125"
        name = input("Give this printer a short name, for example classroom: ").strip()
        name = re.sub(r"[^\w-]", "", name) or model
        printer = printing_mod.Printer(name, model, ip, port)
        self.printers.append(printer)
        self.printer = printer
        self._save_printers()
        self.tell("printer_added", name=name)

    def do_useprinter(self, action):
        name = (action.get("name") or "").strip()
        printer = self._find_printer(name)
        if printer is None:
            self.tell("no_printer_named", name=name)
            return
        self.printer = printer
        self._save_printers()
        self.tell("printer_switched", name=name)

    def do_removeprinter(self, action):
        name = (action.get("name") or "").strip()
        printer = self._find_printer(name)
        if printer is None:
            self.tell("no_printer_named", name=name)
            return
        if len(self.printers) == 1:
            self.plain("You cannot remove your only printer.")
            return
        self.printers.remove(printer)
        if self.printer is printer:
            self.printer = self.printers[0]
        self._save_printers()
        self.tell("printer_removed", name=name)

    def _save_printers(self):
        self.config["printers"] = [p.to_dict() for p in self.printers]
        self.config["current_printer"] = self.printer.name if self.printer else ""
        if self.printer:
            self.config["printer"] = self.printer.model
            self.config["ip"] = self.printer.ip
            self.config["port"] = self.printer.port
        save_config(self.config)

    # ---- lessons -------------------------------------------------------------

    def do_lessons(self, action):
        self.tell("lessons_header", count=len(help_mod.LESSONS))
        for index, title in enumerate(help_mod.lesson_titles(), start=1):
            print("  " + t("lessons_item", index=index, title=title))

    def do_lesson(self, action):
        number = int(action.get("n", 1))
        if not 1 <= number <= len(help_mod.LESSONS):
            self.plain(f"There are {len(help_mod.LESSONS)} lessons. "
                       f"Type lessons to hear them.")
            return
        lesson = help_mod.LESSONS[number - 1]
        # Clear the bed first. Otherwise "cut rod from plate" in step five
        # finds a plate from half an hour ago and quietly ruins it.
        if not self.model.is_empty():
            self.model.change("start lesson " + str(number))
            self.model.clear()
            self.plain("Putting your model away first. "
                       "Type undo after the lesson to get it back.")
        self.external_stl = None
        self.prepared = False
        self.lesson = [number - 1, 0]
        self.tell("lesson_start", n=number, title=lesson["title"],
                  steps=len(lesson["steps"]))
        self._lesson_say()

    def do_next(self, action):
        if self.lesson is None:
            self.plain("You are not in a lesson. Type lessons to hear them.")
            return
        self.lesson[1] += 1
        lesson = help_mod.LESSONS[self.lesson[0]]
        if self.lesson[1] >= len(lesson["steps"]):
            self.lesson = None
            self.tell("lesson_end")
            return
        self._lesson_say()

    def do_again(self, action):
        if self.lesson is None:
            self.plain(self.last_said or "Nothing to repeat.")
            return
        self._lesson_say()

    def do_stop(self, action):
        if self.lesson is not None:
            self.lesson = None
            self.tell("lesson_left")
            return
        if self.receiver is not None:
            self.do_done({})
            return
        self.do_quit(action)

    def do_quit(self, action):
        self.tell("goodbye")
        self.running = False

    def _lesson_say(self):
        lesson = help_mod.LESSONS[self.lesson[0]]
        text, command = lesson["steps"][self.lesson[1]]
        self.tell("lesson_step", n=self.lesson[1] + 1,
                  total=len(lesson["steps"]), text=text)
        if command:
            self.tell("lesson_try", command=command)

    def _lesson_expects(self):
        if self.lesson is None:
            return None
        lesson = help_mod.LESSONS[self.lesson[0]]
        if self.lesson[1] >= len(lesson["steps"]):
            return None
        return lesson["steps"][self.lesson[1]][1]

    def _lesson_check(self, typed, expected):
        if self.lesson is None or not expected:
            return
        first_typed = typed.strip().lower().split()
        first_expected = expected.strip().lower().split()
        if first_typed and first_expected and first_typed[0] == first_expected[0]:
            self.tell("lesson_good")
            self.do_next({})

    # ---- swapping between the two interfaces ---------------------------------

    def do_menus(self, action):
        self.interface = "menus"
        self.config["interface"] = "menus"
        save_config(self.config)
        self.plain("Switching to menus. Use the arrow keys and Enter.")

    def do_numbers(self, action):
        wanted = (action.get("value") or "").lower()
        if wanted not in ("arrows", "typed"):
            self.plain("The two ways of setting a number are arrows and "
                       "typed. arrows means left and right change it, "
                       "faster the longer you hold them. typed means you "
                       "type the number.")
            return
        menu_mod.set_number_mode(wanted)
        self.config["number_mode"] = wanted
        save_config(self.config)
        self.tell("setting_changed", setting="numbers", value=wanted)

    def do_style(self, action):
        wanted = (action.get("value") or "").lower()
        if wanted not in ("speak", "visual"):
            self.plain("The two menu styles are speak and visual. "
                       "speak says each choice as you move to it, which is "
                       "what a screen reader needs. visual highlights the "
                       "line instead.")
            return
        menu_mod.set_style(wanted)
        self.config["menu_style"] = wanted
        save_config(self.config)
        self.tell("setting_changed", setting="menu style", value=wanted)

    # ---- checking the app itself ---------------------------------------------

    def do_check(self, action):
        """
        Test the whole chain, here, on this computer, with no printer needed.

        This is for a classroom machine where there is no Python and no way
        to run the test files -- just the exe. It builds a real shape, slices
        it for real, and says plainly which part is broken if any is.
        """
        self.tell("check_start")
        passed = 0
        failed = 0

        def result(part, ok, why=""):
            nonlocal passed, failed
            if ok:
                passed += 1
                self.tell("check_ok", part=t(part))
            else:
                failed += 1
                self.tell("check_bad", part=t(part), why=why)
            return ok

        have_openscad = result("check_modelling",
                               printing_mod.program_exists(OPENSCAD),
                               f"I cannot find {OPENSCAD}.")
        have_slicer = result("check_slicing",
                             printing_mod.program_exists(SLICER),
                             f"I cannot find {SLICER}.")

        profile = PRINTER_CONFIGS / f"{self.printer.model}.ini" \
            if self.printer else None
        have_profile = result(
            "check_profile", bool(profile and profile.exists()),
            f"I cannot find settings for {self.printer.model}."
            if self.printer else "No printer is set up.")

        models = list(MODELS.glob("*.stl")) if MODELS.exists() else []
        result("check_models", len(models) >= 12,
               f"I found {len(models)} of the 12 ready made models.")

        # Build something small but real: a plate with braille on it, which
        # uses shapes, placing, joining and the dot mesh all at once.
        test_stl = WORK_DIR / "check.stl"
        built = False
        if have_openscad:
            trial = Model()
            trial.add_part("plate", {"width": 40, "length": 20, "height": 3})
            dots = trial.add_part("braille", {"words": "ok", "thick": 1})
            dots.pos = [0, 0, 1.9]
            trial.add_group("join", ["plate", "braille"], name="piece")
            ok, why = printing_mod.run_openscad(
                OPENSCAD, trial.scad(), WORK_DIR / "check.scad", test_stl)
            built = result("check_build", ok, why)

        if built and have_slicer and have_profile:
            try:
                settings = printing_mod.PrintSettings()
                working = settings.write_profile(profile, WORK_DIR)
                ok, why = printing_mod.slice_model(
                    SLICER, [test_stl], working, WORK_DIR / "check.gcode")
                if ok:
                    found = printing_mod.gcode_report(WORK_DIR / "check.gcode")
                    ok = bool(found.get("time"))
                    why = "the printing file came out empty"
            except OSError as problem:
                ok, why = False, str(problem)
            result("check_slice", ok, why)

        if self.printer:
            state = self.printer.status()
            result("check_printer", state is not None,
                   f"No answer from {self.printer.ip}. "
                   f"Check it is switched on and on the same network.")

        for name in ("check.scad", "check.stl", "check.gcode"):
            try:
                (WORK_DIR / name).unlink()
            except OSError:
                pass

        if failed:
            self.tell("check_some_bad", failed=failed, total=passed + failed)
        else:
            self.tell("check_all_good", passed=passed)

    # ---- when nothing matched -------------------------------------------------

    def do_unknown(self, action):
        word = action.get("word", "")
        if action.get("reason") == "need_number":
            self.tell("need_number", word=word)
            return
        hint = action.get("guess")
        if hint:
            self.tell("did_you_mean", word=word, guess=hint)
        else:
            self.tell("unknown", word=word)


# ---------------------------------------------------------------------------

def ask_which_interface(config):
    """
    Asked at every start: menus, or typing?

    Whichever was chosen last time is the one already selected, so a student
    who always wants the same one just presses Enter. The answer is
    remembered so that stays true next time.
    """
    menu_mod.set_style(config.get("menu_style", "speak"))
    was = config.get("interface", "menus")

    # Being fed from a file rather than a keyboard: asking would swallow the
    # first line of that file, which is a baffling way for a session file to
    # fail. Use whatever was chosen last time and get on with it.
    if not keys_mod.keyboard_is_there():
        chosen = config.get("interface", "typing")
        config["interface"] = chosen        # or the app starts the other one
        # Arrow adjusting needs a keyboard to read one key at a time, so a
        # session file always gets the typed one whatever is in the config.
        menu_mod.set_number_mode("typed")
        print(t("interface_chosen_menus") if chosen == "menus"
              else t("interface_chosen_typing"))
        return chosen

    chosen = menu_mod.choose(
        t("which_interface"),
        [("menus", t("interface_menus"), t("interface_menus_hint")),
         ("typing", t("interface_typing"), t("interface_typing_hint"))],
        start=0 if was == "menus" else 1,
        allow_back=False)

    if chosen is None:
        chosen = was
    config["interface"] = chosen
    save_config(config)
    print(t("interface_chosen_menus") if chosen == "menus"
          else t("interface_chosen_typing"))

    # Only worth asking about numbers if the menus are going to be used:
    # somebody typing "width 30" has already typed the number.
    if chosen == "menus":
        ask_how_numbers(config)
    return chosen


def ask_how_numbers(config):
    """Arrow keys or typing, for sizes and every other number."""
    was = config.get("number_mode", "arrows")
    chosen = menu_mod.choose(
        t("which_numbers"),
        [("arrows", t("numbers_arrows"), t("numbers_arrows_hint")),
         ("typed", t("numbers_typed"), t("numbers_typed_hint"))],
        start=0 if was == "arrows" else 1,
        allow_back=False)
    if chosen is None:
        chosen = was
    config["number_mode"] = chosen
    menu_mod.set_number_mode(chosen)
    save_config(config)
    print(t("numbers_chosen_arrows") if chosen == "arrows"
          else t("numbers_chosen_typed"))
    return chosen


def main():
    config = load_config()
    if config is None:
        config = ask_setup()
    else:
        config = upgrade_config(config)
        set_language(config.get("lan", 1))
        print(t("welcome"))

    ask_which_interface(config)
    BgeraPrint(config).run()
