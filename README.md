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

## 🤝 Contributing

Issues and PRs welcome.

## 📄 License

[MIT](LICENSE)
