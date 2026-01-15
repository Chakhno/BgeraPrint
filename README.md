
# BgeraPrint

**BgeraPrint** is a Windows console application designed to make 3D printing accessible through a **keyboard-only interface with audio instructions**. It allows users to create, slice, and print 3D models without navigating graphical interfaces, making it especially suitable for accessibility-focused workflows.

---

## Overview

BgeraPrint enables users to generate and print 3D models entirely from the keyboard while receiving spoken guidance throughout the process. The application aggregates OpenSCAD, PrusaSlicer (CLI), and FFmpeg to automate model generation, slicing, and printing over Wi-Fi.

---

## Features

Users can:

- **Generate basic shapes**  
  Create cubes, cylinders, cones, pyramids, or spheres by typing the shape name and entering dimensions according to instructions.

- **Print built-in complex models**  
  Select predefined models by name and apply a custom scaling factor.

- **Print custom models**  
  Press `M` and paste the full path to a local `.stl` file, then scale and print it.

- **Slice and print via keyboard**  
  Press `p` to start slicing.  
  Press `p` again to send the print job to the printer over Wi-Fi.

- **Receive spoken instructions**  
  All steps are accompanied by audio prompts in the selected language.

Generated `.scad`, `.stl`, and `.gcode` files are automatically saved to the user’s **Downloads** folder.


---

## First-Time Setup

When launching the application for the first time, users will be prompted to:

1. Select a language for audio instructions:
   - Type `1` for **English**
   - Type `2` for **Georgian**
2. Enter the printer name (lowercase, no spaces or special characters), e.g. `xmax3`
3. Enter the printer’s IP address
4. Enter the printer’s port number (commonly `7125`)

These settings are saved and reused in future sessions.

The only way to change this settings is to delete config.json file that is created after the first-time setup in the folder from which the app is opened.

---

## Keyboard Controls

| Action | Input |
|------|------|
| Generate basic shape | `shape_name` + Enter |
| Select built-in model | `model_name` + Enter |
| Import custom STL | `M` + Enter + Path to the .stl file + Enter|
| Slice / continue print process | `p` |
| Exit application | `b` (instead of pressing `p` for printing) |

---

## Supported Printers

This application is currently compatible with the following **QIDI printers**:

- `xmax3`
- `xplus4`
- `xplus3`
- `xsmart3`
- `q1pro`

Printer configuration files are stored in the `printer_configs/` directory.

---

## Aggregated Third-Party Tools

BgeraPrint aggregates the following tools:

- **OpenSCAD 2021.01** — used for generating 3D models  
- **PrusaSlicer 2.9.4 (CLI)** — used for slicing models  
- **FFmpeg 8.0.1** — used for audio playback

Each tool is distributed under its respective license.  
Full license texts and notices are provided in the `LICENSES/` directory and `NOTICE_THIRD_PARTY.md`.

---

## Copyright

© 2026 Luka Chakhnashvili. All rights reserved.

The BgeraPrint name and logo are original works created by the author.

The source code of BgeraPrint is not licensed for redistribution or modification,
except as required by the licenses of aggregated third-party components.
