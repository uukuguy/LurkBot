"""Memory tools - memory_search and memory_get.

Ported from moltbot's memory tools.

These are P1 tools that provide:
- memory_search: Semantic search through memory files
- memory_get: Read specific content from memory files
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

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

DEFAULT_MAX_RESULTS = 10
DEFAULT_MIN_SCORE = 0.0
DEFAULT_MAX_LINES = 100
MEMORY_FILE_PATTERN = re.compile(r"^MEMORY\.md$|^memory/.*\.md$", re.IGNORECASE)


# =============================================================================
# Memory Manager Interface
# =============================================================================


@dataclass
class MemorySearchResult:
    """Single memory search result."""

    path: str
    content: str
    score: float
    line_start: int | None = None
    line_end: int | None = None


@dataclass
class MemorySearchConfig:
    """Configuration for memory search."""

    enabled: bool = True
    root_dir: str | None = None
    max_results: int = DEFAULT_MAX_RESULTS
    min_score: float = DEFAULT_MIN_SCORE
    # Embedding provider for semantic search
    provider: Literal["openai", "local", "keyword"] = "keyword"
    model: str | None = None
    api_key: str | None = None


class MemoryManager:
    """Manager for memory file operations.

    This is a framework implementation using keyword-based search.
    For production semantic search, integrate with an embedding provider.
    """

    def __init__(self, config: MemorySearchConfig) -> None:
        self.config = config
        self._files_cache: dict[str, list[str]] | None = None

    def _get_memory_root(self) -> Path:
        """Get the root directory for memory files."""
        if self.config.root_dir:
            return Path(self.config.root_dir)
        return Path.cwd()

    def _find_memory_files(self) -> list[Path]:
        """Find all memory files in the root directory."""
        root = self._get_memory_root()
        files: list[Path] = []

        # Check MEMORY.md at root
        memory_md = root / "MEMORY.md"
        if memory_md.exists() and memory_md.is_file():
            files.append(memory_md)

        # Check memory/ directory
        memory_dir = root / "memory"
        if memory_dir.exists() and memory_dir.is_dir():
            for f in memory_dir.glob("**/*.md"):
                if f.is_file():
                    files.append(f)

        return files

    def _read_file_lines(self, path: Path) -> list[str]:
        """Read file and return lines."""
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []

    def _keyword_search(
        self,
        query: str,
        max_results: int,
    ) -> list[MemorySearchResult]:
        """Perform keyword-based search.

        This is a simple implementation. For better results,
        use embedding-based semantic search.
        """
        results: list[MemorySearchResult] = []
        root = self._get_memory_root()
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for file_path in self._find_memory_files():
            lines = self._read_file_lines(file_path)
            if not lines:
                continue

            rel_path = str(file_path.relative_to(root))

            # Score each section (paragraphs separated by blank lines)
            current_section_start = 0
            current_section_lines: list[str] = []

            for i, line in enumerate(lines):
                if line.strip():
                    if not current_section_lines:
                        current_section_start = i
                    current_section_lines.append(line)
                else:
                    if current_section_lines:
                        # Score this section
                        section_text = "\n".join(current_section_lines)
                        score = self._compute_keyword_score(section_text, query_lower, query_words)
                        if score > 0:
                            results.append(MemorySearchResult(
                                path=rel_path,
                                content=section_text,
                                score=score,
                                line_start=current_section_start + 1,
                                line_end=i,
                            ))
                        current_section_lines = []

            # Don't forget the last section
            if current_section_lines:
                section_text = "\n".join(current_section_lines)
                score = self._compute_keyword_score(section_text, query_lower, query_words)
                if score > 0:
                    results.append(MemorySearchResult(
                        path=rel_path,
                        content=section_text,
                        score=score,
                        line_start=current_section_start + 1,
                        line_end=len(lines),
                    ))

        # Sort by score descending and limit results
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    def _compute_keyword_score(
        self,
        text: str,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Compute keyword match score."""
        text_lower = text.lower()

        # Exact phrase match gives highest score
        if query_lower in text_lower:
            return 1.0

        # Word overlap score
        text_words = set(text_lower.split())
        overlap = len(query_words & text_words)
        if overlap == 0:
            return 0.0

        return overlap / len(query_words) * 0.8

    async def search(
        self,
        query: str,
        max_results: int | None = None,
        min_score: float | None = None,
    ) -> list[MemorySearchResult]:
        """Search memory files.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        Returns:
            List of search results
        """
        max_results = max_results or self.config.max_results
        min_score = min_score if min_score is not None else self.config.min_score

        # Use keyword search by default
        # TODO: Implement embedding-based search for semantic matching
        results = self._keyword_search(query, max_results * 2)

        # Filter by min_score
        filtered = [r for r in results if r.score >= min_score]

        return filtered[:max_results]

    async def read_file(
        self,
        rel_path: str,
        from_line: int | None = None,
        lines: int | None = None,
    ) -> dict[str, Any]:
        """Read content from a memory file.

        Args:
            rel_path: Relative path to the file
            from_line: Starting line number (1-indexed)
            lines: Number of lines to read

        Returns:
            Dict with path, text, and metadata
        """
        root = self._get_memory_root()
        file_path = root / rel_path

        # Security: ensure path is within root
        try:
            resolved = file_path.resolve()
            root_resolved = root.resolve()
            if not str(resolved).startswith(str(root_resolved)):
                return {
                    "path": rel_path,
                    "text": "",
                    "error": "Path escapes memory root",
                }
        except Exception:
            return {
                "path": rel_path,
                "text": "",
                "error": "Invalid path",
            }

        # Check if file exists and is a memory file
        if not file_path.exists():
            return {
                "path": rel_path,
                "text": "",
                "error": "File not found",
            }

        if not file_path.is_file():
            return {
                "path": rel_path,
                "text": "",
                "error": "Not a file",
            }

        # Read file
        try:
            all_lines = file_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            return {
                "path": rel_path,
                "text": "",
                "error": str(e),
            }

        total_lines = len(all_lines)

        # Handle line range
        start_idx = 0
        if from_line is not None:
            start_idx = max(0, from_line - 1)

        end_idx = total_lines
        if lines is not None:
            end_idx = min(total_lines, start_idx + lines)
        else:
            end_idx = min(total_lines, start_idx + DEFAULT_MAX_LINES)

        selected = all_lines[start_idx:end_idx]
        text = "\n".join(selected)

        return {
            "path": rel_path,
            "text": text,
            "totalLines": total_lines,
            "fromLine": start_idx + 1,
            "toLine": end_idx,
            "truncated": end_idx < total_lines,
        }

    def status(self) -> dict[str, Any]:
        """Get memory manager status."""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "enabled": self.config.enabled,
        }


# =============================================================================
# Global Memory Manager
# =============================================================================

_memory_manager: MemoryManager | None = None


def get_memory_manager(config: MemorySearchConfig | None = None) -> MemoryManager:
    """Get or create the memory manager instance."""
    global _memory_manager
    if _memory_manager is None or config is not None:
        _memory_manager = MemoryManager(config or MemorySearchConfig())
    return _memory_manager


# =============================================================================
# Memory Search Tool
# =============================================================================


class MemorySearchParams(BaseModel):
    """Parameters for memory_search tool."""

    query: str = Field(description="Search query")
    max_results: int | None = Field(
        default=None,
        alias="maxResults",
        description="Maximum number of results",
    )
    min_score: float | None = Field(
        default=None,
        alias="minScore",
        description="Minimum score threshold (0.0-1.0)",
    )

    model_config = {"populate_by_name": True}


async def memory_search_tool(
    params: dict[str, Any],
    config: MemorySearchConfig | None = None,
) -> ToolResult:
    """Search memory files.

    Mandatory recall step: semantically search MEMORY.md + memory/*.md
    before answering questions about prior work, decisions, dates,
    people, preferences, or todos.

    Args:
        params: Tool parameters
        config: Memory configuration

    Returns:
        ToolResult with search results
    """
    config = config or MemorySearchConfig()

    if not config.enabled:
        return json_result({
            "results": [],
            "disabled": True,
            "error": "memory_search is disabled",
        })

    query = read_string_param(params, "query", required=True)
    if not query:
        return error_result("query required")

    max_results = read_number_param(params, "maxResults", integer=True)
    min_score = read_number_param(params, "minScore")

    manager = get_memory_manager(config)

    try:
        results = await manager.search(
            query,
            max_results=max_results,
            min_score=min_score,
        )

        status = manager.status()

        return json_result({
            "results": [
                {
                    "path": r.path,
                    "content": r.content,
                    "score": r.score,
                    "lineStart": r.line_start,
                    "lineEnd": r.line_end,
                }
                for r in results
            ],
            "provider": status["provider"],
            "model": status["model"],
        })

    except Exception as e:
        return json_result({
            "results": [],
            "disabled": True,
            "error": str(e),
        })


# =============================================================================
# Memory Get Tool
# =============================================================================


class MemoryGetParams(BaseModel):
    """Parameters for memory_get tool."""

    path: str = Field(description="Relative path to memory file")
    from_line: int | None = Field(
        default=None,
        alias="from",
        description="Starting line number (1-indexed)",
    )
    lines: int | None = Field(
        default=None,
        description="Number of lines to read",
    )

    model_config = {"populate_by_name": True}


async def memory_get_tool(
    params: dict[str, Any],
    config: MemorySearchConfig | None = None,
) -> ToolResult:
    """Read content from a memory file.

    Safe snippet read from MEMORY.md or memory/*.md with optional
    from/lines; use after memory_search to pull only the needed
    lines and keep context small.

    Args:
        params: Tool parameters
        config: Memory configuration

    Returns:
        ToolResult with file content
    """
    config = config or MemorySearchConfig()

    if not config.enabled:
        return json_result({
            "path": "",
            "text": "",
            "disabled": True,
            "error": "memory_get is disabled",
        })

    rel_path = read_string_param(params, "path", required=True)
    if not rel_path:
        return error_result("path required")

    from_line = read_number_param(params, "from", integer=True)
    lines = read_number_param(params, "lines", integer=True)

    manager = get_memory_manager(config)

    try:
        result = await manager.read_file(
            rel_path,
            from_line=from_line,
            lines=lines,
        )
        return json_result(result)

    except Exception as e:
        return json_result({
            "path": rel_path,
            "text": "",
            "disabled": True,
            "error": str(e),
        })


# =============================================================================
# Tool Registration Helpers
# =============================================================================


def create_memory_search_tool() -> dict[str, Any]:
    """Create memory_search tool definition for PydanticAI."""
    return {
        "name": "memory_search",
        "label": "Memory Search",
        "description": (
            "Mandatory recall step: semantically search MEMORY.md + memory/*.md "
            "(and optional session transcripts) before answering questions about "
            "prior work, decisions, dates, people, preferences, or todos; "
            "returns top snippets with path + lines."
        ),
        "parameters": MemorySearchParams.model_json_schema(),
    }


def create_memory_get_tool() -> dict[str, Any]:
    """Create memory_get tool definition for PydanticAI."""
    return {
        "name": "memory_get",
        "label": "Memory Get",
        "description": (
            "Safe snippet read from MEMORY.md or memory/*.md with optional "
            "from/lines; use after memory_search to pull only the needed "
            "lines and keep context small."
        ),
        "parameters": MemoryGetParams.model_json_schema(),
    }
