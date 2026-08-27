# BgeraPrint — every command

Version 2.1. For students, teachers and anybody printing a worksheet.

Sizes are always in millimetres. Capital letters do not matter. If BgeraPrint
does not understand something, it says so and suggests the nearest command —
it never stops working.

Type `help` in the app for the same information split into short spoken
topics, or `lesson 1` to be walked through a real job.

---

## Two ways of working

BgeraPrint asks which one you want every time it starts. Whichever you chose
last time is already selected, so pressing Enter keeps it.

**Menus** — everything is chosen with the arrow keys.

```
Up and Down     move through the choices
Enter           take the one you are on
Escape          go back one step
1 to 9          jump straight to that choice
a letter        jump to the next choice starting with it
?               hear the choices again
```

Nothing has to be remembered and nothing has to be spelled. After every
Enter the next set of choices appears, right down to the measurements.

**Setting a size** happens one of two ways, chosen when the app starts:

```
numbers arrows    Left and Right change the size you are on
numbers typed     Enter, then type the number
```

With **arrows**, the size menu is one you never leave. Up and Down walk
between width, length and height; Left and Right change whichever one you
are on, and the line reads back as it moves:

```
> Width, now 20
> Width, now 20.1
> Width, now 20.2
```

Each press is a tenth of a millimetre. **Hold the key down and it speeds
up** — a tenth, then half a millimetre, then one, then five, then ten — so
20 to 200 takes a second and a half without giving up fine control. It says
the new step size as it changes, and always says the number it settled on.
Let go, or change direction, and it drops back to a tenth.

With **typed**, Enter on a measurement asks for the number and you type it.

**Typing** — the commands in the rest of this document.

Swap between them at any time: type `menu` to get the menus, or choose
"Switch to typing commands" from the main menu. Everything else works the
same either way, because both are doing exactly the same things underneath.

### Two ways of drawing the menus

```
style speak     says each choice as you land on it       (the normal one)
style visual    highlights the line on screen instead
```

`speak` prints the choice you have moved to as a brand new line. Screen
readers announce new text reliably, and redrawn text only sometimes, so this
is the setting a student using speech wants and it is the one that comes set.

`visual` redraws the list in place with the current line marked, which looks
better but says much less. Use it for a magnifier, or for showing the app to
a sighted audience.

---

## The shortest possible session

With the menus: choose **Make a shape**, then **Cube**, then set each
measurement with the arrow keys, then **Get it ready for the printer**.

By typing:

```
cube
width 30 length 20 height 10
prepare
print
```

---

## Making shapes

Type the name and the shape appears at a sensible starting size.

| Command | What you get | Measurements it uses |
|---|---|---|
| `cube`, `box`, `brick`, `block` | a box | width, length, height |
| `ball`, `sphere`, `globe` | a ball | across |
| `rod`, `cylinder`, `stick`, `pole` | a round bar | across, height |
| `cone` | a cone | across, height |
| `pyramid` | a pyramid | across, height, sides |
| `prism`, `hexagon`, `nut` | a many-sided bar | across, height, sides |
| `tube`, `pipe`, `straw` | a hollow bar | across, height, thick |
| `ring`, `washer`, `bangle` | a flat ring | across, height, thick |
| `donut`, `torus`, `hoop` | a ring with a round section | across, thick |
| `wedge`, `ramp`, `slope` | a ramp | width, length, height |
| `star` | a star | across, height, points |
| `plate`, `slab`, `tile`, `card` | a thin flat base | width, length, height |
| `text Nino` | raised letters | height, thick |
| `braille nino` | real braille dots on a plate | thick |

Ready-made models, unchanged from version 1.3.1:
`lion`, `turtle`, `giraffe`, `wolf`, `camel`, `rocket`,
`pawn`, `rook`, `knight`, `bishop`, `queen`, `king`.

Your own file: `open C:\Users\me\Desktop\thing.stl`

---

## Sizes

Say a measurement and a number. Several on one line is fine.

| Word | Means | Also accepts |
|---|---|---|
| `width` | side to side | `wide`, `w` |
| `length` | front to back | `long`, `deep`, `l` |
| `height` | bottom to top | `tall`, `high`, `h` |
| `across` | width of a round thing | `diameter`, `d` |
| `radius` | half of across | `r` |
| `thick` | wall or ring thickness | `thickness`, `wall`, `t` |
| `sides` | flat faces of a pyramid or prism | `faces`, `n` |
| `points` | points of a star | `p` |

```
width 30 length 20 height 10
across 40 thick 3
```

To change a part you made earlier, say its name first: `base width 60`.
Saying just a shape word, such as `plate`, means **the newest plate** — the
one you are working on.

`bigger 2` doubles the last part. `smaller 2` halves it. `scale 1.5` is exact.

---

## Moving and turning

Parts start in the middle of the bed.

```
move right 20
move up 10 forward 5
centre
turn 90 flat        spins it like a wheel lying down
turn 90 over        tips it forward
turn 90 sideways    rolls it to one side
put ball on cube    sits one part on another
put ball beside cube
```

Directions: `right`, `left`, `forward`, `back`, `up`, `down`.

---

## Putting parts together

```
join cube ball          makes one piece
cut rod from plate      leaves a hole where the rod was
overlap cube ball       keeps only where both sit
```

With no names, the last two parts are used: `join`, `cut`, `overlap`.

The result gets a name of its own — `piece`, then `piece2` — and can be
combined again.

**For a hole that goes right through, make the cutting shape longer than the
part it goes through.** A rod 20 tall through a plate 5 thick works; a rod
exactly 5 tall leaves a skin the printer cannot make.

---

## Changing a part

```
round 3             softens every edge by 3 mm
hollow 2            empties it, leaving 2 mm walls
smooth              wraps a tight skin around it
mirror left         flips it left to right
copy 5 gap 30 right five in a row, 30 mm apart
ring of 8 across 60 eight copies in a circle 60 mm across
remove ball
rename ball head
undo                steps back
redo                steps forward again
new                 empty the bed
```

`undo` goes back a hundred steps. Nothing is ever lost by accident.

---

## Hearing what you have made

```
list        every part with its size and position
describe    the whole model in sentences
size        overall width, length and height
what        what your last command did
settings    all your print settings
```

After **every** command BgeraPrint says one short sentence describing what
changed. You never have to guess.

---

## Print settings

| Command | What it does | Values |
|---|---|---|
| `filling 45` | plastic inside | 0 to 100 |
| `pattern honeycomb` | shape of the plastic inside | cubic, honeycomb, waves, grid, lines, triangles, stars |
| `quality fine` | how thin each layer is | best, fine, normal, rough, draft |
| `walls 3` | how many lines thick the outside is | 1 to 10 |
| `top 4` / `bottom 4` | solid layers closing the top and bottom | 0 to 12 |
| `supports on` | props under overhangs | off, on, bed |
| `brim 5` | flat rim so it does not come loose | 0 to 20 mm |
| `raft 3` | layers under the model, peeled off after | 0 to 10 |
| `speed slow` | how fast the printer moves | slow, normal, fast |
| `material petg` | which plastic is loaded | pla, petg, abs, tpu |
| `heat 215` | nozzle temperature | 170 to 300 |
| `bed 60` | bed temperature | 0 to 120 |
| `vase on` | one hollow spiralling wall, good for cups | on, off |
| `copies 4` | print several at once | 1 to 50 |
| `bigger 2` | print it larger or smaller | 0.1 to 20 |
| `normal` | put every setting back |  |

Say a setting with no value to hear what it does:
`supports` → *"supports: Little props that hold up parts hanging in the air.
off, on, or bed. It is off now."*

Your printer's own profile file is **never changed**. A copy is made for each
print, so a setting from last week cannot surprise the next class.

---

## Preparing and printing

```
prepare     work out how the printer will make it
```

You then hear how long it will take, how much plastic it uses, and how many
layers it has.

```
print       sends it and starts the printer
```

`print` asks a second time before anything actually starts, so nothing is
begun by mistake. The same is true of `stop print`.

```
status      how far along the print is
pause
resume
stop print  ends the print
```

---

## Keeping your work

```
save keyring        keeps the model under that name
open keyring        brings it back
projects            everything you have saved
export              writes the shape file to Downloads
```

Saved work lives in a `projects` folder next to the app, and stays there
between sessions.

---

## Sharing with the class

The computer joined to the printer types `receive` and gives a port number.
Everybody else types `send` and gives that computer's address, the same port,
and their own name.

Files arrive in Downloads with the sender's name at the front. The teacher
types `done`, then `prepare`, and everything is printed together.

---

## Printers

```
printers            the ones you have set up
add printer         set up another
use classroom       switch to the one called classroom
remove printer old
```

## Checking the app itself

```
check
```

Tests everything on this computer and says, in plain sentences, whether the
modelling program, the slicing program, the printer settings and the
ready-made models are all working. It really builds and really slices a
small test plate, then tries the printer. It takes about a minute.

Run it on any computer you have not used before, and any time something
behaves oddly.

---

## Lessons

```
lessons     lists them
lesson 1    starts one
next        go on
again       hear the step again
stop        leave the lesson
```

1. Your first cube
2. Cutting a hole
3. A braille name badge
4. A cup, using vase mode
5. Rounding and stacking

Typing the command a lesson suggests moves you on automatically. Starting a
lesson clears the bed; `undo` afterwards brings your model back.

---

## The old way of typing still works

Everything from version 1.3.1 works unchanged, so old worksheets are still
correct.

| Old | Same as |
|---|---|
| `w20l30h10` | `width 20 length 30 height 10` |
| `d20h40n6` | `across 20 height 40 sides 6` |
| `p` | `prepare` |
| `p45cubicn5` | `filling 45` `pattern cubic` `copies 5` `prepare` |
| `m` then a path | `open <path>` |
| `i` | `help` |
| `base:cube,w40,l40,h10 ++ top:sphere,d30` | a cube joined to a ball |
| `body:cube,w40,h40 -- hole:cylinder,d10,h60` | a cube with a hole cut in it |

In the old one-line form, `x`, `y`, `z` move a part and `rx`, `ry`, `rz` turn
it, exactly as before.

---

## Braille, in detail

Braille uses the Marburg Medium standard, which is what braille books use:

- dot base 1.5 mm across, 0.6 mm high
- 2.5 mm between dots inside a cell
- 6.0 mm from one cell to the next

Dots are domes cut off flat at the base. They print without support and feel
right under a finger.

Letters `a` to `z`, digits `0` to `9` (with the number sign put in for you),
and `, ; : . ? ! ' -` all work. Anything else is left out, and BgeraPrint
tells you which characters it skipped.

A badge:

```
plate
width 90 length 30 height 3
braille nino
put braille on plate
join
walls 3
prepare
```

---

## If something goes wrong

| What you hear | What to do |
|---|---|
| *"The model is too big for the printer bed."* | `smaller 2`, or make the parts smaller |
| *"The shape has a gap in it."* | overlap the parts a little more before joining |
| *"I cannot reach the printer."* | check it is switched on and on the same network |
| *"Prepare the model first."* | type `prepare` before `print` |
| *"Did you mean 'cube'?"* | a typo — type the suggestion |

BgeraPrint catches its own mistakes. If anything unexpected happens it says
so and carries on with your model intact.
