#!/usr/bin/env python
# coding: utf-8
"""
BgeraPrint

3D modelling and 3D printing for students who cannot see the screen.

Everything is typed and everything is spoken back.  This file only starts
the app; the work is done in the bgera folder:

    bgera/texts.py     every word the student hears, English and Georgian
    bgera/shapes.py    the shapes and the OpenSCAD behind them
    bgera/braille.py   real braille dots, at the standard size
    bgera/model.py     the model being built, with undo
    bgera/parser.py    turning typed words into things to do
    bgera/printing.py  print settings, slicing, and the printer
    bgera/transfer.py  sending files between computers
    bgera/help.py      help topics and lessons
    bgera/app.py       the loop that ties it together
"""

import sys

if __name__ == "__main__":
    from bgera.app import main
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)
