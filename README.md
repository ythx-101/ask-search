<div align="center">

# 🔍 ask-search

**Self-hosted web search for AI agents — no search API key needed**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](https://github.com/openclaw/openclaw)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)

*Works in OpenClaw · Claude Code · Antigravity · Any CLI*

</div>

ask-search is a self-hosted web search CLI and MCP server for AI agents. It wraps SearxNG so Claude Code, OpenClaw, Antigravity or any shell can search Google, Bing, DuckDuckGo, Brave and more without a paid search API key. Tavily is an optional backend.

给 AI Agent 用的自托管联网搜索：包装 SearxNG，一条命令 / 一个 MCP server 就能聚合 Google、Bing、DuckDuckGo、Brave 等搜索结果，无需付费搜索 API key。

Python: CLI 3.8+; MCP server 3.10+ (required by the `mcp` package).

---

## 😡 The Problem

Your AI agent wants to search the web, but:
- Most search APIs need a key, cost money, and are rate limited
- Built-in web search sends your queries to third-party services

**You just want your local agent to search Google and friends without a paid API.**

## ✅ The Solution

`ask-search` wraps [SearxNG](https://github.com/searxng/searxng) — a self-hosted meta search engine that aggregates Google, Bing, DuckDuckGo, Brave and many more sources. One command, all results, no per-query fees.

```bash
ask-search "Claude Code vs Cursor 2026"
```

```
[1] Example result title
    https://example.com/article-1
    Example snippet text...
    [google,brave]

[2] Another example result title
    https://example.com/article-2
    ...
```

*(illustrative output)*

## 📊 Compatibility

| Environment | Integration | Status |
|-------------|-------------|--------|
| **OpenClaw** | CLI Skill (`SKILL.md`) | ✅ |
| **Claude Code** | CLI command | ✅ |
| **Antigravity** | MCP Server | ✅ |
| Any shell | `ask-search` CLI | ✅ |

## 🚀 Quick Start

**1. Start SearxNG** (Docker Compose, recommended)

```bash
git clone https://github.com/ythx-101/ask-search
cd ask-search/searxng
cp .env.example .env      # then set SEARXNG_SECRET (python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up -d
```

Or with plain `docker run`:

```bash
docker run -d --name searxng \
  -p 127.0.0.1:8080:8080 \
  -e SEARXNG_SECRET=your-secret-key \
  -v "$PWD/searxng/searxng.yml:/etc/searxng/settings.yml" \
  searxng/searxng
```

**2. Install the command**

```bash
bash install.sh              # or: sudo bash install.sh, or: bash install.sh ~/.local/bin
```

**3. Search**

```bash
ask-search "hello world"
```

### Already have SearxNG?

```bash
git clone https://github.com/ythx-101/ask-search
cd ask-search
bash install.sh
export SEARXNG_URL=http://localhost:8080   # if not the default
ask-search "hello world"
```

Your SearxNG must have `json` enabled in `search.formats` in `settings.yml`:

```yaml
search:
  formats:
    - html
    - json
```

## 🔧 Usage

```bash
ask-search "query"                    # top 10 results
ask-search "query" --num 5            # limit results
ask-search "AI news" --categories news # news only
ask-search "query" --lang zh-CN       # language filter
ask-search "query" --urls-only        # URLs only (pipe to web_fetch)
ask-search "query" --json             # raw JSON
ask-search "query" -e google,brave    # specific engines
```

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | `http://localhost:8080` | SearxNG endpoint |
| `SEARCH_PROVIDER` | `searxng` | Search backend: `searxng` or `tavily` |
| `TAVILY_API_KEY` | *(none)* | Tavily API key (required when `SEARCH_PROVIDER=tavily`) — get one at [app.tavily.com](https://app.tavily.com) |

```bash
# SearxNG (default)
export SEARXNG_URL="http://localhost:8080"
ask-search "query"

# Tavily (opt-in)
export SEARCH_PROVIDER=tavily
export TAVILY_API_KEY=tvly-YOUR_API_KEY
ask-search "query"
```

## 🤖 MCP Integration (Antigravity / Claude Code)

```json
{
  "mcpServers": {
    "ask-search": {
      "command": "python3",
      "args": ["/path/to/ask-search/mcp/server.py"],
      "env": {
        "SEARXNG_URL": "http://localhost:8080",
        "TAVILY_API_KEY": "tvly-YOUR_API_KEY"
      }
    }
  }
}
```

Requires Python 3.10+ and `pip install mcp`.

Claude Code one-liner:

```bash
claude mcp add ask-search -e SEARXNG_URL=http://localhost:8080 -- python3 /path/to/ask-search/mcp/server.py
```

MCP tools provided:
- `web_search` — search via SearxNG
- `web_search_news` — news search via SearxNG
- `web_search_tavily` — search via Tavily API (requires `TAVILY_API_KEY`)

## 🦞 OpenClaw Skill

Copy `SKILL.md` to your OpenClaw skills directory, or:

```bash
# OpenClaw skill loader
skill-add https://github.com/ythx-101/ask-search
```

Then in OpenClaw:
```
ask-search "latest news about X"
```

## 🤝 Agent Workflow

```bash
# 1. Search
ask-search "React Server Components performance 2026" --num 10

# 2. Got a promising URL? Deep-dive:
# Pass the URL to web_fetch / curl for full content

# 3. News mode
ask-search "GPT-5 release" --categories news --lang en
```

## 📁 Structure

```
ask-search/
├── scripts/
│   └── core.py        # Main logic, CLI entry point
├── mcp/
│   └── server.py      # MCP server for AG/CC integration
├── searxng/           # Docker Compose + settings.yml for SearxNG
├── tests/             # unit tests (stdlib unittest, no network)
├── install.sh         # Installer
├── SKILL.md           # OpenClaw skill descriptor
├── llms.txt           # Summary for LLM crawlers
└── README.md
```

## ⚠️ SearxNG Setup Notes

- Must enable `json` in `search.formats` in `settings.yml`
- Bot detection may block requests from some IPs — add your server IP to `pass_ip` in `limiter.toml`
- Bind to `127.0.0.1` for security unless you need remote access

## 🧭 When to use

| Option | API key | Self-hosted | Notes |
|---|---|---|---|
| ask-search + SearxNG | No | Yes | You maintain a SearxNG container |
| ask-search + Tavily | Yes (Tavily) | No | Use when you don't want to run SearxNG |
| Commercial search APIs | Yes | No | Pay-per-use |
| Built-in agent web search | Depends on platform | No | Queries go through the platform provider |
| Perplexica | No | Yes | Full AI search app with a UI; ask-search is a minimal CLI take on the same idea |

Privacy note: no third-party search API sees your queries; SearxNG forwards them to upstream engines from your own server.

## ❓ FAQ

**Does ask-search need an API key?**
Not in the default SearxNG mode. In Tavily mode (`SEARCH_PROVIDER=tavily`) you need `TAVILY_API_KEY`.

**How do I use it in Claude Code?**
Call the CLI from Bash (`ask-search "query"`), or register the MCP server (see MCP Integration above).

**Why do I get 403 or "SearxNG did not return JSON"?**
`json` must be listed in `search.formats` in SearxNG's `settings.yml` (the bundled `searxng/searxng.yml` does this). If requests are blocked by the bot limiter, add your IP to `pass_ip` in `limiter.toml`.

**Is it really private?**
No third-party search API sees your queries, but SearxNG still forwards them to upstream engines (Google, Bing, etc.) from your own server's IP.

**How do I search in Chinese or get news only?**
`ask-search "query" --lang zh-CN` and `ask-search "query" --categories news`.

**Can I use Tavily instead of SearxNG?**
Yes: `export SEARCH_PROVIDER=tavily TAVILY_API_KEY=tvly-YOUR_API_KEY`, and install `tavily-python` (`pip install tavily-python`; `install.sh` does this automatically when `TAVILY_API_KEY` is set). In Tavily mode `--engines`, `--lang` and `--categories` are ignored.

**Does it work on Windows?**
It needs Python 3 and curl; `install.sh` is a bash script, so on Windows use WSL. Not tested on native Windows.

**How is it different from Perplexica?**
Perplexica is a full AI search application with a UI. ask-search only returns search results (title, URL, snippet) for an agent to consume, via one CLI command or an MCP server.

## 中文说明

**ask-search** 是给 AI Agent 用的自托管联网搜索工具：包装 SearxNG 元搜索引擎，聚合 Google、Bing、DuckDuckGo、Brave 等结果，无需 API Key（也可选用 Tavily）。支持 Claude Code 搜索、OpenClaw 技能和 MCP 搜索服务器。

快速开始：
1. `cd searxng && cp .env.example .env && docker compose up -d` 启动 SearxNG
2. `bash install.sh` 安装命令
3. `ask-search "你好" --lang zh-CN`

## 🌐 Deep-Dive Limitations & Workarounds

`ask-search` returns URLs + snippets from search engine indexes. When your agent needs the **full page content** (deep-dive via `curl` / `web_fetch`), some sites will block depending on your server's network environment:

### What works out of the box

| Site | Search (SearxNG) | Deep-dive (curl/fetch) | Why |
|------|:-:|:-:|-----|
| Most sites | ✅ | ✅ | No aggressive anti-bot |
| Reddit | ✅ | ❌ VPS IP blocked | Reddit blocks datacenter IPs |
| Zhihu (知乎) | ✅ | ❌ Login wall + fingerprint | Requires browser JS + login |
| Medium | ✅ | ⚠️ Paywall | Partial content only |

**Key insight**: Search always works because SearxNG queries search engines (Google, Brave, etc.), not the target sites directly. The search engines have already indexed the content. The problem only appears when your agent tries to fetch the full page.

### Solution 1: SOCKS proxy via residential IP

If you have a machine on a residential network (home server, laptop, etc.), create an SSH SOCKS tunnel:

```bash
# On your VPS/server:
ssh -f -N -D 127.0.0.1:1082 user@your-home-machine

# Then fetch through the proxy:
curl -x socks5h://127.0.0.1:1082 "https://reddit.com/r/example/comments/xxx.json"
```

For Reddit specifically, append `.json` to any post URL for structured data:
```bash
# Returns full post + all comments as JSON
curl -x socks5h://127.0.0.1:1082 \
  "https://www.reddit.com/r/LocalLLaMA/comments/xxxxx/post_title.json"
```

To persist the tunnel as a systemd service:
```ini
# /etc/systemd/system/socks-proxy.service
[Unit]
Description=SSH SOCKS Proxy for web scraping
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/ssh -N -D 127.0.0.1:1082 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes user@your-home-machine
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Solution 2: Headless browser for JS-heavy sites

Sites like Zhihu require full browser rendering. Use Playwright with the SOCKS proxy:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy={"server": "socks5://127.0.0.1:1082"}
    )
    page = browser.new_page()
    page.goto("https://example.com/article")
    content = page.inner_text("article")
```

> **Note**: Some sites (Zhihu, etc.) detect headless browsers even through proxies. For these, you may need a real browser session with login cookies, or delegate the fetch to an agent running on a local machine (e.g., Claude Code on a Mac).

### Solution 3: Leverage archive caches

When direct access fails, try archived versions:

```bash
# Archive.org (works surprisingly often for Reddit)
curl "https://web.archive.org/web/2026/https://reddit.com/r/example/comments/xxx"
```

### Solution 4: Multi-node agent architecture

If you run agents on multiple machines (e.g., OpenClaw on VPS + Claude Code on local Mac):

```
VPS agent: ask-search "query" → gets URLs + snippets
                ↓
Local agent: web_fetch(url) → full content (residential IP, no blocks)
                ↓
VPS agent: receives full text, analyzes, responds
```

This is the most robust approach — search on your server, deep-dive from a local machine where anti-bot measures don't apply.

### TL;DR

| Problem | Fix |
|---------|-----|
| Reddit blocks your IP | SSH SOCKS proxy + `.json` API |
| Site needs JS rendering | Playwright + proxy |
| Site needs login (Zhihu) | Delegate to local agent or use logged-in browser |
| Everything blocked | Fall back to search snippets + archive caches |

## 🤝 Contributing

Issues and PRs welcome.

## Acknowledgements

Inspired by [Perplexica](https://github.com/ItzCrazyKns/Perplexica) —
the idea of using self-hosted SearxNG as a private search backend comes from there.
ask-search strips it down to a single CLI command for agent use.

## 📄 License

[MIT](LICENSE)
