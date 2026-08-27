#!/usr/bin/env python
# coding: utf-8
"""
Help, written for listening rather than for reading.

The old app read out one long instruction.  A screen reader takes almost two
minutes to get through it, and by the end the student has forgotten the
beginning.  So help is now split into small topics.  Typing help on its own
gives a list of topics that takes about fifteen seconds to hear.  Each topic
is short enough to hear again without losing patience.

Every line is one idea.  Examples are always real commands the student can
copy straight away.
"""

MENU = [
    "Help topics. Type help and the topic name.",
    "  help shapes      the things you can make",
    "  help size        making a shape bigger or smaller",
    "  help move        putting parts where you want them",
    "  help join        joining, cutting and overlapping parts",
    "  help change      rounding, hollowing, copying, mirroring",
    "  help words       writing names and braille",
    "  help listen      hearing what you have made",
    "  help settings    how the model gets printed",
    "  help print       preparing and printing",
    "  help save        keeping your work",
    "  help share       sending files to another computer",
    "  help printer     setting up and watching the printer",
    "  help using       menus, typing, and swapping between them",
    "  help lessons     step by step practice",
    "  check            test that the app itself is working",
    "  help all         everything, in order",
    "Type stop at any time to leave the app.",
]

TOPICS = {
    "shapes": [
        "Type the name of a shape to make it.",
        "cube, ball, rod, cone, pyramid, prism, tube, ring, donut, wedge, star, plate.",
        "You can also type text or braille to write words.",
        "Built in models: lion, turtle, giraffe, wolf, camel, rocket.",
        "Chess pieces: pawn, rook, knight, bishop, queen, king.",
        "Type open and a file path to use a shape file from your computer.",
        "Example: cube",
        "Then: width 30 length 20 height 10",
    ],
    "size": [
        "After making a shape, say its measurements. All sizes are millimetres.",
        "width, length, height       for a cube, plate or wedge",
        "across                      for a ball, rod, cone, tube or ring",
        "thick                       for the wall of a tube, or a donut ring",
        "sides                       for a pyramid or prism",
        "points                      for a star",
        "You may say several at once.",
        "Example: across 40 height 25 thick 3",
        "To change a part you made earlier, say its name first.",
        "Example: base width 60",
        "bigger 2 makes the last part twice its size. smaller 2 halves it.",
    ],
    "move": [
        "Parts start in the middle of the bed. Move them with a direction and a number.",
        "right, left, forward, back, up, down.",
        "Example: move right 20",
        "Example: move up 10 forward 5",
        "put the ball on the cube        stacks one part on another",
        "put the ball beside the cube    places it next to another",
        "centre                          brings the last part back to the middle",
        "turn 90 flat        spins it like a wheel lying down",
        "turn 90 over        tips it forward",
        "turn 90 sideways    rolls it to one side",
    ],
    "join": [
        "Parts sit next to each other until you combine them.",
        "join cube ball          makes them one piece",
        "cut ball from cube      takes the ball shape out of the cube, leaving a hole",
        "overlap cube ball       keeps only the part where both sit",
        "With no names, join uses the last two parts you made.",
        "For a hole right through, make the cutting shape a little longer than the part.",
        "The result gets a name of its own, which you can hear with list.",
    ],
    "change": [
        "round 3            softens all the edges of the last part by 3 millimetres",
        "hollow 2           empties it out, leaving walls 2 millimetres thick",
        "smooth             wraps a tight skin around it",
        "mirror left        flips it left to right",
        "copy 5 gap 30 right    makes five copies in a row, 30 millimetres apart",
        "ring of 8 across 60    places eight copies in a circle",
        "bigger 2, smaller 2, or scale 1.5 change how big it is",
        "remove ball        takes a part away",
        "rename ball head   gives a part a name you will remember",
        "undo               steps back. redo steps forward again",
    ],
    "words": [
        "text Nino          makes raised letters saying Nino",
        "Then set the letter height and how thick they stand up.",
        "Example: height 12 thick 4",
        "braille nino       makes real braille dots on a small plate",
        "Braille uses the standard size, so it feels like a proper book.",
        "Dots are 1.5 millimetres across and 0.6 millimetres high.",
        "Letters, numbers and full stops all work.",
        "A good name badge: plate width 90 length 30 height 3",
        "Then: braille nino",
        "Then: put braille on plate",
        "Then: join",
    ],
    "using": [
        "BgeraPrint works two ways, and you can swap at any time.",
        "menu        the arrow key menus",
        "typing      commands you type, such as: cube",
        "In the menus: up and down move, Enter chooses, Escape goes back.",
        "A number jumps straight to that choice. A letter jumps to the",
        "next choice starting with it. The question mark repeats them.",
        "style speak   says each choice as you land on it, for screen readers",
        "style visual  highlights the line instead, for looking at",
        "numbers arrows  left and right change a size, faster the longer held",
        "numbers typed   you type each size instead",
    ],
    "listen": [
        "list        names every part and its size",
        "describe    tells you the whole model in sentences",
        "size        the overall width, length and height",
        "what        repeats what you have just done",
        "settings    reads your print settings",
        "After every command the app tells you what changed, so you always know.",
    ],
    "settings": [
        "Change how the model is printed. Say the setting and a value.",
        "filling 45        how much plastic inside, 0 to 100",
        "pattern honeycomb  cubic, honeycomb, waves, grid, lines, triangles, stars",
        "quality fine      best, fine, normal, rough, draft",
        "walls 3           how many lines thick the outside is",
        "supports on       props under parts that hang in the air",
        "brim 5            a flat rim so the model does not come loose",
        "material petg     pla, petg, abs or tpu",
        "speed slow        slow, normal or fast",
        "vase on           prints one hollow spiral wall, good for cups",
        "copies 4          print several at once",
        "settings          reads them all back",
        "normal settings   puts everything back to the usual values",
    ],
    "print": [
        "prepare     works out how the printer will make your model",
        "It then tells you how long it takes and how much plastic it uses.",
        "print       sends it to the printer and starts it",
        "The app asks you to type print a second time, so nothing starts by mistake.",
        "status      how far along the print is",
        "pause and resume     stop and carry on",
        "stop print  ends the print. You must confirm this one too",
        "You can change settings and type prepare again as often as you like.",
    ],
    "save": [
        "save mykeyring     keeps the model under that name",
        "open mykeyring     brings it back later",
        "projects           lists everything you have saved",
        "new                starts an empty model",
        "export             writes the shape file so you can use it elsewhere",
        "Your saved work stays on this computer, next to the app.",
    ],
    "share": [
        "send        sends your printing file to another computer",
        "It asks for the address, the port number and your name.",
        "receive     waits for files coming from other computers",
        "Files that arrive go to your Downloads folder.",
        "Type done when everybody has sent theirs.",
        "A teacher can then prepare and print them all together.",
    ],
    "printer": [
        "check               tests everything: modelling, slicing, the printer",
        "printers            lists the printers you have set up",
        "add printer         sets up another one",
        "use classroom       switches to the printer with that name",
        "remove printer old  takes one off the list",
        "status              what the printer is doing right now",
    ],
    "lessons": [
        "Lessons walk you through a real job, one step at a time.",
        "lessons     lists them",
        "lesson 1    starts the first one",
        "In a lesson, type next to go on, again to hear the step again,",
        "and stop to leave.",
    ],
}

ORDER = ["using", "shapes", "size", "move", "join", "change", "words",
         "listen", "settings", "print", "save", "share", "printer", "lessons"]

# The short first-time introduction.  Under twenty seconds spoken.
INTRO = [
    "BgeraPrint makes 3D models with the keyboard only.",
    "Type a shape name, such as cube, and press Enter.",
    "Then give it sizes, such as width 30 height 20.",
    "Then type prepare, and then print.",
    "Type help at any time to hear what you can do.",
]


# What the menu interface says at the very start.  Even shorter than the
# typing one, because the menus explain themselves as you go.
INTRO_MENUS = [
    "Use the up and down arrows to move, and Enter to choose.",
    "Escape goes back. A number jumps straight to that choice.",
    "Press the question mark to hear the choices again.",
]


def topic(name):
    """The lines for one help topic, or None."""
    name = (name or "").strip().lower()
    if not name:
        return MENU
    if name in ("all", "everything"):
        lines = []
        for key in ORDER:
            lines.append(f"--- {key} ---")
            lines.extend(TOPICS[key])
        return lines
    for key, lines in TOPICS.items():
        if name == key or name.rstrip("s") == key.rstrip("s"):
            return lines
    return None


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------
# Each step is (spoken_text, command_to_try).  When command_to_try is None the
# student just types next.

LESSONS = [
    {
        "title": "Your first cube",
        "steps": [
            ("A cube is the easiest shape. Type cube.", "cube"),
            ("Now give it a size. Every number is in millimetres.",
             "width 30 length 30 height 30"),
            ("Ask the app how big it is.", "size"),
            ("Make it half as tall.", "height 15"),
            ("Work out how the printer will make it.", "prepare"),
            ("You just heard how long it takes. Type print when you are ready.", None),
        ],
    },
    {
        "title": "Cutting a hole",
        "steps": [
            ("Start with a flat plate.", "plate"),
            ("Give it a size.", "width 40 length 40 height 5"),
            ("Now make a rod. It will become the hole.", "rod"),
            ("Make it thin and taller than the plate, so it goes right through.",
             "across 8 height 20"),
            ("Cut the rod out of the plate.", "cut rod from plate"),
            ("Listen to what you have made.", "describe"),
        ],
    },
    {
        "title": "A braille name badge",
        "steps": [
            ("Start with a thin plate for the badge.", "plate"),
            ("Make it badge sized.", "width 90 length 30 height 3"),
            ("Now add your name in braille. Use your own name.", "braille nino"),
            ("Put the braille on top of the plate.", "put braille on plate"),
            ("Join them into one piece.", "join"),
            ("Give it strong walls so the dots do not break.", "walls 3"),
            ("Prepare it for printing.", "prepare"),
        ],
    },
    {
        "title": "A cup, using vase mode",
        "steps": [
            ("Make a rod. It will become the cup.", "rod"),
            ("Cup sized, please.", "across 60 height 80"),
            ("Vase mode prints one thin spiralling wall, so it comes out hollow.",
             "vase on"),
            ("Slow it down a little, so the wall is neat.", "speed slow"),
            ("Prepare it.", "prepare"),
            ("Notice how little plastic it uses compared with a solid rod.", None),
        ],
    },
    {
        "title": "Rounding and stacking",
        "steps": [
            ("Make a cube for the body.", "cube"),
            ("Give it a size.", "width 40 length 40 height 20"),
            ("Soften every edge, so it feels nice in the hand.", "round 4"),
            ("Now make a ball for the head.", "ball"),
            ("Give it a size.", "across 25"),
            ("Sit the ball on top of the cube.", "put ball on cube"),
            ("Join them into one piece.", "join"),
            ("Listen to the result.", "describe"),
        ],
    },
]


def lesson_titles():
    return [lesson["title"] for lesson in LESSONS]
