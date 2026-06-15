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
        with open(p, "w") as f:
            f.write("{not json")
        self.assertIsNone(hud.read_state(p))


if __name__ == "__main__":
    unittest.main()
