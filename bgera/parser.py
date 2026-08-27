#!/usr/bin/env python
# coding: utf-8
"""
Turning what the student types into things the app should do.

Two ways of typing are understood, and they may be mixed freely:

    plain words     cube
                    width 30 length 20 height 10
                    cut rod from plate
                    filling 45 walls 3

    short codes     w30l20h10
                    d20h40n6
                    p45cubicn5
                    base:cube,w20,h30 ++ top:sphere,d20

The short codes are how BgeraPrint worked before, so nobody has to be
retaught and old worksheets still work.

Nothing here touches the model.  parse() returns a list of small
instructions, and app.py carries them out.  Keeping the two apart means a
command can be tested without a printer anywhere near.
"""

import difflib
import re

from . import shapes as shapes_mod
from . import printing as printing_mod
from .model import DIRECTIONS, TURN_AXES

NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")

# Words that mean the same thing, so a student is never wrong for guessing.
ALIASES = {
    "centre": "center", "middle": "center",
    "delete": "remove", "erase": "remove", "rub out": "remove",
    "back": "undo", "step back": "undo",
    "exit": "quit", "leave": "quit", "close": "quit", "bye": "quit",
    "clear": "new", "restart": "new", "start again": "new",
    "tell me": "describe", "read": "describe", "explain": "describe",
    "parts": "list", "pieces": "list",
    "slice": "prepare", "get ready": "prepare", "ready": "prepare",
    "go": "print", "start": "print",
    "how big": "size", "measure": "size",
    "load": "open", "keep": "save",
    "cancel": "stopprint",
    "grow": "bigger", "shrink": "smaller",
    "duplicate": "copy",
    "instructions": "help", "instruction": "help", "i": "help", "?": "help",
    "what can i make": "help",
}

# Simple commands that take nothing after them.
PLAIN = {
    "list": "list", "describe": "describe", "size": "size", "what": "what",
    "undo": "undo", "redo": "redo", "new": "new", "quit": "quit",
    "settings": "settings", "prepare": "prepare", "print": "print",
    "status": "status", "pause": "pause", "resume": "resume",
    "projects": "projects", "export": "export", "send": "send",
    "receive": "receive", "printers": "printers", "lessons": "lessons",
    "next": "next", "again": "again", "center": "center", "smooth": "smooth",
    "done": "done", "help": "help", "stop": "stop", "check": "check",
    "menu": "menus", "menus": "menus",
    "normal": "reset_settings",
}

BUILTIN_MODELS = ["lion", "turtle", "giraffe", "wolf", "camel", "rocket",
                  "pawn", "rook", "queen", "king", "bishop", "knight"]

# Everything a student might reasonably type, for the did-you-mean guess.
def known_words():
    words = set(PLAIN) | set(ALIASES) | set(BUILTIN_MODELS)
    words |= set(shapes_mod.SHAPE_WORDS)
    words |= set(shapes_mod.MEASURE_WORDS)
    words |= set(printing_mod.SETTING_WORDS)
    words |= set(DIRECTIONS) | set(TURN_AXES)
    words |= {"move", "turn", "put", "on", "beside", "cut", "from", "overlap",
              "round", "hollow", "mirror", "bigger", "smaller", "scale",
              "copy", "gap", "ring", "of", "across", "rename", "remove",
              "save", "open", "lesson", "text", "braille", "use", "add",
              "printer", "stop", "help", "prepare", "print", "check",
              "menu", "menus", "typing", "style", "numbers", "arrows"}
    return words


def guess(word):
    matches = difflib.get_close_matches(word.lower(), known_words(), n=1, cutoff=0.72)
    return matches[0] if matches else None


def _number(token):
    return NUMBER.match(token) is not None


def _as_number(token):
    value = float(token)
    return int(value) if value == int(value) else value


def parse(line, model=None):
    """
    Turn one typed line into a list of instructions.

    model is used only to tell a part name apart from a stray word, so that
    `base width 60` works.  It is never changed here.
    """
    raw = (line or "").strip()
    if not raw:
        return []

    lowered = raw.lower()

    # --- the old ways of typing, kept working -----------------------------
    legacy = _parse_legacy(raw, lowered)
    if legacy is not None:
        return legacy

    # --- words -----------------------------------------------------------
    # Split on spaces, not with shlex: shlex treats a backslash as an escape,
    # so C:\Users\Chakh\thing.stl arrives as C:UsersChakhthing.stl and the
    # file is never found. Quotes are stripped by hand instead.
    tokens = [token.strip('"').strip("'") for token in raw.split()]
    tokens = [token for token in tokens if token]
    if not tokens:
        return []

    return _parse_words(tokens, model)


# ---------------------------------------------------------------------------
# The old short codes
# ---------------------------------------------------------------------------

# "p" on its own, or p followed by a number: p45, p45cubic, p45cubicn5, pn5.
# It must never swallow an ordinary word that happens to start with p,
# such as "parts" or "pyramid".
LEGACY_PREPARE = re.compile(r"^p(?:(\d+)([a-z]+)?)?(?:n(\d+))?$")
LEGACY_MEASURE = re.compile(r"^(?:[wlhdntp]-?\d+(?:\.\d+)?)+$")
LEGACY_PAIR = re.compile(r"([wlhdntp])(-?\d+(?:\.\d+)?)")


def _parse_legacy(raw, lowered):
    # base:cube,w20,h30 ++ top:sphere,d20
    if ":" in raw and re.search(r"[a-zA-Z_]\w*\s*:", raw):
        return _parse_legacy_boolean(raw)

    # p45cubicn5
    match = LEGACY_PREPARE.fullmatch(lowered)
    if match and lowered != "p" and any(match.groups()):
        actions = []
        filling, pattern, copies = match.groups()
        if filling:
            actions.append({"do": "setting", "key": "filling", "value": filling})
        if pattern:
            actions.append({"do": "setting", "key": "pattern", "value": pattern})
        if copies:
            actions.append({"do": "setting", "key": "copies", "value": copies})
        actions.append({"do": "prepare"})
        return actions
    if lowered == "p":
        return [{"do": "prepare"}]

    # w20l30h10
    if LEGACY_MEASURE.fullmatch(lowered):
        values = {}
        for letter, number in LEGACY_PAIR.findall(lowered):
            name = shapes_mod.measurement_for(letter)
            if name:
                values[name] = _as_number(number)
        if values:
            return [{"do": "measure", "values": values, "target": None}]

    return None


def _parse_legacy_boolean(raw):
    """
    The old way of describing a whole model on one line:

        base:cube,w40,l40,h10 ++ top:sphere,d30
        body:cube,w40,h40 -- hole:cylinder,d10,h60

    Each piece becomes a shape, and ++ or -- becomes join or cut.
    """
    actions = [{"do": "new", "quiet": True}]
    pieces = re.split(r"\s*(\+\+|--)\s*", raw)
    names = []

    for index, piece in enumerate(pieces):
        if piece in ("++", "--"):
            continue
        bits = piece.split(":", 1)
        if len(bits) != 2:
            return None
        name = bits[0].strip()
        parts = [p.strip() for p in bits[1].split(",") if p.strip()]
        if not parts:
            return None
        shape = shapes_mod.shape_for(parts[0])
        if not shape:
            return None

        values = {}
        move = [0.0, 0.0, 0.0]
        turn = [0.0, 0.0, 0.0]
        for token in parts[1:]:
            pair = re.match(r"^(r?[a-z]+)(-?\d+(?:\.\d+)?)$", token.lower())
            if not pair:
                continue
            key, number = pair.group(1), _as_number(pair.group(2))
            if key in ("x", "y", "z"):
                move["xyz".index(key)] = number
            elif key in ("rx", "ry", "rz"):
                turn["xyz".index(key[1])] = number
            else:
                measure = shapes_mod.measurement_for(key)
                if measure:
                    values[measure] = number

        actions.append({"do": "shape", "shape": shape, "name": name,
                        "values": values, "quiet": True})
        if any(move):
            actions.append({"do": "move", "delta": move, "target": name})
        if any(turn):
            actions.append({"do": "turn", "turn": turn, "target": name})
        names.append(name)

    operators = [p for p in pieces if p in ("++", "--")]
    left = names[0] if names else None
    for index, operator in enumerate(operators):
        right = names[index + 1]
        op = "join" if operator == "++" else "cut"
        actions.append({"do": "combine", "op": op, "a": left, "b": right,
                        "name": f"shape{index + 1}"})
        left = f"shape{index + 1}"

    actions.append({"do": "describe"})
    return actions


# ---------------------------------------------------------------------------
# Plain words
# ---------------------------------------------------------------------------

def _parse_words(tokens, model):
    actions = []
    index = 0
    total = len(tokens)
    names = set(model.items) if model is not None else set()

    def peek(offset=0):
        position = index + offset
        return tokens[position].lower() if position < total else None

    def rest(start):
        return " ".join(tokens[start:])

    while index < total:
        word = tokens[index].lower()
        word = ALIASES.get(word, word)

        # --- two word phrases --------------------------------------------
        two = f"{word} {peek(1)}" if peek(1) else None
        if two and ALIASES.get(two):
            word = ALIASES[two]
            index += 1
        elif two == "stop print":
            actions.append({"do": "stopprint"})
            index += 2
            continue
        elif two == "add printer":
            actions.append({"do": "addprinter"})
            index += 2
            continue
        elif two == "remove printer":
            actions.append({"do": "removeprinter", "name": rest(index + 2)})
            index = total
            continue
        elif two and two.startswith("ring of"):
            index += 2
            count = _as_number(tokens[index]) if index < total and _number(tokens[index]) else 6
            index += 1 if index < total and _number(tokens[index]) else 0
            across = 60
            if peek() in ("across", "wide", "d"):
                index += 1
                if index < total and _number(tokens[index]):
                    across = _as_number(tokens[index])
                    index += 1
            actions.append({"do": "ring", "count": count, "across": across})
            continue

        # --- help ---------------------------------------------------------
        if word == "help":
            actions.append({"do": "help", "topic": rest(index + 1)})
            return actions

        # --- writing words ------------------------------------------------
        if word in ("text", "braille") or shapes_mod.shape_for(word) in ("text", "braille"):
            shape = shapes_mod.shape_for(word) or word
            words = rest(index + 1)
            actions.append({"do": "shape", "shape": shape, "words": words})
            return actions

        # --- shapes -------------------------------------------------------
        # A part the student named comes first: after "rename plate base",
        # typing "base width 60" must change that part, not make a new plate.
        if tokens[index] in names and index + 1 < total:
            shape = None
        else:
            shape = shapes_mod.shape_for(word)
        if shape:
            actions.append({"do": "shape", "shape": shape})
            index += 1
            continue

        # --- built in models ----------------------------------------------
        if word in BUILTIN_MODELS:
            actions.append({"do": "builtin", "name": word})
            index += 1
            continue

        # --- lessons ------------------------------------------------------
        if word == "lesson":
            number = 1
            if peek(1) and _number(peek(1)):
                number = int(float(peek(1)))
                index += 1
            actions.append({"do": "lesson", "n": number})
            index += 1
            continue

        # --- moving -------------------------------------------------------
        if word == "move":
            delta = [0.0, 0.0, 0.0]
            index += 1
            while index < total:
                direction = tokens[index].lower()
                if direction not in DIRECTIONS:
                    break
                index += 1
                amount = 10
                if index < total and _number(tokens[index]):
                    amount = _as_number(tokens[index])
                    index += 1
                dx, dy, dz = DIRECTIONS[direction]
                delta = [delta[0] + dx * amount, delta[1] + dy * amount,
                         delta[2] + dz * amount]
            actions.append({"do": "move", "delta": delta, "target": None})
            continue

        if word in DIRECTIONS and actions and actions[-1].get("do") == "move":
            continue

        if word == "turn":
            index += 1
            amount = 90
            if index < total and _number(tokens[index]):
                amount = _as_number(tokens[index])
                index += 1
            axis = "z"
            if index < total and tokens[index].lower() in TURN_AXES:
                axis = TURN_AXES[tokens[index].lower()]
                index += 1
            turn = [0.0, 0.0, 0.0]
            turn["xyz".index(axis)] = amount
            actions.append({"do": "turn", "turn": turn, "target": None})
            continue

        if word == "put":
            index += 1
            first = tokens[index] if index < total else None
            index += 1
            relation = tokens[index].lower() if index < total else "on"
            index += 1
            if relation in ("on", "onto", "above", "top"):
                # "put the ball on top of the cube" reads well, so allow it.
                while index < total and tokens[index].lower() in ("top", "of"):
                    index += 1
                second = tokens[index] if index < total else None
                actions.append({"do": "stack", "top": first, "bottom": second})
            else:
                second = tokens[index] if index < total else None
                actions.append({"do": "beside", "a": first, "b": second})
            index = total
            continue

        # --- combining ----------------------------------------------------
        if word in ("join", "add", "union", "combine", "stick"):
            index += 1
            first = second = None
            if index < total and tokens[index] in names:
                first = tokens[index]
                index += 1
                if index < total and tokens[index].lower() in ("and", "with", "to"):
                    index += 1
                if index < total and tokens[index] in names:
                    second = tokens[index]
                    index += 1
            actions.append({"do": "combine", "op": "join", "a": first, "b": second})
            continue

        if word in ("cut", "subtract", "hole", "remove from"):
            index += 1
            first = second = None
            if index < total and tokens[index] in names:
                first = tokens[index]
                index += 1
                if index < total and tokens[index].lower() in ("from", "out", "of"):
                    index += 1
                    if index < total and tokens[index].lower() == "of":
                        index += 1
                if index < total and tokens[index] in names:
                    second = tokens[index]
                    index += 1
            # "cut A from B" means B minus A.
            actions.append({"do": "combine", "op": "cut", "a": second, "b": first})
            continue

        if word in ("overlap", "intersect", "common", "share"):
            index += 1
            first = second = None
            if index < total and tokens[index] in names:
                first = tokens[index]
                index += 1
                if index < total and tokens[index].lower() in ("and", "with"):
                    index += 1
                if index < total and tokens[index] in names:
                    second = tokens[index]
                    index += 1
            actions.append({"do": "combine", "op": "overlap", "a": first, "b": second})
            continue

        # --- changing a part ----------------------------------------------
        if word in ("round", "rounded", "soften"):
            index += 1
            amount = 2
            if index < total and _number(tokens[index]):
                amount = _as_number(tokens[index])
                index += 1
            actions.append({"do": "round", "amount": amount})
            continue

        if word in ("hollow", "empty", "shell"):
            index += 1
            amount = 2
            if index < total and _number(tokens[index]):
                amount = _as_number(tokens[index])
                index += 1
            actions.append({"do": "hollow", "amount": amount})
            continue

        if word == "mirror":
            index += 1
            axis = "x"
            if index < total:
                choice = tokens[index].lower()
                axis = {"left": "x", "right": "x", "sideways": "x",
                        "forward": "y", "back": "y", "front": "y",
                        "up": "z", "down": "z"}.get(choice, "x")
                if choice in ("left", "right", "sideways", "forward", "back",
                              "front", "up", "down"):
                    index += 1
            actions.append({"do": "mirror", "axis": axis})
            continue

        if word in ("bigger", "smaller", "scale"):
            index += 1
            factor = 2
            if index < total and _number(tokens[index]):
                factor = _as_number(tokens[index])
                index += 1
            if word == "smaller":
                factor = 1.0 / factor if factor else 1
            actions.append({"do": "scale", "factor": factor})
            continue

        if word == "copy":
            index += 1
            count = 2
            if index < total and _number(tokens[index]):
                count = int(_as_number(tokens[index]))
                index += 1
            gap = 30
            direction = "right"
            while index < total:
                token = tokens[index].lower()
                if token in ("gap", "apart", "spacing", "every"):
                    index += 1
                    if index < total and _number(tokens[index]):
                        gap = _as_number(tokens[index])
                        index += 1
                elif token in DIRECTIONS:
                    direction = token
                    index += 1
                elif token in ("in", "a", "row"):
                    index += 1
                else:
                    break
            actions.append({"do": "copy", "count": count, "gap": gap,
                            "dir": direction})
            continue

        if word == "remove":
            index += 1
            name = tokens[index] if index < total else None
            actions.append({"do": "remove", "name": name})
            index += 1
            continue

        if word == "rename":
            old = tokens[index + 1] if index + 1 < total else None
            new = tokens[index + 2] if index + 2 < total else None
            actions.append({"do": "rename", "old": old, "new": new})
            index += 3
            continue

        # --- projects ------------------------------------------------------
        if word == "save":
            actions.append({"do": "save", "name": rest(index + 1)})
            return actions

        if word == "open":
            target = rest(index + 1)
            if any(mark in target for mark in ("\\", "/", ".stl", ".obj", ".3mf")):
                actions.append({"do": "openfile", "path": target})
            else:
                actions.append({"do": "open", "name": target})
            return actions

        # --- printers ------------------------------------------------------
        if word == "use":
            actions.append({"do": "useprinter", "name": rest(index + 1)})
            return actions

        # --- the menu style ---------------------------------------------------
        if word in ("style", "numbers"):
            index += 1
            value = tokens[index] if index < total else ""
            actions.append({"do": word, "value": value})
            index += 1
            continue

        # --- print settings -------------------------------------------------
        setting = printing_mod.setting_for(word)
        if setting is None and two:
            setting = printing_mod.setting_for(two)
            if setting:
                index += 1
        if setting:
            index += 1
            value = None
            if index < total:
                value = tokens[index]
                index += 1
            elif printing_mod.SETTINGS[setting]["kind"] == "switch":
                value = "on"
            if value is None:
                actions.append({"do": "explain_setting", "key": setting})
            else:
                actions.append({"do": "setting", "key": setting, "value": value})
            continue

        # --- measurements ---------------------------------------------------
        measure = shapes_mod.measurement_for(word)
        if measure:
            index += 1
            if index < total and _number(tokens[index]):
                value = _as_number(tokens[index])
                index += 1
                _merge_measure(actions, measure, value)
            else:
                actions.append({"do": "unknown", "word": word,
                                "reason": "need_number"})
            continue

        # --- a part the student named -----------------------------------
        if tokens[index] in names:
            target = tokens[index]
            index += 1
            following = _parse_words(tokens[index:], model) if index < total else []
            for action in following:
                if action["do"] in ("measure", "move", "turn", "round", "hollow",
                                    "scale", "mirror", "copy", "smooth"):
                    action["target"] = target
            if following:
                actions.extend(following)
            else:
                actions.append({"do": "focus", "name": target})
            return actions

        # --- simple commands ------------------------------------------------
        if word in PLAIN:
            actions.append({"do": PLAIN[word]})
            index += 1
            continue

        # --- nothing matched -------------------------------------------------
        actions.append({"do": "unknown", "word": tokens[index],
                        "guess": guess(tokens[index])})
        index += 1

    return actions


def _merge_measure(actions, measure, value):
    """Several measurements typed on one line become one instruction."""
    if actions and actions[-1]["do"] == "measure" and actions[-1].get("target") is None:
        actions[-1]["values"][measure] = value
    else:
        actions.append({"do": "measure", "values": {measure: value},
                        "target": None})
