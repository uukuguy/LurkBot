# Channels Overview

Channels connect LurkBot to external messaging platforms. Each channel adapter handles platform-specific communication while presenting a unified interface to the rest of the system.

## Supported Channels

| Channel | Platform | Status | Notes |
|---------|----------|--------|-------|
| [Telegram](telegram.md) | Telegram Bot API | ✅ Supported | Most popular |
| [Discord](discord.md) | Discord.js | ✅ Supported | Requires @mention |
| [Slack](slack.md) | Slack Bolt SDK | ✅ Supported | Socket Mode |
| [WhatsApp](more-channels.md#whatsapp) | Baileys | ✅ Supported | QR code pairing |
| [Signal](more-channels.md#signal) | signal-cli | ✅ Supported | CLI-based |
| [iMessage](more-channels.md#imessage) | imsg | ✅ Supported | macOS only |
| [Matrix](more-channels.md#matrix) | matrix-nio | ✅ Supported | Decentralized |
| [MS Teams](more-channels.md#ms-teams) | Bot Framework | ✅ Supported | Enterprise |

## Common Configuration

All channels share these configuration options:

```bash
# Enable/disable a channel
LURKBOT_<CHANNEL>__ENABLED=true

# Channel-specific token
LURKBOT_<CHANNEL>__BOT_TOKEN=...

# User allowlist (comma-separated IDs)
LURKBOT_<CHANNEL>__ALLOWLIST=123456,789012

# Group allowlist
LURKBOT_<CHANNEL>__ALLOWED_GROUPS=-1001234567890

# Require @mention to respond
LURKBOT_<CHANNEL>__MENTION_GATING=true
```

## Channel Features

### Message Handling

Each channel adapter:

- **Receives** messages from the platform
- **Converts** to internal `ChannelMessage` format
- **Routes** through the Gateway to agents
- **Formats** responses for the platform
- **Sends** replies back to users

### Typing Indicators

Channels support typing indicators to show the bot is "thinking":

```python
# Automatic typing while processing
await channel.send_typing(chat_id)
```

### Media Support

Most channels support:

- Text messages
- Images
- Files/documents
- Voice messages (some channels)
- Reactions (some channels)

## Security

### Allowlists

Control who can interact with your bot:

```bash
# Only allow specific users
LURKBOT_TELEGRAM__ALLOWLIST=123456789,987654321

# Only allow specific groups
LURKBOT_TELEGRAM__ALLOWED_GROUPS=-1001234567890
```

### Mention Gating

In group chats, require @mention to respond:

```bash
LURKBOT_TELEGRAM__MENTION_GATING=true
```

This prevents the bot from responding to every message in busy groups.

### Session Isolation

Different contexts have different trust levels:

| Context | Trust Level | Sandbox |
|---------|-------------|---------|
| Owner DM | Full | No |
| Other DM | Partial | Optional |
| Group Chat | Low | Yes |
| Public Channel | None | Yes |

## Quick Setup

### 1. Choose a Channel

Start with [Telegram](telegram.md) - it's the easiest to set up.

### 2. Get Credentials

Each platform requires different credentials:

- **Telegram**: Bot token from @BotFather
- **Discord**: Bot token from Developer Portal
- **Slack**: App token from Slack API

### 3. Configure LurkBot

Add credentials to `~/.lurkbot/.env`:

```bash
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=123456789:ABC...
```

### 4. Start the Gateway

```bash
lurkbot gateway start
```

## Multiple Channels

You can enable multiple channels simultaneously:

```bash
# Telegram
LURKBOT_TELEGRAM__ENABLED=true
LURKBOT_TELEGRAM__BOT_TOKEN=...

# Discord
LURKBOT_DISCORD__ENABLED=true
LURKBOT_DISCORD__BOT_TOKEN=...

# Slack
LURKBOT_SLACK__ENABLED=true
LURKBOT_SLACK__BOT_TOKEN=...
LURKBOT_SLACK__APP_TOKEN=...
```

All channels connect to the same Gateway and share sessions.

## Troubleshooting

### Channel not connecting

1. Check the Gateway is running
2. Verify credentials are correct
3. Check network connectivity
4. Review logs: `tail -f ~/.lurkbot/logs/gateway.log`

### Messages not received

1. Verify allowlist includes your user ID
2. Check mention gating settings
3. Ensure bot has proper permissions

### Slow responses

1. Check AI provider status
2. Try a faster model
3. Review tool execution logs

---

## Next Steps

- [Telegram Setup](telegram.md) - Detailed Telegram configuration
- [Discord Setup](discord.md) - Discord bot setup
- [Slack Setup](slack.md) - Slack app configuration
- [More Channels](more-channels.md) - WhatsApp, Signal, iMessage, etc.
