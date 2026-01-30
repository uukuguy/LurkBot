# Discord Channel

Connect LurkBot to Discord using the Discord Bot API.

## Prerequisites

- A Discord account
- A Discord server where you have admin permissions
- LurkBot installed and configured

## Step 1: Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Enter a name (e.g., "LurkBot")
4. Click "Create"

## Step 2: Create a Bot

1. In your application, go to "Bot" section
2. Click "Add Bot"
3. Under "Token", click "Copy" to get your bot token

> [!IMPORTANT]
> Keep your bot token secret! Anyone with this token can control your bot.

## Step 3: Configure Bot Settings

In the Bot section:

1. **Privileged Gateway Intents**:
   - Enable "Message Content Intent" (required to read messages)
   - Enable "Server Members Intent" (optional, for member info)

2. **Bot Permissions**:
   - Send Messages
   - Read Message History
   - Add Reactions (optional)

## Step 4: Invite Bot to Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes:
   - `bot`
   - `applications.commands` (optional, for slash commands)
3. Select permissions:
   - Send Messages
   - Read Message History
   - Add Reactions
4. Copy the generated URL
5. Open URL in browser and select your server

## Step 5: Configure LurkBot

Add the bot token to your configuration:

=== "Environment Variable"

    ```bash
    export LURKBOT_DISCORD__BOT_TOKEN=MTIzNDU2Nzg5...
    export LURKBOT_DISCORD__ENABLED=true
    ```

=== "Configuration File"

    Add to `~/.lurkbot/.env`:
    ```bash
    LURKBOT_DISCORD__BOT_TOKEN=MTIzNDU2Nzg5...
    LURKBOT_DISCORD__ENABLED=true
    ```

## Step 6: Configure Allowlist

Get your Discord user ID:

1. Enable Developer Mode in Discord settings
2. Right-click your username → "Copy ID"

```bash
LURKBOT_DISCORD__ALLOWLIST=123456789012345678
```

## Step 7: Start the Gateway

```bash
lurkbot gateway start
```

You should see:

```
INFO     | Gateway starting on ws://127.0.0.1:18789
INFO     | Discord channel connected: LurkBot#1234
INFO     | Gateway ready
```

## Configuration Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `BOT_TOKEN` | Discord bot token | Required |
| `ENABLED` | Enable/disable channel | `false` |
| `ALLOWLIST` | Allowed user IDs | Empty |

### Server Options

| Option | Description | Default |
|--------|-------------|---------|
| `ALLOWED_GUILDS` | Allowed server IDs | Empty (all) |
| `ALLOWED_CHANNELS` | Allowed channel IDs | Empty (all) |
| `MENTION_GATING` | Require @mention | `true` |

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `PRESENCE` | Bot status message | None |
| `ACTIVITY_TYPE` | Activity type | `playing` |
| `DM_ENABLED` | Allow DMs | `true` |

## Mention Gating

By default, Discord requires @mention to respond:

```bash
LURKBOT_DISCORD__MENTION_GATING=true
```

With this enabled:

```
User: @LurkBot what's 2+2?
Bot: 2+2 equals 4.

User: what's 2+2?
(no response - not mentioned)
```

## Server and Channel Restrictions

### Allow Specific Servers

```bash
LURKBOT_DISCORD__ALLOWED_GUILDS=123456789012345678,987654321098765432
```

### Allow Specific Channels

```bash
LURKBOT_DISCORD__ALLOWED_CHANNELS=123456789012345678
```

## Slash Commands (Optional)

Enable Discord slash commands:

```bash
LURKBOT_DISCORD__SLASH_COMMANDS=true
```

Available commands:

- `/chat <message>` - Send a message to LurkBot
- `/clear` - Clear conversation history
- `/model <name>` - Change AI model

## Thread Support

LurkBot can respond in Discord threads:

```bash
LURKBOT_DISCORD__THREAD_SUPPORT=true
```

Each thread maintains its own conversation context.

## Troubleshooting

### "Invalid Token"

1. Regenerate token in Developer Portal
2. Make sure you copied the full token

### "Missing Permissions"

1. Re-invite bot with correct permissions
2. Check channel-specific permissions

### "Missing Access" (Message Content)

Enable "Message Content Intent" in Developer Portal:

1. Go to Bot settings
2. Enable "Message Content Intent"
3. Save changes

### Bot doesn't respond

1. Check `MENTION_GATING` setting
2. Verify bot has permission in the channel
3. Check allowlist includes your user ID

## Example Configuration

Complete `.env` example:

```bash
# Discord Channel
LURKBOT_DISCORD__ENABLED=true
LURKBOT_DISCORD__BOT_TOKEN=MTIzNDU2Nzg5...

# Security
LURKBOT_DISCORD__ALLOWLIST=123456789012345678
LURKBOT_DISCORD__ALLOWED_GUILDS=123456789012345678

# Behavior
LURKBOT_DISCORD__MENTION_GATING=true
LURKBOT_DISCORD__DM_ENABLED=true
LURKBOT_DISCORD__THREAD_SUPPORT=true

# Presence
LURKBOT_DISCORD__PRESENCE=Ready to help!
LURKBOT_DISCORD__ACTIVITY_TYPE=listening
```

---

## See Also

- [Channels Overview](index.md) - All supported channels
- [Telegram Setup](telegram.md) - Telegram configuration
- [Slack Setup](slack.md) - Slack configuration
