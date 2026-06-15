# blip

**中文** · [English](README.en.md)

[![Claude Code 插件](https://img.shields.io/badge/Claude_Code-插件_·_状态栏_HUD-da7756)](#claude-code-状态栏-hud)
[![下载 blip.pyz](https://img.shields.io/badge/下载-blip.pyz-2ea44f?logo=python&logoColor=white)](https://github.com/rockcode/blip/releases/latest/download/blip.pyz)
[![最新版本](https://img.shields.io/github/v/release/rockcode/blip?color=2ea44f&label=release)](https://github.com/rockcode/blip/releases/latest)
[![许可证](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

**Claude Code 插件**：把本机到各大模型 API 的延迟，做成一行常驻状态栏的迷你「电波图」——一眼看清是模型在想、还是网络卡死。也能作为独立终端监控运行。纯 Python 标准库，零依赖。

![blip 状态栏 HUD：⟨blip⟩ 一行实时显示到 anthropic 的延迟](assets/screenshot-statusline.png)

*底部 `⟨blip⟩ anthropic … 289ms` 那行就是 blip，常驻 Claude Code 状态栏。*

## 由来

用 AI 时最难受的不是慢，而是**说不清卡在哪**——回答迟迟不出，是模型还在生成、还是网络早就卡死？该等还是该重来？blip 把到各家 API 的延迟实时画成「电波图」常驻状态栏，扫一眼就先排除「是不是网络的锅」。

## Claude Code 状态栏 HUD

一行单目标迷你波形，常驻状态栏：

    ⟨blip⟩ anthropic ▁▂▃▅▇▆▅ 48ms

后台 `blip --daemon` 每秒采样写状态文件，`blip --statusline` 被状态栏调用时读取渲染、按需自动拉起守护进程，Claude Code 关闭后空闲自退。

### 从插件市场安装（推荐）

```text
/plugin marketplace add rockcode/blip   # 1. 添加市场
/plugin install blip-hud@blip           # 2. 安装插件
/reload-plugins                         # 3. 重载生效
/blip-hud                               # 4. 接好状态栏
```

插件自带 `blip.pyz`，装上即用（机器需 Python 3.11+）。`/blip-hud` 把 `statusLine` 写进 `~/.claude/settings.json`；已有状态栏会先问替换还是叠加。

### 手动配置

不用插件，手动加进 `~/.claude/settings.json`：

```json
"statusLine": {
  "type": "command",
  "command": "python3 \"/path/to/blip.py\" --statusline anthropic",
  "refreshInterval": 2
}
```

**`refreshInterval` 别省**——没有它状态栏只在事件后刷新、迷你图不会自动走（设 `1` 更跟手）。

## 独立运行：终端全屏监控

直接在终端跑，多个 API 延迟并排成全屏滚动「电波图」，表头带实时上/下行速率（macOS）：

![blip：四家大模型 API 并排，延迟波形 + 表头实时上/下行速率](assets/screenshot-overview.png)

到 [Releases](https://github.com/rockcode/blip/releases) 下单文件 `blip.pyz` 即跑，或用源码（均需 Python 3.11+）：

    ./blip.pyz                 # 监控全部目标
    ./blip.pyz anthropic       # 只看单个目标
    python3 blip.py            # 从源码跑

首次运行生成 `~/.config/blip/config.toml`（预置 Anthropic / OpenAI / Google / DeepSeek）。`q` 退出、`p` 暂停。

### 流量监控（macOS）

检测到 `nettop` 时自动在表头加实时上/下行速率：

```
anthropic   42ms  avg 48  max 120  loss 0%   ↓1.2M/s ↑45K/s
```

TUN + fake-IP 下每个域名分到独占假 IP，用 `nettop`（免 sudo）按 IP 逐连接差分得速率。**仅 fake-IP 环境准确**；非 macOS / 无 nettop 自动隐藏。

## 配置

查找顺序：`-c 指定` → `./config.toml` → `~/.config/blip/config.toml`。

    interval  = 1.0         # 采样间隔(秒)
    timeout   = 2.0         # 建连超时(秒)
    mode      = "tls"       # 测量方式: tcp / tls / http
    scale_max = 800         # 纵轴固定上限(ms)，便于横向对比

    [thresholds]            # <100 亮绿  <200 绿  <400 黄  >=400 红
    bright = 100
    green  = 200
    yellow = 400

    [[targets]]
    name = "anthropic"
    host = "api.anthropic.com"
    port = 443

超时/失败显示红色满格尖刺并计入 loss。

## 测量方式（mode）

| mode | 含义 | 适用 |
|------|------|------|
| `tcp` | TCP 建连耗时 | 局域网/无代理；**TUN VPN 就地应答握手致失真** |
| `tls` | TCP+TLS 握手（默认） | 真实 RTT，免 key、不刷请求、TUN 下不失真 |
| `http` | HTTPS 首字节（HEAD） | 最贴近真实体验，开销稍高 |

测量不需 API key、不产生计费调用、不受 ICMP 屏蔽影响。

## 测试

    python3 -m unittest discover -s tests -v

## 许可

[MIT](LICENSE) © 2026 rockcode
