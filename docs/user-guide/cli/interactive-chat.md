# Interactive Chat

The interactive chat mode provides a rich terminal interface for conversing with AI models.

## Starting a Chat

```bash
lurkbot agent chat
```

You'll see a prompt where you can type messages:

```
LurkBot Chat (type 'exit' to quit)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You:
```

## Chat Commands

While in chat mode, you can use special commands:

| Command | Description |
|---------|-------------|
| `exit` or `quit` | Exit chat mode |
| `/clear` | Clear conversation history |
| `/model <name>` | Switch AI model |
| `/session <id>` | Switch session |
| `/tools` | List available tools |
| `/help` | Show help |

## Features

### Streaming Responses

Responses stream in real-time as the AI generates them:

```
You: Write a haiku about coding

Claude: Lines of logic flow
         Bugs emerge from shadowed depths
         Debug, compile, run
```

### Tool Execution

The AI can execute tools on your behalf:

```
You: What files are in the current directory?

Claude: Let me check that for you.

[Executing: bash ls -la]

Here are the files in the current directory:
- README.md
- src/
- tests/
- pyproject.toml
```

### Multi-turn Conversations

Context is maintained across messages:

```
You: What is Python?

Claude: Python is a high-level programming language...

You: What are its main features?

Claude: Building on what I mentioned, Python's main features include:
1. Easy to read syntax
2. Dynamic typing
3. ...
```

### Code Highlighting

Code blocks are syntax-highlighted:

```
You: Show me a Python hello world

Claude: Here's a simple Python hello world:

```python
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Ctrl+C` | Cancel current response |
| `Ctrl+D` | Exit chat |
| `Up/Down` | Navigate history |

## Session Persistence

Conversations are automatically saved and can be resumed:

```bash
# Start with a named session
lurkbot agent chat --session my-project

# Resume later
lurkbot agent chat --session my-project
```

Session files are stored in `~/.lurkbot/sessions/`.

## Model Selection

Switch models during chat:

```
You: /model gpt-4o

Switched to model: gpt-4o

You: Hello!

GPT-4o: Hello! How can I help you today?
```

Or start with a specific model:

```bash
lurkbot agent chat --model claude-sonnet-4-20250514
```

## Tool Control

Disable tools for a safer chat:

```bash
lurkbot agent chat --no-tools
```

Or control specific tools:

```
You: /tools disable bash

Disabled tool: bash

You: /tools enable bash

Enabled tool: bash
```

## Output Formats

### Default (Rich)

Full formatting with colors and styling.

### Plain Text

```bash
lurkbot agent chat --plain
```

No colors or special formatting.

### JSON Output

```bash
lurkbot agent chat --output json
```

Each response is output as JSON for scripting.

## Tips

1. **Be specific**: Clear prompts get better responses
2. **Use context**: Reference previous messages
3. **Check tools**: Use `/tools` to see what's available
4. **Save sessions**: Use named sessions for projects

## Troubleshooting

### "Connection refused"

The gateway must be running:

```bash
lurkbot gateway start
```

### "Model not available"

Check your API key is set:

```bash
echo $LURKBOT_ANTHROPIC_API_KEY
```

### Slow responses

Try a faster model:

```bash
lurkbot agent chat --model claude-haiku-3-5-20241022
```

---

## See Also

- [CLI Commands](commands.md) - All CLI commands
- [AI Models](../agents/models.md) - Model configuration
- [Sessions](../agents/sessions.md) - Session management
