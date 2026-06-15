import os
import tempfile
import unittest

from blipmon import hud
from blipmon.config import Thresholds


class TestBlockFor(unittest.TestCase):
    def test_zero_is_lowest_block(self):
        self.assertEqual(hud.block_for(0, 800), hud.BLOCKS[0])

    def test_scale_max_is_full_block(self):
        self.assertEqual(hud.block_for(800, 800), hud.BLOCKS[-1])

    def test_over_scale_is_capped_full(self):
        self.assertEqual(hud.block_for(5000, 800), hud.BLOCKS[-1])

    def test_none_is_full_block(self):
        # 超时/失败 = 满格尖刺（最显眼），沿用全屏版的设计语言
        self.assertEqual(hud.block_for(None, 800), hud.BLOCKS[-1])

    def test_scale_zero_returns_lowest_block(self):
        # 退化刻度(<=0)防崩溃：任意真实延迟都落到最低格
        self.assertEqual(hud.block_for(100, 0), hud.BLOCKS[0])


class TestSparkline(unittest.TestCase):
    def test_one_reset_per_sample(self):
        th = Thresholds()
        line = hud.sparkline([50, 150, 300, None], 800, th)
        # 逐字符染色：每个样本一段 colorize（以 RESET 收尾）
        self.assertEqual(line.count("\x1b[0m"), 4)

    def test_empty_is_empty(self):
        self.assertEqual(hud.sparkline([], 800, Thresholds()), "")


class TestStateIO(unittest.TestCase):
    def test_roundtrip(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "sub", "state.json")
        state = {"ts": 123.0, "targets": {"anthropic": [10.0, None, 20.0]}}
        hud.write_state(p, state)
        self.assertEqual(hud.read_state(p), state)

    def test_missing_returns_none(self):
        self.assertIsNone(hud.read_state("/no/such/state.json"))

    def test_corrupt_returns_none(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "state.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertIsNone(hud.read_state(p))


class TestRenderLine(unittest.TestCase):
    def _state(self, ts, series):
        return {"ts": ts, "targets": {"anthropic": series}}

    def test_no_state_shows_starting(self):
        line = hud.render_line(None, "anthropic", Thresholds(), 800, now=1000)
        self.assertIn("anthropic", line)
        self.assertIn("启动中", line)

    def test_target_absent_shows_starting(self):
        st = self._state(1000, [10.0])  # 只有 anthropic
        line = hud.render_line(st, "openai", Thresholds(), 800, now=1000)
        self.assertIn("启动中", line)
        self.assertIn("openai", line)   # 启动中也回显目标名

    def test_empty_series_shows_starting(self):
        st = self._state(1000, [])      # 已登记但还没样本
        line = hud.render_line(st, "anthropic", Thresholds(), 800, now=1000)
        self.assertIn("启动中", line)

    def test_fresh_has_color_and_ms(self):
        st = self._state(1000, [10.0, 20.0, 30.0])
        line = hud.render_line(st, "anthropic", Thresholds(), 800, now=1001)
        self.assertIn("anthropic", line)
        self.assertIn("30ms", line)         # 最新值
        self.assertIn("\x1b[38;2;", line)   # 含真彩色
        self.assertNotIn("stale", line)

    def test_stale_is_dimmed_and_marked(self):
        st = self._state(1000, [10.0, 20.0])
        # now 远晚于 ts -> 过期
        line = hud.render_line(st, "anthropic", Thresholds(), 800, now=9999)
        self.assertIn("stale", line)
        self.assertIn(hud.ansi.fg(hud.ansi.DIM), line)


if __name__ == "__main__":
    unittest.main()
