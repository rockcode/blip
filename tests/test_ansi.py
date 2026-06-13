import unittest

import ansi


class TestAnsi(unittest.TestCase):
    def test_fg_truecolor(self):
        self.assertEqual(ansi.fg((10, 20, 30)), "\x1b[38;2;10;20;30m")

    def test_colorize_wraps_with_reset(self):
        self.assertEqual(ansi.colorize("hi", (1, 2, 3)),
                         "\x1b[38;2;1;2;3mhi\x1b[0m")

    def test_move_is_one_based(self):
        self.assertEqual(ansi.move(3, 5), "\x1b[3;5H")

    def test_palette_present(self):
        for name in ("GREEN", "YELLOW", "RED", "GRAY", "DIM"):
            rgb = getattr(ansi, name)
            self.assertEqual(len(rgb), 3)


if __name__ == "__main__":
    unittest.main()
