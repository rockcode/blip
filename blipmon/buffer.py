"""每个目标的环形采样缓冲与滚动统计。"""
from collections import deque
from dataclasses import dataclass


@dataclass
class Stats:
    last: float | None
    avg: float | None
    min: float | None
    max: float | None
    loss: float           # 0.0 ~ 1.0
    jitter: float | None
    count: int


class SampleBuffer:
    def __init__(self, maxlen):
        self._samples = deque(maxlen=maxlen)

    def add(self, latency):
        """latency: 成功为 float 毫秒，miss/超时为 None。"""
        self._samples.append(latency)

    def values(self):
        return list(self._samples)

    def stats(self):
        vals = list(self._samples)
        total = len(vals)
        oks = [v for v in vals if v is not None]
        misses = total - len(oks)
        loss = (misses / total) if total else 0.0
        if oks:
            avg = sum(oks) / len(oks)
            mn = min(oks)
            mx = max(oks)
            deltas = [abs(oks[i] - oks[i - 1]) for i in range(1, len(oks))]
            jitter = (sum(deltas) / len(deltas)) if deltas else 0.0
        else:
            avg = mn = mx = None
            jitter = None
        last = vals[-1] if vals else None
        return Stats(last=last, avg=avg, min=mn, max=mx,
                     loss=loss, jitter=jitter, count=total)
