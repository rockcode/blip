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


class TestProbeTLS(unittest.IsolatedAsyncioTestCase):
    async def test_tls_to_plain_server_returns_none(self):
        # 对纯 TCP(非 TLS) 服务器做 TLS 握手会失败 -> None
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            result = await probe.probe_tls("127.0.0.1", port, timeout=1.0)
        self.assertIsNone(result)

    async def test_tls_refused_returns_none(self):
        self.assertIsNone(await probe.probe_tls("127.0.0.1", 1, timeout=1.0))


class TestProbeHTTP(unittest.IsolatedAsyncioTestCase):
    async def test_http_refused_returns_none(self):
        self.assertIsNone(await probe.probe_http("127.0.0.1", 1, timeout=1.0))


class TestMeasureDispatch(unittest.IsolatedAsyncioTestCase):
    async def test_measure_tcp_mode_hits_plain_server(self):
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            result = await probe.measure("127.0.0.1", port,
                                         timeout=1.0, mode="tcp")
        self.assertIsInstance(result, float)

    async def test_measure_default_mode_is_tls(self):
        # 默认 tls：对纯 TCP server 应握手失败 -> None
        # （若默认仍是 tcp 则会返回 float，故 None 反证默认走 tls）
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            result = await probe.measure("127.0.0.1", port, timeout=1.0)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
