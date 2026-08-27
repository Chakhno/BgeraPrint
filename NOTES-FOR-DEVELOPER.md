# BgeraPrint 2.0 — notes for whoever develops it next

## What changed and why

Version 1.3.1 was one 919-line file that ran top to bottom: pick a shape,
give it sizes, slice, print, exit. It worked, but it could only be extended
by adding another branch to a growing `while True`, and it could not be
tested at all without a printer on the desk.

Version 2.0 keeps every command 1.3.1 understood and adds the rest of
OpenSCAD and PrusaSlicer behind plain words. The structure is now:

```
BgeraPrint.py        starts the app, nothing else
bgera/texts.py       every word the student hears (English + Georgian)
bgera/shapes.py      the shape catalogue and its OpenSCAD
bgera/braille.py     braille cells and printable dots
bgera/model.py       the model being built: parts, groups, undo, saving
bgera/parser.py      typed words -> a list of instructions
bgera/keys.py        one keypress at a time, on Windows and on Unix
bgera/menu.py        arrow key menus and the number picker
bgera/guided.py      the menu interface -> the same instructions
bgera/printing.py    print settings, slicing, and the printer
bgera/transfer.py    sending files between computers
bgera/help.py        help topics and lessons
bgera/app.py         runs whichever interface is chosen, and does the work
tests/               203 tests, a self test, and session files to replay
```

The split that matters most is **the instruction in the middle**. Both
interfaces produce the same little dictionaries -- `{"do": "measure",
"values": {"width": 30}}` -- and both hand them to the same `app.do()`.
`parser.py` makes them out of typed words; `guided.py` makes them out of
menu choices. Neither knows anything about models or printers.

That is why the two interfaces cannot drift apart: a bug fixed in `do()` is
fixed in both, a new shape appears in both, and the whole command language
can be tested in a fraction of a second with no printer, no OpenSCAD and no
PrusaSlicer anywhere near.

## The menus, and why they are drawn the way they are

The obvious way to write an arrow key menu is to draw the list once and
redraw it in place with the current line highlighted. It looks good. It is
also close to useless with a screen reader: NVDA and JAWS announce text that
is NEW in a terminal, and text that is REDRAWN is announced inconsistently or
not at all. A student could press Down five times and hear silence.

So `menu.py` draws itself two ways, from one engine:

- **speak** (the default) reads the list out once, then prints the choice you
  have landed on as a brand new line at every keypress. Always announced,
  because it is always new text.
- **visual** does the in-place redraw with colour. For a magnifier, or for
  showing the app to a sighted audience.

`style speak` and `style visual` switch, and the choice is remembered.

`test_every_move_says_something_new` in `tests/test_menus.py` guards this. If
it ever fails, somebody has made the menus silent for the people the app was
written for.

Two smaller things in the same spirit: a key that does not move must not
reprint the line (repetition is noise to somebody listening), and the number
picker says "60 millimetres is the largest it can be" once rather than
repeating the same number at every press.

## Bugs found in 1.3.1 while doing this

These are all fixed, but they are worth knowing about because two of them
would have bitten a class.

1. **Any word starting with `p` was treated as a print command.** The pattern
   `^p(\d+)?([a-z]+)?(?:n(\d+))?$` matches `parts`, `pole`, `pyramid` — the
   optional groups meant `p` plus anything lowercase matched. A student
   typing `pyramid` silently started slicing. The pattern now needs a digit
   after the `p`.

2. **A part named `cube` produced OpenSCAD that called itself forever.**
   `module cube(){ cube(...); }` is infinite recursion, and OpenSCAD gives up
   with an empty model. Since `cube` is the first thing anybody types, this
   would have hit on day one. Every module name now gets a `part_` prefix.

3. **The shipped printer profile was edited in place.** `change_print_config`
   wrote `fill_density` straight back into `assets/printer_configs/*.ini`.
   In the frozen exe that file lives in a temporary folder so it survived by
   luck, but running from source it permanently changed the file in the
   repository. Settings are now applied to a copy in `work/`.

4. **`print_settings` crashed on anything unexpected.** `print_matches[0]`
   raises IndexError when the pattern does not match; `int(input())` at start
   up raises ValueError on any non-number; `x, y, z = sizes` raises ValueError
   when the slicer prints something else. All of these now fail politely.

5. **`receive` blocked the student.** Receiving files and waiting for a print
   command were the same loop, so nothing else could be done while waiting.
   Receiving is now its own job that ends with `done`.

6. **Filenames arriving over the network were not checked.** A sender could
   have chosen `..\..\something.exe`. Names are now stripped to their base and
   filtered.

## Adding things

**A new shape** — one entry in `SHAPES` in `bgera/shapes.py`:

```python
"heart": {
    "words": ["heart", "love"],
    "needs": ["across", "height"],
    "defaults": {"across": 30, "height": 8},
    "scad": _heart,          # a function taking the measurements, returning OpenSCAD
    "hint": "shape_hint_heart",
},
```

Then add `shape_hint_heart` to `EN` in `texts.py`, and a size rule to
`Part.rough_size` in `model.py` if the shape is not a box or a cylinder.
Nothing else changes: the parser, help and describing all read the catalogue.

**A new print setting** — one entry in `SETTINGS` in `bgera/printing.py`. The
`keys` function returns the PrusaSlicer options to write. The parser picks it
up automatically.

**A new lesson** — one entry in `LESSONS` in `bgera/help.py`. Each step is
`(what to say, the command to try)`, or `(what to say, None)` for a step that
just needs `next`. A test plays every lesson through and fails if any command
in it is not understood, so a lesson can never drift out of date.

**A new message** — add the key to `EN` in `texts.py` and call
`self.tell("key", name=...)`. A test fails if any message used in the code is
missing from `EN`.

## Georgian

`bgera/texts.py` holds `EN` and `KA`. The Georgian from 1.3.1 has been
carried over. Everything new is still English, and any key missing from `KA`
falls back to English, so the app works throughout the translation.

To see what is left:

```
python -m bgera.texts
```

It prints the untranslated keys already formatted, ready to paste into `KA`.

A translation with a wrong placeholder cannot crash the app — `t()` falls
back to English if `format` fails.

## Running it from Visual Studio Code

See `START-HERE.md` for the step by step version. In short: open this
folder, pick your Anaconda interpreter, run the "Install what the app needs"
task once, then press F5 and choose "BgeraPrint".

The one thing worth repeating here: BgeraPrint asks questions with
`input()`, and the VS Code Debug Console cannot type back. A run that lands
there looks frozen at the first question with no error at all. Every config
in `.vscode/launch.json` sets `"console": "integratedTerminal"` for that
reason; if you add one of your own and it hangs, that is why.

`justMyCode` is off everywhere, so you can step into any module. The three
places worth a breakpoint: `parser._parse_words` to see what a typed line
became, `app.do()` to watch each instruction being carried out, and
`model.scad()` to see the OpenSCAD before it runs.

## Testing

There are four ways to test, from quickest to most thorough. Use them in
this order.

### 1. The fast tests, while you work

```
python -m tests.test_bgera      the language, the shapes, the settings
python -m tests.test_session    whole sessions typed as a student would
```

About thirty seconds together. Run them after every change.

`test_bgera` runs OpenSCAD for real on every shape, every treatment and
every combination, so a shape that would fail in front of a class fails
here first. It finds `assets\bin\openscad.exe` on its own — nothing has to
be installed. `test_session` uses a small stand-in for PrusaSlicer, so it
needs no printer and no slicer.

Worth keeping: `test_nothing_ever_throws_the_student_out` types thirty
half-finished and nonsense commands and fails if any of them raises. A
student who cannot see the screen and gets dropped back to a bare terminal
has lost their work and their confidence at once.

### 2. The self test, before a build or on a new machine

```
python -m tests.selftest
```

This is the whole app end to end with the real programs it ships with:

    typed command -> model -> OpenSCAD -> STL -> PrusaSlicer -> G-code

It types 32 models the way a student would, builds each with the real
`openscad.exe`, then slices one of them fifteen times with the real
`prusa-slicer-console.exe` under every setting that can make a slicer
refuse a model. It checks that the shipped printer profile came out
unchanged, and measures a ready-made model. No printer is needed.

```
python -m tests.selftest --keep C:\temp\bgeracheck
```

leaves every STL where you can open it in a viewer — or print one and feel
it, which is the only test that really counts for braille.

```
python -m tests.selftest --all-printers        every profile in assets
python -m tests.selftest --printer xplus4      just one
python -m tests.selftest --quick               shapes only, no slicing
python -m tests.selftest --ping 10.1.202.192 7125
```

It exits 0 or 1, so it can go in a build script.

### 3. A scripted session, to hear what a student hears

`tests/session_badge.txt` and `tests/session_shapes.txt` are one command per
line. Play one:

```
python -m tests.play tests/session_badge.txt --fresh
```

`--fresh` gives it a throwaway config and projects folder, so replaying does
not touch your own saved work. Without it, and with no `config.json` present,
the app's first-run questions swallow the whole file.

Piping works too, but only in a shell that has `<` — which PowerShell, the
one VS Code opens on Windows, does not:

```
python BgeraPrint.py < tests\session_badge.txt
```

Both the command and the answer are printed, so it reads like a transcript
of a lesson. Read it aloud, or let a screen reader read it. Every line should
be a sentence that makes sense on its own.

Write more of these for whatever you are working on — they cost nothing, they
catch wording that reads badly, and a test checks that every line in every
`session_*.txt` is still a command the app understands, so one cannot quietly
go stale.

### 4. The `check` command, on a classroom machine

A school computer has the exe and nothing else — no Python, no way to run
any of the above. So the app tests itself:

```
> check
```

It reports, in plain sentences, whether the modelling program, the slicing
program, the printer profile and the ready-made models are all present,
then really builds and really slices a small braille plate, then tries the
printer. It names whichever part is broken. Run it first thing on any
machine you have not used before, and any time something behaves oddly.

### What none of this tests

Nothing here presses the printer's start button, and nothing here can tell
you whether a dot feels right under a finger. Print the badge from
`selftest --keep` and give it to a student who reads braille. That is the
only test that matters in the end.

## Building

```
pyinstaller BgeraPrint.spec
```

The spec now has `pathex=['.']` and lists the `bgera` modules in
`hiddenimports`, so a missing module is a build error rather than a surprise
at run time. `tests` is excluded from the build.

The two anaconda DLL paths in the spec are still hard-coded to
`C:\Users\Chakh\anaconda3\...`. That will need changing on any other machine.

## Things worth doing next

- **Georgian for the new messages.** About 120 keys.
- **Georgian braille.** `bgera/braille.py` is structured so a second alphabet
  table is all it would take; the dot geometry is already right.
- **Reading the model aloud by touch order.** `describe` reads parts in the
  order they were made. Reading them bottom to top, the order a finger meets
  them, might be easier to picture.
- **A `check` command** that warns before slicing: thin walls, parts floating
  in the air, anything over the bed edge. All the numbers needed are already
  in `Model.rough_size`.
- **Text in Georgian letters.** OpenSCAD's `text()` handles it, but the font
  has to be one the computer actually has — that is why no font is named in
  `_text`. `assets/bin/resources/fonts/NotoSans-Regular.ttf` ships with
  PrusaSlicer already and could be pointed at directly.
