# blip 流量监控（实时上/下行速率） 设计文档

- 日期: 2026-06-15
- 状态: 已批准

## 一句话目标

在每个 API 面板的表头实时显示本机到该 API 的上/下行速率（↓下载 ↑上传），检测到 macOS 的 `nettop` 时自动启用。

## 关键原理

操作系统/`nettop` 在连接层面只看得到**远端 IP**，看不到域名。本机跑 TUN 模式 + fake-IP（Clash/sing-box 等）时，**每个域名分配一个独占的假 IP**（如 api.anthropic.com → 198.18.0.12，api.openai.com → 198.18.0.10，各不相同、零共享）。因此：

- 把域名 `getaddrinfo` 解析成它的假 IP；
- `nettop` 按远端 IP 分别报每条连接的累计收发字节；
- 匹配「远端 IP == 目标假 IP」的连接求和，即得该域名的流量。

流量物理上都走同一隧道接口（utun8），但每条连接的**远端地址是各域名专属的假 IP**，故可区分。

**适用边界**：fake-IP 环境下准确；非 fake-IP（裸网 / 真实 CDN 共享 IP）下无法只挑出单个域名的流量，此时该数仅供参考。直连域名（拿到真实专属 IP）也准。

## 决策

| 维度 | 决策 |
|------|------|
| 指标 | 实时上/下行速率（B·K·M/s 自动缩放），非累计总量 |
| 启用 | 检测到 `nettop` 自动开；无 nettop / 非 macOS 自动隐藏（无配置项） |
| 显示 | 各面板表头末尾追加 `↓<rate>/s ↑<rate>/s`，中性灰色（不抢延迟配色），窄终端照常截断 |
| 采集 | 跑 `nettop -x -l 1 -J bytes_in,bytes_out`（免 sudo）。**nettop 实测约 5 秒/次（偶发更久），故用 `asyncio.to_thread` 在线程里执行、不阻塞 1s 的延迟波形循环；超时 30s。流量天然每 ~5–6 秒刷新一次** |
| 速率算法 | **逐连接差分**：按「本地<->远端」唯一键各自算 (本次−上次) 字节、负值钳 0（新连接整笔计入），再按目标假 IP 求和 ÷ 实际间隔。注：完全在两次快照之间开/关的短连接会漏计，但持续/长连接（如 LLM 流式）能抓到 |

## 模块

- `traffic.py`
  - `available()` → `shutil.which("nettop") is not None`
  - `canon_ip(s)` → IP 归一为低 32 位整数（使 `198.18.0.12` 与映射形 `::ffff:0:c612:c` 相等）；非法返回 None
  - `resolve_fake_ips(host)` → `getaddrinfo` 得到的 canon IP 集合
  - `parse_nettop(output)` → `{canon_ip: (bytes_in, bytes_out)}`（解析所有 `<->` 连接行）
  - `async run_nettop(timeout)` → 跑 nettop 返回 stdout；出错/缺失返回 ""
  - `class TrafficMonitor(targets, runner=None, resolver=None)`：持每目标累计与上次快照，`async update(now)` 算速率，暴露 `rates = {name: (down_bps, up_bps)}`；runner/resolver 可注入便于测试
- `app.py`：若 `traffic.available()` 起一个 `traffic_loop` 周期 `update`；`tick_loop`/`_draw` 把 `monitor.rates` 传给 render
- `render.py`：`render_frame`/`render_panel`/`format_header` 增加可选 `rate`，有则表头追加 ↓↑

## 数据流

```
nettop 输出 ──parse_nettop──► {远端IP:(in,out)}
                                │ 按各目标假IP集合求和
                                ▼
            每目标累计(in,out) ──(本次-上次)/dt, 钳零──► rates{name:(↓,↑)}
                                ▼
            render 表头追加 ↓1.2M/s ↑45K/s
```

## 健壮性

- `nettop` 缺失/失败/超时 → `run_nettop` 返回 ""，本次跳过、不崩、保留上次速率。
- 无匹配（非 fake-IP）→ 该目标速率 0。
- 假 IP 可能被代理回收重分配 → 每次 `update` 重新解析域名拿最新假 IP。
- 解析异常一律忽略该行，不影响其余。

## 测试（TDD）

- `canon_ip`：IPv4 与映射 IPv6 归一相等；非法返回 None。
- `parse_nettop`：喂样例 nettop 输出，断言按远端 IP 聚合的收发字节；跳过无字节/星号行。
- `TrafficMonitor.update`：注入假 runner（两次不同累计）+ 假 resolver + 注入 now，断言速率 = 差分/dt 且负值钳零。
- `render`：表头给定 rate 时包含 ↓/↑。
- `traffic_loop`：注入 monitor，跑数拍后 `rates` 被更新。

## 不做（YAGNI）

不做流量历史曲线、累计总量、按进程拆分、抓包/SNI 精确归属、配置开关。
