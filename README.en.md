# blip

[中文](README.md) · **English**

[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin_·_status--line_HUD-da7756)](#claude-code-status-line-hud)
[![Download blip.pyz](https://img.shields.io/badge/download-blip.pyz-2ea44f?logo=python&logoColor=white)](https://github.com/rockcode/blip/releases/latest/download/blip.pyz)
[![Latest release](https://img.shields.io/github/v/release/rockcode/blip?color=2ea44f&label=release)](https://github.com/rockcode/blip/releases/latest)
[![license](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

**A Claude Code plugin** that renders the latency from your machine to the major LLM APIs as a one-line mini "oscilloscope" in your status line — one glance shows whether the model is thinking or the network has frozen. Also runs standalone as a full-screen terminal monitor. Pure Python standard library, zero dependencies.

![blip status-line HUD: the ⟨blip⟩ line showing live latency to anthropic](assets/screenshot-statusline.png)

## Why

The worst part of using AI isn't slowness — it's **not being able to tell where it's stuck**: a reply hangs, and is the model still generating or did the connection die ages ago? Keep waiting or retry? blip paints the latency to each API as a live "oscilloscope" in your status line, so a glance rules out (or pins down) "is it the network?"

## Claude Code status-line HUD

A single-line, single-target mini-waveform in your status line:

    ⟨blip⟩ anthropic ▁▂▃▅▇▆▅ 48ms

`blip --daemon` samples once a second in the background and writes a state file; `blip --statusline` (called by the status line) reads and renders one line, auto-spawning the daemon as needed. The daemon self-exits once Claude Code closes.

### Install from the plugin marketplace (recommended)

```text
/plugin marketplace add rockcode/blip   # 1. add the marketplace
/plugin install blip-hud@blip           # 2. install the plugin
/reload-plugins                         # 3. reload to apply
/blip-hud                               # 4. wire up the status line
```

The plugin bundles `blip.pyz`, so it works on install (needs Python 3.11+). `/blip-hud` writes the `statusLine` into `~/.claude/settings.json`; if you already have one it asks whether to replace or stack.

### Manual setup

Without the plugin, add this to `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python3 \"/path/to/blip.py\" --statusline anthropic",
  "refreshInterval": 2
}
```

**Don't omit `refreshInterval`** — without it the status line only refreshes on events and the mini-waveform won't advance (use `1` for a snappier tick).

## Standalone: full-screen terminal monitor

Run it in a terminal to watch several APIs side by side as full-screen scrolling waveforms, with live up/down throughput per header (macOS):

![blip: four LLM APIs side by side, latency waveforms + live up/down rates in the headers](assets/screenshot-overview.png)

![Working in Claude Code with blip pinned to the bottom of the terminal, watching the network](assets/screenshot-inline.png)

![Whole-screen workflow: collaborating with AI on one side, blip watching every API on the other](assets/screenshot-split.png)

Grab the single file `blip.pyz` from [Releases](https://github.com/rockcode/blip/releases), or use the source (both need Python 3.11+):

    ./blip.pyz                 # watch all targets
    ./blip.pyz anthropic       # watch a single target
    python3 blip.py            # run from source

The first run writes `~/.config/blip/config.toml` (Anthropic / OpenAI / Google / DeepSeek). `q` quits, `p` pauses.

### Traffic (macOS)

When `nettop` is detected, blip auto-appends live up/down throughput to each header:

```
anthropic   42ms  avg 48  max 120  loss 0%   ↓1.2M/s ↑45K/s
```

Under a TUN + fake-IP proxy each domain gets its own fake IP; `nettop` (no sudo) tallies per-connection bytes by IP and diffs them into a rate. **Only accurate under fake-IP**; hidden on non-macOS / without `nettop`.

## Configuration

Lookup order: `-c <path>` → `./config.toml` → `~/.config/blip/config.toml`.

    interval  = 1.0         # sampling interval (seconds)
    timeout   = 2.0         # connection timeout (seconds)
    mode      = "tls"       # measurement: tcp / tls / http
    scale_max = 800         # fixed Y-axis max (ms), shared across panels

    [thresholds]            # <100 bright green  <200 green  <400 yellow  >=400 red
    bright = 100
    green  = 200
    yellow = 400

    [[targets]]
    name = "anthropic"
    host = "api.anthropic.com"
    port = 443

A timeout/failure shows a full-height red spike and counts toward loss.

## Measurement (mode)

| mode | what it measures | when to use |
|------|------|------|
| `tcp` | TCP connect time | LAN / no proxy. **A TUN VPN answers the handshake locally → distorted** |
| `tls` | TCP+TLS handshake (default) | real RTT; no API key, no real requests, undistorted under a TUN proxy |
| `http` | HTTPS first byte (HEAD) | closest to real experience, slightly heavier |

Measurement needs no API key, makes no billable calls, and is unaffected by ICMP blocking.

## Tests

    python3 -m unittest discover -s tests -v

## License

[MIT](LICENSE) © 2026 rockcode
