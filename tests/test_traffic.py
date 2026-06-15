import unittest

import traffic
from config import Target


SAMPLE = """\
                                              bytes_in       bytes_out
syslogd.569                                          0            4352
apsd.575                                        206170          566657
   tcp6 fd00::10.1<->::ffff:0:c612:c.443             100000            5000
   tcp6 fd00::10.2<->::ffff:0:c612:a.443              20000            3000
   tcp6 fd00::10.3<->::ffff:0:c612:c.443               7000            1000
   udp4 *:*<->*:*
"""


class TestCanonIP(unittest.TestCase):
    def test_ipv4_and_mapped_ipv6_equal(self):
        self.assertEqual(traffic.canon_ip("198.18.0.12"),
                         traffic.canon_ip("::ffff:0:c612:c"))

    def test_invalid_returns_none(self):
        self.assertIsNone(traffic.canon_ip("*"))
        self.assertIsNone(traffic.canon_ip("notanip"))


class TestParseNettop(unittest.TestCase):
    def test_per_connection_with_remote_ip(self):
        conns = traffic.parse_nettop(SAMPLE)
        self.assertEqual(len(conns), 3)   # 3 条 tcp 连接(进程行/星号行跳过)
        c = traffic.canon_ip("198.18.0.12")
        o = traffic.canon_ip("198.18.0.10")
        self.assertEqual(set(conns.values()),
                         {(c, 100000, 5000), (c, 7000, 1000), (o, 20000, 3000)})


class TestTrafficMonitor(unittest.IsolatedAsyncioTestCase):
    async def test_per_connection_diff_aggregated_by_target(self):
        ip = traffic.canon_ip("198.18.0.12")
        out1 = "   tcp6 L1<->::ffff:0:c612:c.443   1000   100\n"
        out2 = ("   tcp6 L1<->::ffff:0:c612:c.443   3000   300\n"   # +2000/+200
                "   tcp6 L2<->::ffff:0:c612:c.443    500    50\n")  # 新连接 +500/+50
        out3 = "   tcp6 L1<->::ffff:0:c612:c.443   1000   100\n"    # 计数下降 -> 0
        outputs = iter([out1, out2, out3])

        async def fake_runner():
            return next(outputs)

        def fake_resolver(host):
            return {ip}

        mon = traffic.TrafficMonitor(
            [Target("anthropic", "api.anthropic.com")],
            runner=fake_runner, resolver=fake_resolver)

        await mon.update(now=100.0)                  # 首次无上次 -> 0
        self.assertEqual(mon.rates["anthropic"], (0.0, 0.0))

        await mon.update(now=102.0)                  # dt=2: L1 +2000/+200, L2 新 +500/+50
        down, up = mon.rates["anthropic"]
        self.assertAlmostEqual(down, 1250.0)         # (2000+500)/2
        self.assertAlmostEqual(up, 125.0)            # (200+50)/2

        await mon.update(now=104.0)                  # L1 计数下降->0, L2 消失
        self.assertEqual(mon.rates["anthropic"], (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
