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

    def test_color_follows_height_not_sample(self):
        # 颜色由“高度对应的延迟档”决定：高处红、低处绿。
        # 即便是同一条从低样本连到高样本的竖线，也是顶红、底绿。
        RED, GREEN = (255, 0, 0), (0, 255, 0)
        color_fn = lambda lat: RED if lat >= 300 else GREEN
        c = braille.Canvas(2, 6)   # 6 字符行高, px_h=24
        braille.plot_series(c, [50.0, 580.0], scale=600,
                            color_fn=color_fn, miss_color=(0, 0, 0))
        rows = c.char_rows()
        self.assertEqual(rows[0][1][1], RED)     # 第2列(高样本)顶行 -> 红
        self.assertEqual(rows[-1][1][1], GREEN)  # 第2列底行 -> 绿

    def test_each_sample_owns_one_cell_column(self):
        # 结构回归：一个样本独占一个字符列（修复历史颜色乱跳的前提仍在）
        c = braille.Canvas(2, 4)
        braille.plot_series(c, [50.0, 700.0], scale=800,
                            color_fn=lambda lat: (1, 1, 1),
                            miss_color=(0, 0, 0))
        plain = c.plain_rows()
        self.assertNotEqual(plain[0][1], "⠀")    # 高样本(第2列)到达顶行
        self.assertNotEqual(plain[-1][0], "⠀")   # 低样本(第1列)在底行

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
