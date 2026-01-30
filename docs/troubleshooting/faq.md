# Frequently Asked Questions

Common questions about LurkBot.

## General

### What is LurkBot?

LurkBot is an AI-powered assistant that connects to messaging platforms like Telegram, Discord, and Slack. It uses large language models (Claude, GPT, etc.) to have conversations and execute tasks.

### Is LurkBot free?

LurkBot itself is open source and free. However, you need API keys from AI providers (Anthropic, OpenAI, etc.) which have their own pricing.

### Which AI models are supported?

- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **OpenAI**: GPT-4o, GPT-4, GPT-3.5 Turbo
- **Google**: Gemini Pro, Gemini Flash
- **Ollama**: Any local model (Llama, Mistral, etc.)

### Which messaging platforms are supported?

- Telegram
- Discord
- Slack
- WhatsApp
- Signal
- iMessage (macOS only)
- Matrix
- Microsoft Teams

## Setup

### How do I get started?

1. Install LurkBot: `pip install lurkbot`
2. Set your API key: `export LURKBOT_ANTHROPIC_API_KEY=...`
3. Start the gateway: `lurkbot gateway start`
4. Start chatting: `lurkbot agent chat`

See the [Getting Started](../getting-started/index.md) guide for details.

### Do I need Docker?

Docker is optional. It's only required if you want to use sandbox mode for isolated tool execution.

### Can I run LurkBot on a server?

Yes! Use daemon mode:

```bash
lurkbot gateway start --daemon
```

See [Daemon Mode](../advanced/daemon.md) for production deployment.

## Security

### Is my data secure?

- Messages are processed by your chosen AI provider
- LurkBot doesn't store messages externally
- Session data is stored locally in `~/.lurkbot/`
- Use allowlists to control who can interact with your bot

### Can the AI access my files?

Only if you enable file tools. You can control this with tool policies:

```bash
LURKBOT_DISABLED_TOOLS=bash,write,edit
```

### What is sandbox mode?

Sandbox mode runs tools in isolated Docker containers, preventing them from affecting your system. It's enabled by default for group chats.

## Usage

### How do I add my bot to a group?

1. Add the bot to your group (platform-specific)
2. Add the group ID to your allowlist:
   ```bash
   LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890
   ```
3. Enable mention gating if desired:
   ```bash
   LURKBOT_TELEGRAM__MENTION_GATING=true
   ```

### How do I change the AI model?

```bash
# Environment variable
export LURKBOT_DEFAULT_MODEL=gpt-4o

# Or in chat
/model gpt-4o
```

### How do I clear conversation history?

```bash
# In CLI chat
/clear

# Or via command
lurkbot sessions clear <session_key>
```

### Can I use multiple AI providers?

Yes! You can configure fallback models:

```bash
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514
LURKBOT_FALLBACK_MODELS=gpt-4o,claude-haiku-3-5-20241022
```

## Troubleshooting

### Why isn't my bot responding?

1. Check the gateway is running: `lurkbot gateway status`
2. Verify your allowlist includes your user ID
3. Check mention gating settings
4. Review logs: `tail -f ~/.lurkbot/logs/gateway.log`

### Why are responses slow?

1. Check AI provider status
2. Try a faster model (e.g., Claude Haiku)
3. Reduce context size
4. Check your network connection

### How do I report a bug?

Open an issue on [GitHub](https://github.com/uukuguy/lurkbot/issues) with:

- LurkBot version
- Python version
- Steps to reproduce
- Error messages

## Development

### How do I contribute?

See the [Contributing Guide](../developer/contributing.md).

### How do I create a custom tool?

See [Custom Tools](../developer/extending/custom-tools.md).

### How do I add a new messaging platform?

See [Custom Channels](../developer/extending/custom-channels.md).

### Where can I get help?

- [GitHub Discussions](https://github.com/uukuguy/lurkbot/discussions)
- [GitHub Issues](https://github.com/uukuguy/lurkbot/issues)
- [Documentation](../index.md)

---

## See Also

- [Troubleshooting](index.md) - Common issues
- [Getting Started](../getting-started/index.md) - Setup guide
- [User Guide](../user-guide/index.md) - Complete documentation
