# Building the Windows program, and making a release

## The build command

```
py -m PyInstaller BgeraPrint.spec --noconfirm --clean
```

That is all. `BgeraPrint.spec` already carries the icon, the assets folder,
the two OpenSSL DLLs from Anaconda, and the list of modules — so the options
live in a file that gets committed rather than in a command line that has to
be remembered.

`dist\BgeraPrint.exe` comes out, one file, everything inside it.

### Or the same thing as one line

The command used for version 1.3.1 still works. The app is a package now
rather than a single file, but PyInstaller follows the imports and picks up
all twelve `bgera` modules by itself — this was checked by building it and
running the result, not assumed.

```
py -m PyInstaller --onefile --icon=assets/Icon.ico ^
   --add-data "assets;assets" ^
   --add-binary "C:\Users\Chakh\anaconda3\Library\bin\libssl-3-x64.dll;." ^
   --add-binary "C:\Users\Chakh\anaconda3\Library\bin\libcrypto-3-x64.dll;." ^
   --exclude-module tests --noconfirm --clean BgeraPrint.py
```

Two small additions to the 1.3.1 version: `--exclude-module tests` keeps the
test files out of a program students are given, and `--noconfirm --clean`
stops it asking questions and stops a stale build folder confusing things.

### Before building

```
py -m unittest discover -s tests -p "test_*.py"
py -m tests.selftest
```

The second one is the one that matters before a release: it puts 32 models
through the real OpenSCAD and the real PrusaSlicer. Do not ship a build that
has not passed it.

### After building

```
dist\BgeraPrint.exe
```

Type `check`. It tests the modelling program, the slicer, the printer
profile, the ready made models and the printer, and names whatever is
broken. Then make a cube and print it.

## Where the exe may live

BgeraPrint keeps `config.json`, `projects\` and `work\` **next to the
exe**, so a whole setup can be copied from one classroom machine to another
on a memory stick.

That means it wants a folder it can write to. Desktop, Documents or a stick
are all fine. `C:\Program Files` is not: Windows refuses writes there. If it
finds it cannot write beside itself it moves its settings to
`%LOCALAPPDATA%\BgeraPrint` rather than failing, but the tidy arrangement is
lost, so say in the release notes where to put it.

## What goes in the release

```
BgeraPrint-2.1-windows.zip
├── BgeraPrint.exe
├── README.md
├── NOTICE_THIRD_PARTY.md
└── COMMANDS.md
```

`COMMANDS.md` is worth adding: it is the one a teacher prints out.

### The notices are not optional

The exe carries OpenSCAD (GPL v2) and PrusaSlicer (AGPL v3). Both licences
require that whoever receives the program also receives the licence terms
and can get the source. `NOTICE_THIRD_PARTY.md` is what discharges that,
which is why it goes in the ZIP and not only in the repository.

BgeraPrint runs those two as separate programs rather than linking to them,
which is aggregation and not a derived work — so BgeraPrint itself does not
have to be GPL. Handing on the notices is still required.

### Suggested release notes

> **BgeraPrint 2.1**
>
> Rebuilt from one 919-line script into a tested package.
>
> - Two ways to work: arrow key menus, or typed commands. Chosen at startup,
>   swap at any time.
> - Sizes set with the left and right arrows, from 0.1 mm a press, speeding
>   up while a key is held.
> - Real braille at the Marburg Medium standard — print your own name badge.
> - 14 shapes (was 5), joins, cuts, overlaps, rounding, hollowing, arrays.
> - 16 print settings in plain words. Named projects. 100-step undo.
> - Printer status, pause, resume, cancel.
> - Everything from 1.3.1 still works: `w20l30h10`, `p45cubicn5`, the
>   `base:cube,w40 ++ top:sphere,d30` form.
>
> Fixed from 1.3.1: any word beginning with "p" was treated as a print
> command; a part named "cube" produced OpenSCAD that called itself forever;
> the shipped printer profile was edited in place.
>
> Put the exe in a folder you can write to — Desktop or Documents, not
> Program Files. It keeps your settings and saved work beside it.
>
> Type `check` when it starts to test that everything is working.

## Tagging it

```
git tag -a v2.1 -m "BgeraPrint 2.1"
git push origin v2.1
```

Then on GitHub: Releases, Draft a new release, pick the `v2.1` tag, attach
the ZIP.
