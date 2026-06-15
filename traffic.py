"""按目标假 IP 统计上/下行速率（macOS 的 nettop，免 sudo）。

TUN+fake-IP 环境下每个域名分到一个独占假 IP，故把域名解析成假 IP、再按
nettop 报的「远端 IP」聚合每条连接的累计收发字节，差分即得速率。
"""
import asyncio
import ipaddress
import shutil
import socket
import subprocess


def available():
    """系统是否有 nettop（即可统计流量）。"""
    return shutil.which("nettop") is not None


def canon_ip(s):
    """把 IP 归一为低 32 位整数；非法返回 None。

    使 198.18.0.12 与其映射形 ::ffff:0:c612:c 归一相等。
    """
    try:
        return int(ipaddress.ip_address(s)) & 0xFFFFFFFF
    except ValueError:
        return None


def resolve_fake_ips(host):
    """域名解析得到的 canon IP 集合（拿不到返回空集）。"""
    ips = set()
    try:
        for info in socket.getaddrinfo(host, None):
            c = canon_ip(info[4][0])
            if c is not None:
                ips.add(c)
    except OSError:
        pass
    return ips


_PROTOS = ("tcp4", "tcp6", "udp4", "udp6")


def parse_nettop(output):
    """解析 nettop 输出，返回每条连接 {conn_key: (remote_canon_ip, in, out)}。

    conn_key 为完整 "本地<->远端" 地址（含本地端口，唯一标识一条连接），
    便于逐连接差分；按远端 IP 的聚合交由 TrafficMonitor 完成。
    """
    conns = {}
    for line in output.splitlines():
        if "<->" not in line:
            continue
        parts = line.split()
        if len(parts) < 4 or parts[0] not in _PROTOS:
            continue
        addr = next((p for p in parts if "<->" in p), None)
        if addr is None:
            continue
        try:
            bytes_in, bytes_out = int(parts[-2]), int(parts[-1])
        except ValueError:
            continue
        remote = addr.split("<->", 1)[1]
        # tcp4/udp4 用 host:port，tcp6/udp6 用 host.port
        ip = remote.rsplit(":", 1)[0] if parts[0].endswith("4") \
            else remote.rsplit(".", 1)[0]
        c = canon_ip(ip)
        if c is None:
            continue
        conns[addr] = (c, bytes_in, bytes_out)
    return conns


def _run_nettop_sync(timeout):
    try:
        return subprocess.run(
            ["nettop", "-x", "-l", "1", "-J", "bytes_in,bytes_out"],
            capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


async def run_nettop(timeout=30.0):
    """跑一次 nettop 取累计字节；缺失/出错/超时返回空串。

    用线程执行同步 subprocess（asyncio 子进程在部分 macOS 环境取不到输出）。
    nettop -l 1 实际约 5 秒（偶发更久），故超时给得宽松；线程执行不阻塞事件循环。
    """
    return await asyncio.to_thread(_run_nettop_sync, timeout)


class TrafficMonitor:
    """持每目标累计字节与上次快照，update() 算上/下行速率。"""

    def __init__(self, targets, runner=None, resolver=None):
        self._targets = list(targets)
        self._runner = runner or run_nettop
        self._resolver = resolver or resolve_fake_ips
        self._prev = {}        # conn_key -> (bytes_in, bytes_out)
        self._prev_t = None
        self.rates = {t.name: (0.0, 0.0) for t in self._targets}

    async def update(self, now):
        conns = parse_nettop(await self._runner())   # key -> (ip, in, out)
        if self._prev_t is not None and now > self._prev_t:
            dt = now - self._prev_t
            ipsets = {t.name: self._resolver(t.host) for t in self._targets}
            deltas = {t.name: [0.0, 0.0] for t in self._targets}
            for key, (ip, bin_, bout) in conns.items():
                pin, pout = self._prev.get(key, (0, 0))
                din = max(0.0, bin_ - pin)       # 逐连接差分；新连接整笔计入
                dout = max(0.0, bout - pout)
                for name, ips in ipsets.items():
                    if ip in ips:
                        deltas[name][0] += din
                        deltas[name][1] += dout
            for name, (di, do) in deltas.items():
                self.rates[name] = (di / dt, do / dt)
        self._prev = {key: (bin_, bout) for key, (ip, bin_, bout) in conns.items()}
        self._prev_t = now
