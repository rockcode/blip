import unittest

import braille


class TestCanvas(unittest.TestCase):
    def test_set_top_left_dot(self):
        c = braille.Canvas(1, 1)
        c.set(0, 0)
        self.assertEqual(c.plain_rows(), ["⠁"])   # ⠁

    def test_set_bottom_right_dot(self):
        c = braille.Canvas(1, 1)
        c.set(1, 3)
        self.assertEqual(c.plain_rows(), ["⢀"])   # ⢀

    def test_set_all_dots_full_cell(self):
        c = braille.Canvas(1, 1)
        for x in range(2):
            for y in range(4):
                c.set(x, y)
        self.assertEqual(c.plain_rows(), ["⣿"])   # ⣿

    def test_out_of_bounds_ignored(self):
        c = braille.Canvas(1, 1)
        c.set(5, 5)
        self.assertEqual(c.plain_rows(), ["⠀"])   # 空白

    def test_color_recorded(self):
        c = braille.Canvas(1, 1)
        c.set(0, 0, (1, 2, 3))
        (_, color), = c.char_rows()[0]
        self.assertEqual(color, (1, 2, 3))


class TestPlotSeries(unittest.TestCase):
    def test_miss_fills_full_column(self):
        c = braille.Canvas(1, 1)   # px_w=2, px_h=4
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9))
        # 仅 1 个样本 -> 最右像素列 x=1（奇数=右点列）整列填满
        # 右列 bits 0x08|0x10|0x20|0x80 = 0xB8 -> chr(0x28B8) = ⢸
        self.assertEqual(c.plain_rows(), ["⢸"])

    def test_value_at_scale_hits_top(self):
        c = braille.Canvas(1, 2)   # px_h=8
        braille.plot_series(c, [100.0], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0))
        rows = c.plain_rows()
        self.assertNotEqual(rows[0], "⠀")   # 顶行有点
        self.assertEqual(rows[1], "⠀")      # 底行空白

    def test_empty_values_no_error(self):
        c = braille.Canvas(3, 2)
        braille.plot_series(c, [], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0))
        self.assertEqual(c.plain_rows(), ["⠀" * 3, "⠀" * 3])


if __name__ == "__main__":
    unittest.main()
