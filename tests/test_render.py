import re
import unittest

import render
from buffer import SampleBuffer
from config import Thresholds, Target

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def strip(s):
    return _ANSI.sub("", s)


class TestColorFor(unittest.TestCase):
    def test_thresholds(self):
        th = Thresholds(green=100, yellow=250)
        self.assertEqual(render.color_for(50, th), render.ansi.GREEN)
        self.assertEqual(render.color_for(150, th), render.ansi.YELLOW)
        self.assertEqual(render.color_for(300, th), render.ansi.RED)
        self.assertEqual(render.color_for(None, th), render.ansi.RED)


class TestHeader(unittest.TestCase):
    def test_header_contains_name_and_metrics(self):
        b = SampleBuffer(10); b.add(42.0)
        h = strip(render.format_header("anthropic", b.stats(),
                                       Thresholds(), 60))
        self.assertIn("anthropic", h)
        self.assertIn("42ms", h)
        self.assertIn("loss 0%", h)


class TestPanel(unittest.TestCase):
    def test_panel_has_exact_height(self):
        b = SampleBuffer(120)
        for v in (10.0, 20.0, 30.0):
            b.add(v)
        panel = render.render_panel("x", b, Thresholds(), 40, 6)
        self.assertEqual(len(panel), 6)

    def test_baseline_present(self):
        b = SampleBuffer(120); b.add(10.0)
        panel = render.render_panel("x", b, Thresholds(), 40, 5)
        self.assertIn("┼", strip(panel[-1]))


class TestFrame(unittest.TestCase):
    def test_terminal_too_small(self):
        out = render.render_frame([Target("a", "h")],
                                  {"a": SampleBuffer(10)},
                                  Thresholds(), 40, 2)
        self.assertEqual(strip(out[0]), "terminal too small")

    def test_frame_within_rows(self):
        targets = [Target("a", "h"), Target("b", "h")]
        buffers = {"a": SampleBuffer(10), "b": SampleBuffer(10)}
        buffers["a"].add(10.0); buffers["b"].add(20.0)
        out = render.render_frame(targets, buffers, Thresholds(), 40, 16)
        self.assertLessEqual(len(out), 16)
        self.assertTrue(any("a" in strip(line) for line in out))

    def test_frame_paused_shows_indicator(self):
        targets = [Target("a", "h")]
        buffers = {"a": SampleBuffer(10)}
        buffers["a"].add(10.0)
        out = render.render_frame(targets, buffers, Thresholds(), 40, 16,
                                  paused=True)
        self.assertTrue(any("[paused]" in strip(line) for line in out))
        self.assertLessEqual(len(out), 16)


if __name__ == "__main__":
    unittest.main()
