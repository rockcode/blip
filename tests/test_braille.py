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
    def test_each_sample_owns_a_cell_color(self):
        # 每个样本独占一个字符列；各自的颜色不串到相邻列(稳定、不依赖配对)
        cA, cB = (1, 1, 1), (2, 2, 2)
        color_fn = lambda v: cA if v < 100 else cB
        c = braille.Canvas(2, 3)
        braille.plot_series(c, [50.0, 300.0], scale=400,
                            color_fn=color_fn, miss_color=(0, 0, 0),
                            stem_color=(9, 9, 9))
        rows = c.char_rows()
        col0 = {row[0][1] for row in rows if row[0][1] is not None}
        col1 = {row[1][1] for row in rows if row[1][1] is not None}
        self.assertIn(cA, col0)      # 第0列(样本50)含其色
        self.assertIn(cB, col1)      # 第1列(样本300)含其色
        self.assertNotIn(cB, col0)   # 不串色
        self.assertNotIn(cA, col1)

    def test_top_cell_colored_body_gray(self):
        # 柱顶那一格按延迟着色、柱身为浅灰；彩色格在灰身之上
        TIP, STEM = (1, 2, 3), (9, 9, 9)
        c = braille.Canvas(1, 3)   # px_h=12
        braille.plot_series(c, [400.0], scale=800,   # 半高
                            color_fn=lambda v: TIP,
                            miss_color=(0, 0, 0), stem_color=STEM)
        colors = [row[0][1] for row in c.char_rows()]
        self.assertIn(TIP, colors)
        self.assertIn(STEM, colors)
        tip_row = colors.index(TIP)
        stem_rows = [i for i, col in enumerate(colors) if col == STEM]
        self.assertTrue(all(tip_row < s for s in stem_rows))   # 彩格在灰身之上

    def test_miss_fills_full_cell(self):
        c = braille.Canvas(1, 1)   # 1 样本 = 1 整格
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9), stem_color=(5, 5, 5))
        self.assertEqual(c.plain_rows(), ["⣿"])

    def test_empty_values_no_error(self):
        c = braille.Canvas(3, 2)
        braille.plot_series(c, [], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0), stem_color=(0, 0, 0))
        self.assertEqual(c.plain_rows(), ["⠀" * 3, "⠀" * 3])


if __name__ == "__main__":
    unittest.main()
