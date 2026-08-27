#!/usr/bin/env python
# coding: utf-8
"""
Play a file of commands through the app, as if somebody had typed them.

    python -m tests.play tests/session_badge.txt

Each line of the file is typed into a real BgeraPrint session, and both the
command and the answer are printed, so the result reads like a transcript of
a lesson.  Lines starting with # are ignored, and so are blank lines.

Why this exists rather than just redirecting a file into the app: PowerShell,
which is what VS Code opens on Windows, has no < redirection.  This works in
any shell, and it can be run under the debugger with breakpoints set, which
redirection cannot.

Use it to hear what a student hears after changing any wording, and to
reproduce a bug the same way every time.
"""

import builtins
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


MENU_MARKER = "#!menus"


def drives_menus(path):
    """
    Does this session file answer menus rather than type commands?

    Marked with #!menus on the first line. It matters because the two kinds
    of file cannot be checked the same way: a typed-command file can be
    parsed line by line, a menu file only makes sense played through.
    """
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped == MENU_MARKER
    return False


def lines_from(path):
    text = Path(path).read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            out.append(stripped)
    return out


def use_a_throwaway_setup():
    """
    Point the app at a config and a projects folder it can scribble on.

    Without this, playing a file on a computer that has never run the app
    goes wrong in a way that is baffling the first time: the app asks which
    language you want, and the whole session file is swallowed answering
    that one question. It is also what you want when you are only replaying
    a file to hear the wording, since it keeps the playback away from your
    real saved projects.
    """
    from bgera import app as app_mod

    folder = Path(tempfile.mkdtemp(prefix="bgeraprint-play-"))
    config = folder / "config.json"
    config.write_text(json.dumps({
        "lan": 1,
        "printers": [{"name": "play", "model": _a_printer_model(),
                      "ip": "0.0.0.0", "port": "7125"}],
        "current_printer": "play",
        # Session files are lines of typed commands, so play them that way
        # unless the file itself asks for the menus. Numbers are typed too:
        # there is no keyboard to hold an arrow key down on.
        "interface": "typing",
        "number_mode": "typed",
    }), encoding="utf-8")

    app_mod.CONFIG_PATH = config
    app_mod.PROJECTS_DIR = folder / "projects"
    app_mod.WORK_DIR = folder / "work"
    return folder


def _a_printer_model():
    """Any printer profile that is actually here, so slicing can be tried."""
    from bgera import app as app_mod
    found = sorted(app_mod.PRINTER_CONFIGS.glob("*.ini")) \
        if app_mod.PRINTER_CONFIGS.exists() else []
    return found[0].stem if found else "xmax3"


def play(path, echo=True, fresh=False):
    """Type every line of the file into a real session."""
    from bgera import app as app_mod

    if fresh or not app_mod.CONFIG_PATH.exists():
        folder = use_a_throwaway_setup()
        print(f"[using a throwaway setup in {folder}, "
              f"so your own saved work is not touched]\n")

    # The terminal is still attached, but nobody is at it: every answer is
    # coming from the file. Without this the menus would wait forever for an
    # arrow key.
    from bgera import keys as keys_mod
    keys_mod.force_no_keyboard(True)

    waiting = lines_from(path)
    real_input = builtins.input

    def typed(prompt=""):
        if not waiting:
            raise EOFError
        line = waiting.pop(0)
        if echo:
            print(f"{prompt}{line}")
        return line

    builtins.input = typed
    try:
        from bgera.app import main
        main()
    except EOFError:
        print("\n[the file ran out of commands]")
    finally:
        builtins.input = real_input
        keys_mod.force_no_keyboard(False)


def main():
    arguments = [a for a in sys.argv[1:] if not a.startswith("-")]
    fresh = "--fresh" in sys.argv

    if not arguments:
        here = Path(__file__).resolve().parent
        print("Give me a file of commands to play. For example:")
        print("    python -m tests.play tests/session_badge.txt")
        print()
        print("Add --fresh to play it against a throwaway setup, leaving")
        print("your own config and saved projects alone.")
        print()
        found = sorted(here.glob("session_*.txt"))
        if found:
            print("Files here you could play:")
            for path in found:
                print(f"    tests/{path.name}")
        return 2

    path = Path(arguments[0])
    if not path.exists():
        # Allow it to be given relative to the app folder as well.
        other = Path(__file__).resolve().parent.parent / arguments[0]
        if other.exists():
            path = other
        else:
            print(f"There is no file at {arguments[0]}.")
            return 2

    print(f"--- playing {path.name} ---\n")
    play(path, fresh=fresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
