"""Braille 画布：亚字符分辨率绘图。

Braille 单元格 2 点宽 ×4 点高。像素 (x, y)，y 自顶向下定位一个点。
Unicode braille 基址 U+2800，各点按标准布局映射到一个 bit。
"""

# (dx, dy) -> bit，dy 自单元格顶部
_DOT_BITS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}
_BRAILLE_BASE = 0x2800


class Canvas:
    def __init__(self, width_chars, height_chars):
        self.width_chars = width_chars
        self.height_chars = height_chars
        self.px_w = width_chars * 2
        self.px_h = height_chars * 4
        self._bits = [[0] * width_chars for _ in range(height_chars)]
        self._color = [[None] * width_chars for _ in range(height_chars)]

    def set(self, x, y, color=None):
        if not (0 <= x < self.px_w and 0 <= y < self.px_h):
            return
        cx, cy = x // 2, y // 4
        self._bits[cy][cx] |= _DOT_BITS[(x % 2, y % 4)]
        if color is not None:
            self._color[cy][cx] = color

    def char_rows(self):
        """返回逐行的 (char, color) 列表；color 为 rgb 元组或 None。"""
        rows = []
        for cy in range(self.height_chars):
            row = []
            for cx in range(self.width_chars):
                ch = chr(_BRAILLE_BASE + self._bits[cy][cx])
                row.append((ch, self._color[cy][cx]))
            rows.append(row)
        return rows

    def plain_rows(self):
        return ["".join(ch for ch, _ in row) for row in self.char_rows()]


def plot_series(canvas, values, scale, color_fn, miss_color):
    """把最后 width_chars 个样本右对齐画进画布，每个样本独占一个字符列，画一根
    从基线填到柱顶的实心柱，整列单色 = 该样本的延迟档颜色。

    一个样本独占整列，颜色只由自己决定、不依赖相邻样本、不随滚动闪变。缺失样本
    画整列(miss_color)。

    values:     [float 毫秒 | None]，最旧在前。
    scale:      映射到画布顶部的值（>0）。
    color_fn:   color_fn(value) -> rgb（按该样本延迟值取色）。
    miss_color: 缺失样本整列的 rgb。
    """
    cols = canvas.width_chars
    pxh = canvas.px_h
    vis = values[-cols:] if cols else []
    offset = cols - len(vis)
    for i, v in enumerate(vis):
        cx = offset + i
        x_left, x_right = cx * 2, cx * 2 + 1
        if v is None:
            top, col = 0, miss_color            # 超时：整列
        else:
            frac = 0.0 if scale <= 0 else min(1.0, v / scale)
            top = (pxh - 1) - round(frac * (pxh - 1))
            col = color_fn(v)                   # 整列单色 = 该样本延迟档色
        for yy in range(top, pxh):              # 从柱顶填到基线
            canvas.set(x_left, yy, col)
            canvas.set(x_right, yy, col)
