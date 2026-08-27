#!/usr/bin/env python
# coding: utf-8
"""
Menus you move through with the arrow keys, and a number picker.

    Up / Down       move
    Enter           choose the one you are on
    1 to 9          jump straight to that one
    a letter        jump to the next choice starting with it
    Escape          go back
    ?               hear the choices again

WHY THERE ARE TWO WAYS OF DRAWING A MENU
----------------------------------------
The obvious way -- draw the list once and redraw it in place with the
current line highlighted -- is what most terminal menus do and it looks
good.  It is also close to useless with a screen reader.  NVDA and JAWS
announce text that is NEW in a terminal; text that is REDRAWN in place is
announced inconsistently, and often not at all.  A student could press Down
five times and hear silence.

So the same menu can draw itself two ways:

    "speak"    the list is read out once, then every keypress prints the
               choice you have landed on as a brand new line.  Always
               announced, by every screen reader, because it is new text.
               This is the default, because of who the app is for.

    "visual"   the in-place redraw, with a marker beside the current line.
               Looks better on a screen.  Use it for showing the app off,
               or if a student uses a magnifier rather than speech.

Both take exactly the same keys and return exactly the same answers.
"""

import sys
import time

from . import keys as keys_mod

MARKER = ">"
STYLE = "speak"              # "speak" or "visual"
NUMBER_MODE = "arrows"       # "arrows" or "typed"


def set_style(style):
    global STYLE
    STYLE = "visual" if style == "visual" else "speak"


def get_style():
    return STYLE


# Everything that cares about timing asks this, so a test can hand the whole
# module a fake clock. Acceleration that can only be tested by holding a key
# down for real is acceleration that never gets tested.
def _now():
    return time.monotonic()


def set_number_mode(mode):
    global NUMBER_MODE
    NUMBER_MODE = "typed" if mode == "typed" else "arrows"


def get_number_mode():
    return NUMBER_MODE


# ---------------------------------------------------------------------------
# Holding an arrow key down
# ---------------------------------------------------------------------------

class Ramp:
    """
    How much one press of an arrow key should change a number by.

    A terminal cannot tell you that a key is being HELD.  What it gives you
    instead is the keyboard's own auto-repeat: hold Right and the same key
    arrives over and over, roughly thirty times a second, after a pause of
    about half a second.  So "held for longer" has to be worked out from how
    FAST the presses are arriving.

    Presses closer together than TOGETHER seconds are taken to be the
    keyboard repeating rather than a student pressing again, and the step
    climbs through LADDER the longer the run goes on.  Change direction, or
    pause, and it drops straight back to the smallest step.

    The clock is handed in so the tests can drive it with a fake one; timing
    that can only be tested by holding a key down is timing that never gets
    tested.
    """

    TOGETHER = 0.18          # seconds; closer than this is the key repeating
    LADDER = [(5, 0.1), (10, 0.5), (20, 1.0), (35, 5.0), (None, 10.0)]

    def __init__(self, clock=None):
        self.clock = clock or _now
        self.reset()

    def reset(self):
        self.run = 0
        self.last_at = None
        self.last_way = None

    @property
    def step(self):
        for upto, size in self.LADDER:
            if upto is None or self.run < upto:
                return size
        return self.LADDER[-1][1]

    def next_step(self, way):
        """
        How far to move this time, given which way the arrow points.

        Returns (step, step_changed) so the caller can say the new size out
        loud when it changes, which is the only warning a student gets that
        the numbers are about to move faster.
        """
        now = self.clock()
        before = self.step

        if (self.last_at is not None
                and self.last_way == way
                and now - self.last_at < self.TOGETHER):
            self.run += 1
        else:
            self.run = 0

        self.last_at = now
        self.last_way = way
        return self.step, self.step != before


class Choice:
    """One line in a menu."""

    def __init__(self, value, label, hint=""):
        self.value = value
        self.label = label
        self.hint = hint

    def spoken(self, number=None, total=None):
        text = self.label
        if self.hint:
            text += f", {self.hint}"
        if number and total:
            return f"{number} of {total}. {text}"
        return text


def as_choices(options):
    """Accept plain strings, pairs, triples, or Choice objects."""
    out = []
    for option in options:
        if isinstance(option, Choice):
            out.append(option)
        elif isinstance(option, (list, tuple)):
            if len(option) >= 3:
                out.append(Choice(option[0], option[1], option[2]))
            else:
                out.append(Choice(option[0], option[1]))
        else:
            out.append(Choice(option, str(option)))
    return out


# ---------------------------------------------------------------------------

def choose(title, options, start=0, allow_back=True, back_label="Go back",
           on_adjust=None):
    """
    Show a menu and give back the value of whatever was chosen.

    Returns None if the student pressed Escape or chose "Go back".

    on_adjust turns the menu into something you can change without leaving
    it: press Left or Right on a line and on_adjust(value, way, step) is
    called, where way is +1 or -1. It gives back the new wording for that
    line, which is then read out. That is how "Width, now 20" becomes
    "Width, now 20.1" under a student's finger without any sub-menu at all.
    """
    choices = as_choices(options)
    if not choices:
        return None

    if not keys_mod.keyboard_is_there():
        return _choose_by_typing(title, choices, allow_back)

    if STYLE == "visual":
        return _choose_visually(title, choices, start, allow_back, back_label,
                                on_adjust)
    return _choose_by_speaking(title, choices, start, allow_back, back_label,
                               on_adjust)


def _adjusted(choices, at, on_adjust, key, ramp, talker):
    """
    Handle Left or Right on a menu line. True if the key was ours.

    The wording of the line is replaced with whatever on_adjust gives back,
    and read out -- but no more often than SAY_EVERY, or a held arrow would
    bury a screen reader.
    """
    if on_adjust is None:
        return False
    way = _which_way_sideways(key)
    if way is None:
        return False

    size, size_changed = ramp.next_step(way)
    hint = on_adjust(choices[at].value, way, size)
    if hint is not None:
        choices[at].hint = hint
    extra = f"  (now moving by {_tidy(size)})" if size_changed else ""
    talker.maybe(f"{MARKER} {choices[at].spoken()}{extra}", force=size_changed)
    return True


def _which_way_sideways(key):
    """Only Left and Right adjust: Up and Down still move between lines."""
    if key == keys_mod.RIGHT:
        return 1
    if key == keys_mod.LEFT:
        return -1
    return None


# ---------------------------------------------------------------------------
# The style that works with a screen reader
# ---------------------------------------------------------------------------

def _choose_by_speaking(title, choices, start, allow_back, back_label,
                        on_adjust=None):
    total = len(choices)
    at = max(0, min(start, total - 1))
    ramp = Ramp()
    talker = Talker()

    print()
    print(title)
    for number, choice in enumerate(choices, start=1):
        print(f"  {number}. {choice.spoken()}")
    if allow_back:
        print(f"  Escape. {back_label}")
    if on_adjust is not None:
        print("Up and down move. Left and right change the one you are on, "
              "faster the longer you hold them. Enter when you are done.")
    else:
        print("Use the up and down arrows, then press Enter.")
    print(f"{MARKER} {choices[at].spoken(at + 1, total)}")

    while True:
        try:
            key = keys_mod.read_key()
        except keys_mod.NoKeyboard:
            if keys_mod.pretending():
                raise      # a test ran out of keys; do not sit on input()
            return _choose_by_typing(title, choices, allow_back)
        except KeyboardInterrupt:
            return None

        if _adjusted(choices, at, on_adjust, key, ramp, talker):
            continue
        talker.settle()      # the arrows stopped; say where it landed

        moved = _move(key, at, total, sideways=on_adjust is None)
        if moved is not None:
            if moved != at:
                at = moved
                ramp.reset()
                print(f"{MARKER} {choices[at].spoken(at + 1, total)}")
            continue

        if key == keys_mod.ENTER:
            print(f"Chosen: {choices[at].label}.")
            return choices[at].value

        if key == keys_mod.ESCAPE and allow_back:
            print(back_label + ".")
            return None

        if key == "?":
            for number, choice in enumerate(choices, start=1):
                print(f"  {number}. {choice.spoken()}")
            print(f"{MARKER} {choices[at].spoken(at + 1, total)}")
            continue

        jumped = _jump(key, choices, at)
        if jumped is not None:
            at = jumped
            print(f"{MARKER} {choices[at].spoken(at + 1, total)}")


# ---------------------------------------------------------------------------
# The style that looks like a terminal app
# ---------------------------------------------------------------------------

def _choose_visually(title, choices, start, allow_back, back_label,
                     on_adjust=None):
    total = len(choices)
    at = max(0, min(start, total - 1))
    drawn = 0
    ramp = Ramp()
    talker = Talker()

    while True:
        if drawn:
            sys.stdout.write(f"\x1b[{drawn}A")
        lines = []
        for number, choice in enumerate(choices):
            mark = MARKER if number == at else " "
            body = choice.label + (f"   {choice.hint}" if choice.hint else "")
            if number == at:
                lines.append(f"\x1b[36m{mark} {body}\x1b[0m\x1b[K")
            else:
                lines.append(f"\x1b[2m{mark} {body}\x1b[0m\x1b[K")
        if allow_back:
            lines.append("\x1b[2m  Escape to go back\x1b[0m\x1b[K")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        drawn = len(lines)

        try:
            key = keys_mod.read_key()
        except keys_mod.NoKeyboard:
            if keys_mod.pretending():
                raise      # a test ran out of keys; do not sit on input()
            return _choose_by_typing(title, choices, allow_back)
        except KeyboardInterrupt:
            return None

        if _adjusted(choices, at, on_adjust, key, ramp, talker):
            drawn = 0          # the line changed; draw the list afresh
            continue
        talker.settle()
        moved = _move(key, at, total, sideways=on_adjust is None)
        if moved is not None:
            at = moved
            ramp.reset()
            continue
        if key == keys_mod.ENTER:
            print(f"Chosen: {choices[at].label}.")
            return choices[at].value
        if key == keys_mod.ESCAPE and allow_back:
            return None
        jumped = _jump(key, choices, at)
        if jumped is not None:
            at = jumped


# ---------------------------------------------------------------------------
# Shared key handling
# ---------------------------------------------------------------------------

def _move(key, at, total, sideways=True):
    """
    Where the arrow keys take you, or None if this key does not move.

    sideways is off when the menu can be adjusted, because Left and Right
    are then changing the number rather than walking the list.
    """
    if key == keys_mod.UP:
        return (at - 1) % total
    if key == keys_mod.DOWN:
        return (at + 1) % total
    if key == keys_mod.HOME:
        return 0
    if key == keys_mod.END:
        return total - 1
    if key == keys_mod.PAGE_UP:
        return max(0, at - 5)
    if key == keys_mod.PAGE_DOWN:
        return min(total - 1, at + 5)
    return None


def _jump(key, choices, at):
    """A digit jumps to that line; a letter jumps to the next match."""
    if not key or len(key) != 1:
        return None

    if key.isdigit() and key != "0":
        wanted = int(key) - 1
        if wanted < len(choices):
            return wanted
        return None

    if key.isalpha():
        lowered = key.lower()
        order = list(range(at + 1, len(choices))) + list(range(0, at + 1))
        for index in order:
            if choices[index].label.lower().startswith(lowered):
                return index
    return None


def _choose_by_typing(title, choices, allow_back):
    """
    No keyboard to read one key at a time, so ask for a typed answer.

    This is what makes session files and the tests work with the menus: a
    line such as "3" or "cube" picks a choice just as an arrow key would.
    """
    print()
    print(title)
    for number, choice in enumerate(choices, start=1):
        print(f"  {number}. {choice.spoken()}")
    if allow_back:
        print("  0. Go back")

    while True:
        try:
            answer = input("Type the number, or the name: ").strip()
        except EOFError:
            return None
        if not answer:
            continue
        if answer == "0" and allow_back:
            return None
        if answer.isdigit():
            wanted = int(answer) - 1
            if 0 <= wanted < len(choices):
                print(f"Chosen: {choices[wanted].label}.")
                return choices[wanted].value
        lowered = answer.lower()
        for choice in choices:
            if choice.label.lower() == lowered:
                print(f"Chosen: {choice.label}.")
                return choice.value
        for choice in choices:
            if choice.label.lower().startswith(lowered):
                print(f"Chosen: {choice.label}.")
                return choice.value
        print("I do not know that one. Type one of the numbers above.")


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def pick_number(title, current=20, step=5, low=0.2, high=500, unit="millimetres",
                whole=False):
    """
    Ask for a number, whichever way the student chose at the start.

        "typed"    they type it and press Enter
        "arrows"   Left and Right change it, faster the longer they are held

    Returns the number, or None if they pressed Escape and left it alone.
    """
    if not keys_mod.keyboard_is_there():
        return _type_a_number(title, current, low, high, whole)
    if NUMBER_MODE == "typed":
        return _type_a_number(title, current, low, high, whole)
    return _arrow_a_number(title, current, low, high, unit, whole)


def _arrow_a_number(title, current, low, high, unit, whole):
    """
    Change a number with the arrow keys.

        Left / Down     smaller
        Right / Up      bigger
        Enter           that is the number
        Escape          leave it as it was

    It starts at a tenth of a millimetre a press, and speeds up while an
    arrow is held, so a student can nudge a wall thickness by 0.1 and still
    get from 20 to 200 without wearing out a finger.
    """
    value = _tidy(_clamp(current, low, high), whole)
    ramp = Ramp()
    talker = Talker()
    at_limit = False

    print()
    print(title)
    print("Left and right arrows change it. Hold one down to go faster. "
          "Enter when it is right.")
    print(f"{MARKER} {_say(value, unit)}")

    while True:
        try:
            key = keys_mod.read_key()
        except keys_mod.NoKeyboard:
            if keys_mod.pretending():
                raise      # a test ran out of keys; do not sit on input()
            return _type_a_number(title, value, low, high, whole)
        except KeyboardInterrupt:
            return None

        if key == keys_mod.ENTER:
            talker.settle()
            print(f"Set to {_say(value, unit)}.")
            return value

        if key == keys_mod.ESCAPE:
            print("Left as it was.")
            return None

        way = _which_way(key)
        if way is None:
            talker.settle()
            continue

        size, size_changed = ramp.next_step(way)
        if whole:
            size = max(1, round(size))
        wanted = _tidy(_clamp(value + size * way, low, high), whole)

        if wanted == value:
            if not at_limit:
                edge = "smallest" if way < 0 else "largest"
                print(f"{_say(value, unit)} is the {edge} it can be.")
                at_limit = True
            continue

        at_limit = False
        value = wanted
        extra = f"  (now moving by {_tidy(size, whole)})" if size_changed else ""
        talker.maybe(f"{MARKER} {_say(value, unit)}{extra}", force=size_changed)


def _which_way(key):
    """+1 for bigger, -1 for smaller, None for a key that does neither."""
    if key in (keys_mod.RIGHT, keys_mod.UP):
        return 1
    if key in (keys_mod.LEFT, keys_mod.DOWN):
        return -1
    return None


# How often a running number may be spoken.  Every single 0.1 step would be
# about thirty announcements a second, which no screen reader can keep up
# with and nobody could follow.  Three a second is plenty to tell you which
# way it is going.
SAY_EVERY = 0.3


class Talker:
    """
    Says a changing number often enough to follow, but not so often that a
    screen reader cannot keep up -- and never lets the last one go unsaid.

    Skipping announcements while an arrow is held is necessary. Skipping the
    one where it finally STOPPED would be a bug: the student would hear
    "118" and walk away with 168. So anything held back is remembered, and
    said as soon as the moving stops.
    """

    def __init__(self):
        self.last_at = _now()
        self.held_back = None

    def maybe(self, text, force=False):
        """Say it now if there is room, otherwise keep it for later."""
        now = _now()
        if force or now - self.last_at >= SAY_EVERY:
            self.last_at = now
            self.held_back = None
            print(text)
        else:
            self.held_back = text

    def settle(self):
        """The moving has stopped: say whatever was held back."""
        if self.held_back is not None:
            print(self.held_back)
            self.held_back = None
            self.last_at = _now()


def _type_a_number(title, current, low, high, whole):
    print()
    print(title)
    # A student gets as many goes as they like, but something feeding the
    # app the same wrong answer forever must not spin here: session files
    # and tests have made exactly that mistake.
    for _ in range(20):
        try:
            answer = input(f"Type a number between {_tidy(low, whole)} "
                           f"and {_tidy(high, whole)}: ").strip()
        except EOFError:
            return None
        if not answer:
            return None
        try:
            value = float(answer)
        except ValueError:
            print("That is not a number. Try again.")
            continue
        if not low <= value <= high:
            print(f"It has to be between {_tidy(low, whole)} "
                  f"and {_tidy(high, whole)}.")
            continue
        value = _tidy(value, whole)
        print(f"Set to {value}.")
        return value

    print("I could not make sense of that. Leaving it as it was.")
    return None


def _clamp(value, low, high):
    return max(low, min(high, value))


def _tidy(value, whole=False):
    if whole:
        return int(round(value))
    # One decimal place: the steps start at 0.1, and floating point turns
    # 20 + 0.1 into 20.000000000000004 if it is left alone.
    value = round(float(value), 1)
    return int(value) if value == int(value) else value


def _say(value, unit):
    return f"{value} {unit}" if unit else str(value)


# ---------------------------------------------------------------------------

def confirm(question, default_yes=False):
    """A yes or no question, answered with the arrow keys."""
    answer = choose(question,
                    [(True, "Yes"), (False, "No")],
                    start=0 if default_yes else 1,
                    allow_back=False)
    return bool(answer)


def ask_words(question):
    """Some words the student types, such as a name for braille."""
    print()
    try:
        return input(question).strip()
    except EOFError:
        return ""
