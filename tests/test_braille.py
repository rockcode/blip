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
    def test_miss_fills_full_cell(self):
        c = braille.Canvas(1, 1)   # 1 字符格 = 2x4 点
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9))
        # 1 样本占 1 整格：缺失 -> 整格 8 点全填 -> ⣿
        self.assertEqual(c.plain_rows(), ["⣿"])

    def test_each_cell_colored_by_its_own_sample(self):
        # 关键回归：每个字符格只由它自己的样本上色，互不串色。
        # 旧实现把两个样本塞进同一格、后写覆盖，导致历史颜色随滚动乱跳。
        cA, cB = (1, 1, 1), (2, 2, 2)
        color_fn = lambda v: cA if v < 100 else cB
        c = braille.Canvas(2, 1)   # 2 个字符格
        braille.plot_series(c, [50.0, 150.0], scale=200,
                            color_fn=color_fn, miss_color=(0, 0, 0))
        colors = [col for ch, col in c.char_rows()[0]]
        self.assertEqual(colors[0], cA)   # 样本 50 -> cA
        self.assertEqual(colors[1], cB)   # 样本 150 -> cB

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
