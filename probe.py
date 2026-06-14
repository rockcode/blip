"""异步延迟探测：tcp(建连) / tls(握手) / http(首字节)。

注意：TUN 模式 VPN/本地代理会就地应答 TCP 三次握手，使 tcp 建连时间严重
偏低（测的是本地栈，不是真实服务器）。tls/http 必须把字节中转到真实上游，
代理伪造不了，故能反映真实 RTT —— 默认用 tls。
"""
import asyncio
import ssl
import time

_TLS_CTX = None


def _tls_context():
    """复用一个只测延迟、不校验证书的 TLS 上下文。"""
    global _TLS_CTX
    if _TLS_CTX is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _TLS_CTX = ctx
    return _TLS_CTX


async def _close(writer):
    writer.close()
    try:
        await writer.wait_closed()
    except (OSError, ssl.SSLError):
        pass


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
    await _close(writer)
    return elapsed_ms


async def probe_tls(host, port, timeout):
    """测量 TCP+TLS 握手完成耗时(ms)。超时/连接失败/握手失败返回 None。"""
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=_tls_context(),
                                    server_hostname=host),
            timeout=timeout)
    except (OSError, asyncio.TimeoutError, ssl.SSLError, ValueError):
        return None
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    await _close(writer)
    return elapsed_ms


async def probe_http(host, port, timeout):
    """测量 HTTPS 请求首字节耗时(ms)：建连+握手后发 HEAD，读到首行响应。

    超时/连接失败/无响应返回 None。
    """
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=_tls_context(),
                                    server_hostname=host),
            timeout=timeout)
    except (OSError, asyncio.TimeoutError, ssl.SSLError, ValueError):
        return None
    line = b""
    try:
        request = (f"HEAD / HTTP/1.1\r\nHost: {host}\r\n"
                   f"User-Agent: blip\r\nConnection: close\r\n\r\n")
        writer.write(request.encode())
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    except (OSError, asyncio.TimeoutError, ssl.SSLError):
        line = b""
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    await _close(writer)
    return elapsed_ms if line else None


async def measure(host, port, timeout, mode="tls"):
    """按 mode 选择探测方式，统一返回毫秒数或 None。"""
    if mode == "tcp":
        return await probe_tcp(host, port, timeout)
    if mode == "http":
        return await probe_http(host, port, timeout)
    return await probe_tls(host, port, timeout)
