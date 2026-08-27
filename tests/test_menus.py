#!/usr/bin/env python
# coding: utf-8
"""
The arrow key interface.

Every test here drives the menus with pretend keypresses, so the whole
interface is exercised without a terminal.  That is the only way it can be
tested at all, and it means a broken menu is caught here rather than by a
student sitting in front of a silent screen.

Run from the app folder:      python -m tests.test_menus
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bgera import keys, menu
from bgera import app as app_mod
from bgera.guided import Guided

UP, DOWN, ENTER, ESC = keys.UP, keys.DOWN, keys.ENTER, keys.ESCAPE


class WithPretendKeys(unittest.TestCase):
    """Base class: press these keys, and give back everything that was said."""

    def setUp(self):
        keys.stop_pretending()
        # Say there IS a keyboard: these tests drive the app with pretend
        # keys, but their stdout is redirected, so the app would otherwise
        # decide it was being fed from a file and switch to typed numbers.
        keys.set_keyboard(True)
        menu.set_style("speak")
        menu.set_number_mode("arrows")

    def tearDown(self):
        keys.stop_pretending()
        keys.set_keyboard(None)

    def press(self, keystrokes, work):
        keys.pretend_keys(keystrokes)
        heard = io.StringIO()
        result = None
        with redirect_stdout(heard):
            try:
                result = work()
            except keys.NoKeyboard:
                pass
        return result, heard.getvalue()

    def press_timed(self, plan, work):
        """
        Press keys with a fake clock, so acceleration can be steered.

        plan is [(key, seconds_since_the_last_one), ...]. A gap of 0.5 is a
        student pressing again; 0.03 is the keyboard repeating under a held
        finger. Without this every test would look like a held key, because
        pretend keys arrive with no time between them at all.
        """
        import time as real_time

        clock = [0.0]
        menu._now = lambda: clock[0]
        keys.pretend_keys([k for k, _ in plan])
        gaps = [g for _, g in plan]
        real_read = keys.read_key

        def read():
            if gaps:
                clock[0] += gaps.pop(0)
            return real_read()

        keys.read_key = read
        menu.keys_mod.read_key = read
        heard = io.StringIO()
        result = None
        try:
            with redirect_stdout(heard):
                try:
                    result = work()
                except keys.NoKeyboard:
                    pass
        finally:
            keys.read_key = real_read
            menu.keys_mod.read_key = real_read
            menu._now = lambda: real_time.monotonic()
        return result, heard.getvalue()

    @staticmethod
    def slow(key, times=1):
        """Separate, deliberate presses."""
        return [(key, 0.5)] * times

    @staticmethod
    def held(key, times=1):
        """One key held down, arriving as the keyboard's auto-repeat."""
        return [(key, 0.03)] * times


class TestMenu(WithPretendKeys):

    OPTIONS = [("cube", "Cube", "a box"),
               ("ball", "Ball", "round"),
               ("rod", "Rod", "a bar")]

    def test_enter_takes_the_first_one(self):
        got, _ = self.press([ENTER], lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "cube")

    def test_down_then_enter(self):
        got, _ = self.press([DOWN, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "ball")

    def test_up_wraps_to_the_bottom(self):
        got, _ = self.press([UP, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "rod")

    def test_down_wraps_to_the_top(self):
        got, _ = self.press([DOWN, DOWN, DOWN, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "cube")

    def test_escape_goes_back(self):
        got, _ = self.press([ESC], lambda: menu.choose("Pick", self.OPTIONS))
        self.assertIsNone(got)

    def test_escape_is_refused_when_there_is_no_way_back(self):
        got, _ = self.press([ESC, DOWN, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS,
                                                allow_back=False))
        self.assertEqual(got, "ball")

    def test_a_number_jumps_straight_there(self):
        got, _ = self.press(["3", ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "rod")

    def test_a_letter_jumps_to_the_next_match(self):
        got, _ = self.press(["r", ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "rod")

    def test_home_and_end(self):
        got, _ = self.press([keys.END, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "rod")
        got, _ = self.press([keys.END, keys.HOME, ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(got, "cube")

    def test_starting_position_is_respected(self):
        got, _ = self.press([ENTER],
                            lambda: menu.choose("Pick", self.OPTIONS, start=2))
        self.assertEqual(got, "rod")

    # -- what a screen reader would hear ----------------------------------

    def test_every_move_says_something_new(self):
        """
        The whole point of the speak style: moving must produce NEW text.

        A screen reader announces new lines reliably and redrawn ones only
        sometimes. If this test ever fails, a blind student is pressing Down
        and hearing nothing.
        """
        _, heard = self.press([DOWN, DOWN, ENTER],
                              lambda: menu.choose("Pick", self.OPTIONS))
        spoken = [line for line in heard.splitlines()
                  if line.startswith(menu.MARKER)]
        self.assertEqual(len(spoken), 3, heard)   # start, then two moves
        self.assertIn("Cube", spoken[0])
        self.assertIn("Ball", spoken[1])
        self.assertIn("Rod", spoken[2])

    def test_each_line_says_where_you_are(self):
        _, heard = self.press([DOWN, ENTER],
                              lambda: menu.choose("Pick", self.OPTIONS))
        self.assertIn("2 of 3", heard)

    def test_it_says_what_was_chosen(self):
        _, heard = self.press([DOWN, ENTER],
                              lambda: menu.choose("Pick", self.OPTIONS))
        self.assertIn("Chosen: Ball", heard)

    def test_staying_still_says_nothing_twice(self):
        """Pressing a key that does not move must not repeat the line."""
        _, heard = self.press([ENTER],
                              lambda: menu.choose("Pick", self.OPTIONS, start=0))
        spoken = [l for l in heard.splitlines() if l.startswith(menu.MARKER)]
        self.assertEqual(len(spoken), 1)

    def test_question_mark_repeats_the_choices(self):
        _, heard = self.press(["?", ENTER],
                              lambda: menu.choose("Pick", self.OPTIONS))
        self.assertEqual(heard.count("1. Cube"), 2)

    def test_the_visual_style_returns_the_same_answers(self):
        menu.set_style("visual")
        try:
            got, heard = self.press([DOWN, ENTER],
                                    lambda: menu.choose("Pick", self.OPTIONS))
        finally:
            menu.set_style("speak")
        self.assertEqual(got, "ball")
        self.assertIn("\x1b[", heard)      # it really did use colour codes

    # -- no keyboard ------------------------------------------------------

    def test_it_falls_back_to_typing_when_there_is_no_keyboard(self):
        keys.set_keyboard(False)
        heard = io.StringIO()
        with redirect_stdout(heard):
            import builtins
            real = builtins.input
            builtins.input = lambda prompt="": "2"
            try:
                got = menu.choose("Pick", self.OPTIONS)
            finally:
                builtins.input = real
        self.assertEqual(got, "ball")

    def test_typing_the_name_works_too(self):
        keys.set_keyboard(False)
        import builtins
        real = builtins.input
        builtins.input = lambda prompt="": "rod"
        try:
            with redirect_stdout(io.StringIO()):
                got = menu.choose("Pick", self.OPTIONS)
        finally:
            builtins.input = real
        self.assertEqual(got, "rod")


class TestReadingTheKeyboard(unittest.TestCase):
    """
    The two platforms report arrow keys completely differently.

    The Unix path can be exercised for real here. The Windows path cannot --
    there is no msvcrt on this machine -- so a stand-in feeds it the exact
    bytes Windows sends. That matters, because Windows is where this app
    actually runs, and a wrong letter in the table would make the arrow keys
    do nothing at all with no error to explain why.
    """

    def test_windows_arrow_keys(self):
        import types
        sent = list("\xe0H\xe0P\xe0K\xe0M\xe0G\xe0O\xe0I\xe0Q")
        fake = types.ModuleType("msvcrt")
        fake.getwch = lambda: sent.pop(0)
        sys.modules["msvcrt"] = fake
        try:
            got = [keys._read_windows() for _ in range(8)]
        finally:
            del sys.modules["msvcrt"]
        self.assertEqual(got, [keys.UP, keys.DOWN, keys.LEFT, keys.RIGHT,
                               keys.HOME, keys.END,
                               keys.PAGE_UP, keys.PAGE_DOWN])

    def test_windows_ordinary_keys(self):
        import types
        sent = list("\rq\x1b\x08\t5")
        fake = types.ModuleType("msvcrt")
        fake.getwch = lambda: sent.pop(0)
        sys.modules["msvcrt"] = fake
        try:
            got = [keys._read_windows() for _ in range(6)]
        finally:
            del sys.modules["msvcrt"]
        self.assertEqual(got, [keys.ENTER, "q", keys.ESCAPE,
                               keys.BACKSPACE, keys.TAB, "5"])

    def test_windows_control_c_still_stops_the_app(self):
        import types
        fake = types.ModuleType("msvcrt")
        fake.getwch = lambda: "\x03"
        sys.modules["msvcrt"] = fake
        try:
            with self.assertRaises(KeyboardInterrupt):
                keys._read_windows()
        finally:
            del sys.modules["msvcrt"]

    def test_windows_sends_the_other_marker_byte_too(self):
        """Windows uses 0x00 as well as 0xE0 for special keys."""
        import types
        sent = list("\x00H")
        fake = types.ModuleType("msvcrt")
        fake.getwch = lambda: sent.pop(0)
        sys.modules["msvcrt"] = fake
        try:
            self.assertEqual(keys._read_windows(), keys.UP)
        finally:
            del sys.modules["msvcrt"]

    def test_a_real_terminal_decodes_arrow_keys(self):
        """The Unix path, through an actual pseudo-terminal."""
        import os
        import platform
        import time
        if platform.system() == "Windows":
            self.skipTest("there is no pty on Windows")
        import pty

        script = ("import sys\n"
                  f"sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})\n"
                  "from bgera import keys\n"
                  "print('DECODED:', [keys.read_key() for _ in range(7)], flush=True)\n")
        pid, handle = pty.fork()
        if pid == 0:
            os.execv(sys.executable, [sys.executable, "-c", script])
        time.sleep(0.6)
        os.write(handle, b"\x1b[A\x1b[B\x1b[C\x1b[D\x1b[H\x1b[F\r")
        out = b""
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                chunk = os.read(handle, 1024)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            if b"DECODED" in out:
                break
        os.waitpid(pid, 0)
        text = out.decode(errors="replace")
        self.assertIn("DECODED", text, text)
        for expected in ("'up'", "'down'", "'right'", "'left'",
                         "'home'", "'end'", "'enter'"):
            self.assertIn(expected, text, text)


class TestRamp(unittest.TestCase):
    """
    How much one arrow press moves a number by.

    A terminal cannot say a key is HELD, only that the same key keeps
    arriving. So this is all about how fast the presses come. The clock is
    faked, because acceleration that can only be tested by holding a key
    down for real never gets tested at all.
    """

    def setUp(self):
        self.clock = [0.0]
        self.ramp = menu.Ramp(clock=lambda: self.clock[0])

    def press(self, way, gap):
        self.clock[0] += gap
        return self.ramp.next_step(way)

    def test_it_starts_at_a_tenth_of_a_millimetre(self):
        self.assertEqual(self.ramp.step, 0.1)
        step, _ = self.press(1, 0.5)
        self.assertEqual(step, 0.1)

    def test_deliberate_presses_never_speed_up(self):
        for _ in range(50):
            step, _ = self.press(1, 0.5)
            self.assertEqual(step, 0.1)

    def test_holding_it_down_speeds_up(self):
        seen = []
        for _ in range(45):
            step, _ = self.press(1, 0.03)
            seen.append(step)
        self.assertEqual(seen[0], 0.1)
        self.assertEqual(seen[-1], 10.0)
        # it only ever gets bigger, never smaller, during one run
        self.assertEqual(seen, sorted(seen))

    def test_the_whole_ladder_is_climbed(self):
        seen = []
        for _ in range(45):
            step, changed = self.press(1, 0.03)
            if changed:
                seen.append(step)
        self.assertEqual(seen, [0.5, 1.0, 5.0, 10.0])

    def test_letting_go_drops_back_to_the_smallest(self):
        for _ in range(30):
            self.press(1, 0.03)
        self.assertGreater(self.ramp.step, 0.1)
        step, _ = self.press(1, 0.5)          # a pause
        self.assertEqual(step, 0.1)

    def test_changing_direction_drops_back_to_the_smallest(self):
        for _ in range(30):
            self.press(1, 0.03)
        step, _ = self.press(-1, 0.03)
        self.assertEqual(step, 0.1)

    def test_it_says_when_the_step_changed(self):
        changes = [self.press(1, 0.03)[1] for _ in range(45)]
        self.assertEqual(sum(changes), 4)     # four rungs of the ladder

    def test_reset(self):
        for _ in range(30):
            self.press(1, 0.03)
        self.ramp.reset()
        self.assertEqual(self.ramp.step, 0.1)


class TestTalker(unittest.TestCase):
    """
    Saying a running number often enough to follow, but not so often that a
    screen reader drowns -- and never losing the last one.
    """

    def setUp(self):
        self.clock = [100.0]
        menu._now = lambda: self.clock[0]
        self.talker = menu.Talker()

    def tearDown(self):
        import time
        menu._now = lambda: time.monotonic()

    def said(self, work):
        heard = io.StringIO()
        with redirect_stdout(heard):
            work()
        return heard.getvalue()

    def test_slow_changes_are_all_said(self):
        out = self.said(lambda: [
            (self.clock.__setitem__(0, self.clock[0] + 0.5),
             self.talker.maybe(f"value {n}")) for n in range(4)])
        for n in range(4):
            self.assertIn(f"value {n}", out)

    def test_a_flood_is_thinned_out(self):
        def flood():
            for n in range(30):
                self.clock[0] += 0.01
                self.talker.maybe(f"value {n}")
        out = self.said(flood)
        self.assertLess(len(out.splitlines()), 5, out)

    def test_the_last_one_is_never_lost(self):
        """
        Held back is fine. Held back forever is a bug: the student would
        hear 118 and walk away with 168.
        """
        def flood_then_stop():
            for n in range(30):
                self.clock[0] += 0.01
                self.talker.maybe(f"value {n}")
            self.talker.settle()
        out = self.said(flood_then_stop)
        self.assertIn("value 29", out)

    def test_settle_says_nothing_when_nothing_is_waiting(self):
        self.talker.settle()
        out = self.said(self.talker.settle)
        self.assertEqual(out, "")

    def test_a_forced_message_always_gets_through(self):
        def quick():
            self.clock[0] += 0.01
            self.talker.maybe("stepping by 5", force=True)
        self.assertIn("stepping by 5", self.said(quick))


class TestNumberPickerWithArrows(WithPretendKeys):
    """Left and right change a number; it starts at a tenth of a millimetre."""

    def pick(self, keystrokes, **kw):
        settings = {"current": 20}
        settings.update(kw)
        return self.press(keystrokes,
                          lambda: menu.pick_number("How wide?", **settings))

    def test_enter_accepts_what_is_there(self):
        got, _ = self.pick([ENTER])
        self.assertEqual(got, 20)

    def test_right_makes_it_bigger_by_a_tenth(self):
        got, _ = self.pick([keys.RIGHT, ENTER])
        self.assertEqual(got, 20.1)

    def test_left_makes_it_smaller_by_a_tenth(self):
        got, _ = self.pick([keys.LEFT, ENTER])
        self.assertEqual(got, 19.9)

    def test_up_and_down_do_the_same_as_right_and_left(self):
        got, _ = self.pick([UP, ENTER])
        self.assertEqual(got, 20.1)
        got, _ = self.pick([DOWN, ENTER])
        self.assertEqual(got, 19.9)

    def test_several_deliberate_presses_stay_at_a_tenth(self):
        """Each press separate, so nothing should accelerate."""
        got, _ = self.press_timed(
            self.slow(keys.RIGHT, 5) + self.slow(ENTER),
            lambda: menu.pick_number("How wide?", current=20))
        self.assertEqual(got, 20.5)

    def test_holding_it_down_covers_ground_quickly(self):
        got, _ = self.press_timed(
            self.held(keys.RIGHT, 40) + self.slow(ENTER),
            lambda: menu.pick_number("How wide?", current=20, high=1000))
        # 40 presses at a tenth would be 24. Held, it should be far more.
        self.assertGreater(got, 100)

    def test_escape_leaves_it_alone(self):
        got, _ = self.pick([keys.RIGHT, ESC])
        self.assertIsNone(got)

    def test_it_will_not_go_below_the_smallest(self):
        got, _ = self.pick([keys.LEFT] * 10 + [ENTER], current=10.3, low=10)
        self.assertEqual(got, 10)

    def test_it_will_not_go_above_the_largest(self):
        got, _ = self.pick([keys.RIGHT] * 10 + [ENTER], current=39.7, high=40)
        self.assertEqual(got, 40)

    def test_it_says_so_once_at_the_limit_not_every_press(self):
        _, heard = self.pick([keys.RIGHT] * 8 + [ENTER], current=39.9, high=40)
        self.assertEqual(heard.count("is the largest it can be"), 1, heard)

    def test_whole_numbers_never_go_fractional(self):
        """Sides and points are counts: 6.1 sides is meaningless."""
        got, _ = self.pick([keys.RIGHT, ENTER], current=4, whole=True, low=3,
                           high=64)
        self.assertEqual(got, 5)
        self.assertIsInstance(got, int)

    def test_the_number_never_drifts(self):
        """0.1 added twenty times must be 22, not 21.999999999999996."""
        got, _ = self.press_timed(
            self.slow(keys.RIGHT, 20) + self.slow(ENTER),
            lambda: menu.pick_number("How wide?", current=20))
        self.assertEqual(got, 22)

    def test_the_final_value_is_always_said(self):
        _, heard = self.pick([keys.RIGHT, ENTER])
        self.assertIn("Set to 20.1 millimetres", heard)


class TestNumberPickerByTyping(WithPretendKeys):
    """The other way: the student types the number."""

    def type_it(self, answer, **kw):
        import builtins
        menu.set_number_mode("typed")
        real = builtins.input
        builtins.input = lambda prompt="": answer
        heard = io.StringIO()
        try:
            with redirect_stdout(heard):
                got = menu.pick_number("How wide?", current=20, **kw)
        finally:
            builtins.input = real
        return got, heard.getvalue()

    def test_a_typed_number(self):
        got, _ = self.type_it("37")
        self.assertEqual(got, 37)

    def test_a_typed_decimal(self):
        got, _ = self.type_it("1.5")
        self.assertEqual(got, 1.5)

    def test_nothing_typed_leaves_it_alone(self):
        got, _ = self.type_it("")
        self.assertIsNone(got)

    def test_arrows_are_not_used_in_this_mode(self):
        """No keys should be read at all: it just asks."""
        import builtins
        menu.set_number_mode("typed")
        keys.pretend_keys([keys.RIGHT] * 5)
        real = builtins.input
        builtins.input = lambda prompt="": "42"
        try:
            with redirect_stdout(io.StringIO()):
                got = menu.pick_number("How wide?", current=20)
        finally:
            builtins.input = real
        self.assertEqual(got, 42)


class TestAdjustingInPlace(WithPretendKeys):
    """
    Left and right changing the line you are on, without any sub-menu.

    This is the "width, now 20" behaviour: you never press Enter to get at
    the number, you just push it about with the arrows.
    """

    def test_right_calls_back_with_the_step(self):
        seen = []

        def adjust(value, way, step):
            seen.append((value, way, step))
            return f"now {20 + step * way}"

        got, heard = self.press(
            [keys.RIGHT, ENTER],
            lambda: menu.choose("Size", [("width", "Width", "now 20")],
                                on_adjust=adjust))
        self.assertEqual(seen, [("width", 1, 0.1)])
        self.assertIn("now 20.1", heard)

    def test_left_goes_the_other_way(self):
        seen = []
        self.press([keys.LEFT, ENTER],
                   lambda: menu.choose("Size", [("width", "Width", "now 20")],
                                       on_adjust=lambda v, w, s:
                                       seen.append((v, w, s))))
        self.assertEqual(seen[0][1], -1)

    def test_up_and_down_still_move_between_lines(self):
        """Left and right adjust, so the list is walked with up and down."""
        got, _ = self.press(
            [DOWN, ENTER],
            lambda: menu.choose("Size",
                                [("width", "Width", "now 20"),
                                 ("height", "Height", "now 20")],
                                on_adjust=lambda v, w, s: None))
        self.assertEqual(got, "height")

    def test_moving_to_another_line_starts_the_step_again(self):
        steps = []
        self.press_timed(
            self.held(keys.RIGHT, 20) + self.held(DOWN)
            + self.held(keys.RIGHT) + self.slow(ENTER),
            lambda: menu.choose("Size",
                                [("width", "Width", "now 20"),
                                 ("height", "Height", "now 20")],
                                on_adjust=lambda v, w, s: steps.append(s)))
        self.assertGreater(max(steps), 0.1, "it never sped up")
        self.assertEqual(steps[-1], 0.1, "moving line should reset the step")

    def test_a_held_arrow_does_not_bury_a_screen_reader(self):
        _, heard = self.press_timed(
            self.held(keys.RIGHT, 40) + self.slow(ENTER),
            lambda: menu.choose("Size", [("width", "Width", "now 20")],
                                on_adjust=lambda v, w, s: f"now {s}"))
        spoken = [l for l in heard.splitlines() if l.startswith(menu.MARKER)]
        # 40 presses in 1.2 seconds must not be 40 announcements.
        self.assertLess(len(spoken), 15, spoken)

    def test_the_value_it_settled_on_is_always_said(self):
        """
        Thinning out announcements while an arrow is held is necessary.
        Losing the one where it STOPPED would send a student away with the
        wrong number in their head.
        """
        value = [20.0]

        def adjust(name, way, step):
            value[0] = round(value[0] + step * way, 1)
            return f"now {value[0]}"

        _, heard = self.press_timed(
            self.held(keys.RIGHT, 40) + self.slow(ENTER),
            lambda: menu.choose("Size", [("width", "Width", "now 20")],
                                on_adjust=adjust))
        self.assertIn(f"now {value[0]}", heard)


class TestConfirm(WithPretendKeys):

    def test_yes(self):
        got, _ = self.press([ENTER], lambda: menu.confirm("Sure?",
                                                          default_yes=True))
        self.assertTrue(got)

    def test_no_is_the_default(self):
        got, _ = self.press([ENTER], lambda: menu.confirm("Sure?"))
        self.assertFalse(got)


class TestGuided(WithPretendKeys):
    """The menus driving a real BgeraPrint."""

    def new_app(self, interface="menus"):
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config.json")
        # Carry the mode the test asked for into the config: the app applies
        # the config on construction, so otherwise it would quietly undo
        # whatever set_number_mode the test had just done.
        config = {"lan": 1, "interface": interface,
                  "number_mode": menu.get_number_mode(),
                  "printers": [{"name": "c", "model": "xmax3",
                                "ip": "127.0.0.1", "port": "7125"}],
                  "current_printer": "c"}
        return app_mod.BgeraPrint(config)

    def run_menus(self, keystrokes, app=None, times=1):
        app = app or self.new_app()
        guided = Guided(app)
        keys.pretend_keys(keystrokes)
        heard = io.StringIO()
        with redirect_stdout(heard):
            try:
                for _ in range(times):
                    guided.main_menu()
            except keys.NoKeyboard:
                pass
        return app, heard.getvalue()

    def test_making_a_cube_and_sizing_it_with_the_arrows(self):
        """
        The size menu is never left: Left and Right push the numbers about
        while Up and Down walk between them.
        """
        menu.set_number_mode("arrows")
        app = self.new_app()
        keys.pretend_keys([
            ENTER,                          # Make a shape
            ENTER,                          # Cube
            keys.RIGHT, keys.RIGHT,         # width 20 -> 20.2
            DOWN, keys.LEFT,                # length 20 -> 19.9
            DOWN, keys.RIGHT, keys.RIGHT, keys.RIGHT,   # height -> 20.3
            keys.END, ENTER,                # That is the right size
        ])
        with redirect_stdout(io.StringIO()):
            try:
                Guided(app).main_menu()
            except keys.NoKeyboard:
                pass

        self.assertIn("cube", app.model.items)
        self.assertEqual(app.model.items["cube"].params,
                         {"width": 20.2, "length": 19.9, "height": 20.3})

    def test_making_a_cube_and_sizing_it_by_typing(self):
        import builtins
        menu.set_number_mode("typed")
        answers = iter(["30", "15", "25"])
        real = builtins.input
        builtins.input = lambda prompt="": next(answers)
        try:
            app, heard = self.run_menus([
                ENTER,                      # Make a shape
                ENTER,                      # Cube
                ENTER,                      # Width  -> typed 30
                ENTER,                      # Length -> typed 15
                ENTER,                      # Height -> typed 25
                ENTER,                      # That is the right size
            ])
        finally:
            builtins.input = real
        self.assertEqual(app.model.items["cube"].params,
                         {"width": 30, "length": 15, "height": 25})

    def test_typing_mode_lands_on_the_next_measurement(self):
        """After setting width, the cursor should be on length."""
        import builtins
        menu.set_number_mode("typed")
        real = builtins.input
        builtins.input = lambda prompt="": "30"
        try:
            app, heard = self.run_menus([ENTER, ENTER, ENTER, ENTER])
        finally:
            builtins.input = real
        after = heard.split("What shall we set on cube?")[2]
        first_spoken = [l for l in after.splitlines()
                        if l.startswith(menu.MARKER)][0]
        self.assertIn("Length", first_spoken)

    def test_a_whole_number_is_stored_whole(self):
        """103.0 in a saved project is untidy; it should just be 103."""
        menu.set_number_mode("arrows")
        app = self.new_app()
        app.model.add_part("cube")
        guided = Guided(app)
        self.press_timed(
            self.slow(keys.RIGHT, 10) + self.slow(keys.END) + self.slow(ENTER),
            lambda: guided.ask_measurements(app.model.items["cube"]))
        width = app.model.items["cube"].params["width"]
        self.assertEqual(width, 21)
        self.assertIsInstance(width, int)

    def test_holding_an_arrow_sizes_a_cube_quickly(self):
        """A student should be able to get from 20 to 200 without pain."""
        menu.set_number_mode("arrows")
        app = self.new_app()
        app.model.add_part("cube")
        guided = Guided(app)
        self.press_timed(
            self.held(keys.RIGHT, 45) + self.slow(keys.END) + self.slow(ENTER),
            lambda: guided.ask_measurements(app.model.items["cube"]))
        self.assertGreater(app.model.items["cube"].params["width"], 150)

    def test_a_shape_with_words_asks_for_the_words(self):
        import builtins
        real = builtins.input
        asked = []

        def fake_input(prompt=""):
            asked.append(prompt)
            return "nino"

        builtins.input = fake_input
        try:
            app, heard = self.run_menus([
                ENTER,                  # Make a shape
                "b", "b", ENTER,        # b lands on Ball, again on Braille
                ENTER,                  # accept the plate thickness
            ])
        finally:
            builtins.input = real

        self.assertIn("braille", app.model.items)
        self.assertEqual(app.model.items["braille"].params["words"], "nino")
        self.assertTrue(any("braille" in p.lower() for p in asked), asked)

    def test_a_letter_walks_through_every_match_and_wraps(self):
        options = [("ball", "Ball"), ("box", "Box"), ("rod", "Rod")]
        # Starting on Ball, one press moves on to Box...
        got, _ = self.press(["b", ENTER],
                            lambda: menu.choose("Pick", options))
        self.assertEqual(got, "box")
        # ...and a second press comes back round to Ball.
        got, _ = self.press(["b", "b", ENTER],
                            lambda: menu.choose("Pick", options))
        self.assertEqual(got, "ball")

    def test_escape_backs_out_without_making_anything(self):
        app, heard = self.run_menus([ENTER, ESC])
        self.assertTrue(app.model.is_empty())

    def test_the_main_menu_grows_once_there_is_a_model(self):
        app = self.new_app()
        app.model.add_part("cube")
        _, heard = self.run_menus([ESC], app=app)
        self.assertIn("Put parts together", heard)
        self.assertIn("Listen to your model", heard)

    def test_the_main_menu_is_short_when_there_is_nothing_yet(self):
        _, heard = self.run_menus([ESC])
        self.assertNotIn("Put parts together", heard)
        self.assertIn("Make a shape", heard)

    def test_moving_a_part(self):
        app = self.new_app()
        app.model.add_part("cube")
        app, _ = self.run_menus([
            DOWN, DOWN, ENTER,          # Move a part about
            ENTER,                      # Slide it
            ENTER,                      # Right
            ENTER,                      # 10
            keys.END, ENTER,            # That is where I want it
        ], app=app)
        self.assertEqual(app.model.items["cube"].pos[0], 10)

    def test_joining_two_parts(self):
        app = self.new_app()
        app.model.add_part("cube")
        app.model.add_part("ball")
        app, heard = self.run_menus([
            DOWN, DOWN, DOWN, DOWN, ENTER,   # Put parts together
            ENTER,                            # Join them
            ENTER,                            # first part
            ENTER,                            # second part
        ], app=app)
        groups = [i for i in app.model.items.values()
                  if getattr(i, "operation", None)]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].operation, "join")

    def test_changing_a_print_setting_by_typing(self):
        import builtins
        menu.set_number_mode("typed")
        real = builtins.input
        builtins.input = lambda prompt="": "45"
        try:
            app, heard = self.run_menus([
                DOWN, ENTER,            # Change how it prints
                ENTER,                  # Filling
                keys.END, ENTER,        # That is all
            ])
        finally:
            builtins.input = real
        self.assertEqual(app.settings.values["filling"], 45)

    def test_changing_a_print_setting_with_the_arrows(self):
        menu.set_number_mode("arrows")
        app, heard = self.run_menus([
            DOWN, ENTER,                # Change how it prints
            ENTER,                      # Filling
            keys.RIGHT, keys.RIGHT, ENTER,
            keys.END, ENTER,            # That is all
        ])
        self.assertGreater(app.settings.values["filling"], 15)

    def test_the_heat_can_be_set_and_then_un_set(self):
        """
        Heat and bed have a third state a number picker cannot express:
        leave them alone. Without a way back to it, the menus could set a
        temperature but never undo that.
        """
        app = self.new_app()
        self.assertNotIn("temperature", app.settings.overrides())

        # Change how it prints -> Heat -> Set it myself -> 170 -> That is all
        menu.set_number_mode("arrows")
        app, _ = self.run_menus([
            DOWN, ENTER,
            "h", ENTER,
            DOWN, ENTER,
            ENTER,
            keys.END, ENTER,
        ], app=app)
        self.assertIn("temperature", app.settings.overrides())

        # ...and back to leaving it to the printer. Up first: with a
        # temperature already set, "Set it myself" is the one pre-selected.
        app, _ = self.run_menus([
            DOWN, ENTER,
            "h", ENTER,
            UP, ENTER,
            keys.END, ENTER,
        ], app=app)
        self.assertNotIn("temperature", app.settings.overrides())
        self.assertIn("printer profile", app.settings.spoken("heat"))

    def test_switching_to_typing(self):
        app = self.new_app()
        guided = Guided(app)
        keys.pretend_keys([keys.END, UP, ENTER])   # Switch to typing
        with redirect_stdout(io.StringIO()):
            try:
                guided.main_menu()
            except keys.NoKeyboard:
                pass
        self.assertEqual(app.interface, "typing")

    def test_every_shape_is_in_the_menu(self):
        """A shape that exists but is not offered can never be made."""
        from bgera import shapes as shapes_mod
        self.assertEqual(set(Guided.SHAPE_ORDER), set(shapes_mod.SHAPES))

    def test_every_main_menu_entry_has_something_behind_it(self):
        """A menu choice with no method behind it would just say nothing."""
        app = self.new_app()
        app.model.add_part("cube")
        app.prepared = True
        guided = Guided(app)
        keys.pretend_keys([ESC])
        with redirect_stdout(io.StringIO()):
            try:
                guided.main_menu()
            except keys.NoKeyboard:
                pass
        for name in ("make", "size", "place", "change", "combine", "listen",
                     "settings", "prepare", "print", "printer", "projects",
                     "share", "learn", "typing", "quit"):
            self.assertTrue(hasattr(guided, f"menu_{name}"),
                            f"the main menu offers {name} but nothing does it")


class TestInterfaceChoice(WithPretendKeys):

    def test_the_question_offers_both(self):
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1}
        _, heard = self.press([ENTER],
                              lambda: app_mod.ask_which_interface(config))
        self.assertIn("Menus", heard)
        self.assertIn("Typing", heard)

    def test_choosing_typing(self):
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1}
        got, _ = self.press([DOWN, ENTER],
                            lambda: app_mod.ask_which_interface(config))
        self.assertEqual(got, "typing")
        self.assertEqual(config["interface"], "typing")

    def test_last_time_is_already_selected(self):
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1, "interface": "typing"}
        got, _ = self.press([ENTER],
                            lambda: app_mod.ask_which_interface(config))
        self.assertEqual(got, "typing")

    def test_arrow_numbers_are_impossible_without_a_keyboard(self):
        """
        Holding an arrow key down needs a keyboard read one key at a time.
        Fed from a file there is none, so the app must fall back to typed
        numbers however firmly the config asks for arrows.
        """
        keys.set_keyboard(False)
        menu.set_number_mode("arrows")
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1, "number_mode": "arrows", "interface": "menus",
                  "printers": [{"name": "c", "model": "xmax3",
                                "ip": "1.2.3.4", "port": "7125"}],
                  "current_printer": "c"}
        with redirect_stdout(io.StringIO()):
            app_mod.BgeraPrint(config)
        self.assertEqual(menu.get_number_mode(), "typed")

    def test_it_does_not_ask_when_there_is_no_keyboard(self):
        """
        Being fed from a file: asking would eat the file's first line.
        """
        keys.set_keyboard(False)
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1, "interface": "typing"}
        heard = io.StringIO()
        with redirect_stdout(heard):
            got = app_mod.ask_which_interface(config)
        self.assertEqual(got, "typing")
        self.assertNotIn("1. Menus", heard.getvalue())

    def test_the_announced_choice_is_the_one_that_runs(self):
        """It once said "typing" and then started the menus."""
        keys.set_keyboard(False)
        app_mod.CONFIG_PATH = Path("/tmp/bgeraprint-test-config2.json")
        config = {"lan": 1,
                  "printers": [{"name": "c", "model": "xmax3",
                                "ip": "1.2.3.4", "port": "7125"}],
                  "current_printer": "c"}
        with redirect_stdout(io.StringIO()):
            chosen = app_mod.ask_which_interface(config)
            app = app_mod.BgeraPrint(config)
        self.assertEqual(app.interface, chosen)


if __name__ == "__main__":
    unittest.main(verbosity=2)
