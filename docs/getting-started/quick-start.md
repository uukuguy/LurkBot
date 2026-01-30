# Quick Start

Get LurkBot running in 5 minutes!

## Prerequisites

Before starting, ensure you have:

- [x] LurkBot installed ([Installation Guide](installation.md))
- [x] An API key from Anthropic, OpenAI, or Google

## Step 1: Configure API Key

Set your AI provider API key:

=== "Anthropic (Claude)"

    ```bash
    export LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
    ```

=== "OpenAI (GPT)"

    ```bash
    export LURKBOT_OPENAI_API_KEY=sk-...
    ```

=== "Google (Gemini)"

    ```bash
    export LURKBOT_GOOGLE_API_KEY=...
    ```

Or add to `~/.lurkbot/.env`:

```bash
LURKBOT_ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Step 2: Start the Gateway

The Gateway is LurkBot's central control plane:

```bash
# Using make
make gateway

# Or directly
lurkbot gateway start
```

You should see:

```
INFO     | Gateway starting on ws://127.0.0.1:18789
INFO     | Gateway ready
```

## Step 3: Start Chatting

Open a new terminal and start an interactive chat:

```bash
lurkbot agent chat
```

You'll see a prompt where you can type messages:

```
LurkBot Chat (type 'exit' to quit)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You: Hello! What can you do?

Claude: Hello! I'm LurkBot, an AI assistant. I can help you with:

- Answering questions and having conversations
- Writing and editing code
- Running shell commands
- Browsing the web
- Managing files
- And much more!

What would you like to do today?

You:
```

## Step 4: Try Some Commands

### Ask a Question

```
You: What is the capital of France?
```

### Run a Shell Command

```
You: List the files in the current directory
```

### Write Code

```
You: Write a Python function to calculate fibonacci numbers
```

## What's Next?

Now that you have LurkBot running, you can:

1. **[Create a Telegram Bot](first-bot.md)** - Connect LurkBot to Telegram
2. **[Learn Core Concepts](concepts.md)** - Understand the architecture
3. **[Configure Channels](../user-guide/channels/index.md)** - Add more messaging platforms
4. **[Explore Tools](../user-guide/tools/index.md)** - See what LurkBot can do

## Quick Reference

| Command | Description |
|---------|-------------|
| `lurkbot gateway start` | Start the Gateway server |
| `lurkbot agent chat` | Start interactive chat |
| `lurkbot config show` | Show current configuration |
| `lurkbot --help` | Show all available commands |

## Troubleshooting

### "API key not found"

Make sure your API key is set:

```bash
echo $LURKBOT_ANTHROPIC_API_KEY
```

### "Connection refused"

Ensure the Gateway is running:

```bash
lurkbot gateway start
```

### "Model not available"

Check your API key has access to the model:

```bash
lurkbot config show
```

---

> [!NOTE]
> The Gateway must be running for most LurkBot features to work. Keep it running in a separate terminal or use daemon mode.
