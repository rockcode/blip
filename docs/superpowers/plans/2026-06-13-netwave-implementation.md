# netwave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在终端用 Braille 示波器波形实时监控本机到多个大模型 API 的 TCP 建连延迟。

**Architecture:** 纯 Python 标准库，零外部依赖。`asyncio` 并发：每个目标一个探测协程做 TCP 建连计时，结果写入环形缓冲；一个渲染协程按间隔读缓冲、用 Braille 画布画波形、写 ANSI 帧到终端；一个 stdin reader 处理 `q`/`p`。模块按职责单一拆分，纯逻辑（buffer/braille/render/config）全部可用 `unittest` 单测。

**Tech Stack:** Python 3.14 标准库 — `asyncio`、`tomllib`、`termios`/`tty`、Unicode Braille、ANSI 真彩色。测试用标准库 `unittest`（含 `IsolatedAsyncioTestCase`），**不引入 pytest 或任何第三方包**。

**约定：**
- 所有源码模块放仓库根目录（扁平），入口 `netwave.py`，运行 `python3 netwave.py`。
- 测试放 `tests/`，是一个包（含 `tests/__init__.py`）。从仓库根运行：
  - 单文件：`python3 -m unittest tests.test_xxx -v`
  - 单用例：`python3 -m unittest tests.test_xxx.ClassName.test_name -v`
  - 全部：`python3 -m unittest discover -s tests -v`
- 每个任务做完即 `git commit`。

---

### Task 1: ansi.py — ANSI 转义助手

**Files:**
- Create: `ansi.py`
- Create: `tests/__init__.py`（空文件，使 tests 成为包）
- Test: `tests/test_ansi.py`

- [ ] **Step 1: 创建 `tests/__init__.py`（空文件）**

```bash
mkdir -p tests
: > tests/__init__.py
```

- [ ] **Step 2: 写失败测试 `tests/test_ansi.py`**

```python
import unittest

import ansi


class TestAnsi(unittest.TestCase):
    def test_fg_truecolor(self):
        self.assertEqual(ansi.fg((10, 20, 30)), "\x1b[38;2;10;20;30m")

    def test_colorize_wraps_with_reset(self):
        self.assertEqual(ansi.colorize("hi", (1, 2, 3)),
                         "\x1b[38;2;1;2;3mhi\x1b[0m")

    def test_move_is_one_based(self):
        self.assertEqual(ansi.move(3, 5), "\x1b[3;5H")

    def test_palette_present(self):
        for name in ("GREEN", "YELLOW", "RED", "GRAY", "DIM"):
            rgb = getattr(ansi, name)
            self.assertEqual(len(rgb), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_ansi -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ansi'`

- [ ] **Step 4: 实现 `ansi.py`**

```python
"""ANSI escape sequence helpers (truecolor). Pure string functions."""

ESC = "\x1b"

RESET = f"{ESC}[0m"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
CLEAR_SCREEN = f"{ESC}[2J"
CLEAR_BELOW = f"{ESC}[0J"
CLEAR_LINE = f"{ESC}[K"
HOME = f"{ESC}[H"

# 调色板 (r, g, b)
GREEN = (80, 220, 120)
YELLOW = (230, 200, 60)
RED = (235, 80, 80)
GRAY = (150, 150, 150)
DIM = (90, 90, 90)


def fg(rgb):
    r, g, b = rgb
    return f"{ESC}[38;2;{r};{g};{b}m"


def colorize(text, rgb):
    return f"{fg(rgb)}{text}{RESET}"


def move(row, col):
    """1-based 光标定位。"""
    return f"{ESC}[{row};{col}H"
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_ansi -v`
Expected: PASS（4 个用例）

- [ ] **Step 6: 提交**

```bash
git add ansi.py tests/__init__.py tests/test_ansi.py
git commit -m "feat: ansi truecolor escape helpers"
```

---

### Task 2: probe.py — 异步 TCP 建连计时

**Files:**
- Create: `probe.py`
- Test: `tests/test_probe.py`

- [ ] **Step 1: 写失败测试 `tests/test_probe.py`**

```python
import asyncio
import unittest
from unittest import mock

import probe


class TestProbe(unittest.IsolatedAsyncioTestCase):
    async def test_connect_success_returns_latency(self):
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            latency = await probe.probe_tcp("127.0.0.1", port, timeout=1.0)
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0.0)

    async def test_connection_refused_returns_none(self):
        # 端口 1 基本不会有人监听 -> 连接被拒 -> None
        latency = await probe.probe_tcp("127.0.0.1", 1, timeout=1.0)
        self.assertIsNone(latency)

    async def test_timeout_returns_none(self):
        async def never(*args, **kwargs):
            await asyncio.Event().wait()  # 永不返回
        with mock.patch("asyncio.open_connection", never):
            latency = await probe.probe_tcp("10.0.0.0", 9, timeout=0.05)
        self.assertIsNone(latency)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_probe -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'probe'`

- [ ] **Step 3: 实现 `probe.py`**

```python
"""异步 TCP 建连计时。"""
import asyncio
import time


async def probe_tcp(host, port, timeout):
    """测量到 host:port 的 TCP 建连耗时。

    成功返回毫秒数 (float)；超时/连接失败/DNS 失败返回 None。
    """
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
    except (OSError, asyncio.TimeoutError):
        return None
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return elapsed_ms
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_probe -v`
Expected: PASS（3 个用例）

- [ ] **Step 5: 提交**

```bash
git add probe.py tests/test_probe.py
git commit -m "feat: async tcp connect-time probe"
```

---

### Task 3: buffer.py — 环形缓冲与滚动统计

**Files:**
- Create: `buffer.py`
- Test: `tests/test_buffer.py`

- [ ] **Step 1: 写失败测试 `tests/test_buffer.py`**

```python
import unittest

from buffer import SampleBuffer


class TestSampleBuffer(unittest.TestCase):
    def test_empty_stats(self):
        s = SampleBuffer(10).stats()
        self.assertEqual(s.count, 0)
        self.assertEqual(s.loss, 0.0)
        self.assertIsNone(s.avg)
        self.assertIsNone(s.last)

    def test_basic_stats(self):
        b = SampleBuffer(10)
        for v in (10.0, 20.0, 30.0):
            b.add(v)
        s = b.stats()
        self.assertEqual(s.count, 3)
        self.assertEqual(s.avg, 20.0)
        self.assertEqual(s.min, 10.0)
        self.assertEqual(s.max, 30.0)
        self.assertEqual(s.last, 30.0)
        self.assertEqual(s.loss, 0.0)

    def test_loss_counts_none(self):
        b = SampleBuffer(10)
        b.add(10.0); b.add(None); b.add(30.0); b.add(None)
        s = b.stats()
        self.assertEqual(s.count, 4)
        self.assertEqual(s.loss, 0.5)
        self.assertEqual(s.avg, 20.0)   # 仅统计成功样本
        self.assertIsNone(s.last)       # 最后一个是 miss

    def test_jitter_mean_abs_delta(self):
        b = SampleBuffer(10)
        for v in (10.0, 20.0, 15.0):    # deltas 10, 5 -> 平均 7.5
            b.add(v)
        self.assertEqual(b.stats().jitter, 7.5)

    def test_ring_drops_oldest(self):
        b = SampleBuffer(2)
        b.add(1.0); b.add(2.0); b.add(3.0)
        self.assertEqual(b.values(), [2.0, 3.0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_buffer -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'buffer'`

- [ ] **Step 3: 实现 `buffer.py`**

```python
"""每个目标的环形采样缓冲与滚动统计。"""
from collections import deque
from dataclasses import dataclass


@dataclass
class Stats:
    last: float | None
    avg: float | None
    min: float | None
    max: float | None
    loss: float           # 0.0 ~ 1.0
    jitter: float | None
    count: int


class SampleBuffer:
    def __init__(self, maxlen):
        self._samples = deque(maxlen=maxlen)

    def add(self, latency):
        """latency: 成功为 float 毫秒，miss/超时为 None。"""
        self._samples.append(latency)

    def values(self):
        return list(self._samples)

    def stats(self):
        vals = list(self._samples)
        total = len(vals)
        oks = [v for v in vals if v is not None]
        misses = total - len(oks)
        loss = (misses / total) if total else 0.0
        if oks:
            avg = sum(oks) / len(oks)
            mn = min(oks)
            mx = max(oks)
            deltas = [abs(oks[i] - oks[i - 1]) for i in range(1, len(oks))]
            jitter = (sum(deltas) / len(deltas)) if deltas else 0.0
        else:
            avg = mn = mx = None
            jitter = None
        last = vals[-1] if vals else None
        return Stats(last=last, avg=avg, min=mn, max=mx,
                     loss=loss, jitter=jitter, count=total)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_buffer -v`
Expected: PASS（5 个用例）

- [ ] **Step 5: 提交**

```bash
git add buffer.py tests/test_buffer.py
git commit -m "feat: sample ring buffer with rolling stats"
```

---

### Task 4: braille.py — Braille 画布与波形绘制

**Files:**
- Create: `braille.py`
- Test: `tests/test_braille.py`

**背景：** Braille 单元格为 2 点宽 ×4 点高。像素 (x, y)，y 自顶向下。Unicode 基址 U+2800，点位 → bit：左列 0x01/0x02/0x04/0x40，右列 0x08/0x10/0x20/0x80。

- [ ] **Step 1: 写失败测试 `tests/test_braille.py`**

```python
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
    def test_miss_fills_full_column(self):
        c = braille.Canvas(1, 1)   # px_w=2, px_h=4
        braille.plot_series(c, [None], scale=100,
                            color_fn=lambda v: (0, 0, 0),
                            miss_color=(9, 9, 9))
        # 仅 1 个样本 -> 最右像素列 x=1（奇数=右点列）整列填满
        # 右列 bits 0x08|0x10|0x20|0x80 = 0xB8 -> chr(0x28B8) = ⢸
        self.assertEqual(c.plain_rows(), ["⢸"])

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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_braille -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'braille'`

- [ ] **Step 3: 实现 `braille.py`**

```python
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
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_braille -v`
Expected: PASS（8 个用例）

- [ ] **Step 5: 提交**

```bash
git add braille.py tests/test_braille.py
git commit -m "feat: braille canvas and series plotting"
```

---

### Task 5: config.py — TOML 配置

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试 `tests/test_config.py`**

```python
import os
import tempfile
import tomllib
import unittest

import config


class TestParseConfig(unittest.TestCase):
    def test_defaults_when_empty(self):
        c = config.parse_config({})
        self.assertEqual(c.interval, 1.0)
        self.assertEqual(c.timeout, 2.0)
        self.assertEqual(c.thresholds.green, 100.0)
        self.assertEqual(c.thresholds.yellow, 250.0)
        self.assertEqual(c.targets, [])

    def test_parses_targets_and_thresholds(self):
        data = {
            "interval": 2.0,
            "thresholds": {"green": 50, "yellow": 150},
            "targets": [{"name": "x", "host": "h", "port": 8443},
                        {"name": "y", "host": "h2"}],
        }
        c = config.parse_config(data)
        self.assertEqual(c.interval, 2.0)
        self.assertEqual(c.thresholds.green, 50.0)
        self.assertEqual(len(c.targets), 2)
        self.assertEqual(c.targets[0].port, 8443)
        self.assertEqual(c.targets[1].port, 443)   # 默认端口

    def test_default_toml_is_valid(self):
        data = tomllib.loads(config.DEFAULT_TOML)
        c = config.parse_config(data)
        self.assertGreater(len(c.targets), 0)


class TestLoadConfig(unittest.TestCase):
    def test_ensure_default_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "netwave", "config.toml")
            config.ensure_default(path)
            self.assertTrue(os.path.isfile(path))
            config.ensure_default(path)   # 幂等，不报错

    def test_load_explicit_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write('interval = 5.0\n[[targets]]\nname="a"\nhost="b"\n')
            c = config.load_config(explicit=path)
            self.assertEqual(c.interval, 5.0)
            self.assertEqual(c.targets[0].name, "a")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_config -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: 实现 `config.py`**

```python
"""TOML 配置：解析、默认值、首次运行生成。"""
import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Thresholds:
    green: float = 100.0
    yellow: float = 250.0


@dataclass
class Target:
    name: str
    host: str
    port: int = 443


@dataclass
class Config:
    interval: float = 1.0
    timeout: float = 2.0
    thresholds: Thresholds = field(default_factory=Thresholds)
    targets: list = field(default_factory=list)


DEFAULT_TOML = """\
# netwave 配置
interval = 1.0          # 采样间隔(秒)
timeout  = 2.0          # 建连超时(秒)

[thresholds]
green  = 100            # ms 以下为绿
yellow = 250            # green~yellow 为黄, 以上为红

[[targets]]
name = "anthropic"
host = "api.anthropic.com"
port = 443

[[targets]]
name = "openai"
host = "api.openai.com"
port = 443

[[targets]]
name = "google"
host = "generativelanguage.googleapis.com"
port = 443

[[targets]]
name = "deepseek"
host = "api.deepseek.com"
port = 443
"""


def parse_config(data):
    """从已解析的 TOML dict 构建 Config（纯函数）。"""
    th = data.get("thresholds", {})
    thresholds = Thresholds(
        green=float(th.get("green", 100.0)),
        yellow=float(th.get("yellow", 250.0)),
    )
    targets = []
    for t in data.get("targets", []):
        targets.append(Target(
            name=str(t["name"]),
            host=str(t["host"]),
            port=int(t.get("port", 443)),
        ))
    return Config(
        interval=float(data.get("interval", 1.0)),
        timeout=float(data.get("timeout", 2.0)),
        thresholds=thresholds,
        targets=targets,
    )


def default_config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "netwave", "config.toml")


def find_config_path(explicit=None):
    """返回存在的配置路径，找不到返回 None。"""
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.append(os.path.join(os.getcwd(), "config.toml"))
    candidates.append(default_config_path())
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def ensure_default(path):
    """若 path 不存在则写入 DEFAULT_TOML，返回 path。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_TOML)
    return path


def load_config(explicit=None):
    """从磁盘加载配置；首次运行生成默认配置。"""
    path = find_config_path(explicit)
    if path is None:
        path = ensure_default(default_config_path())
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return parse_config(data)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_config -v`
Expected: PASS（5 个用例）

- [ ] **Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat: toml config parsing, defaults, first-run generation"
```

---

### Task 6: render.py — 面板组合与整帧排版

**Files:**
- Create: `render.py`
- Test: `tests/test_render.py`

**依赖前置类型：** `ansi`（Task 1）、`braille`（Task 4）、`buffer.SampleBuffer`（Task 3）、`config.Thresholds`/`config.Target`（Task 5）。

- [ ] **Step 1: 写失败测试 `tests/test_render.py`**

```python
import re
import unittest

import render
from buffer import SampleBuffer
from config import Thresholds, Target

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def strip(s):
    return _ANSI.sub("", s)


class TestColorFor(unittest.TestCase):
    def test_thresholds(self):
        th = Thresholds(green=100, yellow=250)
        self.assertEqual(render.color_for(50, th), render.ansi.GREEN)
        self.assertEqual(render.color_for(150, th), render.ansi.YELLOW)
        self.assertEqual(render.color_for(300, th), render.ansi.RED)
        self.assertEqual(render.color_for(None, th), render.ansi.RED)


class TestHeader(unittest.TestCase):
    def test_header_contains_name_and_metrics(self):
        b = SampleBuffer(10); b.add(42.0)
        h = strip(render.format_header("anthropic", b.stats(),
                                       Thresholds(), 60))
        self.assertIn("anthropic", h)
        self.assertIn("42ms", h)
        self.assertIn("loss 0%", h)


class TestPanel(unittest.TestCase):
    def test_panel_has_exact_height(self):
        b = SampleBuffer(120)
        for v in (10.0, 20.0, 30.0):
            b.add(v)
        panel = render.render_panel("x", b, Thresholds(), 40, 6)
        self.assertEqual(len(panel), 6)

    def test_baseline_present(self):
        b = SampleBuffer(120); b.add(10.0)
        panel = render.render_panel("x", b, Thresholds(), 40, 5)
        self.assertIn("┼", strip(panel[-1]))


class TestFrame(unittest.TestCase):
    def test_terminal_too_small(self):
        out = render.render_frame([Target("a", "h")],
                                  {"a": SampleBuffer(10)},
                                  Thresholds(), 40, 2)
        self.assertEqual(strip(out[0]), "terminal too small")

    def test_frame_within_rows(self):
        targets = [Target("a", "h"), Target("b", "h")]
        buffers = {"a": SampleBuffer(10), "b": SampleBuffer(10)}
        buffers["a"].add(10.0); buffers["b"].add(20.0)
        out = render.render_frame(targets, buffers, Thresholds(), 40, 16)
        self.assertLessEqual(len(out), 16)
        self.assertTrue(any("a" in strip(line) for line in out))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_render -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: 实现 `render.py`**

```python
"""把 Braille 延迟面板组合成整屏一帧。"""
import ansi
import braille


def color_for(latency, thresholds):
    if latency is None:
        return ansi.RED
    if latency < thresholds.green:
        return ansi.GREEN
    if latency < thresholds.yellow:
        return ansi.YELLOW
    return ansi.RED


def _fmt_ms(v):
    return "--" if v is None else f"{v:.0f}"


def format_header(name, stats, thresholds, width):
    metrics = (f"{_fmt_ms(stats.last)}ms  avg {_fmt_ms(stats.avg)}  "
               f"max {_fmt_ms(stats.max)}  loss {stats.loss * 100:.0f}%")
    plain = f"{name}   {metrics}"
    if len(plain) > width:
        return plain[:width]
    cur = color_for(stats.last, thresholds)
    colored = (ansi.colorize(name, ansi.GRAY) + "   " +
               ansi.colorize(metrics, cur))
    return colored + " " * (width - len(plain))


def _render_cell(ch, color):
    if color is None or ch == "⠀":
        return ch
    return ansi.colorize(ch, color)


def render_panel(name, buffer, thresholds, width, height):
    """返回恰好 `height` 行。布局：表头(1) + 波形(height-2) + 基线(1)。"""
    height = max(height, 3)
    stats = buffer.stats()
    values = buffer.values()
    lines = [format_header(name, stats, thresholds, width)]

    graph_h = height - 2
    ok_vals = [v for v in values if v is not None]
    scale = max(ok_vals) * 1.1 if ok_vals else 1.0
    if scale <= 0:
        scale = 1.0

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


def render_frame(targets, buffers, thresholds, cols, rows, paused=False):
    if not targets:
        return ["no targets configured"]
    min_panel = 4
    if rows < min_panel:
        return ["terminal too small"]
    per = max(min_panel, rows // len(targets))
    lines = []
    for t in targets:
        lines.extend(render_panel(t.name, buffers[t.name],
                                  thresholds, cols, per))
    if paused:
        lines.append(ansi.colorize("[paused] p 继续 · q 退出", ansi.YELLOW))
    return lines[:rows]
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_render -v`
Expected: PASS（6 个用例）

- [ ] **Step 5: 提交**

```bash
git add render.py tests/test_render.py
git commit -m "feat: panel and full-frame rendering"
```

---

### Task 7: app.py + netwave.py — 异步主循环与入口

**Files:**
- Create: `app.py`
- Create: `netwave.py`
- Test: `tests/test_app.py`

**说明：** resize 由渲染循环每帧重读 `os.get_terminal_size()` 自然处理（非 tty 时回退 80×24），无需 SIGWINCH。可单测的部分：`_handle_key`（纯逻辑）与 `probe_loop`（用本地 server 跑几拍）。raw 终端与 `asyncio.run` 包裹层很薄，由后续手动冒烟验证。

- [ ] **Step 1: 写失败测试 `tests/test_app.py`**

```python
import asyncio
import unittest

import app
from buffer import SampleBuffer


class TestHandleKey(unittest.TestCase):
    def test_q_sets_stop(self):
        state = {"paused": False}
        stop = asyncio.Event()
        app._handle_key("q", state, stop)
        self.assertTrue(stop.is_set())

    def test_ctrl_c_sets_stop(self):
        state = {"paused": False}
        stop = asyncio.Event()
        app._handle_key("\x03", state, stop)
        self.assertTrue(stop.is_set())

    def test_p_toggles_pause(self):
        state = {"paused": False}
        stop = asyncio.Event()
        app._handle_key("p", state, stop)
        self.assertTrue(state["paused"])
        app._handle_key("p", state, stop)
        self.assertFalse(state["paused"])


class TestProbeLoop(unittest.IsolatedAsyncioTestCase):
    async def test_accumulates_samples(self):
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        class T:
            name = "t"
            host = "127.0.0.1"
        target = T()
        target.port = port

        buf = SampleBuffer(10)
        state = {"paused": False}
        async with server:
            task = asyncio.create_task(
                app.probe_loop(target, buf, interval=0.01,
                               timeout=1.0, state=state))
            await asyncio.sleep(0.05)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertGreaterEqual(len(buf.values()), 1)

    async def test_paused_skips_probing(self):
        class T:
            name = "t"
            host = "127.0.0.1"
        target = T()
        target.port = 1
        buf = SampleBuffer(10)
        state = {"paused": True}
        task = asyncio.create_task(
            app.probe_loop(target, buf, interval=0.01,
                           timeout=1.0, state=state))
        await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(buf.values(), [])   # 暂停时不采样


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_app -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: 实现 `app.py`**

```python
"""异步应用：探测调度、渲染循环、输入处理。"""
import argparse
import asyncio
import os
import sys
import termios
import tty

import ansi
import render
from buffer import SampleBuffer
from config import load_config
from probe import probe_tcp


async def probe_loop(target, buffer, interval, timeout, state):
    while True:
        if not state["paused"]:
            latency = await probe_tcp(target.host, target.port, timeout)
            buffer.add(latency)
        await asyncio.sleep(interval)


def _term_size():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


async def render_loop(config, buffers, state, out):
    while True:
        cols, rows = _term_size()
        lines = render.render_frame(config.targets, buffers,
                                    config.thresholds, cols, rows,
                                    paused=state["paused"])
        frame = ansi.HOME + "\r\n".join(
            line + ansi.CLEAR_LINE for line in lines) + ansi.CLEAR_BELOW
        out.write(frame)
        out.flush()
        await asyncio.sleep(config.interval)


def _handle_key(ch, state, stop):
    if ch in ("q", "\x03"):        # q 或 Ctrl-C
        stop.set()
    elif ch == "p":
        state["paused"] = not state["paused"]


async def run(config, out=None):
    out = out or sys.stdout
    buffers = {t.name: SampleBuffer(2000) for t in config.targets}
    state = {"paused": False}
    stop = asyncio.Event()

    tasks = [asyncio.create_task(
        probe_loop(t, buffers[t.name], config.interval,
                   config.timeout, state))
        for t in config.targets]
    tasks.append(asyncio.create_task(
        render_loop(config, buffers, state, out)))

    loop = asyncio.get_running_loop()

    def on_stdin():
        ch = sys.stdin.read(1)
        if ch:
            _handle_key(ch, state, stop)

    have_reader = sys.stdin.isatty()
    if have_reader:
        loop.add_reader(sys.stdin.fileno(), on_stdin)
    try:
        await stop.wait()
    finally:
        if have_reader:
            loop.remove_reader(sys.stdin.fileno())
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="netwave", description="终端 API 延迟电波图")
    parser.add_argument("-c", "--config", help="配置文件路径")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if not config.targets:
        print("配置中没有 targets，请在配置文件中添加。", file=sys.stderr)
        return 1

    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    old = termios.tcgetattr(fd) if is_tty else None
    try:
        if is_tty:
            tty.setcbreak(fd)
        sys.stdout.write(ansi.HIDE_CURSOR + ansi.CLEAR_SCREEN)
        sys.stdout.flush()
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(ansi.SHOW_CURSOR + ansi.RESET +
                         ansi.CLEAR_SCREEN + ansi.HOME)
        sys.stdout.flush()
    return 0
```

- [ ] **Step 4: 实现入口 `netwave.py`**

```python
#!/usr/bin/env python3
"""netwave 入口：python3 netwave.py [-c config.toml]"""
import sys

from app import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `python3 -m unittest tests.test_app -v`
Expected: PASS（5 个用例）

- [ ] **Step 6: 提交**

```bash
git add app.py netwave.py tests/test_app.py
git commit -m "feat: async app loop and entry point"
```

---

### Task 8: 全量回归 + 手动冒烟 + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 跑全部单测**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS（全部，共约 36 个用例），无 ERROR/FAIL

- [ ] **Step 2: 手动冒烟（需真实终端）**

Run: `python3 netwave.py`
预期：清屏后看到每个 API 一个面板，表头有现值/avg/max/loss，波形随秒滚动；按 `p` 暂停、再按继续；按 `q` 退出后光标恢复、终端正常。
（首次运行会在 `~/.config/netwave/config.toml` 生成默认配置。可断网或改一个不可达 target 验证红色满格尖刺与 loss 上升。）

- [ ] **Step 3: 写 `README.md`**

```markdown
# netwave

终端里的 API 延迟「电波图」——用 Braille 示波器波形实时监控本机到多个大模型 API 的 TCP 建连延迟。纯 Python 标准库，零依赖。

## 运行

```bash
python3 netwave.py            # 用默认/已有配置
python3 netwave.py -c my.toml # 指定配置文件
```

首次运行会在 `~/.config/netwave/config.toml` 生成默认配置（含 Anthropic / OpenAI / Google / DeepSeek）。

## 操作

- `q` 或 `Ctrl-C` 退出
- `p` 暂停 / 继续

## 配置

查找顺序：`-c 指定` → `./config.toml` → `~/.config/netwave/config.toml`。

```toml
interval = 1.0          # 采样间隔(秒)
timeout  = 2.0          # 建连超时(秒)

[thresholds]
green  = 100            # ms 以下为绿
yellow = 250            # green~yellow 为黄, 以上为红

[[targets]]
name = "anthropic"
host = "api.anthropic.com"
port = 443
```

颜色：`<green` 绿、`green~yellow` 黄、`>yellow` 红；超时/失败显示红色满格尖刺并计入 loss。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
```

- [ ] **Step 4: 提交**

```bash
git add README.md
git commit -m "docs: add README and finalize netwave v1"
```

---

## Self-Review

**1. Spec coverage（逐条对照 spec）：**
- 零依赖 Python + asyncio → Task 1-7 全标准库，测试用 unittest ✓
- TCP 建连计时 → Task 2 `probe_tcp` ✓
- 多目标来自 TOML 配置（预置+可编辑）→ Task 5 `config.py` + DEFAULT_TOML ✓
- Braille 示波器、向左滚动 → Task 4 `braille` + Task 6 右对齐绘制 ✓
- 采样 1s 可配置 → Task 5 `interval` + Task 7 `probe_loop` ✓
- 超时红色满格尖刺 + 计入 loss → Task 4 miss 整列填充 + Task 3 loss 统计 ✓
- 颜色固定阈值可配 → Task 6 `color_for` + Task 5 `Thresholds` ✓
- Y 轴每面板自适应 → Task 6 `scale = max(ok_vals)*1.1` ✓
- q 退出 / p 暂停 / resize / 恢复终端 → Task 7 `_handle_key` / `_term_size` 每帧重读 / finally 恢复 ✓
- 健壮性（DNS/拒绝/超时不崩，终端太小提示，配置缺失生成）→ Task 2 异常吞掉 / Task 6 "terminal too small" / Task 5 `ensure_default` ✓
- 测试策略覆盖 probe/buffer/braille/config/render/app → Task 1-7 各自带测试 ✓

**2. Placeholder scan：** 无 TBD/TODO，每个代码步骤均含完整代码与可运行命令。✓

**3. Type consistency：**
- `SampleBuffer(maxlen)` / `.add` / `.values` / `.stats()->Stats`：Task 3 定义，Task 6/7 一致使用 ✓
- `Stats` 字段 last/avg/min/max/loss/jitter/count：Task 3 定义，Task 6 header 使用 last/avg/max/loss ✓
- `Canvas(width_chars, height_chars)` / `.set` / `.char_rows` / `.plain_rows`、`plot_series(canvas, values, scale, color_fn, miss_color)`：Task 4 定义，Task 6 一致调用 ✓
- `Thresholds(green, yellow)` / `Target(name, host, port)` / `Config(...)`：Task 5 定义，Task 6/7 一致使用 ✓
- `color_for(latency, thresholds)`：Task 6 定义并自用 ✓
- `probe_tcp(host, port, timeout)`：Task 2 定义，Task 7 调用一致 ✓
- `_handle_key(ch, state, stop)` / `probe_loop(target, buffer, interval, timeout, state)`：Task 7 定义与测试签名一致 ✓

无不一致项。计划完成。
