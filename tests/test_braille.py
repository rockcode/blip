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

    def test_one_color_per_column(self):
        # 每一列(字符格)只有一种颜色 = 该样本自己的颜色，不串色不渐变。
        cA, cB = (1, 1, 1), (2, 2, 2)
        color_fn = lambda v: cA if v < 100 else cB
        c = braille.Canvas(2, 3)
        braille.plot_series(c, [50.0, 300.0], scale=400,
                            color_fn=color_fn, miss_color=(0, 0, 0))
        rows = c.char_rows()
        for cx, expect in ((0, cA), (1, cB)):
            seen = {row[cx][1] for row in rows if row[cx][1] is not None}
            self.assertEqual(seen, {expect})   # 该列唯一颜色且正确

    def test_block_sits_at_sample_height(self):
        # 低样本的块在底部、高样本的块在顶部（绿低红高的结构基础）
        c = braille.Canvas(2, 4)
        braille.plot_series(c, [40.0, 760.0], scale=800,
                            color_fn=lambda v: (1, 1, 1),
                            miss_color=(0, 0, 0))
        plain = c.plain_rows()
        self.assertNotEqual(plain[-1][0], "⠀")   # 低样本 -> 底行
        self.assertEqual(plain[0][0], "⠀")       # 低样本不在顶行
        self.assertNotEqual(plain[0][1], "⠀")    # 高样本 -> 顶行
        self.assertEqual(plain[-1][1], "⠀")      # 高样本不在底行

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
