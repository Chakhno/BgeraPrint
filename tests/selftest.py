#!/usr/bin/env python
# coding: utf-8
"""
Test the whole app, end to end, with the real programs it ships with.

The other two test files check the parts.  This one checks the chain:

    typed command -> model -> OpenSCAD -> STL -> PrusaSlicer -> G-code

using the real openscad.exe, the real prusa-slicer-console.exe and the real
printer profile out of assets.  No printer is needed.  Nothing is sent
anywhere.  Everything it makes is left in a folder you can look at.

    python -m tests.selftest                  the usual run
    python -m tests.selftest --printer xplus4 a different printer profile
    python -m tests.selftest --all-printers   every profile in assets
    python -m tests.selftest --quick          build the shapes, skip slicing
    python -m tests.selftest --ping 10.1.202.192 7125   also try the printer
    python -m tests.selftest --keep C:\\temp\\bgeracheck   put the output here

It ends with a count and an exit code, so it can go in a build script.

Run this after changing a shape, before building an exe, and on any new
classroom machine.
"""

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bgera import parser as parser_mod
from bgera import printing as printing_mod
from bgera.model import Model
try:
    from tests.helpers import (APP_DIR, find_openscad, find_slicer,
                               with_bin_on_path)
except ImportError:          # run from inside the tests folder
    from helpers import (APP_DIR, find_openscad, find_slicer,
                         with_bin_on_path)

PROFILES = APP_DIR / "assets" / "printer_configs"
BUILTIN_MODELS = APP_DIR / "assets" / "models"


# ---------------------------------------------------------------------------
# What gets built
# ---------------------------------------------------------------------------
# Each job is (name, the lines a student would type).  Typing them, rather
# than building the model in code, means the command language is tested at
# the same time as the geometry.

JOBS = [
    ("cube", ["cube", "width 30 length 20 height 10"]),
    ("ball", ["ball", "across 30"]),
    ("rod", ["rod", "across 20 height 40"]),
    ("cone", ["cone", "across 30 height 40"]),
    ("pyramid", ["pyramid", "across 30 height 40 sides 4"]),
    ("pyramid-three-sided", ["pyramid", "across 30 height 40 sides 3"]),
    ("prism", ["prism", "across 20 height 40 sides 6"]),
    ("tube", ["tube", "across 30 height 40 thick 3"]),
    ("ring", ["ring", "across 20 height 4 thick 2"]),
    ("donut", ["donut", "across 40 thick 8"]),
    ("wedge", ["wedge", "width 20 length 40 height 15"]),
    ("star", ["star", "across 40 height 5 points 5"]),
    ("plate", ["plate", "width 80 length 30 height 3"]),

    ("text", ["text Nino", "height 12 thick 4"]),
    ("braille", ["braille nino"]),
    ("braille-with-numbers", ["braille room 42"]),

    ("rounded-cube", ["cube", "width 40 length 40 height 20", "round 4"]),
    ("hollow-cube", ["cube", "width 30 length 30 height 30", "hollow 2"]),
    ("mirrored-wedge", ["wedge", "width 20 length 40 height 15", "mirror left"]),
    ("scaled", ["cube", "width 20 length 20 height 20", "bigger 2"]),
    ("moved-and-turned", ["cube", "width 20 length 20 height 20",
                          "move right 10 up 5", "turn 45 over"]),
    ("row-of-copies", ["cube", "width 10 length 10 height 10",
                       "copy 5 gap 20 right"]),
    ("circle-of-copies", ["rod", "across 5 height 20", "ring of 8 across 60"]),

    ("join", ["cube", "width 30 length 30 height 10",
              "ball", "across 20", "put ball on cube", "join"]),
    ("cut", ["plate", "width 40 length 40 height 5",
             "rod", "across 8 height 20", "cut rod from plate"]),
    ("overlap", ["cube", "width 30 length 30 height 30",
                 "ball", "across 38", "overlap"]),
    ("group-of-groups", ["cube", "width 40 length 40 height 10",
                         "rod", "across 8 height 30", "cut rod from cube",
                         "ball", "across 15", "put ball on piece", "join"]),

    ("name-badge", ["plate", "width 90 length 30 height 3",
                    "braille luka", "put braille on plate", "join"]),
    ("keyring", ["ring", "across 25 height 4 thick 3",
                 "text L", "height 14 thick 4", "move right 20", "join"]),

    # The old way of typing, which old worksheets still use.
    ("old-style-join", ["base:cube,w40,l40,h10 ++ top:sphere,d30,z10"]),
    ("old-style-cut", ["body:cube,w40,l40,h40 -- hole:cylinder,d10,h60"]),
    ("old-style-sizes", ["cube", "w20l30h10"]),
]

# Print settings worth putting through the real slicer, because these are the
# ones that can make it refuse a model rather than just print it differently.
SETTING_RUNS = [
    ("normal settings", []),
    ("solid", ["filling 100"]),
    ("empty", ["filling 0"]),
    ("best quality", ["quality best"]),
    ("draft quality", ["quality draft"]),
    ("thick walls", ["walls 5", "top 6", "bottom 6"]),
    ("supports everywhere", ["supports on"]),
    ("supports from the bed", ["supports bed"]),
    ("brim and raft", ["brim 5", "raft 3"]),
    ("slow", ["speed slow"]),
    ("fast", ["speed fast"]),
    ("petg", ["material petg"]),
    ("vase mode", ["vase on"]),
    ("four copies", ["copies 4"]),
    ("twice the size", ["bigger 2"]),
]


# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.passed = 0
        self.failed = []
        self.started = time.time()

    def ok(self, name, detail=""):
        self.passed += 1
        print(f"  ok    {name:<26} {detail}")

    def bad(self, name, why):
        self.failed.append((name, why))
        print(f"  FAIL  {name:<26} {why}")

    def finish(self):
        seconds = time.time() - self.started
        print()
        print("=" * 66)
        if self.failed:
            print(f"{len(self.failed)} of {self.passed + len(self.failed)} "
                  f"checks failed, in {seconds:.0f} seconds:")
            for name, why in self.failed:
                print(f"  {name}: {why}")
        else:
            print(f"All {self.passed} checks passed, in {seconds:.0f} seconds.")
        print("=" * 66)
        return 1 if self.failed else 0


def build(lines):
    """Type some lines and give back the model they make."""
    model = Model()
    for line in lines:
        for action in parser_mod.parse(line, model):
            apply_action(model, action)
    return model


def apply_action(model, action):
    """
    Enough of the app to build a model, without the talking.

    This deliberately does not import app.py: if a change to app.py breaks
    the chain, the tests in test_session.py catch it, and this file stays
    focused on whether the real programs can make the shapes.
    """
    what = action["do"]

    if what == "shape":
        params = dict(action.get("values") or {})
        if action.get("words"):
            params["words"] = action["words"]
        model.add_part(action["shape"], params, name=action.get("name"))

    elif what == "measure":
        item = model.find(action.get("target")) or model.current()
        if item:
            item.params.update(action["values"])

    elif what == "move":
        item = model.find(action.get("target")) or model.current()
        if item:
            item.pos = [item.pos[i] + action["delta"][i] for i in range(3)]

    elif what == "turn":
        item = model.find(action.get("target")) or model.current()
        if item:
            item.turn = [item.turn[i] + action["turn"][i] for i in range(3)]

    elif what == "stack":
        top = model.find(action.get("top"))
        bottom = model.find(action.get("bottom"))
        if top and bottom:
            top.pos = [bottom.pos[0], bottom.pos[1],
                       bottom.pos[2] + model._item_size(bottom)[2] / 2.0
                       + model._item_size(top)[2] / 2.0]

    elif what == "combine":
        tops = model.top_level()
        first = model.find(action.get("a")) or (model.items[tops[-2]]
                                                if len(tops) > 1 else None)
        second = model.find(action.get("b")) or (model.items[tops[-1]]
                                                 if tops else None)
        if first and second and first is not second:
            model.add_group(action["op"], [first.name, second.name],
                            name=action.get("name"))

    elif what in ("round", "hollow"):
        item = model.current()
        if item:
            setattr(item, "round_by" if what == "round" else "hollow",
                    action["amount"])

    elif what == "smooth":
        item = model.current()
        if item:
            item.smooth = True

    elif what == "mirror":
        item = model.current()
        if item:
            item.mirror = action["axis"]

    elif what == "scale":
        item = model.current()
        if item:
            item.scale = [s * action["factor"] for s in item.scale]

    elif what == "copy":
        item = model.current()
        if item:
            item.repeat = {"count": action["count"], "gap": action["gap"],
                           "dir": action["dir"]}

    elif what == "ring":
        item = model.current()
        if item:
            item.circle_repeat = {"count": action["count"],
                                  "across": action["across"]}

    elif what == "new":
        model.clear()


# ---------------------------------------------------------------------------

def check_the_programs(report, openscad, slicer):
    print("Looking for the programs the app needs")
    if openscad and Path(openscad).exists():
        report.ok("OpenSCAD", str(openscad))
    else:
        report.bad("OpenSCAD", "not found in assets/bin or on the PATH")

    if slicer and Path(slicer).exists():
        report.ok("PrusaSlicer", str(slicer))
    else:
        report.bad("PrusaSlicer", "not found in assets/bin or on the PATH")

    profiles = sorted(PROFILES.glob("*.ini")) if PROFILES.exists() else []
    if profiles:
        report.ok("printer profiles",
                  ", ".join(path.stem for path in profiles))
    else:
        report.bad("printer profiles", f"none found in {PROFILES}")

    models = sorted(BUILTIN_MODELS.glob("*.stl")) if BUILTIN_MODELS.exists() else []
    if len(models) >= 12:
        report.ok("ready made models", f"{len(models)} files")
    else:
        report.bad("ready made models",
                   f"expected 12, found {len(models)} in {BUILTIN_MODELS}")
    print()
    return profiles


def check_the_shapes(report, openscad, out_dir, jobs):
    print(f"Building {len(jobs)} models with the real OpenSCAD")
    made = {}
    for name, lines in jobs:
        started = time.time()
        try:
            model = build(lines)
        except Exception as problem:
            report.bad(name, f"the commands failed: {problem!r}")
            continue

        if model.is_empty():
            report.bad(name, "the commands made nothing")
            continue

        scad = out_dir / f"{name}.scad"
        stl = out_dir / f"{name}.stl"
        ok, problem = printing_mod.run_openscad(openscad, model.scad(),
                                                scad, stl)
        seconds = time.time() - started

        if not ok:
            report.bad(name, problem)
            continue
        size = stl.stat().st_size
        if size < 200:
            report.bad(name, "the shape file came out empty")
            continue

        made[name] = stl
        how_big = f"{size / 1024:.0f} KB" if size >= 1024 else f"{size} bytes"
        report.ok(name, f"{how_big}, {seconds:.1f}s")
    print()
    return made


def check_the_slicing(report, slicer, profile, out_dir, stl, runs):
    print(f"Slicing with the real PrusaSlicer and the {profile.stem} profile")
    settings = printing_mod.PrintSettings()

    for name, lines in runs:
        settings.reset()
        broken = False
        for line in lines:
            word, _, value = line.partition(" ")
            key = printing_mod.setting_for(word)
            if key is None:
                report.bad(name, f"'{word}' is not a setting")
                broken = True
                break
            ok, problem, _ = settings.set(key, value)
            if not ok:
                report.bad(name, f"'{line}' was refused: {problem}")
                broken = True
                break
        if broken:
            continue

        started = time.time()
        try:
            working = settings.write_profile(profile, out_dir / "work")
        except OSError as problem:
            report.bad(name, f"could not write the profile: {problem}")
            continue

        gcode = out_dir / f"slice-{name.replace(' ', '-')}.gcode"
        ok, problem = printing_mod.slice_model(
            slicer, [stl], working, gcode,
            copies=settings.values["copies"], scale=settings.values["bigger"])
        seconds = time.time() - started

        if not ok:
            report.bad(name, problem)
            continue

        found = printing_mod.gcode_report(gcode)
        if not found["time"]:
            report.bad(name, "the printing file has no time in it")
            continue
        if found["grams"] is None:
            report.bad(name, "the printing file has no plastic amount in it")
            continue

        report.ok(name, f"{found['time']}, {found['grams']} g, {seconds:.1f}s")
    print()


def check_the_profile_is_untouched(report, profile, before):
    if profile.read_text(encoding="utf-8", errors="ignore") == before:
        report.ok("profile left alone", f"{profile.name} is unchanged")
    else:
        report.bad("profile left alone",
                   f"{profile.name} was written to. It must never be.")
    print()


def check_a_ready_made_model(report, slicer, out_dir):
    lion = BUILTIN_MODELS / "Lion.stl"
    if not lion.exists():
        return
    print("Checking a ready made model")
    size = printing_mod.stl_size(slicer, lion)
    if size and len(size) == 3 and all(value > 0 for value in size):
        report.ok("lion measured", f"{size[0]} by {size[1]} by {size[2]} mm")
    else:
        report.bad("lion measured", f"the slicer gave back {size}")
    print()


def check_the_printer(report, ip, port):
    print(f"Trying the printer at {ip}:{port}")
    printer = printing_mod.Printer("test", "test", ip, port)
    state = printer.status()
    if state is None:
        report.bad("printer reachable",
                   "no answer. Check it is on and on the same network.")
    else:
        report.ok("printer reachable", f"it is {state['state']}")
    print()


# ---------------------------------------------------------------------------

def main():
    ask = argparse.ArgumentParser(
        description="Test BgeraPrint end to end with its real programs.")
    ask.add_argument("--printer", default=None,
                     help="which printer profile to slice with")
    ask.add_argument("--all-printers", action="store_true",
                     help="slice one model with every profile in assets")
    ask.add_argument("--quick", action="store_true",
                     help="build the shapes but do not slice them")
    ask.add_argument("--ping", nargs=2, metavar=("IP", "PORT"),
                     help="also check that a printer answers")
    ask.add_argument("--keep", default=None,
                     help="folder to leave the results in")
    args = ask.parse_args()

    with_bin_on_path()
    openscad = find_openscad()
    slicer = find_slicer()

    out_dir = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(
        prefix="bgeraprint-selftest-"))
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 66)
    print("BgeraPrint self test")
    print(f"App folder:  {APP_DIR}")
    print(f"Results in:  {out_dir}")
    print("=" * 66)
    print()

    report = Report()
    profiles = check_the_programs(report, openscad, slicer)

    if not openscad or not Path(openscad).exists():
        print("Without OpenSCAD nothing else can be checked.")
        return report.finish()

    made = check_the_shapes(report, openscad, out_dir, JOBS)

    if not args.quick and slicer and Path(slicer).exists() and profiles:
        wanted = [p for p in profiles
                  if args.printer is None or p.stem == args.printer]
        if not wanted:
            print(f"There is no profile called {args.printer}. "
                  f"Try one of: {', '.join(p.stem for p in profiles)}")
            return report.finish()

        profile = wanted[0]
        before = profile.read_text(encoding="utf-8", errors="ignore")
        test_stl = made.get("name-badge") or made.get("cube")

        if test_stl:
            check_the_slicing(report, slicer, profile, out_dir, test_stl,
                              SETTING_RUNS)
            check_the_profile_is_untouched(report, profile, before)

            if args.all_printers:
                print("Slicing once with every printer profile")
                for other in profiles:
                    ok, problem = printing_mod.slice_model(
                        slicer, [test_stl], other,
                        out_dir / f"profile-{other.stem}.gcode")
                    if ok:
                        report.ok(f"profile {other.stem}", "sliced")
                    else:
                        report.bad(f"profile {other.stem}", problem)
                print()

        check_a_ready_made_model(report, slicer, out_dir)

    elif not args.quick:
        print("PrusaSlicer was not found, so slicing was not checked.")
        print()

    if args.ping:
        check_the_printer(report, args.ping[0], args.ping[1])

    result = report.finish()
    if args.keep:
        print(f"\nEverything it made is in {out_dir}")
        print("Open the .stl files in any viewer, or feel the printed ones.")
    else:
        shutil.rmtree(out_dir, ignore_errors=True)
        print("\nRun with --keep FOLDER to look at the shape files it made.")
    return result


if __name__ == "__main__":
    sys.exit(main())
