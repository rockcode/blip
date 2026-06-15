import asyncio
import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from blipmon import app
from blipmon.buffer import SampleBuffer
from blipmon.config import Config, Target, Thresholds


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


class TestSampleTick(unittest.IsolatedAsyncioTestCase):
    async def test_one_sample_added_to_every_buffer(self):
        # 同拍并发采样：每拍给每个目标缓冲区各加一个采样
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        targets = [Target("fast", "127.0.0.1", port),
                   Target("slow", "127.0.0.1", 1)]   # 1 端口拒连 -> None
        buffers = {t.name: SampleBuffer(10) for t in targets}
        async with server:
            await app.sample_tick(targets, buffers, timeout=1.0, mode="tcp")
            await app.sample_tick(targets, buffers, timeout=1.0, mode="tcp")
        self.assertEqual(len(buffers["fast"].values()), 2)
        self.assertEqual(len(buffers["slow"].values()), 2)


class TestTickLoop(unittest.IsolatedAsyncioTestCase):
    async def test_buffers_stay_time_aligned(self):
        # 快目标与慢目标采样数始终相等 = 时间轴锁步对齐(快的不会滚得更快)
        server = await asyncio.start_server(
            lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        cfg = Config(interval=0.01, timeout=0.5, mode="tcp",
                     targets=[Target("fast", "127.0.0.1", port),
                              Target("slow", "127.0.0.1", 1)])
        buffers = {t.name: SampleBuffer(100) for t in cfg.targets}
        state = {"paused": False}
        stop = asyncio.Event()
        out = io.StringIO()
        async with server:
            task = asyncio.create_task(
                app.tick_loop(cfg, buffers, state, out, stop))
            await asyncio.sleep(0.08)
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)
        nf = len(buffers["fast"].values())
        ns = len(buffers["slow"].values())
        self.assertGreaterEqual(nf, 1)
        self.assertEqual(nf, ns)           # 锁步对齐

    async def test_paused_skips_sampling(self):
        cfg = Config(interval=0.01, timeout=0.5, mode="tcp",
                     targets=[Target("a", "127.0.0.1", 1)])
        buffers = {"a": SampleBuffer(100)}
        state = {"paused": True}
        stop = asyncio.Event()
        out = io.StringIO()
        task = asyncio.create_task(
            app.tick_loop(cfg, buffers, state, out, stop))
        await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(task, timeout=2.0)
        self.assertEqual(buffers["a"].values(), [])   # 暂停不采样


class TestTargetSelection(unittest.TestCase):
    def test_none_returns_all(self):
        ts = [Target("a", "h"), Target("b", "h")]
        self.assertEqual(app.select_targets(ts, None), ts)

    def test_by_name_case_insensitive(self):
        ts = [Target("anthropic", "h"), Target("openai", "h")]
        sel = app.select_targets(ts, "Anthropic")
        self.assertEqual([t.name for t in sel], ["anthropic"])

    def test_no_match_returns_empty(self):
        self.assertEqual(app.select_targets([Target("a", "h")], "zzz"), [])


class TestPreprocessArgv(unittest.TestCase):
    def test_dash_name_becomes_positional(self):
        self.assertEqual(app._preprocess_argv(["-anthropic"]), ["anthropic"])

    def test_plain_positional_unchanged(self):
        self.assertEqual(app._preprocess_argv(["anthropic"]), ["anthropic"])

    def test_config_flag_and_value_preserved(self):
        self.assertEqual(app._preprocess_argv(["-c", "x.toml", "-openai"]),
                         ["-c", "x.toml", "openai"])

    def test_help_flag_preserved(self):
        self.assertEqual(app._preprocess_argv(["-h"]), ["-h"])

    def test_version_flag_preserved(self):
        self.assertEqual(app._preprocess_argv(["--version"]), ["--version"])
        self.assertEqual(app._preprocess_argv(["-V"]), ["-V"])

    def test_daemon_flag_preserved(self):
        self.assertEqual(app._preprocess_argv(["--daemon"]), ["--daemon"])

    def test_statusline_flag_and_target_preserved(self):
        self.assertEqual(
            app._preprocess_argv(["--statusline", "anthropic"]),
            ["--statusline", "anthropic"])


class TestVersion(unittest.TestCase):
    def test_version_is_semver(self):
        from blipmon import __version__
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")


class TestTrafficLoop(unittest.IsolatedAsyncioTestCase):
    async def test_drives_update_repeatedly(self):
        stop = asyncio.Event()
        calls = []

        class FakeMonitor:
            rates = {}

            async def update(self, now):
                calls.append(now)
                if len(calls) >= 3:
                    stop.set()

        await asyncio.wait_for(
            app.traffic_loop(FakeMonitor(), stop, pause=0.0), timeout=2.0)
        self.assertGreaterEqual(len(calls), 3)


class TestRunStatusline(unittest.TestCase):
    def _with_cache(self, fn):
        """在隔离的临时 XDG_CACHE_HOME 下执行 fn()，结束后恢复。"""
        tmp = tempfile.mkdtemp()
        old = os.environ.get("XDG_CACHE_HOME")
        os.environ["XDG_CACHE_HOME"] = tmp
        try:
            return fn()
        finally:
            if old is None:
                del os.environ["XDG_CACHE_HOME"]
            else:
                os.environ["XDG_CACHE_HOME"] = old

    def test_prints_one_line_without_spawning(self):
        def body():
            from blipmon import hud
            # 预置状态文件 + 存活锁(当前 pid)，使 run_statusline 不去 spawn
            hud.write_state(hud.state_path(),
                            {"ts": 10 ** 12, "targets": {"anthropic": [42.0]}})
            with open(hud.lock_path(), "w") as f:
                f.write(str(os.getpid()))
            cfg = Config(targets=[Target("anthropic", "h")],
                         thresholds=Thresholds())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = app.run_statusline(cfg, now=10 ** 12)
            out = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertEqual(out.count("\n"), 1)      # 恰好一行
            self.assertIn("anthropic", out)
        self._with_cache(body)

    def test_no_state_prints_starting_and_spawns(self):
        # 无状态文件、无锁：仍打印一行(启动中)、返回0、并尝试拉起 daemon
        def body():
            cfg = Config(targets=[Target("anthropic", "h")],
                         thresholds=Thresholds())
            buf = io.StringIO()
            with mock.patch("blipmon.daemon.spawn_daemon") as spawn:
                with contextlib.redirect_stdout(buf):
                    rc = app.run_statusline(cfg)
            out = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertEqual(out.count("\n"), 1)      # 恰好一行
            self.assertIn("anthropic", out)
            self.assertIn("启动中", out)
            spawn.assert_called_once()                # 无守护进程时拉起
        self._with_cache(body)


if __name__ == "__main__":
    unittest.main()
