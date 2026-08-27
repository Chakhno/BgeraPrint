# BgeraPrint

3D modelling and 3D printing for students who cannot see the screen.

Everything is typed or chosen with the arrow keys, and everything is spoken
back. A student describes a shape in plain words — `cube`, `width 30` — or
picks it from a menu, and BgeraPrint builds it with OpenSCAD, prepares it
with PrusaSlicer and sends it to the printer. It never opens a window, never
needs a mouse, and says out loud what it has just done after every single
command.

It writes real braille, at the size braille books use, so a student can print
their own name and read it.

---

## Two ways of working

BgeraPrint asks which you want when it starts.

**Menus** — arrow keys and Enter, nothing to remember or spell.

```
What would you like to do?
  1. Make a shape, cube, ball, braille and the rest
  2. Change the size of a part
  ...
> 1 of 9. Make a shape, cube, ball, braille and the rest
```

Sizes are set without leaving the menu: Up and Down walk between width,
length and height, Left and Right change whichever one you are on. One press
is a tenth of a millimetre; hold the key and it speeds up to half a
millimetre, then one, five, ten — so 20 mm to 200 mm takes a second and a
half without giving up fine control.

**Typing** — plain words.

```
cube
width 30 length 20 height 10
round 3
prepare
print
```

Swap between them at any time. Both produce exactly the same instructions
underneath, so neither can fall behind the other.

## A worked example

A braille name badge, from nothing to a printing file:

```
plate
width 90 length 30 height 3
braille luka
put braille on plate
join
walls 3
prepare
```

## What it can make

Cube, ball, rod, cone, plate, wedge, pyramid, prism, star, tube, ring,
donut, raised text and braille — plus twelve ready-made models (animals and
a full set of chess pieces) and any STL file from the computer.

Parts can be joined, cut out of each other, overlapped, rounded, hollowed,
mirrored, scaled, and repeated in rows or circles. There is a hundred-step
undo.

Sixteen print settings are exposed in plain words: `filling 45`,
`quality fine`, `walls 3`, `supports on`, `vase on`, `material petg`.

## Built for listening

The design decisions that matter are all about what a screen reader will
actually say:

- Every command answers with **one short sentence**. Nothing silent, nothing
  that needs a second look.
- Menus print the choice you have landed on as **new text** on every
  keypress. NVDA and JAWS announce new terminal text reliably and *redrawn*
  text only sometimes, so the prettier in-place redraw is available
  (`style visual`) but is not the default.
- A held arrow key changes a number about thirty times a second. Announcing
  every one would bury a screen reader, so it speaks about three times a
  second — but the value it **settled on** is always spoken. Hearing "118"
  and walking away with 168 would be worse than saying nothing.
- Help is thirteen short topics, not one long block. `help`, `help shapes`,
  `help print`.
- Braille follows the Marburg Medium standard: 1.5 mm dots, 0.6 mm high,
  2.5 mm apart, 6 mm between cells.

## Getting it running

Needs Python 3.9 or newer.

```
git clone <this repository>
cd BgeraPrint
python -m pip install -r requirements.txt
python BgeraPrint.py
```

### OpenSCAD and PrusaSlicer

The repository does not carry them: they are 242 MB of somebody else's
compiled programs. Put them in `assets/bin/` and the app finds them there,
or install them normally and it will find them on the PATH.

- OpenSCAD — https://openscad.org/downloads.html
- PrusaSlicer — https://www.prusa3d.com/page/prusaslicer_424/
  (the console build, `prusa-slicer-console.exe` on Windows)

Once they are in place, `check` inside the app tells you whether everything
is working, and `python -m tests.selftest` puts the whole chain through its
paces.

### The printer

Aimed at QIDI printers speaking Moonraker. Printer profiles live in
`assets/printer_configs/`; adding another is one `.ini` file.

## How it is put together

```
BgeraPrint.py        starts the app
bgera/texts.py       every word the student hears (English and Georgian)
bgera/shapes.py      the shape catalogue and its OpenSCAD
bgera/braille.py     braille cells and printable dots
bgera/model.py       the model being built: parts, groups, undo, saving
bgera/parser.py      typed words -> instructions
bgera/keys.py        one keypress at a time, on Windows and on Unix
bgera/menu.py        arrow key menus, the number picker, the acceleration
bgera/guided.py      the menu interface -> the same instructions
bgera/printing.py    print settings, slicing, and the printer
bgera/transfer.py    sending files between computers in a classroom
bgera/help.py        help topics and lessons
bgera/app.py         runs whichever interface is chosen, and does the work
tests/               237 tests, a self test, and session files to replay
```

Both interfaces build the same small instructions — `{"do": "measure",
"values": {"width": 30}}` — and hand them to the same `app.do()`. Neither
knows anything about models or printers. That is why a fix in one is a fix
in both.

## Testing

```
python -m unittest discover -s tests -p "test_*.py"   237 tests, ~20 seconds
python -m tests.selftest                              the whole chain, for real
python -m tests.play tests/session_badge.txt --fresh  hear a whole session
```

`tests/selftest.py` types 32 models the way a student would, builds every one
with the real OpenSCAD, then slices one of them under fifteen different
settings with the real PrusaSlicer, and checks the shipped printer profile
came out unchanged. `--keep FOLDER` leaves the STLs where you can open them.

**What is verified, and what is not.** The modelling half is tested hard:
OpenSCAD really runs and real STL files come out, and the braille dot mesh is
checked watertight by edge count and by measured volume. The slicing half is
covered by a stand-in that stands in for PrusaSlicer, which exercises the
command building, profile patching and G-code parsing but does no real
slicing. Run `python -m tests.selftest` on a machine with the real programs
to close that gap.

## Languages

English and Georgian. `bgera/texts.py` holds both; anything missing from the
Georgian falls back to English, so the app works throughout a translation.

```
python -m bgera.texts     lists what still needs Georgian
```

## Documents

- `COMMANDS.md` — every command, for students, teachers and worksheets
- `START-HERE.md` — running it from source in VS Code
- `NOTES-FOR-DEVELOPER.md` — how it is built, and how to add to it
- `BUILD-AND-RELEASE.md` — making the Windows program and a release
- `NOTICE_THIRD_PARTY.md` — the licences of everything BgeraPrint carries

## What it carries with it

BgeraPrint runs OpenSCAD and PrusaSlicer as separate programs — it hands
them a file and reads the file that comes back. OpenSCAD is under the GPL
version 2, PrusaSlicer under the AGPL version 3, and the Windows release
carries both, so it ships with `NOTICE_THIRD_PARTY.md` giving their terms
and where to get their source.
