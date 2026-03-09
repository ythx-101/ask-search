---
name: ask-search
description: "Web search via self-hosted SearxNG. Aggregates Google, Bing, DuckDuckGo, Brave. Returns title/url/snippet. Zero API key required."
---

# ask-search

Web search powered by [SearxNG](https://github.com/searxng/searxng). Aggregates multiple search engines, zero API key, full privacy.

## Usage

```bash
ask-search "your query"                    # top 10 results
ask-search "query" --num 5                 # limit results
ask-search "AI news" --categories news     # news only
ask-search "query" --lang zh-CN            # Chinese results
ask-search "query" --urls-only             # URL list (pipe to web_fetch)
ask-search "query" --json                  # raw JSON
```

## Agent Workflow

1. Run `ask-search "topic"` to get candidates
2. Check snippet — if enough, answer directly
3. If snippet truncated, use `web_fetch` on the URL for full content

## Parameters

| Flag | Short | Description |
|------|-------|-------------|
| `--num N` | `-n` | Max results (default 10) |
| `--engines` | `-e` | google,bing,duckduckgo,brave |
| `--lang` | `-l` | zh-CN, en, ja, ko |
| `--categories` | `-c` | general,news,images,science |
| `--json` | `-j` | Raw JSON output |
| `--urls-only` | `-u` | URLs only |

## Setup

Requires SearxNG running locally. Set `SEARXNG_URL` if not on default port 8080.
