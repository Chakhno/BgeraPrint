#!/usr/bin/env python
# coding: utf-8
"""
The menu interface: choose everything with the arrow keys.

This is the second of the app's two ways of working.  Nothing here knows how
to build a model or talk to a printer.  Every menu ends by handing the very
same instruction to the very same BgeraPrint.do() that a typed command
produces, so the two interfaces can never drift apart: fix a bug in one and
it is fixed in both.

The shape of it is: pick something, press Enter, and the next set of choices
appears.  You are never left at an empty prompt wondering what to type,
which is the whole point for a student meeting the app for the first time.
Escape always steps back one level, and never loses work.
"""

from . import help as help_mod
from . import menu
from . import printing as printing_mod
from . import shapes as shapes_mod
from .model import DIRECTIONS, Group

# Sensible starting points for the number picker, per measurement.
STEPS = {
    "width": 5, "length": 5, "height": 5, "across": 5,
    "thick": 1, "sides": 1, "points": 1, "radius": 5, "top": 5,
}
WHOLE_NUMBERS = {"sides", "points"}

MEASURE_QUESTIONS = {
    "width": "How wide, side to side?",
    "length": "How long, front to back?",
    "height": "How tall?",
    "across": "How wide across?",
    "thick": "How thick should the wall be?",
    "sides": "How many sides?",
    "points": "How many points?",
    "radius": "What radius?",
    "top": "How wide across the top?",
}


class Guided:
    """Runs the menus.  `app` is the BgeraPrint instance doing the work."""

    def __init__(self, app):
        self.app = app
        self.running = True

    # -- the loop ---------------------------------------------------------

    def run(self):
        for line in help_mod.INTRO_MENUS:
            print(line)

        while self.running and self.app.running:
            try:
                self.main_menu()
            except KeyboardInterrupt:
                print()
                self.app.tell("goodbye")
                return
            except Exception as problem:        # never drop the student out
                self.app.plain(f"Something went wrong: {problem}")
                self.app.plain("Nothing was lost. "
                               "Choose Listen to your model to check it.")

    def do(self, what, **fields):
        """Hand one instruction to the app, exactly as typing would."""
        fields["do"] = what
        self.app.do(fields)

    # -- the top level ----------------------------------------------------

    def main_menu(self):
        empty = self.app.model.is_empty() and not self.app.external_stl
        choices = [
            ("make", "Make a shape", "cube, ball, braille and the rest"),
        ]
        if not empty:
            choices += [
                ("size", "Change the size of a part"),
                ("place", "Move a part about"),
                ("change", "Change a part in another way",
                 "round it, hollow it, copy it"),
                ("combine", "Put parts together", "join, cut, overlap"),
                ("listen", "Listen to your model"),
            ]
        choices += [
            ("settings", "Change how it prints", "filling, quality, supports"),
            ("prepare", "Get it ready for the printer"),
        ]
        if self.app.prepared:
            choices.append(("print", "Print it now"))
        choices += [
            ("printer", "The printer", "how it is doing, stop it, set one up"),
            ("projects", "Saved work", "save, open, start again"),
            ("share", "Send or receive files"),
            ("learn", "Learn how to use this", "lessons and help"),
            ("typing", "Switch to typing commands"),
            ("quit", "Leave BgeraPrint"),
        ]

        picked = menu.choose("What would you like to do?", choices,
                             allow_back=False)
        if picked is None:
            return

        getattr(self, f"menu_{picked}", self.menu_unknown)()

    def menu_unknown(self):
        self.app.plain("That is not ready yet.")

    # -- making shapes ----------------------------------------------------

    # The order the shapes are offered in: the ones a class reaches for
    # most, first. It is one flat list rather than groups, so any shape is
    # one Enter away, and the number keys jump straight to it.
    SHAPE_ORDER = ["cube", "ball", "rod", "cone", "plate", "wedge",
                   "pyramid", "prism", "star", "tube", "ring", "donut",
                   "text", "braille"]

    def menu_make(self):
        choices = [(name, name.capitalize(), _short_hint(name))
                   for name in self.SHAPE_ORDER]
        choices.append(("builtin", "A ready made model",
                        "lion, turtle, chess pieces"))
        choices.append(("file", "A shape file from my computer"))

        picked = menu.choose("What shall we make?", choices)
        if picked is None:
            return
        if picked == "builtin":
            return self.menu_builtin()
        if picked == "file":
            path = menu.ask_words("Type the full path to your .stl file: ")
            if path:
                self.do("openfile", path=path)
            return

        words = None
        if shapes_mod.SHAPES[picked].get("takes_words"):
            question = ("What should it say? " if picked == "text"
                        else "What should the braille say? ")
            words = menu.ask_words(question)
            if not words:
                self.app.plain("Nothing to write, so nothing was made.")
                return

        if words is None:
            self.do("shape", shape=picked)
        else:
            self.do("shape", shape=picked, words=words)

        # Straight on to the measurements, which is what a student wants
        # next every single time.
        part = self.app.model.current()
        if part is not None:
            self.ask_measurements(part)

    def menu_builtin(self):
        animals = ["lion", "turtle", "giraffe", "wolf", "camel", "rocket"]
        chess = ["pawn", "rook", "knight", "bishop", "queen", "king"]
        choices = [(n, n.capitalize()) for n in animals]
        choices += [(n, f"{n.capitalize()}, a chess piece") for n in chess]
        picked = menu.choose("Which model?", choices)
        if picked:
            self.do("builtin", name=picked)

    # -- measurements -----------------------------------------------------

    def ask_measurements(self, part, one_only=False):
        """
        Set a shape's measurements.

        In "arrows" mode this is one menu you never leave: Up and Down walk
        between width, length and height, Left and Right change whichever
        one you are on, and the line you are hearing updates as it goes.
        In "typed" mode, Enter on a line asks for the number instead.

        This is what replaces typing "width 30 length 20 height 10".
        """
        if isinstance(part, Group):
            self.app.plain(f"{part.name} is made of other parts. "
                           f"Change {', '.join(part.members)} instead.")
            return

        info = shapes_mod.SHAPES[part.shape]
        needed = [m for m in info["needs"] if m in shapes_mod.LIMITS]
        if not needed:
            return

        if menu.get_number_mode() == "arrows":
            self.adjust_measurements(part, needed, info)
        else:
            self.type_measurements(part, needed, info)
        self._say_size(part)

    def adjust_measurements(self, part, needed, info):
        """One menu, changed in place with the left and right arrows."""

        def value_of(measure):
            return part.params.get(measure, info["defaults"].get(measure, 20))

        def label(measure):
            return f"now {_tidy(value_of(measure))}"

        def adjust(measure, way, size):
            low, high = shapes_mod.LIMITS.get(measure, (0.2, 500))
            if measure in WHOLE_NUMBERS:
                size = max(1, round(size))
            wanted = max(low, min(high, value_of(measure) + size * way))
            # menu._tidy keeps 103 an int rather than 103.0, and rounds off
            # the floating point dust that adding 0.1 leaves behind.
            wanted = menu._tidy(wanted, whole=measure in WHOLE_NUMBERS)
            part.params[measure] = wanted
            self.app.prepared = False
            return f"now {_tidy(wanted)}"

        # One undo step for the whole sizing, not one per keypress: a
        # student who held an arrow down does not want fifty undos to get
        # back to where they started.
        self.app.model.change(f"change the size of {part.name}")

        choices = [(m, m.capitalize(), label(m)) for m in needed]
        choices.append(("done", "That is the right size"))
        menu.choose(f"What size shall {part.name} be?", choices,
                    on_adjust=adjust)

    def type_measurements(self, part, needed, info):
        """A menu of measurements; Enter on one asks for the number."""
        at = 0
        while True:
            choices = []
            for measure in needed:
                now = part.params.get(measure, info["defaults"].get(measure))
                choices.append((measure, measure.capitalize(),
                                f"now {_tidy(now)}"))
            choices.append(("done", "That is the right size"))
            picked = menu.choose(f"What shall we set on {part.name}?",
                                 choices, start=at)
            if picked in (None, "done"):
                return
            self.ask_one_measurement(part, picked)
            # Land on the next measurement rather than back at the top.
            at = min(needed.index(picked) + 1, len(choices) - 1)

    def ask_one_measurement(self, part, measure):
        info = shapes_mod.SHAPES[part.shape]
        low, high = shapes_mod.LIMITS.get(measure, (0.2, 500))
        now = part.params.get(measure, info["defaults"].get(measure, 20))
        unit = "" if measure in WHOLE_NUMBERS else "millimetres"

        value = menu.pick_number(
            MEASURE_QUESTIONS.get(measure, f"How much {measure}?"),
            current=now, step=STEPS.get(measure, 5), low=low, high=high,
            unit=unit, whole=measure in WHOLE_NUMBERS)

        if value is not None:
            self.do("measure", values={measure: value}, target=part.name)

    def _say_size(self, part):
        self.app.tell("size_set", name=part.name,
                      dims=shapes_mod.describe_size(part.shape, part.params))

    def menu_size(self):
        part = self.pick_part("Which part shall we resize?")
        if part is not None:
            self.ask_measurements(part)

    # -- moving -----------------------------------------------------------

    def menu_place(self):
        part = self.pick_part("Which part shall we move?")
        if part is None:
            return
        while True:
            picked = menu.choose(
                f"What shall we do with {part.name}?",
                [("move", "Slide it", "right, left, forward, back, up, down"),
                 ("on", "Sit it on top of another part"),
                 ("beside", "Put it beside another part"),
                 ("turn", "Turn it"),
                 ("centre", "Put it back in the middle"),
                 ("done", "That is where I want it")])
            if picked in (None, "done"):
                return
            if picked == "move":
                self.ask_move(part)
            elif picked == "turn":
                self.ask_turn(part)
            elif picked == "centre":
                self.do("center", target=part.name)
            elif picked == "on":
                other = self.pick_part("Sit it on which part?", not_this=part)
                if other is not None:
                    self.do("stack", top=part.name, bottom=other.name)
            elif picked == "beside":
                other = self.pick_part("Beside which part?", not_this=part)
                if other is not None:
                    self.do("beside", a=part.name, b=other.name)

    def ask_move(self, part):
        direction = menu.choose(
            "Which way?",
            [("right", "Right"), ("left", "Left"),
             ("forward", "Forward"), ("back", "Back"),
             ("up", "Up"), ("down", "Down")])
        if direction is None:
            return
        amount = menu.pick_number(f"How far {direction}?", current=10, step=5,
                                  low=0.2, high=300)
        if amount is None:
            return
        dx, dy, dz = DIRECTIONS[direction]
        self.do("move", target=part.name,
                delta=[dx * amount, dy * amount, dz * amount])

    def ask_turn(self, part):
        way = menu.choose(
            "Which way shall it turn?",
            [("z", "Spin it flat", "like a wheel lying down"),
             ("y", "Tip it forward"),
             ("x", "Roll it to one side")])
        if way is None:
            return
        angle = menu.choose(
            "By how much?",
            [(90, "A quarter turn, 90 degrees"),
             (180, "A half turn, 180 degrees"),
             (45, "45 degrees"),
             (270, "Three quarters, 270 degrees"),
             ("other", "Some other angle")])
        if angle is None:
            return
        if angle == "other":
            angle = menu.pick_number("How many degrees?", current=90, step=15,
                                     low=-360, high=360, unit="degrees",
                                     whole=True)
            if angle is None:
                return
        turn = [0.0, 0.0, 0.0]
        turn["xyz".index(way)] = angle
        self.do("turn", target=part.name, turn=turn)

    # -- changing ---------------------------------------------------------

    def menu_change(self):
        part = self.pick_part("Which part shall we change?")
        if part is None:
            return
        while True:
            picked = menu.choose(
                f"What shall we do to {part.name}?",
                [("round", "Round off its edges"),
                 ("hollow", "Hollow it out"),
                 ("bigger", "Make it bigger or smaller"),
                 ("mirror", "Flip it over"),
                 ("copy", "Make a row of copies"),
                 ("ring", "Make a circle of copies"),
                 ("smooth", "Wrap a smooth skin around it"),
                 ("rename", "Give it a different name"),
                 ("remove", "Take it away"),
                 ("done", "Nothing more")])
            if picked in (None, "done"):
                return

            if picked == "round":
                amount = menu.pick_number("How much shall the edges be rounded?",
                                          current=3, step=1, low=0.2, high=20)
                if amount is not None:
                    self.do("round", amount=amount, target=part.name)
            elif picked == "hollow":
                amount = menu.pick_number("How thick shall the walls be?",
                                          current=2, step=0.5, low=0.4, high=20)
                if amount is not None:
                    self.do("hollow", amount=amount, target=part.name)
            elif picked == "bigger":
                factor = menu.choose(
                    "How much bigger or smaller?",
                    [(2, "Twice the size"), (1.5, "Half again as big"),
                     (0.5, "Half the size"), (0.25, "A quarter of the size"),
                     ("other", "Some other amount")])
                if factor == "other":
                    factor = menu.pick_number("How many times its size?",
                                              current=2, step=0.5, low=0.1,
                                              high=20, unit="times")
                if factor is not None:
                    self.do("scale", factor=factor, target=part.name)
            elif picked == "mirror":
                axis = menu.choose("Which way shall it flip?",
                                   [("x", "Left to right"),
                                    ("y", "Front to back"),
                                    ("z", "Top to bottom")])
                if axis is not None:
                    self.do("mirror", axis=axis, target=part.name)
            elif picked == "copy":
                self.ask_copies(part)
            elif picked == "ring":
                count = menu.pick_number("How many copies in the circle?",
                                         current=6, step=1, low=2, high=40,
                                         unit="", whole=True)
                if count is None:
                    continue
                across = menu.pick_number("How wide across is the circle?",
                                          current=60, step=10, low=5, high=300)
                if across is not None:
                    self.do("ring", count=count, across=across,
                            target=part.name)
            elif picked == "smooth":
                self.do("smooth", target=part.name)
            elif picked == "rename":
                new = menu.ask_words("What shall it be called? ")
                if new:
                    self.do("rename", old=part.name, new=new)
                    part = self.app.model.find(new) or part
            elif picked == "remove":
                if menu.confirm(f"Really take {part.name} away?"):
                    self.do("remove", name=part.name)
                    return

    def ask_copies(self, part):
        count = menu.pick_number("How many copies?", current=3, step=1,
                                 low=2, high=50, unit="", whole=True)
        if count is None:
            return
        gap = menu.pick_number("How far apart?", current=30, step=5,
                               low=1, high=300)
        if gap is None:
            return
        direction = menu.choose("Which way shall they go?",
                                [("right", "To the right"),
                                 ("forward", "Forwards"),
                                 ("up", "Upwards")])
        if direction is not None:
            self.do("copy", count=count, gap=gap, dir=direction,
                    target=part.name)

    # -- combining --------------------------------------------------------

    def menu_combine(self):
        tops = self.app.model.top_level()
        if len(tops) < 2:
            self.app.tell("need_two_parts", action="put parts together")
            return

        how = menu.choose(
            "How shall they go together?",
            [("join", "Join them into one piece"),
             ("cut", "Cut one out of the other", "makes a hole"),
             ("overlap", "Keep only where they overlap")])
        if how is None:
            return

        if how == "cut":
            first = self.pick_part("Which part shall keep its shape?")
            if first is None:
                return
            second = self.pick_part("Which part shall be cut out of it?",
                                    not_this=first)
        else:
            first = self.pick_part("Which part first?")
            if first is None:
                return
            second = self.pick_part("And which one with it?", not_this=first)
        if second is None:
            return
        self.do("combine", op=how, a=first.name, b=second.name)

    # -- listening --------------------------------------------------------

    def menu_listen(self):
        picked = menu.choose(
            "What would you like to hear?",
            [("describe", "The whole model, in sentences"),
             ("list", "Every part and its size"),
             ("size", "How big it is altogether"),
             ("settings", "The print settings"),
             ("what", "What I just did"),
             ("undo", "Undo the last thing"),
             ("redo", "Put it back")])
        if picked:
            self.do(picked)

    # -- print settings ---------------------------------------------------

    def menu_settings(self):
        while True:
            choices = []
            for key in printing_mod.SETTINGS:
                choices.append((key, key.capitalize(),
                                f"now {self.app.settings.spoken(key)}"))
            choices.append(("reset", "Put them all back to normal"))
            choices.append(("done", "That is all"))

            picked = menu.choose("Which setting?", choices)
            if picked in (None, "done"):
                return
            if picked == "reset":
                self.do("reset_settings")
                continue
            self.ask_setting(picked)

    def ask_setting(self, key):
        info = printing_mod.SETTINGS[key]
        print()
        print(info["help"])

        if info["kind"] == "choice":
            seen = []
            for word in info["choices"]:
                if word not in seen:
                    seen.append(word)
            value = menu.choose(f"What shall {key} be?",
                                [(w, w.capitalize()) for w in seen],
                                start=_index_of(seen, self.app.settings.values[key]))
        elif info["kind"] == "switch":
            value = menu.choose(f"Shall {key} be on or off?",
                                [("on", "On"), ("off", "Off")],
                                start=0 if self.app.settings.values[key] == "on" else 1)
        elif key in ("heat", "bed"):
            # These two have a third state that a number picker cannot
            # express: leave them alone and let the printer profile decide.
            # Without this the menus could set a temperature but never
            # un-set one.
            now = self.app.settings.values[key]
            what = menu.choose(
                f"What shall {key} be?",
                [(0, "Leave it to the printer",
                  "whatever the printer profile says"),
                 ("set", "Set it myself")],
                start=1 if now else 0)
            if what is None:
                return
            if what == 0:
                value = 0
            else:
                low, high = info["limits"]
                value = menu.pick_number(
                    "How hot?", current=now or low, step=5,
                    low=low, high=high, unit=info["unit"], whole=True)
        else:
            low, high = info["limits"]
            step = 1 if high - low <= 20 else 5
            value = menu.pick_number(
                f"What shall {key} be?", current=self.app.settings.values[key],
                step=step, low=low, high=high, unit=info["unit"],
                whole=info["unit"] in ("walls", "layers", "copies"))

        if value is not None:
            self.do("setting", key=key, value=value)

    # -- printing ---------------------------------------------------------

    def menu_prepare(self):
        self.do("prepare")
        if not self.app.prepared:
            return
        picked = menu.choose(
            "What now?",
            [("print", "Send it to the printer and start"),
             ("settings", "Change a setting and try again"),
             ("back", "Nothing yet")])
        if picked == "print":
            self.menu_print()
        elif picked == "settings":
            self.menu_settings()

    def menu_print(self):
        if not self.app.prepared:
            self.app.tell("prepare_first")
            return
        report = self.app.last_report
        question = (f"Really start printing? It will take "
                    f"{report.get('time', 'a while')}.")
        if menu.confirm(question):
            self.app.confirm = "print"
            self.do("print")

    def menu_printer(self):
        picked = menu.choose(
            "What about the printer?",
            [("status", "How is the print going?"),
             ("pause", "Pause it"),
             ("resume", "Carry on"),
             ("stopprint", "Stop the print"),
             ("printers", "Which printers are set up"),
             ("addprinter", "Set up another printer"),
             ("useprinter", "Use a different printer"),
             ("check", "Check that everything is working")])
        if picked is None:
            return
        if picked == "stopprint":
            if menu.confirm("Really stop the print?"):
                self.app.confirm = "stopprint"
                self.do("stopprint")
            return
        if picked == "useprinter":
            names = [(p.name, p.name, p.model) for p in self.app.printers]
            chosen = menu.choose("Which printer?", names)
            if chosen:
                self.do("useprinter", name=chosen)
            return
        self.do(picked)

    # -- projects ---------------------------------------------------------

    def menu_projects(self):
        from .model import Model
        saved = Model.saved_projects(self.app.projects_dir())

        choices = [("save", "Save what I have made")]
        if saved:
            choices.append(("open", "Open something I saved"))
            choices.append(("list", "What have I saved?"))
        choices.append(("export", "Save the shape file to Downloads"))
        choices.append(("new", "Start again with nothing"))

        picked = menu.choose("Saved work", choices)
        if picked is None:
            return
        if picked == "save":
            name = menu.ask_words("What shall we call it? ")
            if name:
                self.do("save", name=name)
        elif picked == "open":
            chosen = menu.choose("Which one?",
                                 [(n, n, f"saved {w}") for n, w in saved])
            if chosen:
                self.do("open", name=chosen)
        elif picked == "list":
            self.do("projects")
        elif picked == "new":
            if self.app.model.is_empty() or menu.confirm(
                    "Start again? You can undo this afterwards."):
                self.do("new")
        else:
            self.do("export")

    # -- sharing ----------------------------------------------------------

    def menu_share(self):
        picked = menu.choose(
            "Sending files between computers",
            [("send", "Send my file to another computer"),
             ("receive", "Wait for files from other computers"),
             ("done", "Stop waiting for files")])
        if picked:
            self.do(picked)

    # -- learning ---------------------------------------------------------

    def menu_learn(self):
        picked = menu.choose(
            "Learning",
            [("lesson", "Do a lesson"),
             ("help", "Hear about something")])
        if picked == "lesson":
            chosen = menu.choose(
                "Which lesson?",
                [(n, f"Lesson {n}: {title}")
                 for n, title in enumerate(help_mod.lesson_titles(), start=1)])
            if chosen:
                self.app.plain("The lessons teach the typing commands. "
                               "Switching you over for now.")
                self.do("lesson", n=chosen)
                self.app.interface = "typing"
                self.running = False
        elif picked == "help":
            topic = menu.choose(
                "What about?",
                [(name, name.capitalize()) for name in help_mod.ORDER])
            if topic:
                self.do("help", topic=topic)

    # -- switching and leaving --------------------------------------------

    def menu_typing(self):
        self.app.plain("Switching to typing. "
                       "Type menu at any time to come back.")
        self.app.interface = "typing"
        self.running = False

    def menu_quit(self):
        if menu.confirm("Leave BgeraPrint?", default_yes=True):
            self.do("quit")
            self.running = False

    # -- picking a part ---------------------------------------------------

    def pick_part(self, question, not_this=None):
        tops = self.app.model.top_level()
        if not_this is not None:
            tops = [n for n in tops if n != not_this.name]
        if not tops:
            self.app.tell("nothing_yet")
            return None
        if len(tops) == 1:
            return self.app.model.items[tops[0]]

        choices = []
        for name in tops:
            item = self.app.model.items[name]
            kind = ("made of " + ", ".join(item.members)
                    if isinstance(item, Group) else f"a {item.shape}")
            choices.append((name, name, kind))
        chosen = menu.choose(question, choices, start=len(choices) - 1)
        return self.app.model.items.get(chosen) if chosen else None


# ---------------------------------------------------------------------------

def _short_hint(name):
    plain = {
        "cube": "a box", "ball": "round all over", "rod": "a round bar",
        "cone": "pointed at the top", "pyramid": "flat sides meeting at a point",
        "prism": "a bar with flat sides", "tube": "a bar with a hole through it",
        "ring": "a flat ring", "donut": "a round ring",
        "wedge": "a ramp", "star": "a star", "plate": "thin and flat",
        "text": "raised letters", "braille": "real braille dots",
    }
    return plain.get(name, "")


def _index_of(items, value):
    try:
        return items.index(value)
    except ValueError:
        return 0


def _tidy(value):
    if value is None:
        return "not set"
    if isinstance(value, float) and value == int(value):
        return int(value)
    return value
