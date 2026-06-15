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
    def test_one_color_per_column(self):
        # 每根柱整列单色 = 该样本的颜色，且不串到相邻列(稳定、不依赖配对)
        cA, cB = (1, 1, 1), (2, 2, 2)
        color_fn = lambda v: cA if v < 100 else cB
        c = braille.Canvas(2, 3)
        braille.plot_series(c, [50.0, 300.0], scale=400,
                            color_fn=color_fn, miss_color=(0, 0, 0))
        rows = c.char_rows()
        col0 = {row[0][1] for row in rows if row[0][1] is not None}
        col1 = {row[1][1] for row in rows if row[1][1] is not None}
        self.assertEqual(col0, {cA})   # 第0列整列 cA
        self.assertEqual(col1, {cB})   # 第1列整列 cB

    def test_bar_fills_from_baseline(self):
        # 整列从基线填到柱顶：两柱都到底，低柱不到顶、高柱到顶
        c = braille.Canvas(2, 4)
        braille.plot_series(c, [40.0, 760.0], scale=800,
                            color_fn=lambda v: (1, 1, 1),
                            miss_color=(0, 0, 0))
        plain = c.plain_rows()
        self.assertNotEqual(plain[-1][0], "⠀")
        self.assertNotEqual(plain[-1][1], "⠀")
        self.assertEqual(plain[0][0], "⠀")       # 低柱不到顶
        self.assertNotEqual(plain[0][1], "⠀")    # 高柱到顶

    def test_miss_fills_full_cell(self):
        c = braille.Canvas(1, 1)   # 1 样本 = 1 整格
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9))
        self.assertEqual(c.plain_rows(), ["⣿"])

    def test_empty_values_no_error(self):
        c = braille.Canvas(3, 2)
        braille.plot_series(c, [], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0))
        self.assertEqual(c.plain_rows(), ["⠀" * 3, "⠀" * 3])


if __name__ == "__main__":
    unittest.main()
