"""把 Braille 延迟面板组合成整屏一帧。"""
from . import ansi
from . import braille


def color_for(latency, thresholds):
    if latency is None:
        return ansi.RED
    if latency < thresholds.bright:
        return ansi.BRIGHT_GREEN
    if latency < thresholds.green:
        return ansi.GREEN
    if latency < thresholds.yellow:
        return ansi.YELLOW
    return ansi.RED


def _fmt_ms(v):
    return "--" if v is None else f"{v:.0f}"


def _fmt_rate(bps):
    bps = max(0.0, bps)
    for unit in ("B", "K", "M", "G"):
        if bps < 1024 or unit == "G":
            return f"{bps:.0f}{unit}" if unit == "B" else f"{bps:.1f}{unit}"
        bps /= 1024.0


def format_header(name, stats, thresholds, width, rate=None):
    metrics = (f"{_fmt_ms(stats.last)}ms  avg {_fmt_ms(stats.avg)}  "
               f"max {_fmt_ms(stats.max)}  loss {stats.loss * 100:.0f}%")
    traffic_txt = ""
    if rate is not None:
        down, up = rate
        traffic_txt = f"  ↓{_fmt_rate(down)}/s ↑{_fmt_rate(up)}/s"
    plain = f"{name}   {metrics}{traffic_txt}"
    if len(plain) > width:
        return plain[:width]
    cur = color_for(stats.last, thresholds)
    colored = (ansi.colorize(name, ansi.GRAY) + "   " +
               ansi.colorize(metrics, cur) +
               ansi.colorize(traffic_txt, ansi.GRAY))
    return colored + " " * (width - len(plain))


def _render_cell(ch, color):
    if color is None or ch == "⠀":
        return ch
    return ansi.colorize(ch, color)


def render_panel(name, buffer, thresholds, width, height, scale_max=800.0,
                 rate=None):
    """返回恰好 `height` 行。布局：表头(1) + 波形(height-2) + 基线(1)。

    纵轴固定为 scale_max（所有面板统一、不随各自数据自适应），因此同样的柱高
    在任何面板都代表同样的延迟，可横向对比。超过 scale_max 的值在波形上顶到头
    (饱和)，真实数值仍在表头显示。rate=(下行,上行)字节/秒，有则表头追加 ↓↑。
    """
    height = max(height, 3)
    stats = buffer.stats()
    values = buffer.values()
    lines = [format_header(name, stats, thresholds, width, rate)]

    graph_h = height - 2
    scale = scale_max if scale_max > 0 else 1.0

    gutter_w = max(3, len(f"{scale:.0f}"))
    canvas_w = max(1, width - gutter_w - 1)   # -1 给轴字符
    canvas = braille.Canvas(canvas_w, graph_h)
    braille.plot_series(canvas, values, scale,
                        lambda v: color_for(v, thresholds), ansi.RED)

    top_label = f"{scale:.0f}".rjust(gutter_w)
    for r, row in enumerate(canvas.char_rows()):
        label = top_label if r == 0 else " " * gutter_w
        gutter = ansi.colorize(label + "┤", ansi.DIM)
        cells = "".join(_render_cell(ch, col) for ch, col in row)
        lines.append(gutter + cells)

    base_label = "0".rjust(gutter_w)
    baseline = ansi.colorize(base_label + "┼" + "─" * canvas_w, ansi.DIM)
    lines.append(baseline)
    return lines[:height]


def render_frame(targets, buffers, thresholds, cols, rows, paused=False,
                 scale_max=800.0, rates=None):
    if not targets:
        return ["no targets configured"]
    min_panel = 4
    if rows < min_panel:
        return ["terminal too small"]
    avail = rows - (1 if paused else 0)
    per = max(min_panel, avail // len(targets))
    lines = []
    for t in targets:
        rate = rates.get(t.name) if rates else None
        lines.extend(render_panel(t.name, buffers[t.name],
                                  thresholds, cols, per, scale_max, rate))
    lines = lines[:avail]
    if paused:
        lines.append(ansi.colorize("[paused] p 继续 · q 退出", ansi.YELLOW))
    return lines[:rows]
