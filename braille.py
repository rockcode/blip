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
    """把最后 width_chars 个样本右对齐画进画布，每个样本占一个字符格。

    每个点按它「所在高度对应的延迟档」着色（color_fn 收到该高度代表的延迟
    值），而非按样本本身的值——颜色因此始终与纵轴高度一致：低处绿、高处红，
    连线经过哪一档就显哪种色（陡降会呈现红→绿的渐变竖柱），不会出现“快样本
    的连线整条变绿、顶到天”的误导。一个样本独占一个字符格、颜色随高度恒定，
    波形整格左移时历史颜色不抖。

    values:     [float 毫秒 | None]，最旧在前。
    scale:      映射到画布顶部的值（>0）。
    color_fn:   color_fn(latency) -> rgb（按“该高度代表的延迟”取色）。
    miss_color: 缺失样本整格尖刺的 rgb。
    """
    cols = canvas.width_chars
    pxh = canvas.px_h
    span = pxh - 1 if pxh > 1 else 1

    def band_color(yy):
        # 该点所在字符行(高 4 点)中心代表的延迟 -> 取色，保证整格同色
        center = (yy // 4) * 4 + 1.5
        frac = (span - center) / span
        frac = 0.0 if frac < 0 else (1.0 if frac > 1 else frac)
        return color_fn(frac * scale)

    vis = values[-cols:] if cols else []
    offset = cols - len(vis)
    prev_y = None
    for i, v in enumerate(vis):
        cx = offset + i
        x_left, x_right = cx * 2, cx * 2 + 1
        if v is None:
            for y in range(pxh):
                canvas.set(x_left, y, miss_color)
                canvas.set(x_right, y, miss_color)
            prev_y = None
            continue
        frac = 0.0 if scale <= 0 else min(1.0, v / scale)
        y = (pxh - 1) - round(frac * (pxh - 1))
        lo, hi = (y, y) if prev_y is None else (
            (prev_y, y) if prev_y <= y else (y, prev_y))
        for yy in range(lo, hi + 1):    # 画点并向上一样本连线，逐高度分档上色
            col = band_color(yy)
            canvas.set(x_left, yy, col)
            canvas.set(x_right, yy, col)
        prev_y = y
