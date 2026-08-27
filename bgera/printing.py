#!/usr/bin/env python
# coding: utf-8
"""
Print settings, slicing and talking to the printer.

Everything the student can change about how a model is printed lives in
SETTINGS below.  Each entry says:

    words     the plain words a student may type
    kind      number, choice or switch
    limits    smallest and largest sensible number
    choices   for choice settings, the plain word and what PrusaSlicer calls it
    keys      the PrusaSlicer options this setting writes
    say       how to read the value back to the student

The shipped printer profile is never changed.  A copy is made for each
print, so a setting from last week can never surprise anybody.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# What a student may change
# ---------------------------------------------------------------------------

SETTINGS = {
    "filling": {
        "words": ["filling", "infill", "fill", "inside", "solid"],
        "kind": "number", "limits": (0, 100), "unit": "percent",
        "default": 15,
        "keys": lambda v: {"fill_density": f"{int(v)}%"},
        "help": "How much plastic goes inside. 15 is normal, 0 is empty, 100 is solid.",
    },
    "pattern": {
        "words": ["pattern", "fill pattern", "infill pattern", "shape inside"],
        "kind": "choice", "default": "cubic",
        "choices": {
            "cubic": "cubic", "grid": "grid", "lines": "rectilinear",
            "straight": "rectilinear", "honeycomb": "honeycomb",
            "triangles": "triangles", "stars": "stars", "waves": "gyroid",
            "gyroid": "gyroid", "solid": "rectilinear",
        },
        "keys": lambda v: {"fill_pattern": v},
        "help": "The shape of the plastic inside. cubic, honeycomb, waves, grid, lines, triangles, stars.",
    },
    "quality": {
        "words": ["quality", "detail", "layer", "fineness"],
        "kind": "choice", "default": "normal",
        "choices": {"draft": 0.30, "rough": 0.28, "normal": 0.20,
                    "fine": 0.15, "best": 0.12},
        "keys": lambda v: {"layer_height": f"{v}",
                           "first_layer_height": f"{max(v, 0.2)}"},
        "help": "How thin each layer is. best is slowest and smoothest, draft is fastest.",
    },
    "walls": {
        "words": ["walls", "wall", "perimeters", "skin", "outside"],
        "kind": "number", "limits": (1, 10), "unit": "walls", "default": 2,
        "keys": lambda v: {"perimeters": str(int(v))},
        "help": "How many lines thick the outside is. 2 is normal, 4 is strong.",
    },
    "top": {
        "words": ["top", "top layers", "lid"],
        "kind": "number", "limits": (0, 12), "unit": "layers", "default": 4,
        "keys": lambda v: {"top_solid_layers": str(int(v))},
        "help": "How many solid layers close the top. 0 leaves it open.",
    },
    "bottom": {
        "words": ["bottom", "bottom layers", "floor"],
        "kind": "number", "limits": (0, 12), "unit": "layers", "default": 4,
        "keys": lambda v: {"bottom_solid_layers": str(int(v))},
        "help": "How many solid layers make the bottom.",
    },
    "supports": {
        "words": ["supports", "support", "props", "scaffold"],
        "kind": "choice", "default": "off",
        "choices": {"off": "off", "no": "off", "on": "everywhere",
                    "yes": "everywhere", "everywhere": "everywhere",
                    "bed": "bed", "from the bed": "bed", "touching": "bed"},
        "keys": lambda v: (
            {"support_material": "0", "support_material_auto": "0",
             "support_material_buildplate_only": "0"} if v == "off" else
            {"support_material": "1", "support_material_auto": "1",
             "support_material_buildplate_only": "1" if v == "bed" else "0"}),
        "help": "Little props that hold up parts hanging in the air. off, on, or bed.",
    },
    "brim": {
        "words": ["brim", "skirt", "edge"],
        "kind": "number", "limits": (0, 20), "unit": "millimetres", "default": 0,
        "keys": lambda v: {"brim_width": str(v),
                           "brim_type": "outer_only" if v else "no_brim"},
        "help": "A flat rim around the model so it does not come loose. 5 is a good size.",
    },
    "raft": {
        "words": ["raft", "mat"],
        "kind": "number", "limits": (0, 10), "unit": "layers", "default": 0,
        "keys": lambda v: {"raft_layers": str(int(v))},
        "help": "Layers printed under the model, then peeled off. Usually 0.",
    },
    "speed": {
        "words": ["speed", "fast", "slow"],
        "kind": "choice", "default": "normal",
        "choices": {"slow": 0.6, "careful": 0.6, "normal": 1.0,
                    "fast": 1.4, "quick": 1.4},
        "keys": None,   # handled separately, it scales several options
        "help": "How fast the printer moves. slow is neater, fast is quicker.",
    },
    "material": {
        "words": ["material", "plastic", "filament"],
        "kind": "choice", "default": "pla",
        "choices": {"pla": "PLA", "petg": "PETG", "abs": "ABS",
                    "tpu": "FLEX", "flex": "FLEX", "rubber": "FLEX"},
        "keys": lambda v: {"filament_type": v},
        "help": "Which plastic is in the printer. pla, petg, abs or tpu.",
    },
    "heat": {
        "words": ["heat", "temperature", "hot", "nozzle"],
        "kind": "number", "limits": (170, 300), "unit": "degrees", "default": 0,
        "keys": lambda v: {"temperature": str(int(v)),
                           "first_layer_temperature": str(int(v) + 5)},
        "help": "How hot the nozzle gets. Leave this alone unless your teacher says so.",
    },
    "bed": {
        "words": ["bed", "bed heat", "plate heat"],
        "kind": "number", "limits": (0, 120), "unit": "degrees", "default": 0,
        "keys": lambda v: {"bed_temperature": str(int(v)),
                           "first_layer_bed_temperature": str(int(v))},
        "help": "How hot the printing bed gets.",
    },
    "vase": {
        "words": ["vase", "spiral", "hollow print", "cup"],
        "kind": "switch", "default": "off",
        "keys": lambda v: (
            {"spiral_vase": "1", "perimeters": "1", "top_solid_layers": "0",
             "fill_density": "0%"} if v == "on" else {"spiral_vase": "0"}),
        "help": "Prints one thin spiralling wall, so the model comes out hollow like a cup.",
    },
    "copies": {
        "words": ["copies", "many", "number", "how many"],
        "kind": "number", "limits": (1, 50), "unit": "copies", "default": 1,
        "keys": None,   # passed to the slicer on the command line
        "help": "How many of the model to print at once.",
    },
    "bigger": {
        "words": ["bigger", "scale", "enlarge"],
        "kind": "number", "limits": (0.1, 20), "unit": "times", "default": 1,
        "keys": None,   # passed to the slicer on the command line
        "help": "Print the model bigger or smaller. 2 means twice the size.",
    },
}

SETTING_WORDS = {}
for _key, _info in SETTINGS.items():
    SETTING_WORDS[_key] = _key
    for _word in _info["words"]:
        SETTING_WORDS[_word] = _key

# Speed settings are scaled together so the whole print gets faster or slower.
SPEED_KEYS = {
    "perimeter_speed": 45, "small_perimeter_speed": 25,
    "external_perimeter_speed": 25, "infill_speed": 80,
    "solid_infill_speed": 80, "top_solid_infill_speed": 40,
    "support_material_speed": 50, "bridge_speed": 25,
    "gap_fill_speed": 40, "travel_speed": 180,
}


def setting_for(word):
    return SETTING_WORDS.get(word.lower())


class PrintSettings:
    """The student's current print settings, in plain words."""

    def __init__(self):
        self.values = {k: v["default"] for k, v in SETTINGS.items()}

    def reset(self):
        self.values = {k: v["default"] for k, v in SETTINGS.items()}

    def set(self, key, value):
        """
        Returns (ok, message_key, extra).  The caller turns that into speech.
        """
        info = SETTINGS[key]

        if info["kind"] == "number":
            try:
                number = float(value)
            except (TypeError, ValueError):
                return False, "need_number", {"word": key}
            low, high = info["limits"]
            if key in ("heat", "bed") and number == 0:
                # Zero means "say nothing about it and let the printer
                # profile decide", which is how these two start out. Without
                # this, a temperature could be set but never un-set.
                self.values[key] = 0
                return True, None, {"value": "as the printer profile says"}
            if number < low:
                return False, "number_too_small", {"word": key, "low": low}
            if number > high:
                return False, "number_too_big", {"word": key, "high": high}
            if number == int(number):
                number = int(number)
            self.values[key] = number
            return True, None, {"value": f"{number} {info['unit']}"}

        if info["kind"] == "switch":
            word = str(value).lower()
            if word in ("on", "yes", "1", "true"):
                self.values[key] = "on"
            elif word in ("off", "no", "0", "false"):
                self.values[key] = "off"
            else:
                return False, "setting_unknown_value", {
                    "value": value, "setting": key, "choices": "on, off"}
            return True, None, {"value": self.values[key]}

        word = str(value).lower()
        if word not in info["choices"]:
            return False, "setting_unknown_value", {
                "value": value, "setting": key,
                "choices": ", ".join(sorted(set(info["choices"])))}
        self.values[key] = word
        return True, None, {"value": word}

    def spoken(self, key):
        info = SETTINGS[key]
        value = self.values[key]
        if info["kind"] == "number":
            if key in ("heat", "bed") and not value:
                return "as the printer profile says"
            return f"{value} {info['unit']}"
        return str(value)

    def all_spoken(self):
        return [(key, self.spoken(key)) for key in SETTINGS]

    # -- turning the settings into a PrusaSlicer profile -------------------

    def overrides(self):
        """The PrusaSlicer options these settings change."""
        out = {}
        for key, info in SETTINGS.items():
            value = self.values[key]
            if info["keys"] is None:
                continue
            if key in ("heat", "bed") and not value:
                continue          # leave the printer profile alone
            if info["kind"] == "choice":
                value = info["choices"][value]
            out.update(info["keys"](value))

        factor = SETTINGS["speed"]["choices"][self.values["speed"]]
        if factor != 1.0:
            for option, normal in SPEED_KEYS.items():
                out[option] = str(round(normal * factor))

        # Filling of 100 percent must be straight lines, or it looks wrong.
        if str(out.get("fill_density", "")).startswith("100"):
            out["fill_pattern"] = "rectilinear"
        return out

    def write_profile(self, source_ini, work_dir):
        """
        Copy the printer profile and apply the student's settings to the copy.
        The file that ships with the app is never touched.
        """
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        target = work_dir / "current_print.ini"

        lines = Path(source_ini).read_text(encoding="utf-8", errors="ignore").splitlines()
        wanted = self.overrides()
        seen = set()
        out = []
        for line in lines:
            match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=", line)
            if match and match.group(1) in wanted:
                option = match.group(1)
                out.append(f"{option} = {wanted[option]}")
                seen.add(option)
            else:
                out.append(line)
        for option, value in wanted.items():
            if option not in seen:
                out.append(f"{option} = {value}")

        target.write_text("\n".join(out) + "\n", encoding="utf-8")
        return target


# ---------------------------------------------------------------------------
# OpenSCAD and PrusaSlicer
# ---------------------------------------------------------------------------

def as_command(program):
    """
    A program to run, as a list of words.

    Usually this is one path to an .exe.  Allowing a list as well means a
    test can put a stand-in in its place -- [sys.executable, "stub.py"] --
    which is the only way to do it on Windows, where a .py file cannot be
    run as a program on its own.
    """
    if isinstance(program, (list, tuple)):
        return [str(part) for part in program]
    return [str(program)]


def program_exists(program):
    """Is this program actually here?  Works for a path or a command list."""
    words = as_command(program)
    if not words:
        return False
    # For a command list such as [python, "stub.py"], the script is what
    # matters; for a plain path it is the path itself.
    return Path(words[-1]).exists() or shutil.which(words[0]) is not None


def run_openscad(openscad, scad_text, scad_path, stl_path, timeout=180):
    """Write the OpenSCAD program and turn it into an STL shape file."""
    Path(scad_path).parent.mkdir(parents=True, exist_ok=True)
    Path(scad_path).write_text(scad_text, encoding="utf-8")

    command = as_command(openscad) + ["-o", str(stl_path), str(scad_path)]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout)
    except FileNotFoundError:
        return False, "The modelling program could not be found."
    except subprocess.TimeoutExpired:
        return False, "The model took too long to build. Try something simpler."

    if result.returncode != 0 or not Path(stl_path).exists():
        return False, _first_useful_line(result.stderr)
    return True, ""


def _first_useful_line(text):
    for line in (text or "").splitlines():
        line = line.strip()
        if line and not line.startswith("ECHO"):
            return line
    return "Something in the model did not make sense."


def stl_size(slicer, stl_path):
    """The real size of a shape file, from the slicer, in millimetres."""
    try:
        info = subprocess.run(as_command(slicer) + ["--info", str(stl_path)],
                              capture_output=True, text=True, timeout=120)
    except Exception:
        return None
    sizes = []
    for line in info.stdout.splitlines():
        if line.strip().startswith("size_"):
            try:
                sizes.append(round(float(line.split("=")[1]), 1))
            except (ValueError, IndexError):
                pass
    return sizes if len(sizes) == 3 else None


def slice_model(slicer, stl_files, profile, output_gcode, copies=1, scale=1):
    """Turn shape files into a printing file.  Returns (ok, message)."""
    if isinstance(stl_files, (str, Path)):
        stl_files = [stl_files]

    command = as_command(slicer) + ["--load", str(profile),
                                    "--printer-technology", "FFF"]
    if float(scale) != 1:
        command += ["--scale", str(scale)]
    if int(copies) > 1:
        command += ["--merge", "--duplicate", str(int(copies))]
    command += ["--slice", "--export-gcode", "--output", str(output_gcode)]
    command += [str(f) for f in stl_files]

    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=900)
    except FileNotFoundError:
        return False, "The slicing program could not be found."
    except subprocess.TimeoutExpired:
        return False, "Slicing took too long. Try a smaller model."

    if result.returncode != 0 or not Path(output_gcode).exists():
        return False, _slicer_problem(result.stderr or result.stdout)
    return True, ""


def _slicer_problem(text):
    """Turn a slicer complaint into something a student can act on."""
    lowered = (text or "").lower()
    if "outside" in lowered and "print" in lowered:
        return "The model is too big for the printer bed. Make it smaller."
    if "empty" in lowered or "no objects" in lowered:
        return "There was nothing to print."
    if "not manifold" in lowered or "manifold" in lowered:
        return ("The shape has a gap in it. Try overlapping the parts a "
                "little more before joining them.")
    return _first_useful_line(text)


def gcode_report(gcode_path):
    """
    Read the printing file and pull out the numbers a student cares about:
    how long it takes and how much plastic it uses.
    """
    report = {"time": None, "grams": None, "metres": None, "layers": None}
    if not Path(gcode_path).exists():
        return report

    try:
        text = Path(gcode_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return report

    time_match = re.search(r"estimated printing time \(normal mode\)\s*=\s*(.+)", text)
    if time_match:
        report["time"] = _spoken_time(time_match.group(1).strip())

    grams = re.search(r"filament used \[g\]\s*=\s*([\d.]+)", text)
    if grams:
        report["grams"] = round(float(grams.group(1)), 1)

    metres = re.search(r"filament used \[mm\]\s*=\s*([\d.]+)", text)
    if metres:
        report["metres"] = round(float(metres.group(1)) / 1000.0, 2)

    layers = re.search(r";\s*total layers count\s*=\s*(\d+)", text)
    if layers:
        report["layers"] = int(layers.group(1))

    return report


def _spoken_time(raw):
    days = hours = minutes = seconds = 0
    for value, unit in re.findall(r"(\d+)([dhms])", raw):
        value = int(value)
        if unit == "d":
            days = value
        elif unit == "h":
            hours = value
        elif unit == "m":
            minutes = value
        else:
            seconds = value

    if seconds > 0:
        minutes += 1
    if minutes >= 60:
        hours += minutes // 60
        minutes %= 60
    if hours >= 24:
        days += hours // 24
        hours %= 24

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes or not parts:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " and ".join(parts) if len(parts) <= 2 else \
        ", ".join(parts[:-1]) + " and " + parts[-1]


# ---------------------------------------------------------------------------
# The printer itself
# ---------------------------------------------------------------------------

class Printer:
    """A QIDI printer, spoken to over its Moonraker connection."""

    def __init__(self, name, model, ip, port):
        self.name = name
        self.model = model
        self.ip = ip
        self.port = str(port)

    @property
    def base(self):
        return f"http://{self.ip}:{self.port}"

    def upload_and_print(self, file_path, timeout=300):
        if not Path(file_path).exists():
            return False, "The printing file is missing."
        try:
            with open(file_path, "rb") as handle:
                response = requests.post(
                    f"{self.base}/server/files/upload",
                    data={"root": "gcodes", "print": "true"},
                    files={"file": (os.path.basename(file_path), handle)},
                    timeout=timeout)
        except requests.exceptions.ConnectionError:
            return False, "offline"
        except requests.exceptions.Timeout:
            return False, "The printer took too long to answer."
        except Exception as problem:
            return False, str(problem)

        if response.status_code in (200, 201):
            return True, ""
        return False, f"The printer answered with code {response.status_code}."

    def status(self, timeout=15):
        """
        What the printer is doing.  Returns a dictionary, or None if it
        cannot be reached.
        """
        try:
            response = requests.get(
                f"{self.base}/printer/objects/query",
                params={"print_stats": "", "display_status": "",
                        "virtual_sdcard": ""},
                timeout=timeout)
            data = response.json()["result"]["status"]
        except Exception:
            return None

        stats = data.get("print_stats", {})
        sdcard = data.get("virtual_sdcard", {})
        display = data.get("display_status", {})

        progress = display.get("progress", sdcard.get("progress", 0)) or 0
        done = stats.get("print_duration", 0) or 0
        left = None
        if progress > 0.01 and done:
            left = _spoken_seconds((done / progress) - done)

        return {
            "state": stats.get("state", "unknown"),
            "file": stats.get("filename", ""),
            "percent": int(round(progress * 100)),
            "left": left,
        }

    def _command(self, path, timeout=15):
        try:
            response = requests.post(f"{self.base}{path}", timeout=timeout)
            return response.status_code in (200, 201), ""
        except requests.exceptions.ConnectionError:
            return False, "offline"
        except Exception as problem:
            return False, str(problem)

    def cancel(self):
        return self._command("/printer/print/cancel")

    def pause(self):
        return self._command("/printer/print/pause")

    def resume(self):
        return self._command("/printer/print/resume")

    def to_dict(self):
        return {"name": self.name, "model": self.model,
                "ip": self.ip, "port": self.port}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["model"], data["ip"], data["port"])


def _spoken_seconds(seconds):
    seconds = max(0, int(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if hours and minutes:
        return f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minutes"
    if hours:
        return f"{hours} hour{'s' if hours > 1 else ''}"
    return f"{max(1, minutes)} minute{'s' if minutes != 1 else ''}"
