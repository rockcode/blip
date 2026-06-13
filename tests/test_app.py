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
