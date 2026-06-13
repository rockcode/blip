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
    """把最后 px_w 个样本右对齐画进画布。

    values:     [float 毫秒 | None]，最旧在前。
    scale:      映射到画布顶部的值（>0）。
    color_fn:   color_fn(value) -> 成功样本的 rgb。
    miss_color: 缺失样本整列尖刺的 rgb。
    """
    pxw = canvas.px_w
    pxh = canvas.px_h
    vis = values[-pxw:] if pxw else []
    offset = pxw - len(vis)
    prev_y = None
    for i, v in enumerate(vis):
        x = offset + i
        if v is None:
            for y in range(pxh):
                canvas.set(x, y, miss_color)
            prev_y = None
            continue
        frac = 0.0 if scale <= 0 else min(1.0, v / scale)
        y_from_bottom = round(frac * (pxh - 1))
        y = (pxh - 1) - y_from_bottom
        color = color_fn(v)
        canvas.set(x, y, color)
        if prev_y is not None:          # 连成线，避免断点
            lo, hi = (prev_y, y) if prev_y <= y else (y, prev_y)
            for yy in range(lo, hi + 1):
                canvas.set(x, yy, color)
        prev_y = y
