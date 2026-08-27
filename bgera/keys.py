#!/usr/bin/env python
# coding: utf-8
"""
Reading one keypress at a time, on Windows and on everything else.

Menus need to know the moment an arrow key is pressed, which input() cannot
tell them: input() waits for Enter. So this reads the keyboard directly.

Windows and Unix report arrow keys completely differently -- Windows sends a
marker byte and then a letter, Unix sends an escape sequence -- so both are
handled here and the rest of the app only ever sees the names below.

If there is no keyboard at all (the app is being fed from a file, which is
how the tests and tests/play.py drive it), read_key raises NoKeyboard and
the menus fall back to reading a typed line instead. That matters: it means
every session file still works with the menu interface.
"""

import sys

UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"
ENTER = "enter"
ESCAPE = "escape"
BACKSPACE = "backspace"
TAB = "tab"
HOME = "home"
END = "end"
PAGE_UP = "page up"
PAGE_DOWN = "page down"
DELETE = "delete"

NAMED = {UP, DOWN, LEFT, RIGHT, ENTER, ESCAPE, BACKSPACE, TAB, HOME, END,
         PAGE_UP, PAGE_DOWN, DELETE}


class NoKeyboard(Exception):
    """There is no keyboard to read: input is coming from a file or a pipe."""


# ---------------------------------------------------------------------------
# A way for the tests to pretend
# ---------------------------------------------------------------------------

_pretend = None
_forced = None          # None = work it out; True = yes; False = no


def pretend_keys(keys):
    """
    Make read_key hand back these keys, one at a time.

    Only the tests use this.  It is what lets the whole menu interface be
    tested without a terminal, which is the only way it can be tested at all.
    """
    global _pretend
    _pretend = list(keys)


def stop_pretending():
    global _pretend
    _pretend = None


def pretending():
    return _pretend is not None


# ---------------------------------------------------------------------------

def set_keyboard(present):
    """
    Settle the question by hand: True, False, or None to work it out.

    Both answers are needed. tests/play.py says False because it feeds the
    app from a file by replacing input() while a real terminal is still
    attached, and without that the menus would sit waiting for an arrow key
    nobody is going to press. The tests say True because they drive the app
    with pretend keys while their own output is redirected, which makes the
    terminal look absent when it is not.
    """
    global _forced
    _forced = None if present is None else bool(present)


def force_no_keyboard(yes=True):
    """Older name for set_keyboard(False)."""
    set_keyboard(not yes)


def keyboard_is_there():
    """Is there a real keyboard, or is input coming from a file?"""
    if _forced is not None:
        return _forced
    if _pretend is not None:
        return True
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (ValueError, AttributeError):
        return False


def read_key():
    """
    Wait for one keypress and give back either a name from above or the
    character that was typed.
    """
    if _pretend is not None:
        if not _pretend:
            raise NoKeyboard("the pretend keys ran out")
        return _pretend.pop(0)

    if not keyboard_is_there():
        raise NoKeyboard("input is not coming from a keyboard")

    if sys.platform == "win32":
        return _read_windows()
    return _read_unix()


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

# Windows sends 0x00 or 0xE0 first to say "a special key follows", then a
# letter saying which one.
_WINDOWS_SPECIAL = {
    "H": UP, "P": DOWN, "K": LEFT, "M": RIGHT,
    "G": HOME, "O": END, "I": PAGE_UP, "Q": PAGE_DOWN, "S": DELETE,
}


def _read_windows():
    import msvcrt

    char = msvcrt.getwch()

    if char in ("\x00", "\xe0"):
        which = msvcrt.getwch()
        return _WINDOWS_SPECIAL.get(which, "")

    if char in ("\r", "\n"):
        return ENTER
    if char == "\x1b":
        return ESCAPE
    if char in ("\x08", "\x7f"):
        return BACKSPACE
    if char == "\t":
        return TAB
    if char == "\x03":
        raise KeyboardInterrupt
    return char


# ---------------------------------------------------------------------------
# Everything else
# ---------------------------------------------------------------------------

_UNIX_SPECIAL = {
    "A": UP, "B": DOWN, "C": RIGHT, "D": LEFT,
    "H": HOME, "F": END,
}
_UNIX_TILDE = {"1": HOME, "3": DELETE, "4": END, "5": PAGE_UP, "6": PAGE_DOWN}


def _read_unix():
    import termios
    import tty

    handle = sys.stdin.fileno()
    saved = termios.tcgetattr(handle)
    try:
        tty.setraw(handle)
        char = sys.stdin.read(1)

        if char == "\x1b":
            # Might be a bare Escape, or the start of an arrow key.
            following = sys.stdin.read(1)
            if following != "[":
                return ESCAPE
            third = sys.stdin.read(1)
            if third in _UNIX_SPECIAL:
                return _UNIX_SPECIAL[third]
            if third.isdigit():
                rest = ""
                while True:
                    more = sys.stdin.read(1)
                    if more == "~" or not more:
                        break
                    rest += more
                return _UNIX_TILDE.get(third, "")
            return ""

        if char in ("\r", "\n"):
            return ENTER
        if char in ("\x7f", "\x08"):
            return BACKSPACE
        if char == "\t":
            return TAB
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\x04":
            raise NoKeyboard("end of input")
        return char
    finally:
        termios.tcsetattr(handle, termios.TCSADRAIN, saved)
