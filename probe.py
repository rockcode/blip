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
