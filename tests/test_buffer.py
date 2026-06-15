import unittest

from blipmon.buffer import SampleBuffer


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
