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
    def test_two_samples_fill_one_char_width(self):
        # 一个字符宽 = 2 点列 = 容纳 2 次采样(分辨率翻倍)
        c = braille.Canvas(1, 2)
        braille.plot_series(c, [800.0, 800.0], scale=800,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0), stem_color=(0, 0, 0))
        self.assertEqual(c.plain_rows(), ["⣿", "⣿"])   # 左右点列都满

    def test_tip_colored_stem_gray(self):
        # 柱顶按延迟着色、柱身(下影线)为浅灰；彩色顶点在灰影之上
        TIP, STEM = (1, 2, 3), (9, 9, 9)
        c = braille.Canvas(1, 3)   # px_h=12
        braille.plot_series(c, [400.0], scale=800,   # 半高
                            color_fn=lambda v: TIP,
                            miss_color=(0, 0, 0), stem_color=STEM)
        colors = [row[0][1] for row in c.char_rows()]
        self.assertIn(TIP, colors)    # 有彩色顶点
        self.assertIn(STEM, colors)   # 有浅灰下影
        tip_row = colors.index(TIP)
        stem_rows = [i for i, col in enumerate(colors) if col == STEM]
        self.assertTrue(all(tip_row <= s for s in stem_rows))  # 顶点不在灰影下方

    def test_miss_fills_its_dot_column(self):
        c = braille.Canvas(1, 1)   # px_w=2，单个尾采样 -> 右点列
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9), stem_color=(5, 5, 5))
        self.assertEqual(c.plain_rows(), ["⢸"])   # 右点列整列(0xB8)

    def test_empty_values_no_error(self):
        c = braille.Canvas(3, 2)
        braille.plot_series(c, [], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(0, 0, 0), stem_color=(0, 0, 0))
        self.assertEqual(c.plain_rows(), ["⠀" * 3, "⠀" * 3])


if __name__ == "__main__":
    unittest.main()
