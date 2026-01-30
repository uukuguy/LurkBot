---
name: memory
description: Semantic search and read from MEMORY.md and memory/ directory for prior work, decisions, and context.
metadata: {"moltbot":{"emoji":"🧠"}}
---

# Memory Management

Search and retrieve information from memory files using semantic search and targeted reads.

## Available Tools

- `memory_search` - Semantically search MEMORY.md and memory/*.md files
- `memory_get` - Read specific content from memory files with line ranges

## Quick Examples

### Search for prior decisions

```bash
{
  "query": "why did we choose FastAPI",
  "maxResults": 5,
  "minScore": 0.3
}
```

### Read specific memory content

```bash
{
  "path": "MEMORY.md",
  "from": 45,    # line number (1-indexed)
  "lines": 20    # number of lines to read
}
```

## Memory File Structure

Memory tools search these locations:

```
workspace/
├── MEMORY.md           # Main memory file
└── memory/             # Memory directory
    ├── decisions.md    # Decision records
    ├── todos.md        # Todo items
    ├── meetings.md     # Meeting notes
    └── ...             # Other .md files
```

## Search Strategy

**Current implementation**: Keyword-based search
- Fast, no external dependencies
- Scores: 1.0 for exact phrase match, 0.0-0.8 for word overlap

**Future**: Embedding-based semantic search
- Better semantic understanding
- Requires embedding model configuration

## Use Cases

**Recall decisions**: "Why did we choose technology X?"

**Find todos**: Search for pending tasks and action items.

**Review history**: Look up past project milestones and events.

**Context retrieval**: Get detailed context after search locates relevant sections.

## Parameters

### memory_search

- `query` (required) - Search query string
- `maxResults` (optional) - Maximum results to return (default: 10)
- `minScore` (optional) - Minimum score threshold 0.0-1.0 (default: 0.0)

### memory_get

- `path` (required) - Relative path to memory file (e.g., "MEMORY.md", "memory/decisions.md")
- `from` (optional) - Starting line number (1-indexed)
- `lines` (optional) - Number of lines to read (default: 100)

## Best Practices

**Structure your memory files**: Use clear headings and sections.

**Include timestamps**: Add dates to important records (e.g., "2026-01-15: Decision made").

**Use keywords**: Include searchable terms in important content.

**Search then read**: Use memory_search to locate, then memory_get for detailed content.

**Set appropriate minScore**: Higher score (0.7+) for precise matches, lower (0.3+) for broad search.

## Tips

- Memory tools are read-only (no write access)
- Paths are validated to prevent directory traversal
- Default max: 10 results, 100 lines per read
- Results include line numbers for easy memory_get follow-up

## Related Skills

- `sessions` - Use memory search in subagent sessions
- `web` - Combine web search with memory search for comprehensive results
