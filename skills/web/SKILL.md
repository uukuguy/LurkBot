---
name: web
description: Search the web and fetch content from URLs using configurable providers (Tavily, Serper) or mock results.
metadata: {"moltbot":{"emoji":"🌐"}}
---

# Web Tools

Search the web for current information and fetch content from URLs.

## Available Tools

- `web_search` - Search the web using configured providers (Tavily, Serper, or mock)
- `web_fetch` - Fetch and extract content from web pages

## Quick Examples

### Search the web

```bash
{
  "query": "Python async programming best practices",
  "maxResults": 5
}
```

Returns list of results with title, URL, and snippet.

### Fetch web page content

```bash
{
  "url": "https://example.com/article",
  "extractMode": "markdown",  # or "text"
  "maxChars": 50000
}
```

Returns extracted content in markdown or plain text format.

## Search Providers

**Mock** (default for development):
- No API key required
- Returns placeholder results
- Good for testing

**Tavily** (recommended for production):
- Configure with API key in config
- High-quality search results
- Rate limits apply

**Serper** (alternative):
- Google search via Serper API
- Configure with API key
- Good for general queries

## Use Cases

**Current information**: Find latest news, documentation, or data beyond AI's knowledge cutoff.

**Research**: Gather information from multiple sources for comprehensive analysis.

**Content extraction**: Pull article text, documentation, or specific web page content.

**Verification**: Check facts or get up-to-date information.

## Parameters

### web_search

- `query` (required) - Search query string
- `maxResults` (optional) - Maximum results (default: 10)

### web_fetch

- `url` (required) - HTTP or HTTPS URL to fetch
- `extractMode` (optional) - "markdown" (default) or "text"
- `maxChars` (optional) - Max characters to return (default: 50000)

## Features

**Caching**: Both tools cache results for 15 minutes to reduce redundant requests.

**HTML to Markdown**: web_fetch converts HTML to readable markdown format automatically.

**Content extraction**: Strips scripts, styles, and focuses on main content.

**Timeout handling**: Configurable timeouts (default: 30 seconds).

**Redirect following**: Automatically follows redirects (max: 3).

## Best Practices

**Specific queries**: Use detailed search terms for better results.

**Site filters**: Include `site:domain.com` to search specific sites.

**Date ranges**: Mention time constraints when searching for recent info.

**Extract mode**: Use "markdown" for structured content, "text" for plain text.

**Respect rate limits**: Cache helps, but be mindful of API quotas.

## Configuration

Set provider and API keys in config:

```python
WebSearchConfig(
    provider="tavily",  # or "serper", "mock"
    api_key="your-api-key",
    max_results=10,
    timeout_seconds=30
)
```

## Tips

- Mock provider returns placeholder results—configure a real provider for production
- Cached results include `"cached": true` in response
- web_fetch works best with HTML pages; JSON/XML returned as-is
- Both tools validate URLs for http/https schemes only

## Related Skills

- `memory` - Combine web search with memory search
- `github` - Use GitHub CLI for repository-specific searches
- `web-search` - Alternative skill using free tools (ddgr, SearXNG)
