---
name: web-search
description: Search the web for current information using free search APIs or tools.
metadata: {"moltbot":{"emoji":"🔍","always":true}}
---

# Web Search

Search the web for current information beyond the AI's knowledge cutoff.

## DuckDuckGo (no API key)

Using `ddgr` CLI tool:
```bash
ddgr --num 5 "your search query"
```

Or using curl with DuckDuckGo's instant answer API:
```bash
curl -s "https://api.duckduckgo.com/?q=python+programming&format=json" | jq '.Abstract'
```

## SearXNG (self-hosted or public instances)

Public instances available at: https://searx.space/

Example query:
```bash
curl -s "https://searx.be/search?q=hello+world&format=json" | jq '.results[:5]'
```

## Tips

- Use specific queries for better results
- Include site filter for specific domains: `site:github.com python library`
- Use date ranges when searching for recent info
- Combine multiple search tools for comprehensive results
