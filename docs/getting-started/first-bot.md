# Create Your First Bot

This guide walks you through creating a Telegram bot connected to LurkBot.

## Prerequisites

- LurkBot installed and configured ([Installation](installation.md))
- A Telegram account
- An AI provider API key (Anthropic, OpenAI, or Google)

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the prompts:
   - Enter a name for your bot (e.g., "My LurkBot")
   - Enter a username (must end in `bot`, e.g., `my_lurkbot`)
4. BotFather will give you a **bot token** like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

> [!IMPORTANT]
> Keep your bot token secret! Anyone with this token can control your bot.

## Step 2: Configure LurkBot

Add the bot token to your configuration:

### Option A: Environment Variable

```bash
export LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
export LURKBOT_TELEGRAM__ENABLED=true
```

### Option B: Configuration File

Add to `~/.lurkbot/.env`:

```bash
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
LURKBOT_TELEGRAM__ENABLED=true
```

## Step 3: Configure Allowlist (Recommended)

For security, restrict who can use your bot:

```bash
# Get your Telegram user ID
# Send /start to @userinfobot on Telegram

# Add to .env
LURKBOT_TELEGRAM__ALLOWLIST=123456789,987654321
```

## Step 4: Start the Gateway

```bash
make gateway
```

You should see:

```
INFO     | Gateway starting on ws://127.0.0.1:18789
INFO     | Telegram channel connected
INFO     | Gateway ready
```

## Step 5: Test Your Bot

1. Open Telegram
2. Find your bot by username
3. Send `/start` or any message
4. Your bot should respond!

```
You: Hello!

Bot: Hello! I'm LurkBot, your AI assistant. How can I help you today?
```

## Troubleshooting

### Bot doesn't respond

1. Check the Gateway is running:
   ```bash
   lurkbot gateway status
   ```

2. Verify your bot token:
   ```bash
   echo $LURKBOT_TELEGRAM__BOT_TOKEN
   ```

3. Check the logs for errors:
   ```bash
   tail -f ~/.lurkbot/logs/gateway.log
   ```

### "User not in allowlist"

Add your Telegram user ID to the allowlist:

```bash
# Get your ID from @userinfobot
LURKBOT_TELEGRAM__ALLOWLIST=YOUR_USER_ID
```

### "API key not found"

Ensure your AI provider API key is set:

```bash
echo $LURKBOT_ANTHROPIC_API_KEY
```

## Advanced Configuration

### Multiple Channels

You can enable multiple channels simultaneously:

```bash
# Telegram
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=...

# Discord
LURKBOT_DISCORD__ENABLED=true
LURKBOT_DISCORD__BOT_TOKEN=...
```

### Group Chat Support

To use your bot in group chats:

```bash
# Allow specific groups
LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890,-1009876543210

# Require @mention to respond
LURKBOT_TELEGRAM__MENTION_GATING=true
```

### Custom Model

Change the AI model:

```bash
LURKBOT_DEFAULT_MODEL=claude-sonnet-4-20250514
# or
LURKBOT_DEFAULT_MODEL=gpt-4o
```

## Next Steps

- [Core Concepts](concepts.md) - Understand how LurkBot works
- [Channel Configuration](../user-guide/channels/telegram.md) - Advanced Telegram settings
- [Tool Policies](../user-guide/tools/tool-policies.md) - Control what your bot can do
- [Add More Channels](../user-guide/channels/index.md) - Discord, Slack, and more

---

> [!TIP]
> For production use, consider running LurkBot as a daemon. See [Daemon Mode](../advanced/daemon.md).
