# Agents Overview

Agents are the AI brains of LurkBot. They process messages, maintain context, and execute tools on behalf of users.

## Supported AI Models

LurkBot supports multiple AI providers:

| Provider | Models | Status |
|----------|--------|--------|
| [Anthropic](models.md#anthropic) | Claude 3.5, Claude 3 | ✅ Recommended |
| [OpenAI](models.md#openai) | GPT-4o, GPT-4, GPT-3.5 | ✅ Supported |
| [Google](models.md#google) | Gemini Pro, Gemini Flash | ✅ Supported |
| [Ollama](models.md#ollama) | Llama, Mistral, etc. | ✅ Local |

## Quick Configuration

Set your default model:

```bash
# Use Claude (recommended)
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514

# Or GPT-4o
LURKBOT_DEFAULT_MODEL=gpt-4o

# Or Gemini
LURKBOT_DEFAULT_MODEL=gemini-pro
```

## Key Concepts

### Sessions

[Sessions](sessions.md) represent individual conversations:

- Each session has its own context and history
- Sessions can be isolated (sandboxed) for security
- Sessions persist across restarts

### Subagents

[Subagents](subagents.md) are specialized agents for specific tasks:

- Code execution
- Web browsing
- File operations
- And more

### Tool Execution

Agents can execute [tools](../tools/index.md) to perform actions:

- Run shell commands
- Read/write files
- Browse the web
- Send messages

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `DEFAULT_MODEL` | Default AI model | `claude-sonnet-4-20250514` |
| `MAX_TOKENS` | Max response tokens | `4096` |
| `TEMPERATURE` | Response randomness | `0.7` |
| `SYSTEM_PROMPT` | Custom system prompt | (built-in) |

## Next Steps

- [AI Models](models.md) - Configure AI providers
- [Sessions](sessions.md) - Understand session management
- [Subagents](subagents.md) - Learn about specialized agents
- [Tools](../tools/index.md) - See available tools
