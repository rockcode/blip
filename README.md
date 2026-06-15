# blip

终端里的 API 延迟「电波图」——用 Braille 示波器波形实时监控本机到多个大模型 API 的 TCP 建连延迟。纯 Python 标准库，零依赖。

```
api.anthropic.com          42ms   avg 48   max 120   loss 0%
120┤                              ⠙⢠
   │        ⢠           ⢠⡀        ⢰⠙⢤    ⢠⡀
 60┤   ⢠⣤⠒⠐⠉⠲⢤⡀  ⢠⣤⢰⠒⠐  ⠉⠲⢤⣀⠤⠐    ⠘⢢⡀⢠⠐ ⠉
  0┼──────────────────────────────────────────  ◀ 滚动
```

## 运行

    python3 blip.py            # 用默认/已有配置(监控全部目标)
    python3 blip.py -c my.toml # 指定配置文件
    python3 blip.py anthropic  # 只监控名为 anthropic 的单个目标(也可写 -anthropic)

首次运行会在 `~/.config/blip/config.toml` 生成默认配置（含 Anthropic / OpenAI / Google / DeepSeek）。

需要 Python 3.11+（依赖标准库 `tomllib`）；无任何第三方依赖。

## 操作

- `q` 或 `Ctrl-C` 退出
- `p` 暂停 / 继续

## 配置

查找顺序：`-c 指定` → `./config.toml` → `~/.config/blip/config.toml`。

    interval  = 1.0         # 采样间隔(秒)
    timeout   = 2.0         # 建连超时(秒)
    mode      = "tls"       # 测量方式: tcp / tls / http
    scale_max = 800         # 纵轴固定上限(ms)，所有面板统一以便横向对比

    [thresholds]
    bright = 100            # ms 以下: 亮绿(极佳)
    green  = 200            # ms 以下: 绿
    yellow = 400            # ms 以下: 黄, 以上: 红

    [[targets]]
    name = "anthropic"
    host = "api.anthropic.com"
    port = 443

颜色（四档，越快越亮）：`<bright` 亮绿、`<green` 绿、`<yellow` 黄、`>=yellow` 红；超时/失败显示红色满格尖刺并计入 loss。

## 测量方式（mode）

| mode | 含义 | 适用 |
|------|------|------|
| `tcp` | TCP 建连耗时 | 局域网/无代理；**注意：TUN 模式 VPN 会就地应答握手，使该值严重偏低失真** |
| `tls` | TCP+TLS 握手耗时（默认） | 真实网络 RTT，不需 key、不刷请求、TUN 代理下不失真 |
| `http` | HTTPS 首字节耗时（发 HEAD） | 最贴近真实体验（含服务端处理），开销稍高 |

## 工作原理

对每个 `host:443` 异步测量延迟（默认 TLS 握手，见上表），不需要 API key、不产生计费调用、不受 ICMP 屏蔽影响；采样写入环形缓冲，每个目标用一块 Braille 画布画成向左滚动的波形。

## 流量监控（macOS）

检测到 macOS 的 `nettop` 时**自动启用**，表头追加本机到该 API 的实时上/下行速率：

```
anthropic   42ms  avg 48  max 120  loss 0%   ↓1.2M/s ↑45K/s
```

原理：在 TUN + fake-IP 代理下，每个域名分到一个**独占假 IP**；把域名解析成假 IP，再用 `nettop`（免 sudo）按远端 IP 逐连接统计收发字节、差分得速率。流量约每 5~6 秒刷新一次（nettop 自身较慢，在线程里跑、不阻塞延迟波形）。

**仅在 fake-IP 环境下准确**：裸网/真实 CDN 共享 IP 下无法按域名区分流量；非 macOS / 无 nettop 时该功能自动隐藏。

## 测试

    python3 -m unittest discover -s tests -v
