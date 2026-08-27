# BgeraPrint 2.1 — running it from the source, in VS Code

This folder is the app as scripts. Nothing here was built by PyInstaller.
Everything runs straight from Python, so you can change a line and see the
result immediately.

## The short version

1. Open **this folder** in VS Code (File → Open Folder).
2. Ctrl+Shift+P → `Python: Select Interpreter` → your Anaconda Python.
3. Terminal → Run Task… → **Install what the app needs**.
4. Press **F5**, choose **BgeraPrint**.

The app starts in the terminal panel at the bottom, ready to type at.

---

## The detailed version

### 1. Open the folder

File → Open Folder → this folder (`BgeraPrint v2.0`).

Open **this** folder, not one above or below it. The settings in `.vscode`
use `${workspaceFolder}`, which means "the folder you opened", and they
expect `BgeraPrint.py`, `bgera` and `tests` to be sitting directly inside it.

VS Code may offer to install the recommended extensions. Say yes — they are
just the Python ones.

### 2. Choose your Python

Ctrl+Shift+P, type `Python: Select Interpreter`, press Enter, and pick your
Anaconda Python (the one you used to build the exe before).

You can check which one is selected at any time: it is shown at the bottom
right of the window when a `.py` file is open.

### 3. Install what it needs

Terminal menu → Run Task… → **Install what the app needs**.

That runs `pip install -r requirements.txt`, which installs:

- **requests** — the app needs this to talk to the printer. Without it the
  app will not even start.
- **pyinstaller** — only for building an exe later. Harmless now.

You only do this once per Python installation.

OpenSCAD and PrusaSlicer are *not* installed this way. They are already in
`assets\bin`, and the app finds them there by itself.

### 4. Run it

Press **F5**. A small box appears at the top of the window listing the ways
to run. Choose **BgeraPrint**.

The terminal panel opens at the bottom. The first thing it asks is how you
want to work:

```
How would you like to use BgeraPrint today?
  1. Menus, choose everything with the arrow keys and Enter
  2. Typing, type commands such as: cube, width 30
```

Whichever you picked last time is already selected, so Enter keeps it. If
you choose Menus it asks one more thing — how you would like to set sizes:

```
And how would you like to set sizes and numbers?
  1. With the arrow keys, left and right change it, faster the longer you hold them
  2. By typing them, type the number and press Enter
```

**Menus** — arrow keys and Enter, all the way down to the measurements.
Choose "Make a shape", then "Cube", and you land on a size menu you never
leave: Up and Down walk between width, length and height, Left and Right
change whichever one you are on, a tenth of a millimetre a press. Hold a
key down and it speeds up to half a millimetre, then one, then five, then
ten. Escape always steps back.

**Typing** — click in the terminal and type:

```
cube
width 30 length 20 height 10
prepare
```

Swap at any time: type `menu` for the menus, or pick "Switch to typing
commands" from the main menu. Both do exactly the same things underneath.

Type `quit` to leave, or press Ctrl+C.

The very first time, the app asks for your language, printer model, IP
address and port, and remembers them in `config.json` next to
`BgeraPrint.py`. Delete that file if you ever want to see the setup
questions again.

---

## The menus and screen readers

There are two ways the menus can draw themselves, and the difference matters
more than it looks:

```
style speak     says each choice as you land on it        (how it comes set)
style visual    highlights the line on screen instead
```

`speak` prints the choice you moved to as a **new line** every time. Screen
readers announce new terminal text reliably, and redrawn text only sometimes
— so the pretty in-place version would leave a blind student pressing Down
and hearing silence. That is why `speak` is the default.

`visual` is the in-place redraw with colour, which looks much better. Use it
for a magnifier, or when showing the app to a sighted audience.

The same thinking shapes the accelerating numbers. At full speed the value
changes about thirty times a second, and announcing every one would bury a
screen reader — so while an arrow is held it is read out about three times a
second, plus whenever the step size changes. The value it finally settled on
is always read out, whatever else was skipped: hearing "118" and walking
away with 168 would be worse than saying nothing at all.

Change either at any time with `numbers arrows`, `numbers typed`,
`style speak` or `style visual`.

## The one thing that will catch you out

BgeraPrint asks questions with `input()`. **The VS Code Debug Console cannot
type back.** If a run ends up there, the app looks completely frozen at the
first question and nothing you type does anything — no error, no clue.

Every config in `.vscode\launch.json` sets `"console": "integratedTerminal"`
to avoid this. If you write a config of your own and it seems to hang, that
is why.

The same applies to the ▷ play button in the top right of the editor. It
uses the terminal, so it is fine — but pressing F5 with a config chosen is
the reliable way.

---

## What else F5 offers

| Choose this | And you get |
|---|---|
| **BgeraPrint** | the app, ready to type at |
| **BgeraPrint (play a session file)** | replays `tests\session_badge.txt` and prints the whole conversation |
| | there is a `tests\session_menus.txt` too, which drives the menus |
| **Fast tests** | the language, shapes and settings tests |
| **Session tests** | whole sessions typed as a student would |
| **Self test (everything, real programs)** | the full chain with the real OpenSCAD and PrusaSlicer; results kept in `selftest-output` |
| **Self test (quick, shapes only)** | the same without slicing, about 20 seconds |
| **Georgian still to translate** | lists the message keys still needing Georgian |
| **The file I am looking at** | runs whatever is open in the editor |

## Tasks

**Ctrl+Shift+B** runs all 211 tests. Terminal → Run Task… for the others:
the two self tests, both session replays, the Georgian list, installing the
requirements, and building an exe when you eventually want one.

## The Testing panel

The flask icon in the left bar lists every test with a green arrow beside
it. Click an arrow to run one test; click the little bug to debug it. Useful
when one test fails and you do not want to sit through the other 150.

If the list ever comes up empty, it is the interpreter: choose it again with
`Python: Select Interpreter`, then `Test: Refresh Tests`.

`tests\test_menus.py` drives the whole arrow key interface with pretend
keypresses, so the menus are tested without a terminal. It also feeds the
Windows key-decoding table the exact bytes Windows sends, which is worth
having because Windows is where the app actually runs and a wrong letter in
that table would make the arrow keys silently do nothing.

## Breakpoints

`justMyCode` is off in every config, so you can step into any part of the
app. The three places worth a breakpoint when something behaves oddly:

- `bgera\parser.py`, in `_parse_words` — see what a typed line turned into.
- `bgera\app.py`, in `do()` — see each instruction being carried out.
- `bgera\model.py`, in `scad()` — see the OpenSCAD just before it is run.

To debug something a student typed, put their commands in a text file in
`tests\` named `session_something.txt`, then use the **play a session file**
config with breakpoints set. It reproduces the same thing every time, which
typing by hand does not.

---

## Running it without VS Code

Open a terminal in this folder and:

```
python BgeraPrint.py                              the app
python -m unittest discover -s tests -p "test_*.py"   all the tests
python -m tests.selftest                          the full self test
python -m tests.play tests/session_badge.txt --fresh
python -m bgera.texts                             untranslated Georgian
```

Inside the app itself, `check` tests that everything is working — the
modelling program, the slicer, the printer profile and the printer.

---

## What is in this folder

```
BgeraPrint.py        starts the app
bgera\               the app itself, twelve modules
tests\               211 tests, the self test, and session files to replay
assets\              OpenSCAD, PrusaSlicer, printer profiles, ready made models
COMMANDS.md          every command, for students and worksheets
NOTES-FOR-DEVELOPER.md   how it is built and how to extend it
BgeraPrint.spec      for PyInstaller, when you want an exe
requirements.txt     what to pip install
config.json          your language and printer, remembered
.vscode\             the run configurations described above
```

Nothing built by PyInstaller was copied here. When you do want an exe:

```
python -m PyInstaller BgeraPrint.spec --noconfirm
```

or Terminal → Run Task… → **Build the exe**. It appears in `dist\`, and
`build\` is scratch you can delete. Your original
`Desktop\BgeraPrint v1.3.1` folder is untouched, exe and all.
