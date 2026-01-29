"""Web tools - web_search and web_fetch.

Ported from moltbot's web tools.

These are P1 tools that provide:
- web_search: Search the web using various search providers
- web_fetch: Fetch and extract content from web pages
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from lurkbot.tools.builtin.common import (
    ToolResult,
    error_result,
    json_result,
    read_number_param,
    read_string_param,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_FETCH_MAX_CHARS = 50_000
DEFAULT_FETCH_MAX_REDIRECTS = 3
DEFAULT_SEARCH_MAX_RESULTS = 10
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CACHE_TTL_MINUTES = 15
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


# =============================================================================
# Cache
# =============================================================================


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    data: Any
    expires_at: float


_fetch_cache: dict[str, CacheEntry] = {}
_search_cache: dict[str, CacheEntry] = {}


def normalize_cache_key(url: str) -> str:
    """Normalize URL for cache key."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def read_cache(cache: dict[str, CacheEntry], key: str) -> Any | None:
    """Read from cache if not expired."""
    entry = cache.get(key)
    if entry and entry.expires_at > time.time():
        return entry.data
    return None


def write_cache(
    cache: dict[str, CacheEntry],
    key: str,
    data: Any,
    ttl_minutes: int = DEFAULT_CACHE_TTL_MINUTES,
) -> None:
    """Write to cache with TTL."""
    cache[key] = CacheEntry(
        data=data,
        expires_at=time.time() + ttl_minutes * 60,
    )


# =============================================================================
# Content Extraction
# =============================================================================


def html_to_markdown(html_content: str, max_chars: int = DEFAULT_FETCH_MAX_CHARS) -> str:
    """Convert HTML to markdown-like text.

    This is a simplified implementation. For production use,
    consider using a library like html2text or readability.
    """
    # Remove script and style elements
    content = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements
    # Headers
    content = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<h[456][^>]*>(.*?)</h[456]>", r"\n#### \1\n", content, flags=re.DOTALL | re.IGNORECASE)

    # Links
    content = re.sub(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", content, flags=re.DOTALL | re.IGNORECASE)

    # Bold and italic
    content = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", content, flags=re.DOTALL | re.IGNORECASE)

    # Lists
    content = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", content, flags=re.DOTALL | re.IGNORECASE)

    # Paragraphs and line breaks
    content = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<hr\s*/?>", "\n---\n", content, flags=re.IGNORECASE)

    # Code blocks
    content = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", content, flags=re.DOTALL | re.IGNORECASE)

    # Remove remaining HTML tags
    content = re.sub(r"<[^>]+>", "", content)

    # Decode HTML entities
    content = html.unescape(content)

    # Clean up whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"[ \t]+", " ", content)
    content = content.strip()

    # Truncate if needed
    if len(content) > max_chars:
        content = content[:max_chars] + "..."

    return content


def markdown_to_text(markdown: str) -> str:
    """Convert markdown to plain text."""
    text = markdown

    # Remove markdown links
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove markdown formatting
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove headers
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    return text


# =============================================================================
# Web Fetch Tool
# =============================================================================


class WebFetchParams(BaseModel):
    """Parameters for web_fetch tool."""

    url: str = Field(description="HTTP or HTTPS URL to fetch")
    extract_mode: Literal["markdown", "text"] | None = Field(
        default=None,
        alias="extractMode",
        description='Extraction mode ("markdown" or "text")',
    )
    max_chars: int | None = Field(
        default=None,
        alias="maxChars",
        description="Maximum characters to return",
    )

    model_config = {"populate_by_name": True}


@dataclass
class WebFetchConfig:
    """Configuration for web fetch."""

    enabled: bool = True
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_chars: int = DEFAULT_FETCH_MAX_CHARS
    max_redirects: int = DEFAULT_FETCH_MAX_REDIRECTS
    user_agent: str = DEFAULT_USER_AGENT
    cache_ttl_minutes: int = DEFAULT_CACHE_TTL_MINUTES


async def web_fetch_tool(
    params: dict[str, Any],
    config: WebFetchConfig | None = None,
) -> ToolResult:
    """Fetch and extract content from a web page.

    Args:
        params: Tool parameters
        config: Fetch configuration

    Returns:
        ToolResult with extracted content
    """
    config = config or WebFetchConfig()

    if not config.enabled:
        return error_result("web_fetch is disabled")

    url = read_string_param(params, "url", required=True)
    if not url:
        return error_result("url required")

    # Validate URL
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return error_result("Invalid URL: must be http or https")
    except Exception:
        return error_result("Invalid URL format")

    extract_mode = read_string_param(params, "extractMode") or "markdown"
    if extract_mode not in ("markdown", "text"):
        extract_mode = "markdown"

    max_chars = read_number_param(params, "maxChars", integer=True)
    if max_chars is None or max_chars < 100:
        max_chars = config.max_chars

    # Check cache
    cache_key = normalize_cache_key(f"{url}:{extract_mode}:{max_chars}")
    cached = read_cache(_fetch_cache, cache_key)
    if cached:
        return json_result({**cached, "cached": True})

    # Fetch URL
    try:
        async with httpx.AsyncClient(
            timeout=config.timeout_seconds,
            follow_redirects=True,
            max_redirects=config.max_redirects,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": config.user_agent},
            )

        if response.status_code >= 400:
            return error_result(f"HTTP error: {response.status_code}")

        content_type = response.headers.get("content-type", "")

        # Check if HTML
        if "text/html" in content_type:
            html_content = response.text
            if extract_mode == "text":
                extracted = markdown_to_text(html_to_markdown(html_content, max_chars))
            else:
                extracted = html_to_markdown(html_content, max_chars)
        else:
            # Return raw text for non-HTML
            extracted = response.text[:max_chars]
            if len(response.text) > max_chars:
                extracted += "..."

        result = {
            "url": str(response.url),
            "status": response.status_code,
            "contentType": content_type,
            "extractMode": extract_mode,
            "content": extracted,
            "chars": len(extracted),
            "truncated": len(extracted) >= max_chars,
        }

        # Cache result
        write_cache(_fetch_cache, cache_key, result, config.cache_ttl_minutes)

        return json_result(result)

    except httpx.TimeoutException:
        return error_result(f"Request timed out after {config.timeout_seconds}s")
    except httpx.TooManyRedirects:
        return error_result(f"Too many redirects (max {config.max_redirects})")
    except httpx.RequestError as e:
        return error_result(f"Request failed: {e}")
    except Exception as e:
        return error_result(f"Fetch error: {e}")


# =============================================================================
# Web Search Tool
# =============================================================================


class WebSearchParams(BaseModel):
    """Parameters for web_search tool."""

    query: str = Field(description="Search query")
    max_results: int | None = Field(
        default=None,
        alias="maxResults",
        description="Maximum number of results",
    )

    model_config = {"populate_by_name": True}


@dataclass
class SearchResult:
    """Single search result."""

    title: str
    url: str
    snippet: str


@dataclass
class WebSearchConfig:
    """Configuration for web search."""

    enabled: bool = True
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    cache_ttl_minutes: int = DEFAULT_CACHE_TTL_MINUTES
    # Search provider configuration
    provider: Literal["tavily", "serper", "mock"] = "mock"
    api_key: str | None = None


async def web_search_tool(
    params: dict[str, Any],
    config: WebSearchConfig | None = None,
) -> ToolResult:
    """Search the web.

    Note: This is a framework implementation. For production use,
    configure with a real search provider (Tavily, Serper, etc.)

    Args:
        params: Tool parameters
        config: Search configuration

    Returns:
        ToolResult with search results
    """
    config = config or WebSearchConfig()

    if not config.enabled:
        return error_result("web_search is disabled")

    query = read_string_param(params, "query", required=True)
    if not query:
        return error_result("query required")

    max_results = read_number_param(params, "maxResults", integer=True)
    if max_results is None or max_results < 1:
        max_results = config.max_results

    # Check cache
    cache_key = normalize_cache_key(f"search:{query}:{max_results}")
    cached = read_cache(_search_cache, cache_key)
    if cached:
        return json_result({**cached, "cached": True})

    # Use configured search provider
    if config.provider == "tavily" and config.api_key:
        results = await _search_tavily(query, max_results, config.api_key, config.timeout_seconds)
    elif config.provider == "serper" and config.api_key:
        results = await _search_serper(query, max_results, config.api_key, config.timeout_seconds)
    else:
        # Mock results for development
        results = _search_mock(query, max_results)

    result_data = {
        "query": query,
        "provider": config.provider,
        "count": len(results),
        "results": [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in results
        ],
    }

    # Cache result
    write_cache(_search_cache, cache_key, result_data, config.cache_ttl_minutes)

    return json_result(result_data)


async def _search_tavily(
    query: str,
    max_results: int,
    api_key: str,
    timeout: int,
) -> list[SearchResult]:
    """Search using Tavily API."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "max_results": max_results,
                    "api_key": api_key,
                },
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results: list[SearchResult] = []

            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                ))

            return results[:max_results]

    except Exception:
        return []


async def _search_serper(
    query: str,
    max_results: int,
    api_key: str,
    timeout: int,
) -> list[SearchResult]:
    """Search using Serper API."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key},
                json={"q": query, "num": max_results},
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results: list[SearchResult] = []

            for item in data.get("organic", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                ))

            return results[:max_results]

    except Exception:
        return []


def _search_mock(query: str, max_results: int) -> list[SearchResult]:
    """Generate mock search results for development."""
    return [
        SearchResult(
            title=f"Mock result for: {query}",
            url=f"https://example.com/search?q={query.replace(' ', '+')}",
            snippet=f"This is a mock search result for the query '{query}'. "
                    "Configure a real search provider (Tavily, Serper) for production use.",
        )
    ][:max_results]


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_web_fetch_tool() -> dict[str, Any]:
    """Create web_fetch tool definition for PydanticAI."""
    return {
        "name": "web_fetch",
        "label": "Web Fetch",
        "description": (
            "Fetch and extract content from a web page. "
            "Returns content in markdown or plain text format. "
            "Supports caching to reduce redundant requests."
        ),
        "parameters": WebFetchParams.model_json_schema(),
    }


def create_web_search_tool() -> dict[str, Any]:
    """Create web_search tool definition for PydanticAI."""
    return {
        "name": "web_search",
        "label": "Web Search",
        "description": (
            "Search the web for information. "
            "Returns a list of search results with titles, URLs, and snippets."
        ),
        "parameters": WebSearchParams.model_json_schema(),
    }
