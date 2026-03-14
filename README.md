<div align="center">

# 🔍 ask-search

**Self-hosted web search for AI agents — zero API key, full privacy**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](https://github.com/openclaw/openclaw)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)

*Works in OpenClaw · Claude Code · Antigravity · Any CLI*

</div>

---

## 😡 The Problem

Your AI agent wants to search the web, but:
- Brave Search API: $3/1000 queries, rate limited
- Google Custom Search: $5/1000, daily caps
- Bing API: paid, complex setup
- Built-in web search: sends queries to third-party servers

**You just want your local agent to search Google without paying or leaking queries.**

## ✅ The Solution

`ask-search` wraps [SearxNG](https://github.com/searxng/searxng) — a self-hosted meta search engine that aggregates Google, Bing, DuckDuckGo, Brave and 70+ more sources. One command, all results, zero cost.

```bash
ask-search "Claude Code vs Cursor 2026"
```

```
[1] Claude Code Is Eating Cursor's Lunch
    https://techcrunch.com/2026/...
    After Anthropic launched Claude Code with agent mode...
    [google,brave]

[2] Why I switched from Cursor to Claude Code
    https://reddit.com/r/LocalLLaMA/...
    ...
```

## 📊 Compatibility

| Environment | Integration | Status |
|-------------|-------------|--------|
| **OpenClaw** | CLI Skill (`SKILL.md`) | ✅ |
| **Claude Code** | CLI command | ✅ |
| **Antigravity** | MCP Server | ✅ |
| Any shell | `ask-search` CLI | ✅ |

## 🚀 Quick Start

### 30-second version (if SearxNG already running)

```bash
git clone https://github.com/ythx-101/ask-search
cd ask-search
bash install.sh
ask-search "hello world"
```

### Full setup with Docker Compose (Recommended)

```bash
# Clone and navigate to the project
git clone https://github.com/ythx-101/ask-search
cd ask-search

# Generate a secure secret key
python3 -c "import secrets; print('SEARXNG_SECRET=' + secrets.token_hex(32))"

# Copy .env.example to .env and set your secret key
cp searxng/.env.example searxng/.env
# Edit .env with your generated secret

# Start SearxNG
cd searxng && docker-compose up -d

# Configure ask-search with your secret
export SEARXNG_SECRET="your-generated-secret"
ask-search "hello world"
```

### Full setup (SearxNG + ask-search)

**Step 1: Deploy SearxNG**

```bash
# Docker (recommended)
docker run -d --name searxng \
  -p 127.0.0.1:8080:8080 \
  -e SEARXNG_SECRET_KEY=your-secret-key \
  searxng/searxng

# Or Docker Compose — see searxng/docker-compose.yml in this repo
```

**Step 2: Enable JSON output**

Edit SearxNG `settings.yml`:
```yaml
search:
  formats:
    - html
    - json
```

**Step 3: Install ask-search**

```bash
bash install.sh
```

**Step 4: Use it**

```bash
ask-search "your query"
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

```bash
export SEARXNG_URL="http://localhost:8080"
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
        "SEARXNG_URL": "http://localhost:8080"
      }
    }
  }
}
```

Requires: `pip install mcp`

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
├── install.sh         # Installer
├── SKILL.md           # OpenClaw skill descriptor
└── README.md
```

## ⚠️ SearxNG Setup Notes

- Must enable `json` in `search.formats` in `settings.yml`
- Bot detection may block requests from some IPs — add your server IP to `pass_ip` in `limiter.toml`
- Bind to `127.0.0.1` for security unless you need remote access

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

When direct access fails, try cached versions:

```bash
# Archive.org (works surprisingly often for Reddit)
curl "https://web.archive.org/web/2026/https://reddit.com/r/example/comments/xxx"

# Google Cache (may redirect — not always reliable)
curl "https://webcache.googleusercontent.com/search?q=cache:example.com/page"
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
