#!/usr/bin/env python
# coding: utf-8
"""
Tests for BgeraPrint.

Run from the app folder:      python -m tests.test_bgera

The important ones actually run OpenSCAD, so a shape that would fail in
front of a class fails here first instead.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bgera import braille, help as help_mod, parser, printing, shapes
from bgera.model import Model
try:
    from tests.helpers import OPENSCAD, compile_scad
except ImportError:          # discovered from inside the tests folder
    from helpers import OPENSCAD, compile_scad


class TestParser(unittest.TestCase):

    def parse(self, line, model=None):
        return parser.parse(line, model)

    # -- plain words -------------------------------------------------------

    def test_shape_word(self):
        self.assertEqual(self.parse("cube"), [{"do": "shape", "shape": "cube"}])

    def test_shape_synonyms(self):
        for word in ("box", "brick", "block"):
            self.assertEqual(self.parse(word)[0]["shape"], "cube")
        for word in ("sphere", "ball", "globe"):
            self.assertEqual(self.parse(word)[0]["shape"], "ball")
        for word in ("cylinder", "rod", "pole"):
            self.assertEqual(self.parse(word)[0]["shape"], "rod")

    def test_measurements_on_one_line(self):
        actions = self.parse("width 30 length 20 height 10")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["values"],
                         {"width": 30, "length": 20, "height": 10})

    def test_measurement_synonyms(self):
        actions = self.parse("wide 30 tall 10 across 8")
        self.assertEqual(actions[0]["values"],
                         {"width": 30, "height": 10, "across": 8})

    def test_decimal_measurement(self):
        actions = self.parse("thick 1.5")
        self.assertEqual(actions[0]["values"], {"thick": 1.5})

    def test_measurement_without_number(self):
        actions = self.parse("width")
        self.assertEqual(actions[0]["do"], "unknown")
        self.assertEqual(actions[0]["reason"], "need_number")

    def test_move(self):
        actions = self.parse("move right 20")
        self.assertEqual(actions[0]["do"], "move")
        self.assertEqual(actions[0]["delta"], [20, 0, 0])

    def test_move_two_directions(self):
        actions = self.parse("move up 10 forward 5")
        self.assertEqual(actions[0]["delta"], [0, 5, 10])

    def test_move_negative_direction(self):
        self.assertEqual(self.parse("move left 15")[0]["delta"], [-15, 0, 0])
        self.assertEqual(self.parse("move down 4")[0]["delta"], [0, 0, -4])

    def test_turn(self):
        actions = self.parse("turn 90 over")
        self.assertEqual(actions[0]["turn"], [0, 90, 0])
        self.assertEqual(self.parse("turn 45")[0]["turn"], [0, 0, 45])

    def test_put_on(self):
        model = Model()
        model.add_part("ball")
        model.add_part("cube")
        actions = self.parse("put ball on cube", model)
        self.assertEqual(actions[0], {"do": "stack", "top": "ball",
                                      "bottom": "cube"})

    def test_put_on_top_of(self):
        model = Model()
        model.add_part("ball")
        model.add_part("cube")
        actions = self.parse("put ball on top of cube", model)
        self.assertEqual(actions[0]["do"], "stack")
        self.assertEqual(actions[0]["bottom"], "cube")

    def test_cut_from_reads_the_right_way_round(self):
        model = Model()
        model.add_part("plate")
        model.add_part("rod")
        actions = self.parse("cut rod from plate", model)
        # The plate keeps its identity; the rod is what disappears.
        self.assertEqual(actions[0], {"do": "combine", "op": "cut",
                                      "a": "plate", "b": "rod"})

    def test_join_with_no_names(self):
        actions = self.parse("join")
        self.assertEqual(actions[0]["do"], "combine")
        self.assertEqual(actions[0]["op"], "join")
        self.assertIsNone(actions[0]["a"])

    def test_join_two_names(self):
        model = Model()
        model.add_part("cube")
        model.add_part("ball")
        actions = self.parse("join cube and ball", model)
        self.assertEqual(actions[0]["op"], "join")
        self.assertEqual({actions[0]["a"], actions[0]["b"]}, {"cube", "ball"})

    def test_round_and_hollow(self):
        self.assertEqual(self.parse("round 3")[0], {"do": "round", "amount": 3})
        self.assertEqual(self.parse("hollow 2")[0], {"do": "hollow", "amount": 2})

    def test_smaller_inverts(self):
        actions = self.parse("smaller 2")
        self.assertAlmostEqual(actions[0]["factor"], 0.5)

    def test_copy(self):
        actions = self.parse("copy 5 gap 30 right")
        self.assertEqual(actions[0], {"do": "copy", "count": 5, "gap": 30,
                                      "dir": "right"})

    def test_ring_of(self):
        actions = self.parse("ring of 8 across 60")
        self.assertEqual(actions[0], {"do": "ring", "count": 8, "across": 60})

    def test_text_keeps_the_words(self):
        actions = self.parse("text Nino Beridze")
        self.assertEqual(actions[0], {"do": "shape", "shape": "text",
                                      "words": "Nino Beridze"})

    def test_braille_keeps_the_words(self):
        actions = self.parse("braille nino")
        self.assertEqual(actions[0]["shape"], "braille")
        self.assertEqual(actions[0]["words"], "nino")

    def test_settings(self):
        actions = self.parse("filling 45 walls 3")
        self.assertEqual(actions[0], {"do": "setting", "key": "filling",
                                      "value": "45"})
        self.assertEqual(actions[1], {"do": "setting", "key": "walls",
                                      "value": "3"})

    def test_setting_synonyms(self):
        self.assertEqual(self.parse("infill 20")[0]["key"], "filling")
        self.assertEqual(self.parse("quality fine")[0]["key"], "quality")
        self.assertEqual(self.parse("supports on")[0]["key"], "supports")

    def test_naming_a_part_then_changing_it(self):
        model = Model()
        model.add_part("cube", name="base")
        model.add_part("ball")
        actions = self.parse("base width 60", model)
        self.assertEqual(actions[0]["do"], "measure")
        self.assertEqual(actions[0]["target"], "base")
        self.assertEqual(actions[0]["values"], {"width": 60})

    def test_part_name_that_is_also_a_shape_word(self):
        model = Model()
        model.add_part("cube")
        actions = self.parse("cube", model)
        # Typing a bare shape word always makes a new one.
        self.assertEqual(actions[0]["do"], "shape")

    def test_help_topic(self):
        self.assertEqual(self.parse("help printing")[0],
                         {"do": "help", "topic": "printing"})
        self.assertEqual(self.parse("help")[0]["topic"], "")

    def test_stop_print_is_two_words(self):
        self.assertEqual(self.parse("stop print")[0]["do"], "stopprint")
        self.assertEqual(self.parse("stop")[0]["do"], "stop")

    def test_aliases(self):
        self.assertEqual(self.parse("slice")[0]["do"], "prepare")
        self.assertEqual(self.parse("i")[0]["do"], "help")
        self.assertEqual(self.parse("parts")[0]["do"], "list")

    def test_unknown_word_gets_a_guess(self):
        actions = self.parse("cbue")
        self.assertEqual(actions[0]["do"], "unknown")
        self.assertEqual(actions[0]["guess"], "cube")

    def test_unknown_word_without_a_guess(self):
        actions = self.parse("zzzzqqq")
        self.assertEqual(actions[0]["do"], "unknown")
        self.assertIsNone(actions[0]["guess"])

    def test_empty_line(self):
        self.assertEqual(self.parse(""), [])
        self.assertEqual(self.parse("   "), [])

    def test_a_windows_path_survives(self):
        """Backslashes must not be eaten, or the file is never found."""
        actions = self.parse(r"open C:\Users\Chakh\Desktop\thing.stl")
        self.assertEqual(actions[0], {"do": "openfile",
                                      "path": r"C:\Users\Chakh\Desktop\thing.stl"})

    def test_a_quoted_path_survives(self):
        actions = self.parse('open "C:\\My Models\\thing.stl"')
        self.assertEqual(actions[0]["do"], "openfile")
        self.assertIn("My Models", actions[0]["path"])

    def test_case_does_not_matter(self):
        self.assertEqual(self.parse("CUBE")[0]["shape"], "cube")
        self.assertEqual(self.parse("Width 30")[0]["values"], {"width": 30})

    # -- the old short codes ------------------------------------------------

    def test_legacy_dimensions(self):
        actions = self.parse("w20l30h10")
        self.assertEqual(actions[0]["values"],
                         {"width": 20, "length": 30, "height": 10})

    def test_legacy_diameter(self):
        actions = self.parse("d20h40n6")
        self.assertEqual(actions[0]["values"],
                         {"across": 20, "height": 40, "sides": 6})

    def test_legacy_prepare_plain(self):
        self.assertEqual(self.parse("p"), [{"do": "prepare"}])

    def test_legacy_prepare_with_settings(self):
        actions = self.parse("p45cubicn5")
        self.assertEqual(actions[0], {"do": "setting", "key": "filling",
                                      "value": "45"})
        self.assertEqual(actions[1], {"do": "setting", "key": "pattern",
                                      "value": "cubic"})
        self.assertEqual(actions[2], {"do": "setting", "key": "copies",
                                      "value": "5"})
        self.assertEqual(actions[3], {"do": "prepare"})

    def test_legacy_boolean_line(self):
        actions = self.parse("base:cube,w40,l40,h10 ++ top:sphere,d30")
        kinds = [a["do"] for a in actions]
        self.assertIn("shape", kinds)
        self.assertIn("combine", kinds)
        combine = [a for a in actions if a["do"] == "combine"][0]
        self.assertEqual(combine["op"], "join")
        self.assertEqual(combine["a"], "base")
        self.assertEqual(combine["b"], "top")

    def test_legacy_boolean_difference(self):
        actions = self.parse("body:cube,w40,h40 -- hole:cylinder,d10,h60")
        combine = [a for a in actions if a["do"] == "combine"][0]
        self.assertEqual(combine["op"], "cut")

    def test_legacy_boolean_positions(self):
        actions = self.parse("a:cube,w20 ++ b:sphere,d10,x15,rz45")
        moves = [a for a in actions if a["do"] == "move"]
        turns = [a for a in actions if a["do"] == "turn"]
        self.assertEqual(moves[0]["delta"], [15, 0, 0])
        self.assertEqual(turns[0]["turn"], [0, 0, 45])


class TestBraille(unittest.TestCase):

    def test_letters(self):
        cells, skipped = braille.to_cells("abc")
        self.assertEqual(cells, [(1,), (1, 2), (1, 4)])
        self.assertEqual(skipped, [])

    def test_the_whole_alphabet_is_there(self):
        for letter in "abcdefghijklmnopqrstuvwxyz":
            self.assertIn(letter, braille.LETTERS)

    def test_every_letter_has_a_different_pattern(self):
        patterns = [tuple(sorted(v)) for v in braille.LETTERS.values()]
        self.assertEqual(len(patterns), len(set(patterns)))

    def test_numbers_get_a_number_sign(self):
        cells, _ = braille.to_cells("42")
        self.assertEqual(cells[0], braille.NUMBER_SIGN)
        self.assertEqual(cells[1], braille.LETTERS["d"])
        self.assertEqual(cells[2], braille.LETTERS["b"])
        self.assertEqual(len(cells), 3)

    def test_number_sign_appears_once_per_run(self):
        cells, _ = braille.to_cells("123")
        self.assertEqual(cells.count(braille.NUMBER_SIGN), 1)

    def test_number_sign_returns_after_a_letter(self):
        cells, _ = braille.to_cells("a1b2")
        self.assertEqual(cells.count(braille.NUMBER_SIGN), 2)

    def test_space_is_an_empty_cell(self):
        cells, _ = braille.to_cells("a b")
        self.assertEqual(cells[1], ())

    def test_unknown_characters_are_reported(self):
        cells, skipped = braille.to_cells("ab@#")
        self.assertEqual(skipped, ["@", "#"])

    def test_width_matches_the_standard(self):
        cells, _ = braille.to_cells("abc")
        # three cells: two gaps of 6mm, plus one cell 2.5 + 1.5 wide
        self.assertAlmostEqual(braille.cells_width(cells), 2 * 6.0 + 2.5 + 1.5)

    def test_dot_positions_match_the_standard(self):
        cells, _ = braille.to_cells("b")           # dots 1 and 2
        places = braille.dot_positions(cells)
        self.assertEqual(places, [(0.0, 0.0), (0.0, -braille.DOT_GAP)])

    def test_the_dot_mesh_is_closed(self):
        """Every edge must be used by exactly two faces, or it will not print."""
        points, faces = braille._dome(0, 0, 0)
        edges = {}
        for face in faces:
            for index in range(len(face)):
                a, b = face[index], face[(index + 1) % len(face)]
                edges[frozenset((a, b))] = edges.get(frozenset((a, b)), 0) + 1
        odd = [edge for edge, count in edges.items() if count != 2]
        self.assertEqual(odd, [], "the dot has a hole in it")

    def test_the_dot_is_the_right_size(self):
        points, _ = braille._dome(0, 0, 0)
        highest = max(z for _, _, z in points)
        widest = max((x * x + y * y) ** 0.5 for x, y, _ in points)
        self.assertAlmostEqual(highest, braille.DOT_HEIGHT, places=6)
        self.assertAlmostEqual(widest, braille.DOT_ACROSS / 2.0, places=3)

    def test_the_dot_sinks_into_the_plate(self):
        points, _ = braille._dome(0, 0, 0)
        lowest = min(z for _, _, z in points)
        self.assertAlmostEqual(lowest, -braille.SINK, places=6)

    def test_capitals_only_when_asked(self):
        plain, _ = braille.to_cells("Ab")
        with_caps, _ = braille.to_cells("Ab", capitals=True)
        self.assertEqual(len(plain), 2)
        self.assertEqual(len(with_caps), 3)
        self.assertEqual(with_caps[0], braille.CAPITAL_SIGN)


class TestPrintSettings(unittest.TestCase):

    def setUp(self):
        self.settings = printing.PrintSettings()

    def test_defaults_are_sensible(self):
        self.assertEqual(self.settings.values["filling"], 15)
        self.assertEqual(self.settings.values["quality"], "normal")
        self.assertEqual(self.settings.values["supports"], "off")

    def test_number_setting(self):
        ok, _, extra = self.settings.set("filling", "45")
        self.assertTrue(ok)
        self.assertEqual(self.settings.values["filling"], 45)

    def test_number_out_of_range(self):
        ok, key, extra = self.settings.set("filling", "500")
        self.assertFalse(ok)
        self.assertEqual(key, "number_too_big")
        ok, key, _ = self.settings.set("walls", "0")
        self.assertFalse(ok)
        self.assertEqual(key, "number_too_small")

    def test_number_that_is_not_a_number(self):
        ok, key, _ = self.settings.set("filling", "lots")
        self.assertFalse(ok)
        self.assertEqual(key, "need_number")

    def test_choice_setting(self):
        ok, _, _ = self.settings.set("quality", "fine")
        self.assertTrue(ok)
        ok, key, extra = self.settings.set("quality", "amazing")
        self.assertFalse(ok)
        self.assertEqual(key, "setting_unknown_value")
        self.assertIn("fine", extra["choices"])

    def test_switch_setting(self):
        self.assertTrue(self.settings.set("vase", "on")[0])
        self.assertEqual(self.settings.values["vase"], "on")
        self.assertTrue(self.settings.set("vase", "off")[0])

    def test_overrides_write_prusaslicer_options(self):
        self.settings.set("filling", "45")
        self.settings.set("quality", "fine")
        self.settings.set("walls", "3")
        self.settings.set("supports", "on")
        options = self.settings.overrides()
        self.assertEqual(options["fill_density"], "45%")
        self.assertEqual(options["layer_height"], "0.15")
        self.assertEqual(options["perimeters"], "3")
        self.assertEqual(options["support_material"], "1")

    def test_full_filling_becomes_straight_lines(self):
        self.settings.set("filling", "100")
        self.settings.set("pattern", "honeycomb")
        self.assertEqual(self.settings.overrides()["fill_pattern"], "rectilinear")

    def test_supports_from_the_bed_only(self):
        self.settings.set("supports", "bed")
        options = self.settings.overrides()
        self.assertEqual(options["support_material_buildplate_only"], "1")

    def test_speed_scales_several_options(self):
        self.settings.set("speed", "slow")
        options = self.settings.overrides()
        self.assertEqual(options["perimeter_speed"], "27")   # 45 * 0.6
        self.assertEqual(options["infill_speed"], "48")      # 80 * 0.6

    def test_heat_left_alone_by_default(self):
        self.assertNotIn("temperature", self.settings.overrides())
        self.settings.set("heat", "215")
        self.assertEqual(self.settings.overrides()["temperature"], "215")

    def test_vase_mode_turns_off_the_things_that_fight_it(self):
        self.settings.set("vase", "on")
        options = self.settings.overrides()
        self.assertEqual(options["spiral_vase"], "1")
        self.assertEqual(options["perimeters"], "1")
        self.assertEqual(options["top_solid_layers"], "0")

    def test_profile_is_copied_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "printer.ini"
            source.write_text("fill_density = 15%\nlayer_height = 0.2\n"
                              "nozzle_diameter = 0.4\n", encoding="utf-8")
            before = source.read_text(encoding="utf-8")

            self.settings.set("filling", "60")
            target = self.settings.write_profile(source, Path(folder) / "work")

            self.assertEqual(source.read_text(encoding="utf-8"), before)
            written = target.read_text(encoding="utf-8")
            self.assertIn("fill_density = 60%", written)
            self.assertIn("nozzle_diameter = 0.4", written)

    def test_spoken_time(self):
        self.assertEqual(printing._spoken_time("2h 30m 12s"),
                         "2 hours and 31 minutes")
        self.assertEqual(printing._spoken_time("45s"), "1 minute")
        self.assertEqual(printing._spoken_time("1h 0m"), "1 hour")

    def test_gcode_report_reads_the_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            gcode = Path(folder) / "m.gcode"
            gcode.write_text(
                "G1 X0 Y0\n"
                "; estimated printing time (normal mode) = 1h 12m 30s\n"
                "; filament used [g] = 14.62\n"
                "; filament used [mm] = 4900.3\n"
                "; total layers count = 100\n", encoding="utf-8")
            report = printing.gcode_report(gcode)
            self.assertEqual(report["grams"], 14.6)
            self.assertEqual(report["layers"], 100)
            self.assertIn("hour", report["time"])

    def test_slicer_problems_are_explained_plainly(self):
        message = printing._slicer_problem("Object is outside the print area")
        self.assertIn("too big", message)
        message = printing._slicer_problem("Mesh is not manifold")
        self.assertIn("gap", message)


class TestModel(unittest.TestCase):

    def test_names_never_clash(self):
        model = Model()
        first = model.add_part("cube")
        second = model.add_part("cube")
        self.assertEqual(first.name, "cube")
        self.assertEqual(second.name, "cube2")

    def test_undo_and_redo(self):
        model = Model()
        model.change("add a cube")
        model.add_part("cube")
        self.assertEqual(len(model.items), 1)
        model.undo()
        self.assertEqual(len(model.items), 0)
        model.redo()
        self.assertEqual(len(model.items), 1)

    def test_undo_on_an_empty_history(self):
        self.assertIsNone(Model().undo())

    def test_removing_a_part_removes_what_was_built_from_it(self):
        model = Model()
        model.add_part("cube")
        model.add_part("ball")
        model.add_group("join", ["cube", "ball"], name="both")
        model.remove("cube")
        self.assertNotIn("both", model.items)
        self.assertIn("ball", model.items)

    def test_renaming_updates_groups(self):
        model = Model()
        model.add_part("cube")
        model.add_part("ball")
        model.add_group("join", ["cube", "ball"], name="both")
        model.rename("cube", "base")
        self.assertEqual(model.items["both"].members, ["base", "ball"])

    def test_top_level_hides_parts_inside_a_group(self):
        model = Model()
        model.add_part("cube")
        model.add_part("ball")
        model.add_group("join", ["cube", "ball"], name="both")
        self.assertEqual(model.top_level(), ["both"])

    def test_rough_size(self):
        model = Model()
        part = model.add_part("cube", {"width": 40, "length": 20, "height": 10})
        self.assertEqual(part.rough_size(), [40, 20, 10])

    def test_rough_size_grows_with_rounding(self):
        model = Model()
        part = model.add_part("cube", {"width": 40, "length": 20, "height": 10})
        part.round_by = 3
        self.assertEqual(part.rough_size(), [46, 26, 16])

    def test_overall_size_counts_position(self):
        model = Model()
        model.add_part("cube", {"width": 20, "length": 20, "height": 20})
        second = model.add_part("cube", {"width": 20, "length": 20, "height": 20})
        second.pos = [30, 0, 0]
        self.assertEqual(model.rough_size()[0], 50)

    def test_saving_and_opening(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Model()
            model.add_part("cube", {"width": 33})
            model.add_part("ball")
            model.save(folder, "keyring")

            again = Model()
            self.assertTrue(again.load(folder, "keyring"))
            self.assertEqual(list(again.items), ["cube", "ball"])
            self.assertEqual(again.items["cube"].params["width"], 33)

    def test_opening_something_that_is_not_there(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(Model().load(folder, "nothing"))

    def test_project_list(self):
        with tempfile.TemporaryDirectory() as folder:
            Model().save(folder, "one")
            Model().save(folder, "two")
            names = [n for n, _ in Model.saved_projects(folder)]
            self.assertEqual(names, ["one", "two"])

    def test_describe_says_something_useful(self):
        model = Model()
        part = model.add_part("cube", {"width": 40, "length": 20, "height": 10})
        part.pos = [10, 0, 0]
        text = model.describe_item(part)
        self.assertIn("cube", text)
        self.assertIn("40", text)
        self.assertIn("right", text)

    def test_find_prefers_the_newest_of_a_shape(self):
        model = Model()
        model.add_part("plate")           # named "plate"
        second = model.add_part("plate")  # named "plate2"
        self.assertIs(model.find("plate"), second)

    def test_find_by_exact_name(self):
        model = Model()
        model.add_part("cube", name="body")
        model.add_part("cube")
        self.assertEqual(model.find("body").name, "body")

    def test_find_by_a_synonym(self):
        model = Model()
        part = model.add_part("cube")
        self.assertIs(model.find("box"), part)

    def test_find_gives_up_politely(self):
        self.assertIsNone(Model().find("elephant"))

    def test_module_names_are_safe_for_openscad(self):
        self.assertEqual(Model._safe("my part!"), "part_my_part_")
        self.assertEqual(Model._safe("2nd"), "part_2nd")

    def test_module_names_never_collide_with_openscad(self):
        """A part called cube must not turn into a module that calls itself."""
        for builtin in ("cube", "sphere", "cylinder", "text", "circle",
                        "square", "polygon", "union", "difference"):
            self.assertNotEqual(Model._safe(builtin), builtin)


@unittest.skipIf(OPENSCAD is None, "OpenSCAD is not installed here")
class TestOpenScadReallyCompiles(unittest.TestCase):
    """
    The tests that matter most: every shape and every treatment must turn
    into a real, printable STL file.
    """

    def build(self, model):
        ok, problem, size = compile_scad(model.scad())
        self.assertTrue(ok, f"OpenSCAD refused this model:\n{problem}\n\n"
                            f"{model.scad()}")
        self.assertGreater(size, 200, "The shape file came out empty.")

    def test_every_shape_compiles(self):
        for name in shapes.SHAPES:
            with self.subTest(shape=name):
                model = Model()
                params = {"words": "ab"} if name in ("text", "braille") else {}
                model.add_part(name, params)
                self.build(model)

    def test_shapes_with_awkward_numbers(self):
        cases = [
            ("pyramid", {"sides": 3}),
            ("pyramid", {"sides": 12}),
            ("prism", {"sides": 3}),
            ("star", {"points": 3}),
            ("star", {"points": 12}),
            ("tube", {"across": 10, "thick": 4}),      # walls nearly meet
            ("donut", {"across": 20, "thick": 19}),    # ring nearly fills itself
            ("cube", {"width": 0.5, "length": 0.5, "height": 0.5}),
            ("ball", {"across": 300}),
        ]
        for shape, params in cases:
            with self.subTest(shape=shape, params=params):
                model = Model()
                model.add_part(shape, params)
                self.build(model)

    def test_moving_and_turning(self):
        model = Model()
        part = model.add_part("cube", {"width": 20, "length": 20, "height": 20})
        part.pos = [10, -5, 3]
        part.turn = [0, 45, 90]
        self.build(model)

    def test_rounding(self):
        model = Model()
        part = model.add_part("cube", {"width": 20, "length": 20, "height": 20})
        part.round_by = 3
        self.build(model)

    def test_hollowing(self):
        model = Model()
        part = model.add_part("cube", {"width": 30, "length": 30, "height": 30})
        part.hollow = 2
        self.build(model)

    def test_mirroring_and_scaling(self):
        model = Model()
        part = model.add_part("wedge")
        part.mirror = "x"
        part.scale = [2, 1, 0.5]
        self.build(model)

    def test_copies_in_a_row(self):
        model = Model()
        part = model.add_part("cube", {"width": 10, "length": 10, "height": 10})
        part.repeat = {"count": 5, "gap": 20, "dir": "right"}
        self.build(model)

    def test_copies_in_a_circle(self):
        model = Model()
        part = model.add_part("rod", {"across": 5, "height": 20})
        part.circle_repeat = {"count": 8, "across": 60}
        self.build(model)

    def test_join(self):
        model = Model()
        model.add_part("cube", {"width": 30, "length": 30, "height": 10})
        ball = model.add_part("ball", {"across": 20})
        ball.pos = [0, 0, 8]
        model.add_group("join", ["cube", "ball"], name="both")
        self.build(model)

    def test_cut_makes_a_hole(self):
        model = Model()
        model.add_part("plate", {"width": 40, "length": 40, "height": 5})
        model.add_part("rod", {"across": 8, "height": 20})
        model.add_group("cut", ["plate", "rod"], name="holed")
        self.build(model)

    def test_overlap(self):
        model = Model()
        model.add_part("cube", {"width": 30, "length": 30, "height": 30})
        model.add_part("ball", {"across": 38})
        model.add_group("overlap", ["cube", "ball"], name="rounded")
        self.build(model)

    def test_groups_can_be_combined_again(self):
        model = Model()
        model.add_part("cube", {"width": 40, "length": 40, "height": 10})
        model.add_part("rod", {"across": 8, "height": 30})
        model.add_group("cut", ["cube", "rod"], name="holed")
        ball = model.add_part("ball", {"across": 15})
        ball.pos = [0, 0, 10]
        model.add_group("join", ["holed", "ball"], name="final")
        self.build(model)

    def test_a_rounded_group(self):
        model = Model()
        model.add_part("cube", {"width": 30, "length": 30, "height": 10})
        model.add_part("cube", {"width": 10, "length": 10, "height": 30})
        group = model.add_group("join", ["cube", "cube2"], name="tee")
        group.round_by = 2
        self.build(model)

    def test_braille_compiles_and_is_the_right_size(self):
        model = Model()
        model.add_part("braille", {"words": "nino 42"})
        self.build(model)

    def test_text_compiles(self):
        model = Model()
        model.add_part("text", {"words": "Nino", "height": 12, "thick": 4})
        self.build(model)

    def test_a_whole_name_badge(self):
        """The badge from lesson 3, built exactly as a student would."""
        model = Model()
        model.add_part("plate", {"width": 90, "length": 30, "height": 3})
        dots = model.add_part("braille", {"words": "nino", "thick": 1})
        dots.pos = [0, 0, 2]
        model.add_group("join", ["plate", "braille"], name="badge")
        self.build(model)

    def test_several_loose_parts_all_appear(self):
        model = Model()
        model.add_part("cube")
        second = model.add_part("ball")
        second.pos = [40, 0, 0]
        self.build(model)


class TestHelp(unittest.TestCase):

    def test_every_menu_topic_exists(self):
        for line in help_mod.MENU:
            match = line.strip()
            if not match.startswith("help "):
                continue
            name = match.split()[1]
            self.assertIsNotNone(help_mod.topic(name),
                                 f"The menu offers '{name}' but there is no topic.")

    def test_topics_are_short_enough_to_listen_to(self):
        for name, lines in help_mod.TOPICS.items():
            with self.subTest(topic=name):
                self.assertLessEqual(len(lines), 14,
                                     f"Topic '{name}' is too long to hear.")

    def test_help_menu_is_short(self):
        self.assertLessEqual(len(help_mod.MENU), 18)

    def test_unknown_topic(self):
        self.assertIsNone(help_mod.topic("elephants"))

    def test_all_topic_covers_everything(self):
        lines = help_mod.topic("all")
        for name in help_mod.TOPICS:
            self.assertIn(f"--- {name} ---", lines)

    def test_lesson_commands_are_understood(self):
        """Every command a lesson tells a student to type must actually work."""
        for lesson in help_mod.LESSONS:
            model = Model()
            for text, command in lesson["steps"]:
                if not command:
                    continue
                with self.subTest(lesson=lesson["title"], command=command):
                    actions = parser.parse(command, model)
                    self.assertTrue(actions, f"'{command}' parsed to nothing")
                    kinds = [a["do"] for a in actions]
                    self.assertNotIn("unknown", kinds,
                                     f"'{command}' is not understood: {actions}")
                    # Keep the little model in step, so later commands in the
                    # lesson can refer to parts by name.
                    for action in actions:
                        if action["do"] == "shape":
                            model.add_part(action["shape"])
                        elif action["do"] == "combine":
                            members = [n for n in (action.get("a"), action.get("b"))
                                       if n in model.items]
                            if len(members) == 2:
                                model.add_group(action["op"], members)


class TestTexts(unittest.TestCase):

    def test_every_message_used_in_the_app_exists(self):
        from bgera import texts
        source = Path(__file__).resolve().parent.parent / "bgera"
        used = set()
        pattern = __import__("re").compile(
            r"""(?:self\.tell|say|\bt)\(\s*["']([a-z_]+)["']""")
        for path in source.glob("*.py"):
            used.update(pattern.findall(path.read_text(encoding="utf-8")))
        missing = sorted(k for k in used if k not in texts.EN)
        self.assertEqual(missing, [], f"These messages have no English text: {missing}")

    def test_georgian_falls_back_to_english(self):
        from bgera import texts
        texts.set_language(2)
        try:
            self.assertEqual(texts.t("shape_added", shape="cube", name="cube"),
                             "Added cube, named cube.")
        finally:
            texts.set_language(1)

    def test_a_broken_translation_does_not_crash(self):
        from bgera import texts
        texts.KA["shape_added"] = "{nonsense}"
        texts.set_language(2)
        try:
            self.assertIn("cube", texts.t("shape_added", shape="cube", name="cube"))
        finally:
            texts.KA.pop("shape_added")
            texts.set_language(1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
