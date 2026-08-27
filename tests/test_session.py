#!/usr/bin/env python
# coding: utf-8
"""
Whole sessions, typed the way a student would type them.

The printer is not here, so a small stand-in stands in for PrusaSlicer.  The
modelling half is real: OpenSCAD runs and a real shape file comes out.

Run from the app folder:      python -m tests.test_session
"""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bgera import app as app_mod
try:
    from tests.helpers import OPENSCAD, make_stub_slicer
except ImportError:          # discovered from inside the tests folder
    from helpers import OPENSCAD, make_stub_slicer

PROFILE = """[print:test]
layer_height = 0.2
fill_density = 15%
fill_pattern = cubic
perimeters = 2
nozzle_diameter = 0.4
"""


@unittest.skipIf(OPENSCAD is None, "OpenSCAD is not installed here")
class TestSession(unittest.TestCase):
    """Type a series of commands and check what the student would hear."""

    @classmethod
    def setUpClass(cls):
        cls.folder = Path(tempfile.mkdtemp())
        slicer = make_stub_slicer(cls.folder)

        configs = cls.folder / "printer_configs"
        configs.mkdir()
        (configs / "xmax3.ini").write_text(PROFILE)

        cls.saved = (app_mod.OPENSCAD, app_mod.SLICER, app_mod.PRINTER_CONFIGS,
                     app_mod.WORK_DIR, app_mod.PROJECTS_DIR, app_mod.DOWNLOADS,
                     app_mod.CONFIG_PATH)
        app_mod.OPENSCAD = OPENSCAD
        app_mod.SLICER = slicer
        app_mod.PRINTER_CONFIGS = configs
        app_mod.WORK_DIR = cls.folder / "work"
        app_mod.PROJECTS_DIR = cls.folder / "projects"
        app_mod.DOWNLOADS = cls.folder / "downloads"
        app_mod.CONFIG_PATH = cls.folder / "config.json"
        app_mod.DOWNLOADS.mkdir()

    @classmethod
    def tearDownClass(cls):
        (app_mod.OPENSCAD, app_mod.SLICER, app_mod.PRINTER_CONFIGS,
         app_mod.WORK_DIR, app_mod.PROJECTS_DIR, app_mod.DOWNLOADS,
         app_mod.CONFIG_PATH) = cls.saved
        shutil.rmtree(cls.folder, ignore_errors=True)

    def new_app(self):
        config = {"lan": 1, "printers": [{"name": "class", "model": "xmax3",
                                          "ip": "127.0.0.1", "port": "7125"}],
                  "current_printer": "class"}
        instance = app_mod.BgeraPrint(config)
        instance.stl_path = self.folder / "downloads" / "m.stl"
        instance.scad_path = self.folder / "downloads" / "m.scad"
        instance.gcode_path = self.folder / "downloads" / "m.gcode"
        return instance

    def type(self, instance, *lines):
        """Type some commands and give back everything the student heard."""
        heard = io.StringIO()
        with redirect_stdout(heard):
            for line in lines:
                instance.handle(line)
        return heard.getvalue()

    # -- the ordinary path --------------------------------------------------

    def test_a_cube_from_start_to_finish(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "width 30 length 20 height 10", "size")
        self.assertIn("Added cube", heard)
        self.assertIn("width 30", heard)
        self.assertIn("30 wide, 20 long and 10 tall", heard)

        heard = self.type(bgera, "prepare")
        self.assertIn("1 hour", heard)
        self.assertIn("14.6", heard)
        self.assertTrue(bgera.prepared)
        self.assertTrue(bgera.gcode_path.exists())

    def test_printing_needs_two_goes(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "prepare")
        heard = self.type(bgera, "print")
        self.assertIn("print again", heard)
        # The printer is not really there, so the second go fails politely
        # rather than crashing.
        heard = self.type(bgera, "print")
        self.assertIn("cannot reach", heard.lower() + " ")

    def test_you_cannot_print_before_preparing(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "print")
        self.assertIn("Prepare the model first", heard)

    def test_changing_a_setting_means_preparing_again(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "prepare")
        self.assertTrue(bgera.prepared)
        self.type(bgera, "filling 60")
        self.assertFalse(bgera.prepared)

    def test_settings_reach_the_profile(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "filling 60", "quality fine", "walls 4",
                  "supports on", "prepare")
        profile = (app_mod.WORK_DIR / "current_print.ini").read_text()
        self.assertIn("fill_density = 60%", profile)
        self.assertIn("layer_height = 0.15", profile)
        self.assertIn("perimeters = 4", profile)
        self.assertIn("support_material = 1", profile)
        self.assertIn("nozzle_diameter = 0.4", profile)

    def test_the_shipped_profile_is_never_changed(self):
        source = app_mod.PRINTER_CONFIGS / "xmax3.ini"
        before = source.read_text()
        bgera = self.new_app()
        self.type(bgera, "cube", "filling 90", "prepare")
        self.assertEqual(source.read_text(), before)

    # -- building things ----------------------------------------------------

    def test_hole_through_a_plate(self):
        bgera = self.new_app()
        heard = self.type(bgera, "plate", "width 40 length 40 height 5",
                          "rod", "across 8 height 20", "cut rod from plate")
        self.assertIn("Cut rod out of plate", heard)
        heard = self.type(bgera, "prepare")
        self.assertNotIn("failed", heard.lower())

    def test_stacking_puts_it_at_the_right_height(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "width 40 length 40 height 20",
                  "ball", "across 20", "put ball on cube")
        ball = bgera.model.items["ball"]
        # 20/2 + 20/2, less the hair of overlap that keeps a joined pair
        # one solid rather than two objects touching on a plane.
        self.assertAlmostEqual(ball.pos[2], 20 - app_mod.OVERLAP)
        self.assertLess(app_mod.OVERLAP, 0.1, "the overlap must not be felt")

    def test_a_stacked_pair_joins_into_one_solid(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "width 20 length 20 height 20",
                          "cube", "width 20 length 20 height 20",
                          "put cube2 on cube", "join", "prepare")
        self.assertNotIn("failed", heard.lower())
        self.assertNotIn("gap", heard.lower())

    def test_a_braille_badge(self):
        bgera = self.new_app()
        heard = self.type(bgera, "plate", "width 90 length 30 height 3",
                          "braille nino", "put braille on plate", "join")
        self.assertIn("Braille for 'nino' made", heard)
        self.assertIn("4 cells", heard)
        self.assertIn("Joined", heard)
        heard = self.type(bgera, "prepare")
        self.assertNotIn("failed", heard.lower())
        self.assertTrue(bgera.stl_path.exists())
        self.assertGreater(bgera.stl_path.stat().st_size, 1000)

    def test_braille_says_which_characters_it_cannot_do(self):
        bgera = self.new_app()
        heard = self.type(bgera, "braille nino@home")
        self.assertIn("cannot write", heard)
        self.assertIn("@", heard)

    def test_undo_puts_everything_back(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "width 50")
        self.assertEqual(bgera.model.items["cube"].params["width"], 50)
        heard = self.type(bgera, "undo")
        self.assertIn("Undone", heard)
        self.assertNotIn("width", bgera.model.items["cube"].params)
        self.type(bgera, "undo")
        self.assertTrue(bgera.model.is_empty())
        heard = self.type(bgera, "undo")
        self.assertIn("nothing left to undo", heard)

    def test_naming_and_renaming(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "rename cube body", "body width 55")
        self.assertIn("body", bgera.model.items)
        self.assertEqual(bgera.model.items["body"].params["width"], 55)

    def test_saving_and_opening_a_project(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "width 44", "ball", "save keyring")
        fresh = self.new_app()
        heard = self.type(fresh, "open keyring")
        self.assertIn("Opened keyring", heard)
        self.assertEqual(fresh.model.items["cube"].params["width"], 44)

    def test_projects_list(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "save one", "save two")
        heard = self.type(bgera, "projects")
        self.assertIn("one", heard)
        self.assertIn("two", heard)

    def test_a_ready_made_model(self):
        bgera = self.new_app()
        app_mod.MODELS.mkdir(parents=True, exist_ok=True)
        heard = self.type(bgera, "lion")
        # The real file may not be here in the test folder; either answer
        # is polite, neither is a crash.
        self.assertTrue("Using the built in lion" in heard
                        or "missing" in heard)

    # -- being kind about mistakes -------------------------------------------

    def test_a_typo_gets_a_suggestion(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cbue")
        self.assertIn("Did you mean 'cube'", heard)

    def test_a_measurement_out_of_range(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "width 9000")
        self.assertIn("at most", heard)
        self.assertNotIn("width", bgera.model.items["cube"].params)

    def test_measuring_before_making_anything(self):
        bgera = self.new_app()
        heard = self.type(bgera, "width 30")
        self.assertIn("not made anything yet", heard)

    def test_naming_a_part_that_is_not_there(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "remove elephant")
        self.assertIn("no part named elephant", heard)

    def test_nothing_ever_throws_the_student_out(self):
        bgera = self.new_app()
        awkward = ["", "   ", "!!!", "cube cube cube", "move", "turn",
                   "put", "join", "cut", "width", "height 0",
                   "filling abc", "quality wonderful", "save", "open",
                   "remove", "rename", "lesson 99", "help nonsense",
                   "copy", "ring of", "text", "braille", "-5", "999999",
                   "p", "w20l20h20", "p45cubicn5", "a:cube,w20 ++ b:ball,d10"]

        for line in awkward:
            with self.subTest(line=line):
                heard = io.StringIO()
                with redirect_stdout(heard):
                    try:
                        bgera.handle(line)
                    except Exception as problem:
                        self.fail(f"'{line}' crashed the app: {problem!r}")

    # -- playing a session file -------------------------------------------------

    def test_a_session_file_is_all_understood(self):
        """
        Every line of every session file must be a real command.

        These files are what you replay to hear how the app sounds, so a
        stale line in one is worse than useless: it teaches you that a
        command works when it does not.
        """
        from bgera import parser as parser_mod
        from bgera.model import Model
        from tests.play import drives_menus, lines_from

        folder = Path(__file__).resolve().parent
        found = [p for p in sorted(folder.glob("session_*.txt"))
                 if not drives_menus(p)]
        self.assertTrue(found, "there are no typed session files to check")

        for path in found:
            model = Model()
            for line in lines_from(path):
                with self.subTest(file=path.name, line=line):
                    actions = parser_mod.parse(line, model)
                    self.assertTrue(actions, f"'{line}' means nothing")
                    self.assertNotIn("unknown", [a["do"] for a in actions],
                                     f"'{line}' is not understood")
                    for action in actions:
                        if action["do"] == "shape":
                            model.add_part(action["shape"])
                        elif action["do"] == "combine":
                            both = [n for n in (action.get("a"), action.get("b"))
                                    if n in model.items]
                            if len(both) == 2:
                                model.add_group(action["op"], both)

    def test_a_menu_session_file_really_builds_the_model(self):
        """
        A menu session file cannot be checked line by line, because its
        lines are answers to menus rather than commands. So play it for
        real and look at what came out the other end.
        """
        from tests import play as play_mod

        path = Path(__file__).resolve().parent / "session_menus.txt"
        if not path.exists():
            self.skipTest("there is no menu session file")

        built = {}
        real_build = app_mod.BgeraPrint

        class Watched(real_build):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                built["app"] = self

        app_mod.BgeraPrint = Watched
        heard = io.StringIO()
        try:
            with redirect_stdout(heard):
                play_mod.play(path, echo=False, fresh=True)
        finally:
            app_mod.BgeraPrint = real_build

        said = heard.getvalue()
        self.assertNotIn("I do not understand", said)
        self.assertNotIn("Something went wrong", said)
        self.assertNotIn("I do not know that one", said)

        app = built.get("app")
        self.assertIsNotNone(app, "the app never started")
        self.assertIn("plate", app.model.items)
        self.assertIn("braille", app.model.items)
        self.assertEqual(app.model.items["plate"].params,
                         {"width": 90, "length": 30, "height": 3})
        self.assertEqual(app.model.items["braille"].params["words"], "luka")
        # the braille was sat on the plate and the two were joined
        self.assertGreater(app.model.items["braille"].pos[2], 0)
        self.assertEqual(len(app.model.top_level()), 1)
        self.assertEqual(app.settings.values["walls"], 3)

    def test_play_ignores_comments_and_blank_lines(self):
        from tests.play import lines_from
        scratch = self.folder / "sample.txt"
        scratch.write_text("# a note\n\ncube\n   \n  width 20  \n",
                           encoding="utf-8")
        self.assertEqual(lines_from(scratch), ["cube", "width 20"])

    # -- surviving a hostile computer -------------------------------------------

    def test_setup_survives_the_answers_running_out(self):
        """
        Piping a file into a fresh copy runs out of input at the first setup
        question. That used to end in a raw Python traceback -- a horrible
        thing to hand anybody, and a baffling one to hear read aloud.
        """
        import builtins

        real = builtins.input

        def no_more(prompt=""):
            raise EOFError

        builtins.input = no_more
        saved = app_mod.CONFIG_PATH
        app_mod.CONFIG_PATH = self.folder / "brand-new-config.json"
        heard = io.StringIO()
        try:
            with redirect_stdout(heard):
                config = app_mod.ask_setup()
        except EOFError:
            self.fail("setup fell over when the answers ran out")
        finally:
            builtins.input = real
            app_mod.CONFIG_PATH = saved

        self.assertIn("lan", config)
        self.assertIn("printers", config)
        self.assertTrue(config["printers"][0]["port"],
                        "it should fall back to a port rather than an empty one")
        self.assertNotIn("Traceback", heard.getvalue())

    def test_setup_survives_ctrl_c(self):
        import builtins
        real = builtins.input
        builtins.input = lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt)
        saved = app_mod.CONFIG_PATH
        app_mod.CONFIG_PATH = self.folder / "another-new-config.json"
        try:
            with redirect_stdout(io.StringIO()):
                config = app_mod.ask_setup()
        except KeyboardInterrupt:
            self.fail("setup fell over on Ctrl+C")
        finally:
            builtins.input = real
            app_mod.CONFIG_PATH = saved
        self.assertIn("printers", config)

    def test_setup_does_not_loop_forever_on_a_wrong_answer(self):
        """Something feeding the same wrong answer must not spin."""
        import builtins
        real = builtins.input
        builtins.input = lambda prompt="": "not a language"
        saved = app_mod.CONFIG_PATH
        app_mod.CONFIG_PATH = self.folder / "third-new-config.json"
        try:
            with redirect_stdout(io.StringIO()):
                config = app_mod.ask_setup()
        finally:
            builtins.input = real
            app_mod.CONFIG_PATH = saved
        self.assertIn("printers", config)

    def test_it_finds_somewhere_writable_when_its_own_folder_is_not(self):
        """
        The exe keeps config.json, projects and work beside itself, so it can
        be carried about on a memory stick. Dropped into Program Files it
        cannot write there, and it used to crash at startup -- before any of
        the friendly error handling got a chance to run.
        """
        saved = app_mod.beside_the_app
        # A path under a regular FILE: mkdir fails for everybody, root too.
        unusable = Path(__file__).resolve() / "BgeraPrint"
        app_mod.beside_the_app = lambda: unusable
        try:
            chosen = app_mod.somewhere_writable()
        finally:
            app_mod.beside_the_app = saved

        self.assertNotEqual(chosen, unusable)
        chosen.mkdir(parents=True, exist_ok=True)
        probe = chosen / "probe.txt"
        probe.write_text("x", encoding="utf-8")     # must not raise
        probe.unlink()

    def test_it_uses_its_own_folder_when_that_works(self):
        """The fallback must not kick in when there is nothing wrong."""
        saved = app_mod.beside_the_app
        app_mod.beside_the_app = lambda: self.folder / "normal"
        try:
            self.assertEqual(app_mod.somewhere_writable(),
                             self.folder / "normal")
        finally:
            app_mod.beside_the_app = saved

    def test_starting_up_where_no_folder_can_be_made_says_so(self):
        """It should explain itself rather than end in a traceback."""
        saved_work, saved_projects = app_mod.WORK_DIR, app_mod.PROJECTS_DIR
        unusable = Path(__file__).resolve() / "nope"
        app_mod.WORK_DIR = unusable / "work"
        app_mod.PROJECTS_DIR = unusable / "projects"
        heard = io.StringIO()
        try:
            with redirect_stdout(heard):
                bgera = self.new_app()
        except Exception as problem:
            self.fail(f"it fell over instead of explaining: {problem!r}")
        finally:
            app_mod.WORK_DIR, app_mod.PROJECTS_DIR = saved_work, saved_projects

        self.assertIsNotNone(bgera)
        said = heard.getvalue()
        self.assertIn("cannot make a folder", said)
        self.assertIn("write to", said)

    # -- the check command -----------------------------------------------------

    def test_check_reports_a_working_setup(self):
        bgera = self.new_app()
        heard = self.type(bgera, "check")
        self.assertIn("the modelling program: working", heard)
        self.assertIn("the slicing program: working", heard)
        self.assertIn("making a shape: working", heard)
        self.assertIn("getting a shape ready to print: working", heard)
        # No printer is really there, and this test folder has no ready
        # made models, so those two are expected to fail and nothing else.
        self.assertIn("reaching the printer: NOT working", heard)
        self.assertIn("checks failed", heard)
        self.assertEqual(heard.count("NOT working"), 2, heard)

    def test_check_names_the_broken_part(self):
        bgera = self.new_app()
        saved = app_mod.OPENSCAD
        app_mod.OPENSCAD = Path("does-not-exist-openscad")
        try:
            heard = self.type(bgera, "check")
        finally:
            app_mod.OPENSCAD = saved
        self.assertIn("the modelling program: NOT working", heard)
        self.assertIn("does-not-exist-openscad", heard)

    def test_check_leaves_no_mess(self):
        bgera = self.new_app()
        self.type(bgera, "check")
        for name in ("check.scad", "check.stl", "check.gcode"):
            self.assertFalse((app_mod.WORK_DIR / name).exists(),
                             f"{name} was left behind")

    # -- help and lessons ------------------------------------------------------

    def test_help_menu_and_a_topic(self):
        bgera = self.new_app()
        heard = self.type(bgera, "help")
        self.assertIn("Help topics", heard)
        heard = self.type(bgera, "help shapes")
        self.assertIn("cube", heard)
        self.assertNotIn("Help topics", heard)

    def test_the_old_i_command_still_gives_help(self):
        bgera = self.new_app()
        heard = self.type(bgera, "i")
        self.assertIn("Help topics", heard)

    def test_a_lesson_moves_on_when_you_get_it_right(self):
        bgera = self.new_app()
        heard = self.type(bgera, "lesson 1")
        self.assertIn("Lesson 1", heard)
        self.assertIn("Type: cube", heard)

        heard = io.StringIO()
        with redirect_stdout(heard):
            expected = bgera._lesson_expects()
            bgera.handle("cube")
            bgera._lesson_check("cube", expected)
        self.assertIn("That is right", heard.getvalue())
        self.assertEqual(bgera.lesson[1], 1)

    def test_leaving_a_lesson(self):
        bgera = self.new_app()
        self.type(bgera, "lesson 2")
        heard = self.type(bgera, "stop")
        self.assertIn("left the lesson", heard)
        self.assertIsNone(bgera.lesson)
        self.assertTrue(bgera.running)   # stop left the lesson, not the app

    def test_every_lesson_can_be_played_through(self):
        for number in range(1, 6):
            with self.subTest(lesson=number):
                bgera = self.new_app()
                from bgera import help as help_mod
                self.type(bgera, f"lesson {number}")
                lesson = help_mod.LESSONS[number - 1]
                for text, command in lesson["steps"]:
                    line = command or "next"
                    heard = self.type(bgera, line)
                    self.assertNotIn("do not understand", heard)
                    self.assertNotIn("Did you mean", heard)

    # -- the old ways still work ------------------------------------------------

    def test_old_short_dimensions(self):
        bgera = self.new_app()
        self.type(bgera, "cube", "w20l30h10")
        self.assertEqual(bgera.model.items["cube"].params,
                         {"width": 20, "length": 30, "height": 10})

    def test_old_print_command(self):
        bgera = self.new_app()
        heard = self.type(bgera, "cube", "p45cubicn5")
        self.assertEqual(bgera.settings.values["filling"], 45)
        self.assertEqual(bgera.settings.values["copies"], 5)
        self.assertIn("1 hour", heard)

    def test_old_one_line_model(self):
        bgera = self.new_app()
        heard = self.type(bgera, "base:cube,w40,l40,h10 ++ top:sphere,d30,z10")
        self.assertIn("base", bgera.model.items)
        self.assertIn("top", bgera.model.items)
        self.assertEqual(bgera.model.top_level(), ["shape1"])
        heard = self.type(bgera, "prepare")
        self.assertNotIn("failed", heard.lower())

    def test_old_difference_line(self):
        bgera = self.new_app()
        self.type(bgera, "body:cube,w40,l40,h40 -- hole:cylinder,d10,h60")
        group = bgera.model.items["shape1"]
        self.assertEqual(group.operation, "cut")
        heard = self.type(bgera, "prepare")
        self.assertNotIn("failed", heard.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
